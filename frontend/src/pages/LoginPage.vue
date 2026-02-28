<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { api, setToken, setStoredUser, ApiError } from '../services/api'

const router = useRouter()
const pin = ref('')
const error = ref('')
const loading = ref(false)
const needsSetup = ref(false)

// Setup form
const parentName = ref('爸爸')
const parentPin = ref('')
const childName = ref('')
const childPin = ref('')
const childBirthDate = ref('')

onMounted(async () => {
  try {
    const status = await api.get<{ initialized: boolean }>('/auth/status')
    needsSetup.value = !status.initialized
  } catch {
    error.value = '无法连接服务器'
  }
})

async function handleLogin() {
  error.value = ''
  loading.value = true
  try {
    const res = await api.post<{ user: { id: number; role: string; name: string }; token: string }>(
      '/auth/login',
      { pin: pin.value }
    )
    setToken(res.token)
    setStoredUser(res.user)
    router.push('/')
  } catch (e) {
    if (e instanceof ApiError) {
      error.value = e.message
    } else {
      error.value = '登录失败'
    }
  } finally {
    loading.value = false
  }
}

async function handleSetup() {
  error.value = ''
  loading.value = true
  try {
    await api.post('/auth/setup', {
      parent_name: parentName.value,
      parent_pin: parentPin.value,
      child_name: childName.value,
      child_pin: childPin.value,
      child_birth_date: childBirthDate.value || null,
    })
    needsSetup.value = false
  } catch (e) {
    if (e instanceof ApiError) {
      error.value = e.message
    } else {
      error.value = '初始化失败'
    }
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <h1>FamBank 家庭内部银行</h1>

    <div v-if="needsSetup" class="setup-form">
      <h2>首次设置</h2>
      <div class="form-group">
        <label>甲方（家长）名称</label>
        <input v-model="parentName" type="text" placeholder="如：爸爸" />
      </div>
      <div class="form-group">
        <label>甲方管理密码</label>
        <input v-model="parentPin" type="password" placeholder="设置管理密码" />
      </div>
      <div class="form-group">
        <label>乙方（孩子）名称</label>
        <input v-model="childName" type="text" placeholder="如：小明" />
      </div>
      <div class="form-group">
        <label>乙方 PIN 码</label>
        <input v-model="childPin" type="password" placeholder="设置简单 PIN 码" />
      </div>
      <div class="form-group">
        <label>乙方出生日期（可选）</label>
        <input v-model="childBirthDate" type="date" />
      </div>
      <button @click="handleSetup" :disabled="loading || !parentPin || !childName || !childPin">
        {{ loading ? '初始化中...' : '完成设置' }}
      </button>
    </div>

    <div v-else class="login-form">
      <h2>请输入 PIN 码登录</h2>
      <div class="form-group">
        <input
          v-model="pin"
          type="password"
          placeholder="输入 PIN 码 / 密码"
          @keyup.enter="handleLogin"
        />
      </div>
      <button @click="handleLogin" :disabled="loading || !pin">
        {{ loading ? '登录中...' : '登录' }}
      </button>
    </div>

    <p v-if="error" class="error">{{ error }}</p>
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

.error {
  color: #e74c3c;
  text-align: center;
  margin-top: 16px;
}
</style>
