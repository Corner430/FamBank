/**
 * Constants for FamBank mini program
 */
module.exports = {
  // Account types
  ACCOUNT_TYPE: {
    A: 'A',
    B: 'B',
    C: 'C',
  },

  // Account display names
  ACCOUNT_NAMES: {
    A: '零钱宝',
    B: '梦想金',
    C: '牛马金',
  },

  // Account colors
  ACCOUNT_COLORS: {
    A: '#4A90D9',
    B: '#27ae60',
    C: '#9b59b6',
  },

  // Roles
  ROLE: {
    PARENT: 'parent',
    CHILD: 'child',
  },

  // Transaction type labels
  TX_TYPE_LABELS: {
    income_split_a: 'A 收入分流',
    income_split_b: 'B 收入分流',
    income_split_c: 'C 收入分流',
    a_spend: 'A 消费',
    purchase_debit_principal: 'B 购买(本金)',
    purchase_debit_interest: 'B 购买(利息)',
    refund_credit_principal: 'B 退款(本金)',
    refund_credit_interest: 'B 退款(利息)',
    c_redemption: 'C 赎回',
    c_redemption_fee: 'C 赎回手续费',
    c_dividend: 'C 派息',
    b_overflow: 'B 溢出→C',
    b_interest: 'B 利息',
    violation_penalty: '违约罚金',
    violation_penalty_credit: '违约罚金(入C)',
    violation_transfer: '违约转移(A→C)',
    debt_repayment: '欠款偿还',
    escrow_in: '代管入金',
    escrow_out: '代管释放',
  },
};
