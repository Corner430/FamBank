'use strict';

function ok(data) {
  return { code: 0, data };
}

function fail(code, msg) {
  return { code, msg };
}

function badRequest(msg) {
  return { code: 400, msg };
}

function unauthorized(msg) {
  return { code: 401, msg: msg || '未授权' };
}

function forbidden(msg) {
  return { code: 403, msg: msg || '无权操作' };
}

function notFound(msg) {
  return { code: 404, msg: msg || '未找到' };
}

function serverError(msg) {
  return { code: 500, msg: msg || '系统异常，请重试' };
}

module.exports = { ok, fail, badRequest, unauthorized, forbidden, notFound, serverError };
