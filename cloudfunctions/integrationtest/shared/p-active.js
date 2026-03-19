'use strict';

/**
 * Calculate P_active for a child
 * P_active = active_target_item's current_price, or max_price if no target, or 0 if no wish list
 *
 * @param {Connection} conn - MySQL connection
 * @param {number} userId - Child user ID
 * @returns {BigInt} P_active in cents
 */
async function getPActive(conn, userId) {
  // Find active wish list
  const [lists] = await conn.execute(
    'SELECT id, active_target_item_id, max_price FROM wish_list WHERE user_id = ? AND status = ? AND valid_until >= CURDATE() LIMIT 1',
    [userId, 'active']
  );

  if (lists.length === 0) return 0n;

  const list = lists[0];

  // If has declared target item
  if (list.active_target_item_id) {
    const [items] = await conn.execute(
      'SELECT current_price FROM wish_item WHERE id = ?',
      [list.active_target_item_id]
    );
    if (items.length > 0) {
      return BigInt(items[0].current_price);
    }
  }

  // Otherwise use max_price
  return BigInt(list.max_price || 0);
}

module.exports = { getPActive };
