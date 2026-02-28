<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { api, ApiError } from '../services/api'
import SettlementReport from '../components/SettlementReport.vue'

interface SettlementResult {
  settlement_id: number
  date: string
  steps: {
    c_dividend: { amount: string }
    b_overflow: { amount: string }
    b_interest: { amount: string; tier1: string; tier2: string; tier3: string }
    violation_transfer: { amount: string }
  }
  balances_after: { A: string; B_principal: string; B_interest_pool: string; C: string }
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
const result = ref<SettlementResult | null>(null)
const history = ref<SettlementSummary[]>([])

async function loadHistory() {
  try {
    const res = await api.get<{ settlements: SettlementSummary[] }>('/settlements')
    history.value = res.settlements
  } catch {
    // ignore
  }
}

async function triggerSettlement() {
  error.value = ''
  result.value = null
  loading.value = true
  try {
    const res = await api.post<SettlementResult>('/settlement')
    result.value = res
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

    <SettlementReport
      v-if="result"
      :steps="result.steps"
      :balances-after="result.balances_after"
    />

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
