const { callCloud } = require('../../utils/cloud');
const { waitForLogin, requireParent } = require('../../utils/auth');
const { centsToYuan, yuanToCents } = require('../../utils/money');

Page({
  data: {
    children: [],
    selectedChildId: null,
    amount: '',
    description: '',
    loading: false,
    result: null,
  },

  onLoad() {
    waitForLogin(() => {
      if (!requireParent()) return;
      this.loadChildren();
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
      }
    } catch (err) {
      console.error('加载孩子列表失败:', err);
    }
  },

  onChildSelect(e) {
    this.setData({ selectedChildId: e.detail.childId });
  },

  onAmountInput(e) {
    this.setData({ amount: e.detail.value });
  },

  onDescriptionInput(e) {
    this.setData({ description: e.detail.value });
  },

  async handleSubmit() {
    const { selectedChildId, amount, description, loading } = this.data;
    if (loading) return;

    if (!selectedChildId) {
      wx.showToast({ title: '请选择孩子', icon: 'none' });
      return;
    }

    // Validate format locally, but send yuan string - cloud function does yuanToCents internally
    let amountCheck;
    try {
      amountCheck = yuanToCents(amount);
    } catch (err) {
      wx.showToast({ title: '请输入正确的金额', icon: 'none' });
      return;
    }

    if (amountCheck <= 0) {
      wx.showToast({ title: '金额必须大于0', icon: 'none' });
      return;
    }

    if (!description.trim()) {
      wx.showToast({ title: '请输入收入说明', icon: 'none' });
      return;
    }

    this.setData({ loading: true });
    try {
      const result = await callCloud('income', 'create', {
        childId: selectedChildId,
        amount: amount,
        description: description.trim(),
      });
      this.setData({
        result: {
          total: result.total,
          splitA: result.split.A,
          splitB: result.split.B,
          splitC: result.split.C,
          debtRepaid: result.debt_repaid,
          escrowed: result.escrowed,
        },
      });
      wx.showToast({ title: '记录成功', icon: 'success' });
    } catch (err) {
      console.error('记录收入失败:', err);
    } finally {
      this.setData({ loading: false });
    }
  },

  handleRecordAnother() {
    this.setData({
      amount: '',
      description: '',
      result: null,
    });
  },
});
