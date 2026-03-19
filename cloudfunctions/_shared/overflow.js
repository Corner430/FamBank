'use strict';

/**
 * Calculate B account overflow to C
 * Cap = floor(1.2 * P_active)
 * If B_principal > Cap: overflow = B - Cap
 *
 * @param {BigInt} bPrincipal - B balance in cents
 * @param {BigInt} pActive - P_active in cents
 * @returns {{ capOverflow: BigInt, overflowAmount: BigInt, bAfter: BigInt }}
 */
function calculateOverflow(bPrincipal, pActive) {
  const b = BigInt(bPrincipal);
  const p = BigInt(pActive);

  // If no wish list (P_active = 0), no overflow
  if (p === 0n) {
    return { capOverflow: 0n, overflowAmount: 0n, bAfter: b };
  }

  const capOverflow = p * 12n / 10n;

  if (b > capOverflow) {
    const overflow = b - capOverflow;
    return { capOverflow, overflowAmount: overflow, bAfter: capOverflow };
  }

  return { capOverflow, overflowAmount: 0n, bAfter: b };
}

module.exports = { calculateOverflow };
