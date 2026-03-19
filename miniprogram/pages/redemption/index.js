const { callCloud } = require('../../utils/cloud');
const { centsToYuan, yuanToCents } = require('../../utils/money');
const { waitForLogin, isParent, isChild, getUserId } = require('../../utils/auth');

Page({
  data: {
    isParentRole: false,
    // Child view
    childId: '',
    cBalance: '0.00',
    amount: '',
    reason: '',
    // Parent view
    children: [],
    selectedChildId: null,
    // Shared
    requests: [],
    loading: true,
    submitting: false,
  },

  onLoad(options) {
    waitForLogin((user) => {
      if (!user) return;
      const parentRole = isParent();
      this.setData({ isParentRole: parentRole });

      if (parentRole) {
        this.loadChildren();
      } else {
        const childId = options.childId || getUserId();
        this.setData({ childId });
        this.loadChildData();
      }
    });
  },

  onShow() {
    if (this.data.childId || this.data.selectedChildId) {
      this.loadRequests();
    }
  },

  // --- Parent: load children list ---
  async loadChildren() {
    try {
      const res = await callCloud('family', 'dashboard');
      const children = (res.children || []).map(c => ({
        id: c.user_id,
        name: c.name,
      }));
      this.setData({ children });
      if (children.length > 0) {
        this.setData({ selectedChildId: children[0].id });
        this.loadRequests();
      } else {
        this.setData({ loading: false });
      }
    } catch (err) {
      console.error('加载孩子列表失败', err);
      this.setData({ loading: false });
    }
  },

  onChildChange(e) {
    const childId = e.detail.childId || e.detail;
    this.setData({ selectedChildId: childId });
    this.loadRequests();
  },

  // --- Child: load C balance ---
  async loadChildData() {
    this.setData({ loading: true });
    try {
      const res = await callCloud('accounts', 'list', { childId: this.data.childId });
      const accounts = res.accounts || [];
      const cAccount = accounts.find(a => a.type === 'C');
      this.setData({ cBalance: cAccount ? cAccount.balance : '0.00' });
      await this.loadRequests();
    } catch (err) {
      console.error('加载账户失败', err);
      this.setData({ loading: false });
    }
  },

  // --- Load redemption requests ---
  async loadRequests() {
    this.setData({ loading: true });
    try {
      const res = await callCloud('redemption', 'listPending');
      const requests = (res || []).map(r => ({
        ...r,
        displayAmount: r.amount,
        displayFee: r.fee,
        displayNet: r.net,
        displayDate: r.created_at ? r.created_at.substring(0, 10) : '',
        statusText: this.getStatusText(r.status),
        isPending: r.status === 'pending',
      }));
      this.setData({ requests, loading: false });
    } catch (err) {
      console.error('加载赎回记录失败', err);
      this.setData({ loading: false });
    }
  },

  getStatusText(status) {
    const map = {
      pending: '待审批',
      approved: '已通过',
      rejected: '已拒绝',
    };
    return map[status] || status;
  },

  // --- Child: submit request ---
  onAmountInput(e) {
    this.setData({ amount: e.detail.value });
  },

  onReasonInput(e) {
    this.setData({ reason: e.detail.value });
  },

  async handleSubmit() {
    const { amount, reason, submitting, childId } = this.data;
    if (submitting) return;

    if (!amount) {
      wx.showToast({ title: '请输入赎回金额', icon: 'none' });
      return;
    }
    try {
      const amountCheck = yuanToCents(amount);
      if (amountCheck <= 0) {
        wx.showToast({ title: '金额必须大于0', icon: 'none' });
        return;
      }
    } catch (err) {
      wx.showToast({ title: '请输入正确的金额', icon: 'none' });
      return;
    }

    this.setData({ submitting: true });
    try {
      const res = await callCloud('redemption', 'request', {
        childId,
        amount,
        reason: reason || '',
      });
      wx.showToast({
        title: '提交成功，手续费¥' + (res.fee || '0.00'),
        icon: 'none',
        duration: 2500,
      });
      this.setData({ amount: '', reason: '' });
      this.loadChildData();
    } catch (err) {
      console.error('提交赎回请求失败', err);
    } finally {
      this.setData({ submitting: false });
    }
  },

  // --- Parent: approve / reject ---
  async handleApprove(e) {
    const requestId = e.currentTarget.dataset.id;
    wx.showModal({
      title: '确认通过',
      content: '通过后将从C账户扣除金额并转入A账户（扣除手续费），确认？',
      success: async (res) => {
        if (res.confirm) {
          try {
            await callCloud('redemption', 'approve', { requestId, approve: true });
            wx.showToast({ title: '已通过', icon: 'success' });
            this.loadRequests();
          } catch (err) {
            console.error('审批失败', err);
          }
        }
      },
    });
  },

  async handleReject(e) {
    const requestId = e.currentTarget.dataset.id;
    wx.showModal({
      title: '确认拒绝',
      content: '确定拒绝该赎回请求？',
      success: async (res) => {
        if (res.confirm) {
          try {
            await callCloud('redemption', 'approve', { requestId, approve: false });
            wx.showToast({ title: '已拒绝', icon: 'success' });
            this.loadRequests();
          } catch (err) {
            console.error('拒绝失败', err);
          }
        }
      },
    });
  },
});
