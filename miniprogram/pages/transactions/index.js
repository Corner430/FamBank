const { callCloud } = require('../../utils/cloud');
const { isParent, waitForLogin } = require('../../utils/auth');

Page({
  data: {
    items: [],
    total: 0,
    page: 1,
    pageSize: 20,
    loading: false,
    hasMore: true,
    filterAccount: '',
    children: [],
    selectedChildId: null,
    isParent: false,
    filters: [
      { key: '', label: '全部' },
      { key: 'A', label: 'A' },
      { key: 'B', label: 'B' },
      { key: 'C', label: 'C' },
    ],
  },

  onShow() {
    waitForLogin((user) => {
      const parentRole = isParent();
      this.setData({ isParent: parentRole });
      if (parentRole) {
        this.loadChildren();
      } else {
        this.setData({ selectedChildId: user.id });
        this.loadTransactions(true);
      }
    });
  },

  async loadChildren() {
    try {
      const dashboard = await callCloud('family', 'dashboard');
      const children = (dashboard.children || []).map((c) => ({
        id: c.user_id,
        name: c.name,
      }));
      if (children.length > 0) {
        this.setData({
          children,
          selectedChildId: children[0].id,
        });
        this.loadTransactions(true);
      }
    } catch (err) {
      console.error('加载孩子列表失败:', err);
    }
  },

  async loadTransactions(reset) {
    const { selectedChildId, filterAccount, pageSize, loading } = this.data;
    if (loading) return;
    if (!selectedChildId) return;

    const page = reset ? 1 : this.data.page;
    this.setData({ loading: true });

    try {
      const params = {
        childId: selectedChildId,
        page,
        pageSize,
      };
      if (filterAccount) {
        params.accountType = filterAccount;
      }
      const result = await callCloud('transactions', 'list', params);
      const newItems = result.items || [];
      this.setData({
        items: reset ? newItems : this.data.items.concat(newItems),
        total: result.total || 0,
        page: page + 1,
        hasMore: newItems.length >= pageSize,
      });
    } catch (err) {
      console.error('加载交易记录失败:', err);
    } finally {
      this.setData({ loading: false });
      wx.stopPullDownRefresh();
    }
  },

  onFilterChange(e) {
    const filterAccount = e.currentTarget.dataset.key;
    this.setData({ filterAccount });
    this.loadTransactions(true);
  },

  onChildSelect(e) {
    const selectedChildId = e.detail.childId;
    this.setData({ selectedChildId });
    this.loadTransactions(true);
  },

  onReachBottom() {
    if (this.data.hasMore && !this.data.loading) {
      this.loadTransactions(false);
    }
  },

  onPullDownRefresh() {
    this.loadTransactions(true);
  },
});
