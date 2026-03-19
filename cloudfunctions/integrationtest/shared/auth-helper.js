'use strict';
const { query } = require('./db');
const { unauthorized, forbidden, badRequest } = require('./errors');

/**
 * Get user by openid, returns null if not found
 */
async function getUserByOpenid(openid) {
  const rows = await query(
    'SELECT id, _openid, role, name, family_id, birth_date, created_at FROM `user` WHERE _openid = ?',
    [openid]
  );
  return rows.length > 0 ? rows[0] : null;
}

/**
 * Get or create user by openid (for login)
 */
async function getOrCreateUser(openid) {
  let user = await getUserByOpenid(openid);
  if (!user) {
    await query('INSERT INTO `user` (_openid) VALUES (?)', [openid]);
    user = await getUserByOpenid(openid);
  }
  return user;
}

/**
 * Assert user has joined a family
 */
function requireFamily(user) {
  if (!user || !user.family_id) {
    throw { result: forbidden('请先加入家庭') };
  }
}

/**
 * Assert user is a parent
 */
function requireParent(user) {
  requireFamily(user);
  if (user.role !== 'parent') {
    throw { result: forbidden('仅家长可执行此操作') };
  }
}

/**
 * Resolve child ID:
 * - Parent: must provide childId, validate it belongs to same family
 * - Child: uses own user ID
 */
async function resolveChildId(user, childId) {
  if (user.role === 'child') {
    return parseInt(user.id);
  }
  // Parent must specify childId
  if (!childId) {
    throw { result: badRequest('请指定孩子') };
  }
  const cid = parseInt(childId);
  const rows = await query(
    'SELECT id FROM `user` WHERE id = ? AND family_id = ? AND role = ?',
    [cid, user.family_id, 'child']
  );
  if (rows.length === 0) {
    throw { result: badRequest('无效的孩子ID') };
  }
  return cid;
}

module.exports = { getUserByOpenid, getOrCreateUser, requireFamily, requireParent, resolveChildId };
