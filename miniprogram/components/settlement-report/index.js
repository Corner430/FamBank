const { centsToYuan } = require('../../utils/money');
const { ACCOUNT_NAMES } = require('../../utils/constants');

Component({
  properties: {
    report: {
      type: Object,
      value: null,
    },
  },

  data: {
    accountNames: ACCOUNT_NAMES,
  },

  observers: {
    'report': function (report) {
      if (!report) return;
      this.setData({
        formatted: {
          cDividend: centsToYuan(report.c_dividend),
          bOverflow: centsToYuan(report.b_overflow),
          bInterest: centsToYuan(report.b_interest),
          violationTransfer: centsToYuan(report.violation_transfer),
          pActive: report.p_active != null ? String(report.p_active) : '--',
        },
        snapshotBefore: report.snapshot_before ? this._formatSnapshot(report.snapshot_before) : null,
        snapshotAfter: report.snapshot_after ? this._formatSnapshot(report.snapshot_after) : null,
      });
    },
  },

  methods: {
    _formatSnapshot(snapshot) {
      return {
        a: centsToYuan(snapshot.a),
        b: centsToYuan(snapshot.b),
        c: centsToYuan(snapshot.c),
        bInterestPool: centsToYuan(snapshot.b_interest_pool),
      };
    },
  },
});
