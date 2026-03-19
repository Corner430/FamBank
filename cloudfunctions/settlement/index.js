'use strict';
const cloud = require('wx-server-sdk');
cloud.init({ env: cloud.DYNAMIC_CURRENT_ENV });

const {
  getUserByOpenid, requireParent,
  getConnection, query, centsToYuan,
  getConfigValue, calculateCDividend, calculateBInterest, calculateOverflow, getPActive,
  ok, badRequest, serverError
} = require('@fambank/shared');

exports.main = async (event, context) => {
  const { OPENID } = cloud.getWXContext();
  if (!OPENID) return { code: 401, msg: '未授权' };
  const user = await getUserByOpenid(OPENID);
  if (!user) return { code: 401, msg: '用户不存在' };
  requireParent(user);

  try {
    switch (event.action) {
      case 'execute': return await handleExecute(user, event);
      case 'list': return await handleList(user, event);
      default: return badRequest('未知操作');
    }
  } catch (e) {
    if (e.result) return e.result;
    console.error('[settlement]', event.action, e);
    return serverError();
  }
};

async function handleExecute(user, event) {
  const { settlementDate } = event;
  const today = new Date().toISOString().slice(0, 10);
  const settDate = settlementDate || today;

  // Validate settlement date
  if (settDate > today) {
    return badRequest('结算日期不能是未来日期');
  }
  const threeMonthsAgo = new Date();
  threeMonthsAgo.setMonth(threeMonthsAgo.getMonth() - 3);
  const minDate = threeMonthsAgo.toISOString().slice(0, 10);
  if (settDate < minDate) {
    return badRequest('结算日期不能早于3个月前');
  }

  const children = await query(
    'SELECT id, name FROM `user` WHERE family_id = ? AND role = ?',
    [user.family_id, 'child']
  );
  if (children.length === 0) return badRequest('没有孩子可结算');

  // Apply pending announcements first
  const conn = await getConnection();
  try {
    await conn.beginTransaction();
    const [announcements] = await conn.execute(
      'SELECT id, config_key, new_value, effective_from FROM announcement WHERE family_id = ? AND effective_from <= ?',
      [user.family_id, settDate]
    );
    for (const ann of announcements) {
      await conn.execute(
        'INSERT INTO config (family_id, `key`, value, effective_from, announced_at) VALUES (?, ?, ?, ?, ?) ON DUPLICATE KEY UPDATE value = VALUES(value)',
        [user.family_id, ann.config_key, ann.new_value, ann.effective_from, settDate]
      );
    }
    if (announcements.length > 0) {
      await conn.execute('DELETE FROM announcement WHERE family_id = ? AND effective_from <= ?', [user.family_id, settDate]);
    }
    await conn.commit();
  } catch (e) {
    await conn.rollback();
    throw e;
  } finally {
    conn.release();
  }

  const results = [];
  for (const child of children) {
    const result = await settleChild(user.family_id, child.id, child.name, settDate);
    results.push(result);
  }

  return ok({ settlement_date: settDate, results });
}

