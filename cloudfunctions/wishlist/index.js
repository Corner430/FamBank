'use strict';
const cloud = require('wx-server-sdk');
cloud.init({ env: cloud.DYNAMIC_CURRENT_ENV });

const {
  createLogger,
  getUserByOpenid, requireFamily, requireParent, resolveChildId,
  getConnection, query, centsToYuan, yuanToCents, getConfigValue,
  ok, badRequest, notFound, serverError
} = require('@fambank/shared');

exports.main = async (event, context) => {
  const log = createLogger('wishlist', context);
  const { OPENID } = cloud.getWXContext();
  if (!OPENID) return { code: 401, msg: '未授权' };
  const user = await getUserByOpenid(OPENID);
  if (!user) return { code: 401, msg: '用户不存在' };
  requireFamily(user);

  try {
    switch (event.action) {
      case 'get': return await handleGet(user, event);
      case 'create': requireParent(user); return await handleCreate(user, event);
      case 'updatePrice': return await handleUpdatePrice(user, event);
      case 'declareTarget': return await handleDeclareTarget(user, event);
      case 'clearTarget': return await handleClearTarget(user, event);
      default: return badRequest('未知操作');
    }
  } catch (e) {
    if (e.result) return e.result;
    log.error(event.action, '系统异常', e);
    return serverError();
  }
};

async function handleGet(user, event) {
  const childId = await resolveChildId(user, event.childId);
  const lists = await query(
    'SELECT id, status, registered_at, lock_until, avg_price, max_price, active_target_item_id, valid_until FROM wish_list WHERE user_id = ? ORDER BY created_at DESC LIMIT 5',
    [childId]
  );
  const result = [];
  for (const list of lists) {
    const items = await query(
      'SELECT id, name, registered_price, current_price, last_price_update FROM wish_item WHERE wish_list_id = ?',
      [list.id]
    );
    result.push({
      id: Number(list.id),
      status: list.status,
      registered_at: list.registered_at,
      lock_until: list.lock_until,
      valid_until: list.valid_until,
      avg_price: centsToYuan(list.avg_price),
      max_price: centsToYuan(list.max_price),
      active_target_item_id: list.active_target_item_id ? Number(list.active_target_item_id) : null,
      items: items.map(i => ({
        id: Number(i.id),
        name: i.name,
        registered_price: centsToYuan(i.registered_price),
        current_price: centsToYuan(i.current_price),
        last_price_update: i.last_price_update,
      })),
    });
  }
  return ok(result);
}

async function handleCreate(user, event) {
  const childId = await resolveChildId(user, event.childId);
  const { items } = event;
  if (!items || !Array.isArray(items) || items.length === 0) return badRequest('请添加愿望清单物品');

  const conn = await getConnection();
  try {
    await conn.beginTransaction();

    const lockMonths = await getConfigValue(conn, user.family_id, 'wishlist_lock_months');
    const validMonths = await getConfigValue(conn, user.family_id, 'wishlist_valid_months');

    // Check if existing active list is past lock period
    const [existingLists] = await conn.execute(
      'SELECT id, lock_until FROM wish_list WHERE user_id = ? AND status = ? FOR UPDATE', [childId, 'active']
    );
    if (existingLists.length > 0) {
      const existing = existingLists[0];
      const lockUntil = new Date(existing.lock_until);
      if (new Date() < lockUntil) {
        await conn.rollback();
        return badRequest('当前愿望清单在锁定期内，无法替换');
      }
      // Mark as replaced
      await conn.execute('UPDATE wish_list SET status = ? WHERE id = ?', ['replaced', existing.id]);
    }

    const today = new Date();
    const registeredAt = today.toISOString().slice(0, 10);
    const lockUntil = new Date(today);
    lockUntil.setMonth(lockUntil.getMonth() + lockMonths);
    const validUntil = new Date(today);
    validUntil.setMonth(validUntil.getMonth() + validMonths);

    // Calculate prices
    let maxPrice = 0n;
    let totalPrice = 0n;
    const parsedItems = [];
    for (const item of items) {
      if (!item.name || !item.price) { await conn.rollback(); return badRequest('物品名称和价格必填'); }
      const priceCents = yuanToCents(item.price);
      if (priceCents <= 0n) { await conn.rollback(); return badRequest('价格必须大于0'); }
      parsedItems.push({ name: item.name, price: priceCents });
      totalPrice += priceCents;
      if (priceCents > maxPrice) maxPrice = priceCents;
    }
    const avgPrice = totalPrice / BigInt(parsedItems.length);

    // Insert wish_list
    const [listResult] = await conn.execute(
      'INSERT INTO wish_list (family_id, user_id, status, registered_at, lock_until, avg_price, max_price, valid_until) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
      [user.family_id, childId, 'active', registeredAt, lockUntil.toISOString().slice(0, 10), avgPrice.toString(), maxPrice.toString(), validUntil.toISOString().slice(0, 10)]
    );
    const listId = listResult.insertId;

    // Insert items
    for (const item of parsedItems) {
      await conn.execute(
        'INSERT INTO wish_item (wish_list_id, name, registered_price, current_price) VALUES (?, ?, ?, ?)',
        [listId, item.name, item.price.toString(), item.price.toString()]
      );
    }

    await conn.commit();
    log.audit('create', 'wishlist_create', { childId, listId: Number(listId), itemCount: parsedItems.length });
    return ok({ id: Number(listId), registered_at: registeredAt });
  } catch (e) {
    await conn.rollback();
    throw e;
  } finally {
    conn.release();
  }
}

