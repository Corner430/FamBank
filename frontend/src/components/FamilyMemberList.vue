<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { api, ApiError } from '../services/api'

type Member = {
  id: number
  name: string | null
  role: string | null
}

const members = ref<Member[]>([])
const loading = ref(false)
const error = ref('')

async function loadMembers() {
  loading.value = true
  error.value = ''
  try {
    const res = await api.get<{
      family: { id: number; name: string; created_at: string }
      members: Member[]
    }>('/family')
    members.value = res.members
  } catch (e) {
    error.value = e instanceof ApiError ? e.message : '加载成员列表失败'
  } finally {
    loading.value = false
  }
}

function roleLabel(role: string | null): string {
  if (role === 'parent') return '家长'
  if (role === 'child') return '孩子'
  return '未知'
}

onMounted(loadMembers)
</script>

<template>
  <div class="family-member-list">
    <h3>家庭成员</h3>

    <div v-if="loading" class="loading">加载中...</div>
    <div v-else-if="members.length === 0" class="empty">暂无成员</div>
    <div v-else class="member-list">
      <div v-for="member in members" :key="member.id" class="member-item">
        <span class="member-name">{{ member.name || '未设置' }}</span>
        <span class="member-role" :class="`role-${member.role}`">{{ roleLabel(member.role) }}</span>
      </div>
    </div>

    <p v-if="error" class="error">{{ error }}</p>
  </div>
</template>

<style scoped>
.family-member-list h3 {
  margin-bottom: 12px;
}

.member-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.member-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 12px;
  border: 1px solid #eee;
  border-radius: 4px;
  background: #fafafa;
}

.member-name {
  font-weight: 500;
}

.member-role {
  font-size: 0.85em;
  padding: 2px 10px;
  border-radius: 10px;
}

.role-parent { background: #fff3e0; color: #e65100; }
.role-child { background: #e8f5e9; color: #2e7d32; }

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
