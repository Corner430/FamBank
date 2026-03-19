const { callCloud } = require('../../utils/cloud');
const { waitForLogin, requireParent } = require('../../utils/auth');

Page({
  data: {
    settlements: [],
    executing: false,
    latestResult: null,
    loading: true,
  },

  onLoad() {
    waitForLogin((user) => {
      if (!user) return;
      if (!requireParent()) return;
    });
  },

  onShow() {
    this.loadHistory();
  },

  async loadHistory() {
    this.setData({ loading: true });
    try {
      const res = await callCloud('settlement', 'list');
      // Cloud function already returns yuan-formatted strings
      const settlements = (res || []).map(s => ({
        ...s,
        displayDate: s.settlement_date || '',
      }));
      this.setData({ settlements, loading: false });
    } catch (err) {
      console.error('加载结算历史失败', err);
      wx.showToast({ title: '加载失败', icon: 'none' });
      this.setData({ loading: false });
    }
  },

  handleExecute() {
    wx.showModal({
      title: '确认执行结算',
      content: '将对所有孩子执行月度结算，包括计算利息、派息、溢出处理等。确定执行吗？',
      success: async (res) => {
        if (!res.confirm) return;
        this.setData({ executing: true });
        try {
          const today = this.formatDate(new Date());
          const result = await callCloud('settlement', 'execute', { settlementDate: today });
          // Cloud function already returns yuan-formatted strings
          const latestResult = {
            settlement_date: result.settlement_date,
            results: result.results || [],
          };
          this.setData({ latestResult, executing: false });
          wx.showToast({ title: '结算完成', icon: 'success' });
          this.loadHistory();
        } catch (err) {
          console.error('执行结算失败', err);
          wx.showToast({ title: err.message || '结算失败', icon: 'none' });
          this.setData({ executing: false });
        }
      },
    });
  },

  formatDate(date) {
    const y = date.getFullYear();
    const m = String(date.getMonth() + 1).padStart(2, '0');
    const d = String(date.getDate()).padStart(2, '0');
    return `${y}-${m}-${d}`;
  },
});
