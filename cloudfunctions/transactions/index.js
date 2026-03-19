'use strict';
const cloud = require('wx-server-sdk');
cloud.init({ env: cloud.DYNAMIC_CURRENT_ENV });

const {
  createLogger,
  getUserByOpenid, requireFamily, resolveChildId, query, centsToYuan,
  ok, badRequest, serverError
} = require('@fambank/shared');

exports.main = async (event, context) => {
  const log = createLogger('transactions', context);
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
  const { accountType, txType, page = 1, pageSize = 20 } = event;

  let sql = 'SELECT id, type, source_account, target_account, amount, balance_before, balance_after, charter_clause, description, `timestamp` FROM transaction_log WHERE user_id = ?';
  const params = [childId];

  if (accountType) {
    sql += ' AND (source_account = ? OR target_account = ?)';
    params.push(accountType, accountType);
  }
  if (txType) {
    sql += ' AND type = ?';
    params.push(txType);
  }

  // Count total
  const countSql = sql.replace(/SELECT .* FROM/, 'SELECT COUNT(*) as total FROM');
  const countRows = await query(countSql, params);
  const total = parseInt(countRows[0].total);

  // Paginate
  const limitVal = parseInt(pageSize);
  const offsetVal = (parseInt(page) - 1) * limitVal;
  sql += ` ORDER BY \`timestamp\` DESC LIMIT ${limitVal} OFFSET ${offsetVal}`;

  const rows = await query(sql, params);

  return ok({
    total,
    page: parseInt(page),
    page_size: parseInt(pageSize),
    items: rows.map(r => ({
      id: Number(r.id),
      type: r.type,
      source_account: r.source_account,
      target_account: r.target_account,
      amount: centsToYuan(r.amount),
      balance_before: centsToYuan(r.balance_before),
      balance_after: centsToYuan(r.balance_after),
      charter_clause: r.charter_clause,
      description: r.description,
      timestamp: r.timestamp,
    })),
  });
}
