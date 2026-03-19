'use strict';
const cloud = require('wx-server-sdk');
cloud.init({ env: cloud.DYNAMIC_CURRENT_ENV });

const {
  getUserByOpenid, requireFamily, requireParent, resolveChildId,
  getConnection, centsToYuan, yuanToCents, calculateSplit,
  getConfigRatios,
  ok, badRequest, serverError
} = require('@fambank/shared');

exports.main = async (event, context) => {
  const { OPENID } = cloud.getWXContext();
  if (!OPENID) return { code: 401, msg: '未授权' };

  const user = await getUserByOpenid(OPENID);
  if (!user) return { code: 401, msg: '用户不存在' };
  requireFamily(user);

  const { action } = event;

  try {
    switch (action) {
      case 'create':
        requireParent(user);
        return await handleCreate(user, event);
      default:
        return badRequest('未知操作: ' + action);
    }
  } catch (e) {
    if (e.result) return e.result;
    console.error('[income]', action, e);
    return serverError();
  }
};

async function handleCreate(user, event) {
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

    // Get config ratios
    const { ratioA, ratioB, ratioC } = await getConfigRatios(conn, user.family_id);
    const split = calculateSplit(amountCents, ratioA, ratioB, ratioC);

    // Load accounts
    const [accounts] = await conn.execute(
      'SELECT id, account_type, balance, interest_pool, is_deposit_suspended FROM account WHERE user_id = ? FOR UPDATE',
      [childId]
    );

    const accMap = {};
    for (const acc of accounts) {
      accMap[acc.account_type] = acc;
    }

    if (!accMap.A || !accMap.B || !accMap.C) {
      await conn.rollback();
      return badRequest('账户不完整');
    }

    let actualA = split.a;
    let actualB = split.b;
    const actualC = split.c;
    let escrowed = false;

    // If B deposit suspended, B portion goes to escrow
    if (accMap.B.is_deposit_suspended) {
      await conn.execute(
        'INSERT INTO escrow (family_id, user_id, amount, status) VALUES (?, ?, ?, ?)',
        [user.family_id, childId, actualB.toString(), 'pending']
      );
      // Log escrow
      await conn.execute(
        'INSERT INTO transaction_log (family_id, user_id, type, target_account, amount, balance_before, balance_after, charter_clause, description) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
        [user.family_id, childId, 'escrow_in', 'B_escrow', actualB.toString(), BigInt(accMap.B.balance).toString(), BigInt(accMap.B.balance).toString(), 'FR-011', '入金暂停，B收入代管']
      );
      actualB = 0n;
      escrowed = true;
    }

    // Debt repayment: A portion goes to oldest debts first
    const [debts] = await conn.execute(
      'SELECT id, remaining_amount FROM debt WHERE user_id = ? AND remaining_amount > 0 ORDER BY created_at ASC FOR UPDATE',
      [childId]
    );

    let aForDebt = 0n;
    let aRemaining = actualA;

    for (const debt of debts) {
      if (aRemaining <= 0n) break;
      const debtRemaining = BigInt(debt.remaining_amount);
      const repay = aRemaining < debtRemaining ? aRemaining : debtRemaining;
      await conn.execute(
        'UPDATE debt SET remaining_amount = ? WHERE id = ?',
        [(debtRemaining - repay).toString(), debt.id]
      );
      aForDebt += repay;
      aRemaining -= repay;
    }

    // Credit accounts
    const balA = BigInt(accMap.A.balance);
    const balB = BigInt(accMap.B.balance);
    const balC = BigInt(accMap.C.balance);

    const newBalA = balA + aRemaining;
    const newBalB = balB + (escrowed ? 0n : actualB);
    const newBalC = balC + actualC;

    await conn.execute('UPDATE account SET balance = ? WHERE id = ?', [newBalA.toString(), accMap.A.id]);
    if (!escrowed) {
      await conn.execute('UPDATE account SET balance = ? WHERE id = ?', [newBalB.toString(), accMap.B.id]);
    }
    await conn.execute('UPDATE account SET balance = ? WHERE id = ?', [newBalC.toString(), accMap.C.id]);

    // Transaction logs
    if (aForDebt > 0n) {
      await conn.execute(
        'INSERT INTO transaction_log (family_id, user_id, type, source_account, target_account, amount, balance_before, balance_after, charter_clause, description) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
        [user.family_id, childId, 'debt_repayment', 'A_income', 'debt', aForDebt.toString(), balA.toString(), balA.toString(), 'S3', '收入偿还欠款']
      );
    }
    await conn.execute(
      'INSERT INTO transaction_log (family_id, user_id, type, target_account, amount, balance_before, balance_after, charter_clause, description) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
      [user.family_id, childId, 'income_split_a', 'A', aRemaining.toString(), balA.toString(), newBalA.toString(), 'S2', description || '收入分流A']
    );
    if (!escrowed) {
      await conn.execute(
        'INSERT INTO transaction_log (family_id, user_id, type, target_account, amount, balance_before, balance_after, charter_clause, description) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
        [user.family_id, childId, 'income_split_b', 'B', split.b.toString(), balB.toString(), newBalB.toString(), 'S2', description || '收入分流B']
      );
    }
    await conn.execute(
      'INSERT INTO transaction_log (family_id, user_id, type, target_account, amount, balance_before, balance_after, charter_clause, description) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
      [user.family_id, childId, 'income_split_c', 'C', actualC.toString(), balC.toString(), newBalC.toString(), 'S2', description || '收入分流C']
    );

    await conn.commit();
    return ok({
      total: centsToYuan(amountCents),
      split: {
        A: centsToYuan(aRemaining),
        B: centsToYuan(escrowed ? 0n : split.b),
        C: centsToYuan(actualC),
      },
      debt_repaid: centsToYuan(aForDebt),
      escrowed: escrowed,
    });
  } catch (e) {
    await conn.rollback();
    throw e;
  } finally {
    conn.release();
  }
}
