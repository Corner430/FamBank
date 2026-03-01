<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { api, ApiError } from '../services/api'

type Invitation = {
  id: number
  code: string
  target_role: string
  target_name: string
  status: string
  expires_at: string
}

const invitations = ref<Invitation[]>([])
const loading = ref(false)
const error = ref('')

// Create invitation form
const targetRole = ref<'parent' | 'child'>('child')
const targetName = ref('')
const creating = ref(false)

async function loadInvitations() {
  loading.value = true
  error.value = ''
  try {
    const res = await api.get<{ invitations: Invitation[] }>('/family/invitations')
    invitations.value = res.invitations
  } catch (e) {
    error.value = e instanceof ApiError ? e.message : '加载邀请列表失败'
  } finally {
    loading.value = false
  }
}

async function createInvitation() {
  if (!targetName.value.trim()) {
    error.value = '请输入成员名称'
    return
  }
  error.value = ''
  creating.value = true
  try {
    await api.post('/family/invitations', {
      target_role: targetRole.value,
      target_name: targetName.value.trim(),
    })
    targetName.value = ''
    await loadInvitations()
  } catch (e) {
    error.value = e instanceof ApiError ? e.message : '创建邀请码失败'
  } finally {
    creating.value = false
  }
}

async function revokeInvitation(id: number) {
  error.value = ''
  try {
    await api.delete(`/family/invitations/${id}`)
    await loadInvitations()
  } catch (e) {
    error.value = e instanceof ApiError ? e.message : '撤销失败'
  }
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('zh-CN')
}

function statusLabel(status: string): string {
  const map: Record<string, string> = {
    pending: '待使用',
    used: '已使用',
    revoked: '已撤销',
    expired: '已过期',
  }
  return map[status] || status
}

onMounted(loadInvitations)
</script>

<template>
  <div class="invitation-manager">
    <h3>邀请管理</h3>

    <!-- Create form -->
    <div class="create-form">
      <div class="form-row">
        <select v-model="targetRole">
          <option value="child">孩子</option>
          <option value="parent">家长</option>
        </select>
        <input
          v-model="targetName"
          type="text"
          placeholder="成员名称"
          maxlength="50"
        />
        <button @click="createInvitation" :disabled="creating || !targetName.trim()">
          {{ creating ? '生成中...' : '生成邀请码' }}
        </button>
      </div>
    </div>

    <!-- Invitation list -->
    <div v-if="loading" class="loading">加载中...</div>
    <div v-else-if="invitations.length === 0" class="empty">暂无邀请码</div>
    <div v-else class="invitation-list">
      <div
        v-for="inv in invitations"
        :key="inv.id"
        class="invitation-item"
        :class="{ 'is-pending': inv.status === 'pending' }"
      >
        <div class="inv-info">
          <span class="inv-code">{{ inv.code }}</span>
          <span class="inv-name">{{ inv.target_name }} ({{ inv.target_role === 'parent' ? '家长' : '孩子' }})</span>
          <span class="inv-status" :class="`status-${inv.status}`">{{ statusLabel(inv.status) }}</span>
          <span class="inv-expires">{{ formatDate(inv.expires_at) }}</span>
        </div>
        <button
          v-if="inv.status === 'pending'"
          class="revoke-btn"
          @click="revokeInvitation(inv.id)"
        >
          撤销
        </button>
      </div>
    </div>

    <p v-if="error" class="error">{{ error }}</p>
  </div>
</template>

<style scoped>
.invitation-manager h3 {
  margin-bottom: 12px;
}

.create-form .form-row {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
}

.create-form select,
.create-form input {
  padding: 8px 12px;
  border: 1px solid #ccc;
  border-radius: 4px;
  font-size: 0.9em;
}

.create-form input {
  flex: 1;
}

.create-form button {
  padding: 8px 16px;
  background: #4a90d9;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  white-space: nowrap;
}

.create-form button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.invitation-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.invitation-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 12px;
  border: 1px solid #eee;
  border-radius: 4px;
  background: #fafafa;
}

.invitation-item.is-pending {
  border-color: #4a90d9;
  background: #f0f7ff;
}

.inv-info {
  display: flex;
  gap: 12px;
  align-items: center;
  flex-wrap: wrap;
}

.inv-code {
  font-family: monospace;
  font-weight: bold;
  font-size: 1em;
  letter-spacing: 1px;
}

.inv-name {
  color: #555;
  font-size: 0.9em;
}

.inv-status {
  font-size: 0.8em;
  padding: 2px 8px;
  border-radius: 10px;
}

.status-pending { background: #e3f2fd; color: #1976d2; }
.status-used { background: #e8f5e9; color: #388e3c; }
.status-revoked { background: #fce4ec; color: #c62828; }
.status-expired { background: #f5f5f5; color: #999; }

.inv-expires {
  font-size: 0.8em;
  color: #999;
}

.revoke-btn {
  padding: 4px 12px;
  background: transparent;
  color: #e74c3c;
  border: 1px solid #e74c3c;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.85em;
}

.loading, .empty {
  color: #999;
  text-align: center;
  padding: 16px;
}

.error {
  color: #e74c3c;
  margin-top: 8px;
}
</style>
