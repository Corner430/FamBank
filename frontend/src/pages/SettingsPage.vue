<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { api, getStoredUser, logout } from '../services/api'
import InvitationManager from '../components/InvitationManager.vue'
import FamilyMemberList from '../components/FamilyMemberList.vue'

const router = useRouter()
const user = getStoredUser()

const familyName = ref('')
const familyError = ref('')
const loadingFamily = ref(false)

async function loadFamily() {
  loadingFamily.value = true
  familyError.value = ''
  try {
    const res = await api.get<{
      family: { id: number; name: string; created_at: string }
      members: { id: number; name: string | null; role: string | null }[]
    }>('/family')
    familyName.value = res.family.name
  } catch {
    familyError.value = '加载家庭信息失败'
  } finally {
    loadingFamily.value = false
  }
}

function handleLogout() {
  logout()
  router.push('/login')
}

onMounted(loadFamily)
</script>

<template>
  <div class="settings-page">
    <h1>设置</h1>

    <!-- Family info -->
    <section class="section-card">
      <h2>家庭信息</h2>
      <p v-if="loadingFamily">加载中...</p>
      <p v-else-if="familyError" class="error">{{ familyError }}</p>
      <p v-else class="family-name">{{ familyName }}</p>

      <FamilyMemberList />
    </section>

    <!-- Invitation management (parent only) -->
    <section v-if="user?.role === 'parent'" class="section-card">
      <InvitationManager />
    </section>

    <!-- Logout -->
    <section class="section-card">
      <button class="btn btn-danger" @click="handleLogout">退出登录</button>
    </section>
  </div>
</template>

<style scoped>
.settings-page h1 {
  margin-bottom: 24px;
}

.section-card {
  margin-bottom: 24px;
  padding: 20px;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  background: white;
}

.section-card h2 {
  margin-bottom: 16px;
  font-size: 1.1em;
  color: #333;
}

.family-name {
  font-size: 1.2em;
  font-weight: 500;
  margin-bottom: 16px;
}

.btn {
  padding: 8px 20px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.95em;
}

.btn-danger {
  background: #e74c3c;
  color: white;
  width: 100%;
  padding: 12px;
}

.error {
  color: #e74c3c;
  font-size: 0.9em;
}
</style>
