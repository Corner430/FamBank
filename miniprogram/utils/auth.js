/**
 * Auth utility - access user info from app.globalData
 */
function getUser() {
  const app = getApp();
  return app.globalData.user;
}

function isParent() {
  const user = getUser();
  return user && user.role === 'parent';
}

function isChild() {
  const user = getUser();
  return user && user.role === 'child';
}

function getUserId() {
  const user = getUser();
  return user ? user.id : null;
}

function getFamilyId() {
  const user = getUser();
  return user ? user.family_id : null;
}

/**
 * Wait for login to complete, then call callback with user.
 * Supports multiple callbacks (from multiple pages calling waitForLogin simultaneously).
 */
function waitForLogin(callback) {
  const app = getApp();
  if (app.globalData.loginReady) {
    callback(app.globalData.user);
  } else {
    if (!app.loginReadyCallbacks) {
      app.loginReadyCallbacks = [];
    }
    app.loginReadyCallbacks.push(callback);
  }
}

/**
 * Require parent role, navigate back if not
 */
function requireParent() {
  if (!isParent()) {
    wx.showToast({ title: '仅家长可操作', icon: 'none' });
    wx.navigateBack();
    return false;
  }
  return true;
}

module.exports = { getUser, isParent, isChild, getUserId, getFamilyId, waitForLogin, requireParent };
