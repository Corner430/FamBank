const { callCloud } = require('../../utils/cloud');
const { getUser } = require('../../utils/auth');

Page({
  data: {
    mode: 'choose', // 'choose' | 'create' | 'join'
    familyName: '',
    userName: '',
    inviteCode: '',
    loading: false,
  },

  onLoad() {
    const user = getUser();
    if (user && user.family_id) {
      wx.switchTab({ url: '/pages/index/index' });
    }
  },

  switchMode(e) {
    const mode = e.currentTarget.dataset.mode;
    this.setData({ mode });
  },

  goBack() {
    this.setData({ mode: 'choose', familyName: '', userName: '', inviteCode: '' });
  },

  onFamilyNameInput(e) {
    this.setData({ familyName: e.detail.value });
  },

  onUserNameInput(e) {
    this.setData({ userName: e.detail.value });
  },

  onInviteCodeInput(e) {
    this.setData({ inviteCode: e.detail.value });
  },

  async handleCreate() {
    const { familyName, userName } = this.data;
    if (!familyName.trim()) {
      wx.showToast({ title: '请输入家庭名称', icon: 'none' });
      return;
    }
    if (!userName.trim()) {
      wx.showToast({ title: '请输入你的名字', icon: 'none' });
      return;
    }
    this.setData({ loading: true });
    try {
      const result = await callCloud('family', 'create', {
        familyName: familyName.trim(),
        userName: userName.trim(),
      });
      const app = getApp();
      app.globalData.user = {
        ...app.globalData.user,
        family_id: result.family_id,
        family_name: result.family_name,
        role: result.role,
        name: result.name,
      };
      wx.switchTab({ url: '/pages/index/index' });
    } catch (err) {
      console.error('创建家庭失败:', err);
    } finally {
      this.setData({ loading: false });
    }
  },

  async handleJoin() {
    const { inviteCode } = this.data;
    if (!inviteCode.trim() || inviteCode.trim().length !== 8) {
      wx.showToast({ title: '请输入8位邀请码', icon: 'none' });
      return;
    }
    this.setData({ loading: true });
    try {
      const result = await callCloud('family', 'join', {
        code: inviteCode.trim(),
      });
      const app = getApp();
      app.globalData.user = {
        ...app.globalData.user,
        family_id: result.family_id,
        role: result.role,
        name: result.name,
      };
      wx.switchTab({ url: '/pages/index/index' });
    } catch (err) {
      console.error('加入家庭失败:', err);
    } finally {
      this.setData({ loading: false });
    }
  },
});
