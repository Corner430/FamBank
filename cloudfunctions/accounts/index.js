'use strict';
const cloud = require('wx-server-sdk');
cloud.init({ env: cloud.DYNAMIC_CURRENT_ENV });

const {
  createLogger,
  getUserByOpenid, requireFamily, requireParent, resolveChildId,
  getConnection, query, centsToYuan, yuanToCents,
  ok, badRequest, forbidden, serverError
} = require('@fambank/shared');

exports.main = async (event, context) => {
  const log = createLogger('accounts', context);
  const { OPENID } = cloud.getWXContext();
  if (!OPENID) return { code: 401, msg: '未授权' };

  const user = await getUserByOpenid(OPENID);
  if (!user) return { code: 401, msg: '用户不存在' };
  requireFamily(user);

  const { action } = event;

  try {
    switch (action) {
      case 'list':
        return await handleList(user, event);
      case 'spendA':
        return await handleSpendA(user, event);
      case 'purchaseB':
        return await handlePurchaseB(user, event);
      case 'refundB':
        requireParent(user);
        return await handleRefundB(user, event);
      default:
        return badRequest('未知操作: ' + action);
    }
  } catch (e) {
    if (e.result) return e.result;
    log.error(action, '系统异常', e);
    return serverError();
  }
};

async function handleList(user, event) {
  const childId = await resolveChildId(user, event.childId);

  const accounts = await query(
    'SELECT id, account_type, display_name, balance, interest_pool, is_interest_suspended, is_deposit_suspended FROM account WHERE user_id = ? ORDER BY account_type',
    [childId]
  );

  // Get total debt
  const debtRows = await query(
    'SELECT COALESCE(SUM(remaining_amount), 0) as total_debt FROM debt WHERE user_id = ? AND remaining_amount > 0',
    [childId]
  );
  const totalDebt = debtRows[0].total_debt || '0';

  return ok({
    accounts: accounts.map(a => ({
      id: Number(a.id),
      type: a.account_type,
      name: a.display_name,
      balance: centsToYuan(a.balance),
      interest_pool: a.account_type === 'B' ? centsToYuan(a.interest_pool) : undefined,
      is_interest_suspended: a.account_type === 'B' ? !!a.is_interest_suspended : undefined,
      is_deposit_suspended: a.account_type === 'B' ? !!a.is_deposit_suspended : undefined,
    })),
    total_debt: centsToYuan(totalDebt),
  });
}

async function handleSpendA(user, event) {
  const childId = await resolveChildId(user, event.childId);
  const { amount, description } = event;
  if (!amount) return badRequest('请输入金额');

  const amountCents = yuanToCents(amount);
  if (amountCents <= 0n) return badRequest('金额必须大于0');

  const conn = await getConnection();
  try {
    // Check settlement lock
    const [lockCheck] = await conn.execute("SELECT IS_FREE_LOCK('fambank_settlement') as free");
    if (!lockCheck[0].free) return badRequest('结算进行中，请稍后');

    await conn.beginTransaction();

    const [accounts] = await conn.execute(
      'SELECT id, balance FROM account WHERE user_id = ? AND account_type = ? FOR UPDATE',
      [childId, 'A']
    );
    if (accounts.length === 0) return badRequest('账户不存在');

    const acc = accounts[0];
    const balance = BigInt(acc.balance);
    if (balance < amountCents) return badRequest('余额不足');

    const newBalance = balance - amountCents;
    await conn.execute('UPDATE account SET balance = ? WHERE id = ?', [newBalance.toString(), acc.id]);

    // Transaction log
    await conn.execute(
      'INSERT INTO transaction_log (family_id, user_id, type, source_account, amount, balance_before, balance_after, charter_clause, description) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
      [user.family_id, childId, 'a_spend', 'A', amountCents.toString(), balance.toString(), newBalance.toString(), 'S3', description || 'A账户消费']
    );

    await conn.commit();
    log.audit('spendA', 'spend_a', { childId, amount: centsToYuan(amountCents), newBalance: centsToYuan(newBalance) });
    return ok({ balance: centsToYuan(newBalance) });
  } catch (e) {
    await conn.rollback();
    throw e;
  } finally {
    conn.release();
  }
}

