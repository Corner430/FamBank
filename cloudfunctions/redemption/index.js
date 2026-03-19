'use strict';
const cloud = require('wx-server-sdk');
cloud.init({ env: cloud.DYNAMIC_CURRENT_ENV });

const {
  getUserByOpenid, requireFamily, requireParent, resolveChildId,
  getConnection, query, centsToYuan, yuanToCents, getConfigValue, getAllConfig,
  ok, badRequest, notFound, serverError
} = require('@fambank/shared');

exports.main = async (event, context) => {
  const { OPENID } = cloud.getWXContext();
  if (!OPENID) return { code: 401, msg: '未授权' };
  const user = await getUserByOpenid(OPENID);
  if (!user) return { code: 401, msg: '用户不存在' };
  requireFamily(user);

  try {
    switch (event.action) {
      case 'request': return await handleRequest(user, event);
      case 'approve': requireParent(user); return await handleApprove(user, event);
      case 'listPending': return await handleListPending(user);
      default: return badRequest('未知操作');
    }
  } catch (e) {
    if (e.result) return e.result;
    console.error('[redemption]', event.action, e);
    return serverError();
  }
};

async function handleRequest(user, event) {
  const childId = await resolveChildId(user, event.childId);
  const { amount, reason } = event;
  if (!amount) return badRequest('请输入金额');

  const amountCents = yuanToCents(amount);
  if (amountCents <= 0n) return badRequest('金额必须大于0');

  // Check C balance
  const cAccounts = await query(
    'SELECT balance FROM account WHERE user_id = ? AND account_type = ?', [childId, 'C']
  );
  if (cAccounts.length === 0) return badRequest('账户不存在');
  if (BigInt(cAccounts[0].balance) < amountCents) return badRequest('C账户余额不足');

  // Calculate fee from config
  const config = await getAllConfig(user.family_id);
  const feeRate = BigInt(config.redemption_fee_rate);
  const fee = amountCents * feeRate / 100n;
  const net = amountCents - fee;

  await query(
    'INSERT INTO redemption_request (family_id, amount, fee, net, reason, requested_by) VALUES (?, ?, ?, ?, ?, ?)',
    [user.family_id, amountCents.toString(), fee.toString(), net.toString(), reason || '', childId]
  );

  return ok({
    amount: centsToYuan(amountCents),
    fee: centsToYuan(fee),
    net: centsToYuan(net),
  });
}

async function handleApprove(user, event) {
  const { requestId, approve } = event;
  if (!requestId) return badRequest('缺少请求ID');

  const conn = await getConnection();
  try {
    await conn.beginTransaction();

    const [requests] = await conn.execute(
      'SELECT * FROM redemption_request WHERE id = ? AND family_id = ? AND status = ? FOR UPDATE',
      [requestId, user.family_id, 'pending']
    );
    if (requests.length === 0) { await conn.rollback(); return notFound('请求不存在或已处理'); }

    const req = requests[0];
    const newStatus = approve ? 'approved' : 'rejected';

    await conn.execute(
      'UPDATE redemption_request SET status = ?, reviewed_by = ?, reviewed_at = NOW() WHERE id = ?',
      [newStatus, user.id, req.id]
    );

    if (approve) {
      // Re-calculate fee from config to ensure consistency
      const feeRate = await getConfigValue(conn, user.family_id, 'redemption_fee_rate');
      const amountCents = BigInt(req.amount);
      const feeCents = amountCents * BigInt(feeRate) / 100n;
      const netCents = amountCents - feeCents;
      const childId = parseInt(req.requested_by);

      // Load C and A accounts
      const [cAccounts] = await conn.execute(
        'SELECT id, balance FROM account WHERE user_id = ? AND account_type = ? FOR UPDATE', [childId, 'C']
      );
      const [aAccounts] = await conn.execute(
        'SELECT id, balance FROM account WHERE user_id = ? AND account_type = ? FOR UPDATE', [childId, 'A']
      );

      const cBal = BigInt(cAccounts[0].balance);
      const aBal = BigInt(aAccounts[0].balance);

      if (cBal < amountCents) { await conn.rollback(); return badRequest('C余额不足'); }

      const newC = cBal - amountCents;
      const newA = aBal + netCents;

      await conn.execute('UPDATE account SET balance = ? WHERE id = ?', [newC.toString(), cAccounts[0].id]);
      await conn.execute('UPDATE account SET balance = ? WHERE id = ?', [newA.toString(), aAccounts[0].id]);

      // Transaction logs
      await conn.execute(
        'INSERT INTO transaction_log (family_id, user_id, type, source_account, amount, balance_before, balance_after, charter_clause, description) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
        [user.family_id, childId, 'c_redemption', 'C', netCents.toString(), cBal.toString(), newC.toString(), 'S5', 'C赎回到A']
      );
      if (feeCents > 0n) {
        await conn.execute(
          'INSERT INTO transaction_log (family_id, user_id, type, source_account, amount, balance_before, balance_after, charter_clause, description) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
          [user.family_id, childId, 'c_redemption_fee', 'C', feeCents.toString(), (cBal - netCents).toString(), newC.toString(), 'S5', 'C赎回手续费']
        );
        // Record fee as punitive destruction for audit trail
        await conn.execute(
          'INSERT INTO transaction_log (family_id, user_id, type, amount, charter_clause, description) VALUES (?, ?, ?, ?, ?, ?)',
          [user.family_id, childId, 'redemption_fee', feeCents.toString(), 'S5', '赎回手续费（惩罚性销毁）']
        );
      }
    }

    await conn.commit();
    return ok({ status: newStatus });
  } catch (e) {
    await conn.rollback();
    throw e;
  } finally {
    conn.release();
  }
}

async function handleListPending(user) {
  const rows = await query(
    'SELECT r.id, r.amount, r.fee, r.net, r.reason, r.status, r.created_at, r.reviewed_at, u.name as requester_name FROM redemption_request r JOIN `user` u ON r.requested_by = u.id WHERE r.family_id = ? ORDER BY r.created_at DESC LIMIT 50',
    [user.family_id]
  );
  return ok(rows.map(r => ({
    id: Number(r.id),
    amount: centsToYuan(r.amount),
    fee: centsToYuan(r.fee),
    net: centsToYuan(r.net),
    reason: r.reason,
    status: r.status,
    requester_name: r.requester_name,
    created_at: r.created_at,
    reviewed_at: r.reviewed_at,
  })));
}
