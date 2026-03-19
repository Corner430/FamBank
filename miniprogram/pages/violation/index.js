const { callCloud } = require('../../utils/cloud');
const { yuanToCents } = require('../../utils/money');
const { waitForLogin, requireParent } = require('../../utils/auth');

Page({
  data: {
    children: [],
    selectedChildId: null,
    violations: [],
    showCreateForm: false,
    newAmount: '',
    newAmountEnteredA: '',
    newDescription: '',
    loading: true,
  },

  onLoad() {
    waitForLogin((user) => {
      if (!user) return;
      if (!requireParent()) return;
      this.loadChildren();
    });
  },

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
        this.loadViolations();
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
    this.loadViolations();
  },

  async loadViolations() {
    const { selectedChildId } = this.data;
    if (!selectedChildId) return;
    this.setData({ loading: true });
    try {
      const res = await callCloud('violations', 'list', { childId: selectedChildId });
      // Cloud function already returns yuan-formatted strings
      const violations = (res || []).map(v => ({
        ...v,
        displayAmount: v.violation_amount || '0.00',
        displayPenalty: v.penalty_amount || '0.00',
        displayDate: v.violation_date ? v.violation_date.substring(0, 10) : (v.created_at ? v.created_at.substring(0, 10) : ''),
      }));
      this.setData({ violations, loading: false });
    } catch (err) {
      console.error('加载违约记录失败', err);
      wx.showToast({ title: '加载失败', icon: 'none' });
      this.setData({ loading: false });
    }
  },

  toggleCreateForm() {
    this.setData({
      showCreateForm: !this.data.showCreateForm,
      newAmount: '',
      newAmountEnteredA: '',
      newDescription: '',
    });
  },

  onAmountInput(e) {
    this.setData({ newAmount: e.detail.value });
  },

  onAmountEnteredAInput(e) {
    this.setData({ newAmountEnteredA: e.detail.value });
  },

  onDescriptionInput(e) {
    this.setData({ newDescription: e.detail.value });
  },

  async handleCreate() {
    const { selectedChildId, newAmount, newAmountEnteredA, newDescription } = this.data;
    if (!selectedChildId) {
      wx.showToast({ title: '请选择孩子', icon: 'none' });
      return;
    }
    if (!newAmount) {
      wx.showToast({ title: '请输入违约金额', icon: 'none' });
      return;
    }
    if (!newDescription) {
      wx.showToast({ title: '请输入描述', icon: 'none' });
      return;
    }
    try {
      // Validate format locally, but send yuan strings - cloud function does yuanToCents internally
      const amountCheck = yuanToCents(newAmount);
      if (amountCheck <= 0) {
        wx.showToast({ title: '金额必须大于0', icon: 'none' });
        return;
      }
      const params = {
        childId: selectedChildId,
        amount: newAmount,
        description: newDescription,
      };
      if (newAmountEnteredA) {
        params.amountEnteredA = newAmountEnteredA;
      }
      const res = await callCloud('violations', 'create', params);
      let msg = '记录成功';
      if (res.is_escalated) {
        msg = '已升级处罚！罚金: ¥' + res.penalty;
      }
      wx.showToast({ title: msg, icon: 'success', duration: 2000 });
      this.setData({ showCreateForm: false });
      this.loadViolations();
    } catch (err) {
      console.error('创建违约记录失败', err);
      wx.showToast({ title: err.message || '创建失败', icon: 'none' });
    }
  },
});
