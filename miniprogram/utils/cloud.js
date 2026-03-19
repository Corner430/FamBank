/**
 * CloudBase cloud function call wrapper
 */
function callCloud(name, action, data = {}) {
  return new Promise((resolve, reject) => {
    wx.cloud.callFunction({
      name,
      data: { action, ...data },
    }).then(res => {
      const result = res.result;
      if (result && result.code === 0) {
        resolve(result.data !== undefined ? result.data : result);
      } else {
        const msg = (result && result.msg) || '操作失败';
        wx.showToast({ title: msg, icon: 'none' });
        reject(new Error(msg));
      }
    }).catch(err => {
      console.error(`[callCloud] ${name}/${action} error:`, err);
      wx.showToast({ title: '网络异常，请重试', icon: 'none' });
      reject(err);
    });
  });
}

module.exports = { callCloud };
