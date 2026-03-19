const { callCloud } = require('../../utils/cloud');
const { isParent, isChild, waitForLogin } = require('../../utils/auth');
const { ACCOUNT_NAMES, ACCOUNT_COLORS, TX_TYPE_LABELS } = require('../../utils/constants');

Page({
  data: {
    role: '',
    loading: true,
    // Parent data
    familyName: '',
    totalAssets: '0.00',
    children: [],
    // Child data
    accounts: [],
    totalDebt: '0.00',
    recentTransactions: [],
  },

  onShow() {
    waitForLogin((user) => {
      if (!user) return;
      this.setData({ role: user.role });
      if (isParent()) {
        this.loadParentDashboard();
      } else if (isChild()) {
        this.loadChildDashboard();
      }
    });
  },

  async loadParentDashboard() {
    this.setData({ loading: true });
    try {
      const res = await callCloud('family', 'dashboard');
      // Cloud function already returns yuan-formatted strings
      const children = (res.children || []).map(child => ({
        ...child,
        displayA: child.accounts.A,
        displayB: child.accounts.B_principal,
        displayC: child.accounts.C,
        displayTotal: child.total,
      }));
      this.setData({
        familyName: res.family_name || 'FamBank',
        totalAssets: res.total_assets,
        children,
        loading: false,
      });
    } catch (err) {
      console.error('加载仪表盘失败', err);
      wx.showToast({ title: '加载失败', icon: 'none' });
      this.setData({ loading: false });
    }
  },

  async loadChildDashboard() {
    this.setData({ loading: true });
    try {
      const [accountsRes, txRes] = await Promise.all([
        callCloud('accounts', 'list'),
        callCloud('transactions', 'list', { page: 1, pageSize: 5 }),
      ]);
      // Cloud function already returns yuan-formatted strings
      const accounts = (accountsRes.accounts || []).map(acc => ({
        ...acc,
        displayBalance: acc.balance,
        name: ACCOUNT_NAMES[acc.type] || acc.type,
        color: ACCOUNT_COLORS[acc.type] || '#999',
      }));
      const items = txRes.items || [];
      const recentTransactions = items.map(tx => ({
        ...tx,
        displayAmount: tx.amount,
        typeLabel: TX_TYPE_LABELS[tx.type] || tx.type,
        displayDate: tx.timestamp ? tx.timestamp.substring(0, 10) : '',
      }));
      this.setData({
        accounts,
        totalDebt: accountsRes.total_debt,
        totalDebtValue: parseFloat(accountsRes.total_debt || '0'),
        recentTransactions,
        loading: false,
      });
    } catch (err) {
      console.error('加载账户失败', err);
      wx.showToast({ title: '加载失败', icon: 'none' });
      this.setData({ loading: false });
    }
  },

  onTapChild(e) {
    const { childId, childName } = e.currentTarget.dataset;
    wx.navigateTo({
      url: `/pages/child-detail/index?childId=${childId}&childName=${encodeURIComponent(childName)}`,
    });
  },

  onTapIncome() {
    wx.navigateTo({ url: '/pages/income/index' });
  },
});
