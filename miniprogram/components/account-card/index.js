const { ACCOUNT_NAMES, ACCOUNT_COLORS } = require('../../utils/constants');

Component({
  properties: {
    account: {
      type: Object,
      value: {},
    },
  },

  data: {
    accountNames: ACCOUNT_NAMES,
    accountColors: ACCOUNT_COLORS,
  },

  observers: {
    account(val) {
      if (!val || !val.type) return;
      this.setData({
        _type: val.type,
        _name: val.name || ACCOUNT_NAMES[val.type] || val.type,
        _balance: val.balance || '0.00',
        _interestPool: val.interest_pool || val.interestPool || '0.00',
        _isInterestSuspended: !!val.is_interest_suspended,
        _isDepositSuspended: !!val.is_deposit_suspended,
      });
    },
  },

  methods: {},
});
