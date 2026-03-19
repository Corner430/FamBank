const { callCloud } = require('../../utils/cloud');
const { waitForLogin, requireParent } = require('../../utils/auth');
const { yuanToCents } = require('../../utils/money');
const { ACCOUNT_NAMES } = require('../../utils/constants');

Page({
  data: {
    childId: null,
    childName: '',
    accounts: [],
    totalDebt: '0.00',
    loading: true,
    // Modal state
    showModal: false,
    modalType: '', // 'spendA' | 'purchaseB' | 'refundB'
    modalTitle: '',
    modalAmount: '',
    modalDescription: '',
    modalLoading: false,
  },

  onLoad(options) {
    const childId = options.childId;
    const childName = decodeURIComponent(options.childName || '');
    this.setData({ childId, childName });

    if (childName) {
      wx.setNavigationBarTitle({ title: childName });
    }

    waitForLogin(() => {
      if (!requireParent()) return;
      this.loadAccounts();
    });
  },

  async loadAccounts() {
    const { childId } = this.data;
    if (!childId) return;

    this.setData({ loading: true });
    try {
      const result = await callCloud('accounts', 'list', { childId });
      // Cloud function already returns yuan-formatted strings
      const accounts = (result.accounts || []).map((acc) => ({
        ...acc,
        balanceYuan: acc.balance,
        interestPoolYuan: acc.interest_pool || null,
        displayName: ACCOUNT_NAMES[acc.type] || acc.name,
      }));
      this.setData({
        accounts,
        totalDebt: result.total_debt,
      });
    } catch (err) {
      console.error('加载账户失败:', err);
    } finally {
      this.setData({ loading: false });
    }
  },

  // Modal operations
  openSpendA() {
    this.setData({
      showModal: true,
      modalType: 'spendA',
      modalTitle: 'A 消费',
      modalAmount: '',
      modalDescription: '',
    });
  },

  openPurchaseB() {
    this.setData({
      showModal: true,
      modalType: 'purchaseB',
      modalTitle: 'B 购买',
      modalAmount: '',
      modalDescription: '',
    });
  },

  openRefundB() {
    this.setData({
      showModal: true,
      modalType: 'refundB',
      modalTitle: 'B 退款',
      modalAmount: '',
      modalDescription: '',
    });
  },

  closeModal() {
    this.setData({
      showModal: false,
      modalType: '',
      modalAmount: '',
      modalDescription: '',
    });
  },

  onModalAmountInput(e) {
    this.setData({ modalAmount: e.detail.value });
  },

  onModalDescriptionInput(e) {
    this.setData({ modalDescription: e.detail.value });
  },

  async handleModalSubmit() {
    const { childId, modalType, modalAmount, modalDescription, modalLoading } = this.data;
    if (modalLoading) return;

    // Validate format locally, but send yuan string - cloud function does yuanToCents internally
    let amountCheck;
    try {
      amountCheck = yuanToCents(modalAmount);
    } catch (err) {
      wx.showToast({ title: '请输入正确的金额', icon: 'none' });
      return;
    }

    if (amountCheck <= 0) {
      wx.showToast({ title: '金额必须大于0', icon: 'none' });
      return;
    }

    if (!modalDescription.trim()) {
      wx.showToast({ title: '请输入说明', icon: 'none' });
      return;
    }

    const actionMap = {
      spendA: 'spendA',
      purchaseB: 'purchaseB',
      refundB: 'refundB',
    };

    const action = actionMap[modalType];
    if (!action) return;

    this.setData({ modalLoading: true });
    try {
      await callCloud('accounts', action, {
        childId,
        amount: modalAmount,
        description: modalDescription.trim(),
      });
      wx.showToast({ title: '操作成功', icon: 'success' });
      this.closeModal();
      this.loadAccounts();
    } catch (err) {
      console.error(`${modalType} 操作失败:`, err);
    } finally {
      this.setData({ modalLoading: false });
    }
  },

  navigateToTransactions() {
    wx.navigateTo({
      url: `/pages/transactions/index?childId=${this.data.childId}`,
    });
  },

  navigateToWishlist() {
    wx.navigateTo({
      url: `/pages/wishlist/index?childId=${this.data.childId}`,
    });
  },

  navigateToIncome() {
    wx.navigateTo({
      url: '/pages/income/index',
    });
  },

  navigateToRedemption() {
    wx.navigateTo({
      url: `/pages/redemption/index?childId=${this.data.childId}`,
    });
  },
});
