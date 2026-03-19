'use strict';
const cloud = require('wx-server-sdk');
cloud.init({ env: cloud.DYNAMIC_CURRENT_ENV });

const {
  getUserByOpenid, requireFamily, requireParent, resolveChildId,
  getConnection, query, centsToYuan,
  ok, badRequest, forbidden, notFound, serverError
} = require('@fambank/shared');

exports.main = async (event, context) => {
  const { OPENID } = cloud.getWXContext();
  if (!OPENID) return { code: 401, msg: '未授权' };

  const user = await getUserByOpenid(OPENID);
  if (!user) return { code: 401, msg: '用户不存在' };

  const { action } = event;

  try {
    switch (action) {
      case 'create':
        return await handleCreate(user, event);
      case 'join':
        return await handleJoin(user, event);
      case 'detail':
        requireFamily(user);
        return await handleDetail(user);
      case 'createInvitation':
        requireParent(user);
        return await handleCreateInvitation(user, event);
      case 'listInvitations':
        requireParent(user);
        return await handleListInvitations(user);
      case 'revokeInvitation':
        requireParent(user);
        return await handleRevokeInvitation(user, event);
      case 'dashboard':
        requireParent(user);
        return await handleDashboard(user);
      default:
        return badRequest('未知操作: ' + action);
    }
  } catch (e) {
    if (e.result) return e.result;
    console.error('[family]', action, e);
    return serverError();
  }
};

/**
 * Create a new family
 */
async function handleCreate(user, event) {
  if (user.family_id) return badRequest('您已加入家庭');
  const { familyName, userName } = event;
  if (!familyName || !userName) return badRequest('请填写家庭名称和您的名字');

  const conn = await getConnection();
  try {
    await conn.beginTransaction();

    // Create family
    const [famResult] = await conn.execute(
      'INSERT INTO family (name, created_by) VALUES (?, ?)',
      [familyName, user.id]
    );
    const familyId = famResult.insertId;

    // Update user: set role, name, family_id
    await conn.execute(
      'UPDATE `user` SET role = ?, name = ?, family_id = ? WHERE id = ?',
      ['parent', userName, familyId, user.id]
    );

    // Create 3 accounts for first child? No - parent doesn't get accounts
    // Accounts are only for children

    await conn.commit();
    return ok({
      family_id: Number(familyId),
      family_name: familyName,
      role: 'parent',
      name: userName,
    });
  } catch (e) {
    await conn.rollback();
    throw e;
  } finally {
    conn.release();
  }
}

/**
 * Join a family by invitation code
 */
async function handleJoin(user, event) {
  if (user.family_id) return badRequest('您已加入家庭');
  const { code } = event;
  if (!code) return badRequest('请输入邀请码');

  const conn = await getConnection();
  try {
    await conn.beginTransaction();

    // Find valid invitation
    const [invitations] = await conn.execute(
      'SELECT * FROM invitation WHERE code = ? AND status = ? AND expires_at > NOW()',
      [code, 'pending']
    );
    if (invitations.length === 0) {
      await conn.rollback();
      return badRequest('邀请码无效或已过期');
    }

    const inv = invitations[0];

    // Update user
    await conn.execute(
      'UPDATE `user` SET role = ?, name = ?, family_id = ? WHERE id = ?',
      [inv.target_role, inv.target_name, inv.family_id, user.id]
    );

    // Mark invitation as used
    await conn.execute(
      'UPDATE invitation SET status = ?, used_by = ? WHERE id = ?',
      ['used', user.id, inv.id]
    );

    // If joining as child, create 3 accounts
    if (inv.target_role === 'child') {
      const accounts = [
        { type: 'A', name: '零钱宝' },
        { type: 'B', name: '梦想金' },
        { type: 'C', name: '牛马金' },
      ];
      for (const acc of accounts) {
        await conn.execute(
          'INSERT INTO account (family_id, user_id, account_type, display_name) VALUES (?, ?, ?, ?)',
          [inv.family_id, user.id, acc.type, acc.name]
        );
      }
    }

    await conn.commit();
    return ok({
      family_id: Number(inv.family_id),
      role: inv.target_role,
      name: inv.target_name,
    });
  } catch (e) {
    await conn.rollback();
    throw e;
  } finally {
    conn.release();
  }
}

