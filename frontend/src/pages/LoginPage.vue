<script setup lang="ts">
import { ref, computed, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { sendCode, verifyCode, setToken, setRefreshToken, setStoredUser, ApiError } from '../services/api'

const router = useRouter()
const phone = ref('')
const code = ref('')
const error = ref('')
const loading = ref(false)
const codeSent = ref(false)
const countdown = ref(0)

let countdownTimer: ReturnType<typeof setInterval> | null = null

const phoneValid = computed(() => /^1\d{10}$/.test(phone.value))
const codeValid = computed(() => /^\d{6}$/.test(code.value))

function startCountdown() {
  countdown.value = 60
  countdownTimer = setInterval(() => {
    countdown.value--
    if (countdown.value <= 0) {
      if (countdownTimer) clearInterval(countdownTimer)
      countdownTimer = null
    }
  }, 1000)
}

onBeforeUnmount(() => {
  if (countdownTimer) {
    clearInterval(countdownTimer)
    countdownTimer = null
  }
})

async function handleSendCode() {
  if (!phoneValid.value) {
    error.value = '请输入正确的11位手机号'
    return
  }
  error.value = ''
  loading.value = true
  try {
    await sendCode(phone.value)
    codeSent.value = true
    startCountdown()
  } catch (e) {
    if (e instanceof ApiError) {
      error.value = e.message
    } else {
      error.value = '发送验证码失败'
    }
  } finally {
    loading.value = false
  }
}

async function handleVerify() {
  if (!codeValid.value) {
    error.value = '请输入6位数字验证码'
    return
  }
  error.value = ''
  loading.value = true
  try {
    const res = await verifyCode(phone.value, code.value)
    setToken(res.access_token)
    setRefreshToken(res.refresh_token)
    setStoredUser(res.user)

    // Redirect based on user state
    if (res.user.family_id === null) {
      router.push('/onboarding')
    } else if (res.user.role === 'parent') {
      router.push('/dashboard')
    } else {
      router.push('/')
    }
  } catch (e) {
    if (e instanceof ApiError) {
      error.value = e.message
    } else {
      error.value = '验证失败'
    }
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <h1>FamBank 家庭内部银行</h1>

    <div class="login-form">
      <h2>手机号登录</h2>

      <div class="form-group">
        <label>手机号</label>
        <input
          v-model="phone"
          type="tel"
          maxlength="11"
          placeholder="请输入手机号"
          :disabled="codeSent && countdown > 0"
          @keyup.enter="codeSent ? handleVerify() : handleSendCode()"
        />
        <p v-if="phone && !phoneValid" class="field-error">请输入正确的11位手机号</p>
      </div>

      <div v-if="!codeSent" class="actions">
        <button
          @click="handleSendCode"
          :disabled="loading || !phoneValid"
        >
          {{ loading ? '发送中...' : '获取验证码' }}
        </button>
      </div>

      <template v-else>
        <div class="form-group">
          <label>验证码</label>
          <input
            v-model="code"
            type="text"
            maxlength="6"
            inputmode="numeric"
            placeholder="请输入6位验证码"
            @keyup.enter="handleVerify"
          />
        </div>

        <div class="actions">
          <button
            @click="handleVerify"
            :disabled="loading || !codeValid"
          >
            {{ loading ? '登录中...' : '登录 / 注册' }}
          </button>
          <button
            class="resend-btn"
            @click="handleSendCode"
            :disabled="countdown > 0 || loading"
          >
            {{ countdown > 0 ? `重新发送 (${countdown}s)` : '重新发送' }}
          </button>
        </div>
      </template>

      <p v-if="error" class="error">{{ error }}</p>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  max-width: 400px;
  margin: 80px auto;
  padding: 24px;
}

h1 {
  text-align: center;
  margin-bottom: 32px;
}

h2 {
  text-align: center;
  margin-bottom: 24px;
  font-size: 1.2em;
}

.form-group {
  margin-bottom: 16px;
}

.form-group label {
  display: block;
  margin-bottom: 4px;
  font-size: 0.9em;
  color: #666;
}

.form-group input {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 1em;
  box-sizing: border-box;
}

.field-error {
  color: #e74c3c;
  font-size: 0.85em;
  margin-top: 4px;
}

.actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

button {
  width: 100%;
  padding: 12px;
  background: #4a90d9;
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 1em;
  cursor: pointer;
}

button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.resend-btn {
  background: transparent;
  color: #4a90d9;
  border: 1px solid #4a90d9;
}

.resend-btn:disabled {
  color: #999;
  border-color: #ddd;
}

.error {
  color: #e74c3c;
  text-align: center;
  margin-top: 16px;
}
</style>