async function handlePurchaseB(user, event) {
  const childId = await resolveChildId(user, event.childId);
  const { amount, itemId, isSubstitute, description } = event;
  if (!amount) return badRequest('请输入金额');

  const actualCost = yuanToCents(amount);
  if (actualCost <= 0n) return badRequest('金额必须大于0');

  const conn = await getConnection();
  try {
    await conn.beginTransaction();

    // If substitute purchase, validate cost <= 120% of item price
    if (isSubstitute && itemId) {
      const [items] = await conn.execute('SELECT current_price FROM wish_item WHERE id = ?', [itemId]);
      if (items.length > 0) {
        const maxCost = BigInt(items[0].current_price) * 120n / 100n;
        if (actualCost > maxCost) {
          await conn.rollback();
          return badRequest('替代品价格不能超过原商品的120%');
        }
      }
    }

    // Load B account
    const [accounts] = await conn.execute(
      'SELECT id, balance, interest_pool FROM account WHERE user_id = ? AND account_type = ? FOR UPDATE',
      [childId, 'B']
    );
    if (accounts.length === 0) { await conn.rollback(); return badRequest('账户不存在'); }

    const acc = accounts[0];
    const principal = BigInt(acc.balance);
    const interestPool = BigInt(acc.interest_pool);
    const totalAvailable = principal + interestPool;

    if (totalAvailable < actualCost) {
      await conn.rollback();
      return badRequest('余额不足');
    }

    // Deduct: principal first, then interest pool
    let deductPrincipal = actualCost < principal ? actualCost : principal;
    let deductInterest = actualCost - deductPrincipal;

    const newPrincipal = principal - deductPrincipal;
    const newInterestPool = interestPool - deductInterest;

    await conn.execute(
      'UPDATE account SET balance = ?, interest_pool = ?, last_compliant_purchase_date = CURDATE(), is_interest_suspended = FALSE WHERE id = ?',
      [newPrincipal.toString(), newInterestPool.toString(), acc.id]
    );

    // Transaction logs
    if (deductPrincipal > 0n) {
      await conn.execute(
        'INSERT INTO transaction_log (family_id, user_id, type, source_account, amount, balance_before, balance_after, charter_clause, description) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
        [user.family_id, childId, 'purchase_debit_principal', 'B', deductPrincipal.toString(), principal.toString(), newPrincipal.toString(), 'S4.6', description || 'B购买(本金)']
      );
    }
    if (deductInterest > 0n) {
      await conn.execute(
        'INSERT INTO transaction_log (family_id, user_id, type, source_account, amount, balance_before, balance_after, charter_clause, description) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
        [user.family_id, childId, 'purchase_debit_interest', 'B_interest', deductInterest.toString(), interestPool.toString(), newInterestPool.toString(), 'S4.6', description || 'B购买(利息)']
      );
    }

    await conn.commit();
    log.audit('purchaseB', 'purchase_b', { childId, amount: centsToYuan(actualCost), deductPrincipal: centsToYuan(deductPrincipal), deductInterest: centsToYuan(deductInterest) });
    return ok({
      balance: centsToYuan(newPrincipal),
      interest_pool: centsToYuan(newInterestPool),
    });
  } catch (e) {
    await conn.rollback();
    throw e;
  } finally {
    conn.release();
  }
}

async function handleRefundB(user, event) {
  const childId = await resolveChildId(user, event.childId);
  const { principalAmount, interestAmount, description } = event;

  const principalCents = principalAmount ? yuanToCents(principalAmount) : 0n;
  const interestCents = interestAmount ? yuanToCents(interestAmount) : 0n;
  if (principalCents <= 0n && interestCents <= 0n) return badRequest('退款金额必须大于0');

  const conn = await getConnection();
  try {
    await conn.beginTransaction();

    const [accounts] = await conn.execute(
      'SELECT id, balance, interest_pool FROM account WHERE user_id = ? AND account_type = ? FOR UPDATE',
      [childId, 'B']
    );
    if (accounts.length === 0) { await conn.rollback(); return badRequest('账户不存在'); }

    const acc = accounts[0];
    const principal = BigInt(acc.balance);
    const interestPool = BigInt(acc.interest_pool);

    const newPrincipal = principal + principalCents;
    const newInterestPool = interestPool + interestCents;

    await conn.execute(
      'UPDATE account SET balance = ?, interest_pool = ? WHERE id = ?',
      [newPrincipal.toString(), newInterestPool.toString(), acc.id]
    );

    if (principalCents > 0n) {
      await conn.execute(
        'INSERT INTO transaction_log (family_id, user_id, type, target_account, amount, balance_before, balance_after, charter_clause, description) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
        [user.family_id, childId, 'refund_credit_principal', 'B', principalCents.toString(), principal.toString(), newPrincipal.toString(), 'S4.6', description || 'B退款(本金)']
      );
    }
    if (interestCents > 0n) {
      await conn.execute(
        'INSERT INTO transaction_log (family_id, user_id, type, target_account, amount, balance_before, balance_after, charter_clause, description) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
        [user.family_id, childId, 'refund_credit_interest', 'B_interest', interestCents.toString(), interestPool.toString(), newInterestPool.toString(), 'S4.6', description || 'B退款(利息)']
      );
    }

    await conn.commit();
    log.audit('refundB', 'refund_b', { childId, principal: centsToYuan(principalCents), interest: centsToYuan(interestCents) });
    return ok({
      balance: centsToYuan(newPrincipal),
      interest_pool: centsToYuan(newInterestPool),
    });
  } catch (e) {
    await conn.rollback();
    throw e;
  } finally {
    conn.release();
  }
}
