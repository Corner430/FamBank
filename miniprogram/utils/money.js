/**
 * Money utilities - cents/yuan conversion for display
 * All internal values are in cents (integer)
 */

/**
 * Convert cents integer to yuan display string "12.34"
 */
function centsToYuan(cents) {
  if (cents === null || cents === undefined) return '0.00';
  const n = parseInt(cents, 10);
  if (isNaN(n)) return '0.00';
  const sign = n < 0 ? '-' : '';
  const abs = Math.abs(n);
  const yuan = Math.floor(abs / 100);
  const fen = abs % 100;
  return sign + yuan + '.' + String(fen).padStart(2, '0');
}

/**
 * Convert yuan string "12.34" to cents integer 1234
 */
function yuanToCents(yuanStr) {
  if (!yuanStr) return 0;
  const str = String(yuanStr).trim();
  const match = str.match(/^(-?)(\d+)(?:\.(\d{1,2}))?$/);
  if (!match) throw new Error('金额格式不正确');
  const sign = match[1] === '-' ? -1 : 1;
  const intPart = parseInt(match[2], 10);
  const decPart = match[3] ? match[3].padEnd(2, '0') : '00';
  return sign * (intPart * 100 + parseInt(decPart, 10));
}

module.exports = { centsToYuan, yuanToCents };
