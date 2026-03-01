<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { api, getStoredUser } from '../services/api'

type Child = {
  id: number
  name: string | null
  role: string | null
}

const emit = defineEmits<{
  (e: 'select', childId: number): void
}>()

const user = getStoredUser()
const children = ref<Child[]>([])
const selectedId = ref<number | null>(null)
const loading = ref(false)

async function loadChildren() {
  if (user?.role !== 'parent') return

  loading.value = true
  try {
    const res = await api.get<{
      family: { id: number; name: string }
      members: Child[]
    }>('/family')
    children.value = res.members.filter(m => m.role === 'child')
    // Auto-select first child
    if (children.value.length > 0 && selectedId.value === null) {
      const first = children.value[0]
      if (first) {
        selectedId.value = first.id
        emit('select', first.id)
      }
    }
  } catch {
    // ignore
  } finally {
    loading.value = false
  }
}

watch(selectedId, (val) => {
  if (val !== null) {
    emit('select', val)
  }
})

onMounted(loadChildren)
</script>

<template>
  <div v-if="user?.role === 'parent'" class="child-selector">
    <label>选择孩子</label>
    <select v-model="selectedId" :disabled="loading || children.length === 0">
      <option v-if="loading" :value="null">加载中...</option>
      <option v-else-if="children.length === 0" :value="null">暂无孩子</option>
      <option v-for="child in children" :key="child.id" :value="child.id">
        {{ child.name || `孩子 ${child.id}` }}
      </option>
    </select>
  </div>
</template>

<style scoped>
.child-selector {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
}

.child-selector label {
  font-size: 0.9em;
  color: #666;
  white-space: nowrap;
}

.child-selector select {
  padding: 8px 12px;
  border: 1px solid #ccc;
  border-radius: 4px;
  font-size: 0.9em;
  flex: 1;
  max-width: 200px;
}
</style>