async function settleChild(familyId, childId, childName, settDate) {
  const conn = await getConnection();
  try {
    // Acquire advisory lock
    const [lockResult] = await conn.execute('SELECT GET_LOCK(?, 10) as locked', [`fambank_settlement_${childId}`]);
    if (!lockResult[0].locked) return { child_id: childId, name: childName, error: '获取锁失败' };

    try {
      // Check duplicate
      const [existing] = await conn.execute(
        'SELECT id FROM settlement WHERE user_id = ? AND settlement_date = ?', [childId, settDate]
      );
      if (existing.length > 0) return { child_id: childId, name: childName, error: '本月已结算' };

      await conn.beginTransaction();

      // Load accounts
      const [accounts] = await conn.execute(
        'SELECT id, account_type, balance, interest_pool, is_interest_suspended, is_deposit_suspended, deposit_suspend_until, last_compliant_purchase_date FROM account WHERE user_id = ? FOR UPDATE',
        [childId]
      );
      const accMap = {};
      for (const a of accounts) accMap[a.account_type] = a;

      const snapshotBefore = {
        A: accMap.A.balance, B: accMap.B.balance,
        B_interest: accMap.B.interest_pool, C: accMap.C.balance,
      };

      let balA = BigInt(accMap.A.balance);
      let balB = BigInt(accMap.B.balance);
      let balBInterest = BigInt(accMap.B.interest_pool);
      let balC = BigInt(accMap.C.balance);

      // Get config
      const cAnnualRate = await getConfigValue(conn, familyId, 'c_annual_rate');
      const tier1Rate = await getConfigValue(conn, familyId, 'b_tier1_rate');
      const tier1Limit = await getConfigValue(conn, familyId, 'b_tier1_limit');
      const tier2Rate = await getConfigValue(conn, familyId, 'b_tier2_rate');
      const tier3Rate = await getConfigValue(conn, familyId, 'b_tier3_rate');
      const bSuspendMonths = await getConfigValue(conn, familyId, 'b_suspend_months');

      // Auto-expire wish lists past valid_until
      await conn.execute(
        'UPDATE wish_list SET status = ? WHERE user_id = ? AND status = ? AND valid_until < CURDATE()',
        ['expired', childId, 'active']
      );

      // Get P_active
      const pActive = await getPActive(conn, childId);

      // === Step 1: C dividend -> A ===
      const dividend = calculateCDividend(balC, cAnnualRate);
      if (dividend > 0n) {
        const oldC = balC; const oldA = balA;
        balC -= dividend; balA += dividend;
        await conn.execute(
          'INSERT INTO transaction_log (family_id, user_id, type, source_account, target_account, amount, balance_before, balance_after, charter_clause, description) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
          [familyId, childId, 'c_dividend', 'C', 'A', dividend.toString(), oldC.toString(), balC.toString(), 'S5', 'C月度派息']
        );
      }

      // === Step 2: B overflow -> C ===
      const { overflowAmount } = calculateOverflow(balB, pActive);
      if (overflowAmount > 0n) {
        const oldB = balB; const oldC2 = balC;
        balB -= overflowAmount; balC += overflowAmount;
        await conn.execute(
          'INSERT INTO transaction_log (family_id, user_id, type, source_account, target_account, amount, balance_before, balance_after, charter_clause, description) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
          [familyId, childId, 'b_overflow', 'B', 'C', overflowAmount.toString(), oldB.toString(), balB.toString(), 'S4.4', 'B溢出转C']
        );
      }

      // === Step 3: B tiered interest -> interest_pool ===
      const isSuspended = !!accMap.B.is_interest_suspended;
      // Check if should suspend: no compliant purchase for b_suspend_months
      let shouldSuspend = isSuspended;
      if (!isSuspended) {
        const lastPurchase = accMap.B.last_compliant_purchase_date;
        if (lastPurchase) {
          const lpDate = new Date(lastPurchase);
          const suspendThreshold = new Date(lpDate);
          suspendThreshold.setDate(suspendThreshold.getDate() + bSuspendMonths * 30);
          if (new Date(settDate) >= suspendThreshold) shouldSuspend = true;
        }
        // Also check wish_list registered_at
        const [wlists] = await conn.execute(
          'SELECT registered_at FROM wish_list WHERE user_id = ? AND status = ? LIMIT 1', [childId, 'active']
        );
        if (wlists.length > 0 && !lastPurchase) {
          const regDate = new Date(wlists[0].registered_at);
          const suspendThreshold = new Date(regDate);
          suspendThreshold.setDate(suspendThreshold.getDate() + bSuspendMonths * 30);
          if (new Date(settDate) >= suspendThreshold) shouldSuspend = true;
        }
      }

      const interest = calculateBInterest(balB, pActive, { tier1Rate, tier1Limit, tier2Rate, tier3Rate }, shouldSuspend);
      if (interest.total > 0n) {
        const oldBi = balBInterest;
        balBInterest += interest.total;
        await conn.execute(
          'INSERT INTO transaction_log (family_id, user_id, type, target_account, amount, balance_before, balance_after, charter_clause, description) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
          [familyId, childId, 'b_interest', 'B_interest', interest.total.toString(), oldBi.toString(), balBInterest.toString(), 'S4.5', 'B月度利息']
        );
      }

      // === Step 4: Violation transfer A -> C ===
      const [violations] = await conn.execute(
        'SELECT id, amount_entered_a FROM violation WHERE user_id = ? AND violation_date >= DATE_SUB(?, INTERVAL 1 MONTH) AND violation_date < ? AND amount_entered_a > 0',
        [childId, settDate, settDate]
      );
      let violationTransfer = 0n;
      for (const v of violations) {
        const enteredA = BigInt(v.amount_entered_a);
        const transfer = balA < enteredA ? balA : enteredA;
        if (transfer > 0n) {
          const oldA = balA; const oldC3 = balC;
          balA -= transfer; balC += transfer;
          violationTransfer += transfer;
          await conn.execute(
            'INSERT INTO transaction_log (family_id, user_id, type, source_account, target_account, amount, balance_before, balance_after, charter_clause, description) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            [familyId, childId, 'violation_transfer', 'A', 'C', transfer.toString(), oldA.toString(), balA.toString(), 'S7', '违约转移A→C']
          );
        }
        // If A insufficient, create debt
        const shortfall = enteredA - transfer;
        if (shortfall > 0n) {
          await conn.execute(
            'INSERT INTO debt (family_id, user_id, original_amount, remaining_amount, reason, violation_id) VALUES (?, ?, ?, ?, ?, ?)',
            [familyId, childId, shortfall.toString(), shortfall.toString(), '违约转移不足', v.id]
          );
        }
      }

      // Check B deposit suspension release
      if (accMap.B.is_deposit_suspended && accMap.B.deposit_suspend_until) {
        const suspendUntil = new Date(accMap.B.deposit_suspend_until);
        if (new Date(settDate) >= suspendUntil) {
          // Release escrows
          const [escrows] = await conn.execute(
            'SELECT id, amount FROM escrow WHERE user_id = ? AND status = ? FOR UPDATE', [childId, 'pending']
          );
          let escrowTotal = 0n;
          for (const esc of escrows) {
            escrowTotal += BigInt(esc.amount);
            await conn.execute('UPDATE escrow SET status = ?, released_at = NOW() WHERE id = ?', ['released', esc.id]);
          }
          if (escrowTotal > 0n) {
            const oldB2 = balB;
            balB += escrowTotal;
            await conn.execute(
              'INSERT INTO transaction_log (family_id, user_id, type, target_account, amount, balance_before, balance_after, charter_clause, description) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
              [familyId, childId, 'escrow_out', 'B', escrowTotal.toString(), oldB2.toString(), balB.toString(), 'FR-011', '代管金释放']
            );
          }
          shouldSuspend = false;
        }
      }

      // Update accounts
      await conn.execute('UPDATE account SET balance = ? WHERE user_id = ? AND account_type = ?', [balA.toString(), childId, 'A']);
      await conn.execute('UPDATE account SET balance = ?, interest_pool = ?, is_interest_suspended = ?, is_deposit_suspended = ? WHERE user_id = ? AND account_type = ?',
        [balB.toString(), balBInterest.toString(), shouldSuspend ? 1 : 0, accMap.B.is_deposit_suspended && !(accMap.B.deposit_suspend_until && new Date(settDate) >= new Date(accMap.B.deposit_suspend_until)) ? 1 : 0, childId, 'B']);
      await conn.execute('UPDATE account SET balance = ? WHERE user_id = ? AND account_type = ?', [balC.toString(), childId, 'C']);

      const snapshotAfter = {
        A: balA.toString(), B: balB.toString(),
        B_interest: balBInterest.toString(), C: balC.toString(),
      };

      // Insert settlement record
      await conn.execute(
        'INSERT INTO settlement (family_id, user_id, settlement_date, status, c_dividend_amount, b_overflow_amount, b_interest_amount, violation_transfer_amount, p_active_at_settlement, snapshot_before, snapshot_after) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
        [familyId, childId, settDate, 'completed', dividend.toString(), overflowAmount.toString(), interest.total.toString(), violationTransfer.toString(), pActive.toString(), JSON.stringify(snapshotBefore), JSON.stringify(snapshotAfter)]
      );

      await conn.commit();
      return {
        child_id: childId, name: childName,
        c_dividend: centsToYuan(dividend),
        b_overflow: centsToYuan(overflowAmount),
        b_interest: centsToYuan(interest.total),
        violation_transfer: centsToYuan(violationTransfer),
        p_active: centsToYuan(pActive),
      };
    } finally {
      await conn.execute('SELECT RELEASE_LOCK(?)', [`fambank_settlement_${childId}`]);
    }
  } catch (e) {
    await conn.rollback();
    throw e;
  } finally {
    conn.release();
  }
}