/**
 * Get family detail
 */
async function handleDetail(user) {
  const familyRows = await query(
    'SELECT id, name, created_at FROM family WHERE id = ?',
    [user.family_id]
  );
  if (familyRows.length === 0) return notFound('家庭不存在');

  const members = await query(
    'SELECT id, name, role, created_at FROM `user` WHERE family_id = ?',
    [user.family_id]
  );

  return ok({
    family: {
      id: Number(familyRows[0].id),
      name: familyRows[0].name,
      created_at: familyRows[0].created_at,
    },
    members: members.map(m => ({
      id: Number(m.id),
      name: m.name,
      role: m.role,
    })),
  });
}

/**
 * Create invitation code
 */
async function handleCreateInvitation(user, event) {
  const { targetRole, targetName } = event;
  if (!targetRole || !targetName) return badRequest('请指定角色和名字');
  if (!['parent', 'child'].includes(targetRole)) return badRequest('无效角色');

  // Generate 8-char code (exclude O/0/I/1)
  const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
  let code = '';
  for (let i = 0; i < 8; i++) {
    code += chars[Math.floor(Math.random() * chars.length)];
  }

  // Expires in 7 days
  const expiresAt = new Date(Date.now() + 7 * 24 * 60 * 60 * 1000);

  await query(
    'INSERT INTO invitation (family_id, code, target_role, target_name, created_by, expires_at) VALUES (?, ?, ?, ?, ?, ?)',
    [user.family_id, code, targetRole, targetName, user.id, expiresAt]
  );

  return ok({ code, target_role: targetRole, target_name: targetName, expires_at: expiresAt });
}

/**
 * List invitations for the family
 */
async function handleListInvitations(user) {
  const rows = await query(
    'SELECT id, code, target_role, target_name, status, expires_at, created_at FROM invitation WHERE family_id = ? ORDER BY created_at DESC',
    [user.family_id]
  );
  return ok(rows.map(r => ({
    id: Number(r.id),
    code: r.code,
    target_role: r.target_role,
    target_name: r.target_name,
    status: r.status,
    expires_at: r.expires_at,
    created_at: r.created_at,
  })));
}

/**
 * Revoke an invitation
 */
async function handleRevokeInvitation(user, event) {
  const { invitationId } = event;
  if (!invitationId) return badRequest('缺少邀请ID');

  const result = await query(
    'UPDATE invitation SET status = ? WHERE id = ? AND family_id = ? AND status = ?',
    ['revoked', invitationId, user.family_id, 'pending']
  );
  if (result.affectedRows === 0) return notFound('邀请码不存在或已使用');
  return ok(null);
}

/**
 * Parent dashboard - all children with account summaries
 */
async function handleDashboard(user) {
  const children = await query(
    'SELECT id, name FROM `user` WHERE family_id = ? AND role = ?',
    [user.family_id, 'child']
  );

  const familyRows = await query('SELECT name FROM family WHERE id = ?', [user.family_id]);
  const familyName = familyRows.length > 0 ? familyRows[0].name : '';

  let totalAssets = 0n;
  const childrenData = [];

  for (const child of children) {
    const accounts = await query(
      'SELECT account_type, balance, interest_pool FROM account WHERE user_id = ?',
      [child.id]
    );

    let aBalance = 0n, bPrincipal = 0n, bInterestPool = 0n, cBalance = 0n;
    for (const acc of accounts) {
      const bal = BigInt(acc.balance);
      const ip = BigInt(acc.interest_pool);
      switch (acc.account_type) {
        case 'A': aBalance = bal; break;
        case 'B': bPrincipal = bal; bInterestPool = ip; break;
        case 'C': cBalance = bal; break;
      }
    }
    const childTotal = aBalance + bPrincipal + bInterestPool + cBalance;
    totalAssets += childTotal;

    childrenData.push({
      user_id: Number(child.id),
      name: child.name,
      accounts: {
        A: centsToYuan(aBalance),
        B_principal: centsToYuan(bPrincipal),
        B_interest_pool: centsToYuan(bInterestPool),
        C: centsToYuan(cBalance),
      },
      total: centsToYuan(childTotal),
    });
  }

  return ok({
    family_name: familyName,
    total_assets: centsToYuan(totalAssets),
    children: childrenData,
  });
}
