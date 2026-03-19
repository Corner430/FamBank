'use strict';

/**
 * 创建一个绑定了函数名和请求上下文的 logger 实例。
 * 
 * @param {string} funcName  - 云函数名称，如 'income'
 * @param {object} context   - 云函数 context 参数（含 request_id 等）
 * @returns {object} logger 实例，含 info/warn/error/audit 方法
 */
function createLogger(funcName, context) {
  const requestId = (context && context.request_id) || '';

  function emit(level, action, message, extra) {
    const entry = {
      timestamp: new Date().toISOString(),
      level,
      func: funcName,
      action: action || '',
      requestId,
      message,
    };
    if (extra !== undefined && extra !== null) {
      if (extra instanceof Error) {
        entry.error = { message: extra.message, stack: extra.stack };
      } else {
        entry.data = extra;
      }
    }
    const json = JSON.stringify(entry);
    switch (level) {
      case 'error': console.error(json); break;
      case 'warn':  console.warn(json);  break;
      default:      console.log(json);   break;
    }
  }

  return {
    /**
     * 记录普通信息
     * @param {string} action  - 当前 action 名称
     * @param {string} message - 日志消息
     * @param {*} [extra]      - 附加数据
     */
    info(action, message, extra) {
      emit('info', action, message, extra);
    },

    /**
     * 记录警告
     * @param {string} action  - 当前 action 名称
     * @param {string} message - 日志消息
     * @param {*} [extra]      - 附加数据
     */
    warn(action, message, extra) {
      emit('warn', action, message, extra);
    },

    /**
     * 记录错误
     * @param {string} action  - 当前 action 名称
     * @param {string} message - 日志消息
     * @param {*} [extra]      - 附加数据（通常为 Error 对象）
     */
    error(action, message, extra) {
      emit('error', action, message, extra);
    },

    /**
     * 记录业务审计日志（关键金融操作）
     * @param {string} action    - action 名称
     * @param {string} operation - 操作类型，如 'income_create', 'spend_a'
     * @param {object} detail    - 操作详情（金额、用户 ID 等）
     */
    audit(action, operation, detail) {
      emit('info', action, `[AUDIT] ${operation}`, detail);
    },
  };
}

module.exports = { createLogger };
