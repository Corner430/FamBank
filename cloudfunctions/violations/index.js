'use strict';
const cloud = require('wx-server-sdk');
cloud.init({ env: cloud.DYNAMIC_CURRENT_ENV });

const {
  createLogger,
  getUserByOpenid, requireFamily, requireParent, resolveChildId,
  getConnection, query, centsToYuan, yuanToCents, getConfigValue,
  ok, badRequest, serverError
} = require('@fambank/shared');

exports.main = async (event, context) => {
  const log = createLogger('violations', context);
  const { OPENID } = cloud.getWXContext();
  if (!OPENID) return { code: 401, msg: '未授权' };
  const user = await getUserByOpenid(OPENID);
  if (!user) return { code: 401, msg: '用户不存在' };
  requireFamily(user);

  try {
    switch (event.action) {
      case 'create': requireParent(user); return await handleCreate(user, event);
      case 'list': return await handleListViolations(user, event);
      default: return badRequest('未知操作');
    }
  } catch (e) {
    if (e.result) return e.result;
    log.error(event.action, '系统异常', e);
    return serverError();
  }
};

async function handleCreate(user, event) {
  const childId = await resolveChildId(user, event.childId);
  const { amount, amountEnteredA, description } = event;
  if (!amount || !description) return badRequest('请填写金额和描述');

  const violationAmount = yuanToCents(amount);
  if (violationAmount <= 0n) return badRequest('金额必须大于0');
  const enteredA = amountEnteredA ? yuanToCents(amountEnteredA) : 0n;
  if (enteredA < 0n) return badRequest('罚入A金额不能为负数');
  if (enteredA > violationAmount) return badRequest('罚入A金额不能超过违约金额');

  const conn = await getConnection();
  try {
    await conn.beginTransaction();

    const penaltyMultiplier = await getConfigValue(conn, user.family_id, 'penalty_multiplier');
    
    // Load B account
    const [bAccounts] = await conn.execute(
      'SELECT id, interest_pool FROM account WHERE user_id = ? AND account_type = ? FOR UPDATE', [childId, 'B']
    );
    const [cAccounts] = await conn.execute(
      'SELECT id, balance FROM account WHERE user_id = ? AND account_type = ? FOR UPDATE', [childId, 'C']
    );
    
    const bInterestPool = BigInt(bAccounts[0].interest_pool);
    const cBalance = BigInt(cAccounts[0].balance);

    // Penalty = min(B_interest_pool, multiplier * violation_amount)
    const maxPenalty = BigInt(penaltyMultiplier) * violationAmount;
    const penalty = bInterestPool < maxPenalty ? bInterestPool : maxPenalty;

    // Transfer penalty: B.interest_pool -> C
    const newBInterest = bInterestPool - penalty;
    const newCBalance = cBalance + penalty;
    
    await conn.execute('UPDATE account SET interest_pool = ? WHERE id = ?', [newBInterest.toString(), bAccounts[0].id]);
    await conn.execute('UPDATE account SET balance = ? WHERE id = ?', [newCBalance.toString(), cAccounts[0].id]);

    if (penalty > 0n) {
      await conn.execute(
        'INSERT INTO transaction_log (family_id, user_id, type, source_account, amount, balance_before, balance_after, charter_clause, description) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
        [user.family_id, childId, 'violation_penalty', 'B_interest', penalty.toString(), bInterestPool.toString(), newBInterest.toString(), 'S7', description]
      );
      await conn.execute(
        'INSERT INTO transaction_log (family_id, user_id, type, target_account, amount, balance_before, balance_after, charter_clause, description) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
        [user.family_id, childId, 'violation_penalty_credit', 'C', penalty.toString(), cBalance.toString(), newCBalance.toString(), 'S7', description]
      );
    }

    // Check escalation: 2nd violation in 12 months
    const [recentViolations] = await conn.execute(
      'SELECT COUNT(*) as cnt FROM violation WHERE user_id = ? AND violation_date >= DATE_SUB(CURDATE(), INTERVAL 365 DAY)',
      [childId]
    );
    const isEscalated = parseInt(recentViolations[0].cnt) >= 1; // this is 2nd+

    if (isEscalated) {
      // Suspend B deposits
      const nextMonth = new Date();
      nextMonth.setMonth(nextMonth.getMonth() + 1);
      nextMonth.setDate(1);
      const suspendUntil = new Date(nextMonth);
      suspendUntil.setDate(suspendUntil.getDate() + 30);
      
      await conn.execute(
        'UPDATE account SET is_deposit_suspended = TRUE, deposit_suspend_until = ? WHERE user_id = ? AND account_type = ?',
        [suspendUntil.toISOString().slice(0, 10), childId, 'B']
      );
    }

    // Insert violation record
    const today = new Date().toISOString().slice(0, 10);
    await conn.execute(
      'INSERT INTO violation (family_id, user_id, violation_date, violation_amount, penalty_amount, amount_entered_a, is_escalated, description) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
      [user.family_id, childId, today, violationAmount.toString(), penalty.toString(), enteredA.toString(), isEscalated, description]
    );

    await conn.commit();
    log.audit('create', 'violation_create', {
      childId,
      violationAmount: centsToYuan(violationAmount),
      penalty: centsToYuan(penalty),
      isEscalated,
    });
    return ok({
      violation_amount: centsToYuan(violationAmount),
      penalty: centsToYuan(penalty),
      is_escalated: isEscalated,
    });
  } catch (e) {
    await conn.rollback();
    throw e;
  } finally {
    conn.release();
  }
}

async function handleListViolations(user, event) {
  const childId = await resolveChildId(user, event.childId);
  const rows = await query(
    'SELECT id, violation_date, violation_amount, penalty_amount, amount_entered_a, is_escalated, description, created_at FROM violation WHERE user_id = ? ORDER BY violation_date DESC LIMIT 50',
    [childId]
  );
  return ok(rows.map(r => ({
    id: Number(r.id),
    violation_date: r.violation_date,
    violation_amount: centsToYuan(r.violation_amount),
    penalty_amount: centsToYuan(r.penalty_amount),
    amount_entered_a: centsToYuan(r.amount_entered_a),
    is_escalated: !!r.is_escalated,
    description: r.description,
    created_at: r.created_at,
  })));
}
