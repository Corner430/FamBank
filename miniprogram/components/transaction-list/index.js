const { TX_TYPE_LABELS } = require('../../utils/constants');

Component({
  properties: {
    items: {
      type: Array,
      value: [],
    },
    loading: {
      type: Boolean,
      value: false,
    },
    hasMore: {
      type: Boolean,
      value: false,
    },
  },

  data: {
    txTypeLabels: TX_TYPE_LABELS,
  },

  methods: {
    onScrollToLower() {
      if (!this.data.loading && this.data.hasMore) {
        this.triggerEvent('loadmore');
      }
    },
  },
});
