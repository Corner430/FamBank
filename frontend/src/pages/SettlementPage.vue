<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { api, ApiError } from '../services/api'
import SettlementReport from '../components/SettlementReport.vue'

interface ChildSettlementResult {
  child_id: number
  child_name: string | null
  status: 'completed' | 'failed'
  error?: string
  settlement_id?: number
  steps?: {
    c_dividend: { amount: string }
    b_overflow: { amount: string }
    b_interest: { amount: string; tier1: string; tier2: string; tier3: string }
    violation_transfer: { amount: string }
  }
  balances_after?: { A: string; B_principal: string; B_interest_pool: string; C: string }
}

interface FamilySettlementResponse {
  settlement_date: string
  results: ChildSettlementResult[]
}

interface SettlementSummary {
  id: number
  date: string
  status: string
  c_dividend: string
  b_overflow: string
  b_interest: string
  violation_transfer: string
}

const loading = ref(false)
const error = ref('')
const familyResult = ref<FamilySettlementResponse | null>(null)
const history = ref<SettlementSummary[]>([])
const expandedChild = ref<number | null>(null)
const historyError = ref('')

async function loadHistory() {
  historyError.value = ''
  try {
    const res = await api.get<{ settlements: SettlementSummary[] }>('/settlements')
    history.value = res.settlements
  } catch {
    historyError.value = '加载结算历史失败'
  }
}

async function triggerSettlement() {
  error.value = ''
  familyResult.value = null
  loading.value = true
  try {
    const res = await api.post<FamilySettlementResponse>('/settlement')
    familyResult.value = res
    await loadHistory()
  } catch (e: unknown) {
    if (e instanceof ApiError) {
      error.value = e.message
    } else {
      error.value = '结算失败'
    }
  } finally {
    loading.value = false
  }
}

function toggleChild(childId: number) {
  expandedChild.value = expandedChild.value === childId ? null : childId
}

onMounted(loadHistory)
</script>

<template>
  <div class="settlement-page">
    <h1>月度结算</h1>

    <div class="actions">
      <button @click="triggerSettlement" :disabled="loading" class="btn-primary">
        {{ loading ? '结算中...' : '执行月度结算' }}
      </button>
    </div>

    <p v-if="error" class="error">{{ error }}</p>

    <!-- Per-child settlement results -->
    <div v-if="familyResult" class="family-result">
      <h2>结算结果 — {{ familyResult.settlement_date }}</h2>
      <div
        v-for="child in familyResult.results"
        :key="child.child_id"
        class="child-result"
        :class="{ failed: child.status === 'failed' }"
      >
        <div class="child-header" @click="toggleChild(child.child_id)">
          <span class="child-name">{{ child.child_name || `孩子 ${child.child_id}` }}</span>
          <span class="child-status" :class="child.status">
            {{ child.status === 'completed' ? '已完成' : '失败' }}
          </span>
          <span class="toggle">{{ expandedChild === child.child_id ? '▼' : '▶' }}</span>
        </div>

        <div v-if="child.status === 'failed' && child.error" class="error-detail">
          {{ child.error }}
        </div>

        <div v-if="expandedChild === child.child_id && child.steps && child.balances_after">
          <SettlementReport
            :steps="child.steps"
            :balances-after="child.balances_after"
          />
        </div>
      </div>
    </div>

    <p v-if="historyError" class="error">{{ historyError }}</p>
    <div v-if="history.length > 0" class="history">
      <h2>结算历史</h2>
      <table>
        <thead>
          <tr>
            <th>日期</th>
            <th>C派息</th>
            <th>B溢出</th>
            <th>B利息</th>
            <th>违约划转</th>
            <th>状态</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="s in history" :key="s.id">
            <td>{{ s.date }}</td>
            <td>&yen;{{ s.c_dividend }}</td>
            <td>&yen;{{ s.b_overflow }}</td>
            <td>&yen;{{ s.b_interest }}</td>
            <td>&yen;{{ s.violation_transfer }}</td>
            <td>{{ s.status === 'completed' ? '已完成' : '已回滚' }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
.settlement-page {
  max-width: 800px;
}

.actions {
  margin-bottom: 16px;
}

.btn-primary {
  padding: 12px 24px;
  background: #4a90d9;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 1em;
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.error {
  color: #e74c3c;
}

.family-result {
  margin-bottom: 24px;
}

.family-result h2 {
  font-size: 1.1em;
  margin-bottom: 12px;
}

.child-result {
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  margin-bottom: 12px;
  overflow: hidden;
}

.child-result.failed {
  border-color: #ffcdd2;
}

.child-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: #f5f5f5;
  cursor: pointer;
}

.child-result.failed .child-header {
  background: #fff3e0;
}

.child-name {
  font-weight: 600;
  flex: 1;
}

.child-status {
  font-size: 0.85em;
  padding: 2px 8px;
  border-radius: 4px;
}
.child-status.completed { background: #e8f5e9; color: #2e7d32; }
.child-status.failed { background: #ffebee; color: #c62828; }

.toggle {
  font-size: 0.8em;
  color: #999;
}

.error-detail {
  padding: 8px 16px;
  color: #c62828;
  font-size: 0.9em;
}

.history {
  margin-top: 32px;
}

.history h2 {
  font-size: 1.1em;
}

table {
  width: 100%;
  border-collapse: collapse;
}

th, td {
  padding: 8px;
  text-align: left;
  border-bottom: 1px solid #ddd;
}

th {
  font-weight: 600;
  color: #555;
}
</style>
