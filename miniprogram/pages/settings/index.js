const { callCloud } = require('../../utils/cloud');
const { getUser, isParent, waitForLogin } = require('../../utils/auth');

Page({
  data: {
    user: null,
    familyDetail: null,
    loading: true,
    isParent: false,
  },

  onShow() {
    waitForLogin((user) => {
      this.setData({
        user,
        isParent: isParent(),
      });
      this.loadFamilyDetail();
    });
  },

  async loadFamilyDetail() {
    this.setData({ loading: true });
    try {
      const detail = await callCloud('family', 'detail');
      this.setData({ familyDetail: detail });
    } catch (err) {
      console.error('加载家庭信息失败:', err);
    } finally {
      this.setData({ loading: false });
    }
  },

  navigateToConfig() {
    wx.navigateTo({ url: '/pages/config/index' });
  },

  navigateToSettlement() {
    wx.navigateTo({ url: '/pages/settlement/index' });
  },

  navigateToViolations() {
    wx.navigateTo({ url: '/pages/violation/index' });
  },

  navigateToRedemption() {
    wx.navigateTo({ url: '/pages/redemption/index' });
  },
});