async function handleList(user, event) {
  const rows = await query(
    'SELECT s.id, s.user_id, u.name as child_name, s.settlement_date, s.c_dividend_amount, s.b_overflow_amount, s.b_interest_amount, s.violation_transfer_amount, s.p_active_at_settlement, s.snapshot_before, s.snapshot_after, s.created_at FROM settlement s JOIN `user` u ON s.user_id = u.id WHERE s.family_id = ? ORDER BY s.settlement_date DESC, s.created_at DESC LIMIT 50',
    [user.family_id]
  );
  return ok(rows.map(r => ({
    id: Number(r.id),
    child_name: r.child_name,
    settlement_date: r.settlement_date,
    c_dividend: centsToYuan(r.c_dividend_amount),
    b_overflow: centsToYuan(r.b_overflow_amount),
    b_interest: centsToYuan(r.b_interest_amount),
    violation_transfer: centsToYuan(r.violation_transfer_amount),
    p_active: centsToYuan(r.p_active_at_settlement),
    snapshot_before: typeof r.snapshot_before === 'string' ? JSON.parse(r.snapshot_before) : r.snapshot_before,
    snapshot_after: typeof r.snapshot_after === 'string' ? JSON.parse(r.snapshot_after) : r.snapshot_after,
    created_at: r.created_at,
  })));
}