async function handleUpdatePrice(user, event) {
  const { itemId, newPrice } = event;
  if (!itemId || !newPrice) return badRequest('请提供物品ID和新价格');

  const priceCents = yuanToCents(newPrice);
  if (priceCents <= 0n) return badRequest('价格必须大于0');

  const conn = await getConnection();
  try {
    await conn.beginTransaction();

    // Check item exists AND belongs to user's family
    const [items] = await conn.execute(
      'SELECT wi.id, wi.wish_list_id, wi.last_price_update FROM wish_item wi JOIN wish_list wl ON wi.wish_list_id = wl.id WHERE wi.id = ? AND wl.family_id = ?',
      [itemId, user.family_id]
    );
    if (items.length === 0) { await conn.rollback(); return notFound('物品不存在'); }

    const item = items[0];
    if (item.last_price_update) {
      const lastUpdate = new Date(item.last_price_update);
      const oneMonthAgo = new Date();
      oneMonthAgo.setMonth(oneMonthAgo.getMonth() - 1);
      if (lastUpdate > oneMonthAgo) {
        await conn.rollback();
        return badRequest('每月只能更新一次价格');
      }
    }

    await conn.execute(
      'UPDATE wish_item SET current_price = ?, last_price_update = CURDATE() WHERE id = ?',
      [priceCents.toString(), itemId]
    );

    // Recalculate max_price and avg_price
    const [allItems] = await conn.execute(
      'SELECT current_price FROM wish_item WHERE wish_list_id = ?', [item.wish_list_id]
    );
    let newMax = 0n, newTotal = 0n;
    for (const i of allItems) {
      const p = BigInt(i.current_price);
      newTotal += p;
      if (p > newMax) newMax = p;
    }
    const newAvg = newTotal / BigInt(allItems.length);
    await conn.execute(
      'UPDATE wish_list SET max_price = ?, avg_price = ? WHERE id = ?',
      [newMax.toString(), newAvg.toString(), item.wish_list_id]
    );

    await conn.commit();
    return ok({ current_price: centsToYuan(priceCents) });
  } catch (e) {
    await conn.rollback();
    throw e;
  } finally {
    conn.release();
  }
}

async function handleDeclareTarget(user, event) {
  const childId = await resolveChildId(user, event.childId);
  const { itemId } = event;
  if (!itemId) return badRequest('请指定目标物品');

  // Validate item belongs to active wish list of this child
  const rows = await query(
    'SELECT wi.id FROM wish_item wi JOIN wish_list wl ON wi.wish_list_id = wl.id WHERE wi.id = ? AND wl.user_id = ? AND wl.status = ?',
    [itemId, childId, 'active']
  );
  if (rows.length === 0) return badRequest('无效的物品');

  await query('UPDATE wish_list SET active_target_item_id = ? WHERE user_id = ? AND status = ?',
    [itemId, childId, 'active']);
  return ok(null);
}

async function handleClearTarget(user, event) {
  const childId = await resolveChildId(user, event.childId);
  await query('UPDATE wish_list SET active_target_item_id = NULL WHERE user_id = ? AND status = ?',
    [childId, 'active']);
  return ok(null);
}
