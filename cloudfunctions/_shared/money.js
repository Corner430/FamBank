'use strict';

/**
 * Convert cents (BigInt or number/string) to yuan string "12.34"
 * Uses ROUND_HALF_UP equivalent
 */
function centsToYuan(cents) {
  const n = BigInt(cents || 0);
  const sign = n < 0n ? '-' : '';
  const abs = n < 0n ? -n : n;
  const yuan = abs / 100n;
  const fen = abs % 100n;
  return sign + yuan.toString() + '.' + fen.toString().padStart(2, '0');
}

/**
 * Convert yuan string "12.34" to cents BigInt
 * Rejects more than 2 decimal places
 */
function yuanToCents(yuanStr) {
  if (!yuanStr) return 0n;
  const str = String(yuanStr).trim();
  const match = str.match(/^(-?)(\d+)(?:\.(\d{1,2}))?$/);
  if (!match) throw new Error('金额格式不正确: ' + yuanStr);
  const sign = match[1] === '-' ? -1n : 1n;
  const intPart = BigInt(match[2]);
  const decStr = match[3] ? match[3].padEnd(2, '0') : '00';
  const decPart = BigInt(decStr);
  return sign * (intPart * 100n + decPart);
}

/**
 * Calculate income split: A + B + C = total, remainder goes to C
 * All values are BigInt cents
 */
function calculateSplit(amountCents, ratioA, ratioB, ratioC) {
  const amount = BigInt(amountCents);
  const rA = BigInt(ratioA);
  const rB = BigInt(ratioB);
  const rC = BigInt(ratioC);
  if (rA + rB + rC !== 100n) throw new Error('分配比例之和必须为100');
  const a = amount * rA / 100n;
  const b = amount * rB / 100n;
  const c = amount - a - b; // remainder to C
  return { a, b, c };
}

module.exports = { centsToYuan, yuanToCents, calculateSplit };
