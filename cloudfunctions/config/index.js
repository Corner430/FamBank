'use strict';
const cloud = require('wx-server-sdk');
cloud.init({ env: cloud.DYNAMIC_CURRENT_ENV });

const {
  createLogger,
  getUserByOpenid, requireParent,
  query, getAllConfig, DEFAULT_CONFIG,
  ok, badRequest, serverError
} = require('@fambank/shared');

exports.main = async (event, context) => {
  const log = createLogger('config', context);
  const { OPENID } = cloud.getWXContext();
  if (!OPENID) return { code: 401, msg: '未授权' };
  const user = await getUserByOpenid(OPENID);
  if (!user) return { code: 401, msg: '用户不存在' };
  requireParent(user);

  try {
    switch (event.action) {
      case 'list': return await handleList(user);
      case 'announce': return await handleAnnounce(user, event);
      case 'listAnnouncements': return await handleListAnnouncements(user);
      default: return badRequest('未知操作');
    }
  } catch (e) {
    if (e.result) return e.result;
    log.error(event.action, '系统异常', e);
    return serverError();
  }
};

async function handleList(user) {
  const config = await getAllConfig(user.family_id);
  return ok(config);
}

async function handleAnnounce(user, event) {
  const { key, newValue } = event;
  if (!key || newValue === undefined) return badRequest('请指定参数和新值');
  if (!(key in DEFAULT_CONFIG)) return badRequest('无效的参数: ' + key);

  const parsedValue = parseInt(newValue);
  if (isNaN(parsedValue)) return badRequest('参数值必须为整数');

  // Validate split ratios sum to 100
  const config = await getAllConfig(user.family_id);
  const splitKeys = ['split_ratio_a', 'split_ratio_b', 'split_ratio_c'];
  if (splitKeys.includes(key)) {
    const proposed = { ...config, [key]: parsedValue };
    const sum = splitKeys.reduce((s, k) => s + proposed[k], 0);
    if (sum !== 100) return badRequest(`分流比例之和必须为100%，当前为${sum}%`);
  }

  // Get current value
  const oldValue = config[key];

  // Effective from: first day of next month
  const now = new Date();
  const effectiveFrom = new Date(now.getFullYear(), now.getMonth() + 1, 1);
  const announcedAt = now.toISOString().slice(0, 10);

  await query(
    'INSERT INTO announcement (family_id, config_key, old_value, new_value, announced_at, effective_from) VALUES (?, ?, ?, ?, ?, ?)',
    [user.family_id, key, String(oldValue), String(parsedValue), announcedAt, effectiveFrom.toISOString().slice(0, 10)]
  );

  log.audit(event.action, 'config_announce', { key, oldValue, newValue: parsedValue, effectiveFrom: effectiveFrom.toISOString().slice(0, 10) });

  return ok({
    key,
    old_value: oldValue,
    new_value: parsedValue,
    effective_from: effectiveFrom.toISOString().slice(0, 10),
  });
}

async function handleListAnnouncements(user) {
  const rows = await query(
    'SELECT id, config_key, old_value, new_value, announced_at, effective_from FROM announcement WHERE family_id = ? ORDER BY created_at DESC LIMIT 50',
    [user.family_id]
  );
  return ok(rows.map(r => ({
    id: Number(r.id),
    config_key: r.config_key,
    old_value: r.old_value,
    new_value: r.new_value,
    announced_at: r.announced_at,
    effective_from: r.effective_from,
  })));
}
