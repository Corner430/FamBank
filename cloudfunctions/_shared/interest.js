'use strict';

/**
 * Calculate C account monthly dividend (C -> A)
 * Formula: floor(C_balance * annual_rate / 10000 / 12)
 * 
 * @param {BigInt} cBalance - C account balance in cents
 * @param {number} annualRateBps - Annual rate in basis points (500 = 5.0%)
 * @returns {BigInt} dividend amount in cents
 */
function calculateCDividend(cBalance, annualRateBps) {
  const balance = BigInt(cBalance);
  const rate = BigInt(annualRateBps);
  if (balance <= 0n) return 0n;
  return balance * rate / 10000n / 12n;
}

/**
 * Calculate B account tiered interest
 * Tier1: min(B, tier1_limit) * tier1_rate / 10000
 * Tier2: max(0, min(B, P_active) - tier1_limit) * tier2_rate / 10000
 * Tier3: max(0, min(B, 1.2*P_active) - P_active) * tier3_rate / 10000
 *
 * @param {BigInt} bPrincipal - B account balance (principal only) in cents
 * @param {BigInt} pActive - P_active value in cents (target price or max_price)
 * @param {Object} rates - { tier1Rate, tier1Limit, tier2Rate, tier3Rate } all in bps/cents
 * @param {boolean} isSuspended - Whether interest is suspended
 * @returns {{ tier1: BigInt, tier2: BigInt, tier3: BigInt, total: BigInt }}
 */
function calculateBInterest(bPrincipal, pActive, rates, isSuspended) {
  const b = BigInt(bPrincipal);
  const p = BigInt(pActive);
  const tier1Rate = BigInt(rates.tier1Rate);
  const tier1Limit = BigInt(rates.tier1Limit);
  const tier2Rate = BigInt(rates.tier2Rate);
  const tier3Rate = BigInt(rates.tier3Rate);

  if (isSuspended || b <= 0n) {
    return { tier1: 0n, tier2: 0n, tier3: 0n, total: 0n };
  }

  // Cap overflow = 1.2 * P_active
  const capOverflow = p * 12n / 10n;

  // Tier 1: 0 ~ tier1_limit
  const tier1Base = b < tier1Limit ? b : tier1Limit;
  const tier1 = tier1Base * tier1Rate / 10000n;

  let tier2 = 0n;
  let tier3 = 0n;

  if (p > 0n) {
    // Tier 2: tier1_limit ~ P_active
    const tier2Upper = b < p ? b : p;
    const tier2Base = tier2Upper > tier1Limit ? tier2Upper - tier1Limit : 0n;
    tier2 = tier2Base * tier2Rate / 10000n;

    // Tier 3: P_active ~ 1.2*P_active
    const tier3Upper = b < capOverflow ? b : capOverflow;
    const tier3Base = tier3Upper > p ? tier3Upper - p : 0n;
    tier3 = tier3Base * tier3Rate / 10000n;
  }

  return { tier1, tier2, tier3, total: tier1 + tier2 + tier3 };
}

module.exports = { calculateCDividend, calculateBInterest };
