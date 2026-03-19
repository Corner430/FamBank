'use strict';
const cloud = require('wx-server-sdk');
cloud.init({ env: cloud.DYNAMIC_CURRENT_ENV });

const { createLogger, getOrCreateUser, ok, unauthorized, serverError } = require('@fambank/shared');

exports.main = async (event, context) => {
  const log = createLogger('auth', context);
  const { OPENID } = cloud.getWXContext();
  if (!OPENID) return unauthorized();

  const { action } = event;

  try {
    switch (action) {
      case 'login':
        return await handleLogin(OPENID);
      default:
        return { code: 400, msg: '未知操作: ' + action };
    }
  } catch (e) {
    if (e.result) return e.result;
    log.error(action, '系统异常', e);
    return serverError();
  }
};

async function handleLogin(openid) {
  const user = await getOrCreateUser(openid);
  return ok({
    id: parseInt(user.id),
    role: user.role,
    name: user.name,
    family_id: user.family_id ? parseInt(user.family_id) : null,
    birth_date: user.birth_date,
  });
}
