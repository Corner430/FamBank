'use strict';
const { query } = require('./db');

const DEFAULT_CONFIG = {
  split_ratio_a: 15,
  split_ratio_b: 30,
  split_ratio_c: 55,
  b_tier1_rate: 200,
  b_tier1_limit: 100000,
  b_tier2_rate: 120,
  b_tier3_rate: 30,
  c_annual_rate: 500,
  penalty_multiplier: 2,
  redemption_fee_rate: 10,
  wishlist_lock_months: 3,
  wishlist_valid_months: 12,
  b_suspend_months: 12,
  c_lock_age: 18,
};

/**
 * Get a single config value for a family
 */
async function getConfigValue(conn, familyId, key) {
  const [rows] = await conn.execute(
    'SELECT value FROM config WHERE family_id = ? AND `key` = ? AND effective_from <= CURDATE() ORDER BY effective_from DESC LIMIT 1',
    [familyId, key]
  );
  if (rows.length > 0) {
    return parseInt(rows[0].value);
  }
  return DEFAULT_CONFIG[key] !== undefined ? DEFAULT_CONFIG[key] : null;
}

/**
 * Get income split ratios for a family
 */
async function getConfigRatios(conn, familyId) {
  const a = await getConfigValue(conn, familyId, 'split_ratio_a');
  const b = await getConfigValue(conn, familyId, 'split_ratio_b');
  const c = await getConfigValue(conn, familyId, 'split_ratio_c');
  return { ratioA: a, ratioB: b, ratioC: c };
}

/**
 * Get all current config values for a family
 */
async function getAllConfig(familyId) {
  const result = { ...DEFAULT_CONFIG };
  const rows = await query(
    `SELECT DISTINCT \`key\`, 
     (SELECT value FROM config c2 WHERE c2.family_id = ? AND c2.\`key\` = c1.\`key\` AND c2.effective_from <= CURDATE() ORDER BY c2.effective_from DESC LIMIT 1) as value
     FROM config c1 WHERE c1.family_id = ?`,
    [familyId, familyId]
  );
  for (const row of rows) {
    if (row.value !== null) {
      result[row.key] = parseInt(row.value);
    }
  }
  return result;
}

module.exports = { DEFAULT_CONFIG, getConfigValue, getConfigRatios, getAllConfig };
