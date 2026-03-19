App({
  globalData: {
    user: null,
    loginReady: false,
  },

  onLaunch() {
    if (!wx.cloud) {
      console.error('请使用 2.2.3 或以上的基础库以使用云能力');
      return;
    }
    wx.cloud.init({
      env: 'fambank-prod-5g8v3rta823bda48',
      traceUser: true,
    });
    this.doLogin();
  },

  doLogin() {
    wx.cloud.callFunction({
      name: 'auth',
      data: { action: 'login' },
    }).then(res => {
      const result = res.result;
      if (result.code === 0) {
        this.globalData.user = result.data;
        this.globalData.loginReady = true;
        if (this.loginReadyCallbacks) {
          this.loginReadyCallbacks.forEach(cb => cb(result.data));
          this.loginReadyCallbacks = null;
        }
        // If no family, redirect to onboarding
        if (!result.data.family_id) {
          wx.redirectTo({ url: '/pages/onboarding/index' });
        }
      } else {
        console.error('Login failed:', result.msg);
        wx.showToast({ title: '登录失败', icon: 'none' });
      }
    }).catch(err => {
      console.error('Login error:', err);
      wx.showToast({ title: '登录失败', icon: 'none' });
    });
  },
});
