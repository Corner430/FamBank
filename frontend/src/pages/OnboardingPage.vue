<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { api, setToken, setStoredUser, getStoredUser, logout as doLogout, ApiError } from '../services/api'

const router = useRouter()
const mode = ref<'choose' | 'create' | 'join'>('choose')
const error = ref('')
const loading = ref(false)
const checking = ref(true)

// Create family form
const familyName = ref('')
const creatorName = ref('')

// Join family form
const inviteCode = ref('')

// Check if user already has a family (e.g. previous create succeeded but client didn't update)
onMounted(async () => {
  try {
    const res = await api.get<{
      family: { id: number; name: string }
      members: { id: number; name: string | null; role: string | null }[]
    }>('/family')
    // User already has a family — sync local state and redirect
    const user = getStoredUser()
    if (user) {
      const me = res.members.find(m => m.id === user.id)
      setStoredUser({
        ...user,
        family_id: res.family.id,
        role: me?.role ?? user.role,
        name: me?.name ?? user.name,
      })
    }
    router.replace(user?.role === 'parent' ? '/dashboard' : '/')
  } catch {
    // 401/404 = no family yet, stay on onboarding
  } finally {
    checking.value = false
  }
})

function handleLogout() {
  doLogout()
  router.push('/login')
}

async function handleCreate() {
  if (!familyName.value.trim()) {
    error.value = '请输入家庭名称'
    return
  }
  error.value = ''
  loading.value = true
  try {
    const res = await api.post<{
      family: { id: number; name: string; created_at: string }
      access_token: string
    }>('/family', {
      name: familyName.value.trim(),
      creator_name: creatorName.value.trim() || undefined,
    })

    // Update stored token and user
    setToken(res.access_token)
    const user = getStoredUser()
    if (user) {
      setStoredUser({
        ...user,
        family_id: res.family.id,
        role: 'parent',
        name: creatorName.value.trim() || '家长',
      })
    }
    router.push('/dashboard')
  } catch (e) {
    if (e instanceof ApiError) {
      error.value = e.message
    } else {
      error.value = '创建家庭失败'
    }
  } finally {
    loading.value = false
  }
}

async function handleJoin() {
  if (!inviteCode.value.trim() || inviteCode.value.trim().length !== 8) {
    error.value = '请输入8位邀请码'
    return
  }
  error.value = ''
  loading.value = true
  try {
    const res = await api.post<{
      family: { id: number; name: string; created_at: string }
      role: string
      name: string
      access_token: string
    }>('/family/join', {
      code: inviteCode.value.trim().toUpperCase(),
    })

    // Update stored token and user
    setToken(res.access_token)
    const user = getStoredUser()
    if (user) {
      setStoredUser({
        ...user,
        family_id: res.family.id,
        role: res.role,
        name: res.name,
      })
    }

    if (res.role === 'parent') {
      router.push('/dashboard')
    } else {
      router.push('/')
    }
  } catch (e) {
    if (e instanceof ApiError) {
      error.value = e.message
    } else {
      error.value = '加入家庭失败'
    }
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="onboarding-page">
    <h1>FamBank 家庭内部银行</h1>

    <p v-if="checking" style="text-align: center; color: #999;">加载中...</p>

    <template v-else>
    <div v-if="mode === 'choose'" class="choose-mode">
      <h2>欢迎！请选择操作</h2>
      <button class="primary-btn" @click="mode = 'create'">创建家庭</button>
      <button class="secondary-btn" @click="mode = 'join'">输入邀请码</button>
    </div>

    <div v-else-if="mode === 'create'" class="create-form">
      <h2>创建家庭</h2>
      <div class="form-group">
        <label>家庭名称</label>
        <input v-model="familyName" type="text" placeholder="如：张家" maxlength="100" />
      </div>
      <div class="form-group">
        <label>您的昵称（可选）</label>
        <input v-model="creatorName" type="text" placeholder="如：爸爸（默认为家长）" maxlength="50" />
      </div>
      <button class="primary-btn" @click="handleCreate" :disabled="loading || !familyName.trim()">
        {{ loading ? '创建中...' : '创建家庭' }}
      </button>
      <button class="back-btn" @click="mode = 'choose'" :disabled="loading">返回</button>
    </div>

    <div v-else-if="mode === 'join'" class="join-form">
      <h2>输入邀请码</h2>
      <div class="form-group">
        <label>邀请码</label>
        <input
          v-model="inviteCode"
          type="text"
          placeholder="请输入8位邀请码"
          maxlength="8"
          style="text-transform: uppercase;"
        />
      </div>
      <button class="primary-btn" @click="handleJoin" :disabled="loading || inviteCode.trim().length !== 8">
        {{ loading ? '加入中...' : '加入家庭' }}
      </button>
      <button class="back-btn" @click="mode = 'choose'" :disabled="loading">返回</button>
    </div>

    <p v-if="error" class="error">{{ error }}</p>
    </template>

    <button class="logout-btn" @click="handleLogout">退出登录</button>
  </div>
</template>

<style scoped>
.onboarding-page {
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

.choose-mode {
  display: flex;
  flex-direction: column;
  gap: 12px;
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

.primary-btn {
  width: 100%;
  padding: 12px;
  background: #4a90d9;
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 1em;
  cursor: pointer;
  margin-bottom: 8px;
}

.primary-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.secondary-btn {
  width: 100%;
  padding: 12px;
  background: transparent;
  color: #4a90d9;
  border: 1px solid #4a90d9;
  border-radius: 6px;
  font-size: 1em;
  cursor: pointer;
}

.back-btn {
  width: 100%;
  padding: 10px;
  background: transparent;
  color: #999;
  border: none;
  font-size: 0.9em;
  cursor: pointer;
  margin-top: 4px;
}

.error {
  color: #e74c3c;
  text-align: center;
  margin-top: 16px;
}

.logout-btn {
  width: 100%;
  padding: 10px;
  background: transparent;
  color: #999;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 0.9em;
  cursor: pointer;
  margin-top: 32px;
}

.logout-btn:hover {
  color: #e74c3c;
  border-color: #e74c3c;
}
</style>
