<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { api, getStoredUser, ApiError } from '../services/api'
import ChildSelector from '../components/ChildSelector.vue'

interface ViolationItem {
  id: number
  violation_date: string
  violation_amount: string
  penalty_amount: string
  amount_entered_a: string
  is_escalated: boolean
  description: string
}

interface ViolationResponse {
  violation_id: number
  penalty: string
  is_escalated: boolean
  b_interest_pool_before: string
  b_interest_pool_after: string
  c_balance_before: string
  c_balance_after: string
  deposit_suspend_until: string | null
}

const violations = ref<ViolationItem[]>([])
const totalViolations = ref(0)
const loading = ref(false)
const error = ref('')

// Form state
const violationAmount = ref('')
const enteredA = ref('0.00')
const description = ref('')
const submitLoading = ref(false)
const submitError = ref('')
const result = ref<ViolationResponse | null>(null)

const childId = ref<number | null>(null)
const user = computed(() => getStoredUser())
const isParent = computed(() => user.value?.role === 'parent')

function onChildSelect(id: number) {
  childId.value = id
  loadViolations()
}

async function loadViolations() {
  loading.value = true
  error.value = ''
  try {
    const params = isParent.value && childId.value ? `?child_id=${childId.value}` : ''
    const res = await api.get<{ items: ViolationItem[]; total: number }>(`/violations${params}`)
    violations.value = res.items
    totalViolations.value = res.total
  } catch (e: unknown) {
    error.value = e instanceof ApiError ? e.message : '加载失败'
  } finally {
    loading.value = false
  }
}

async function submitViolation() {
  submitLoading.value = true
  submitError.value = ''
  result.value = null
  try {
    const body: Record<string, unknown> = {
      violation_amount: violationAmount.value,
      amount_entered_a: enteredA.value,
      description: description.value,
    }
    if (isParent.value && childId.value) {
      body.child_id = childId.value
    }
    const res = await api.post<ViolationResponse>('/violations', body)
    result.value = res
    violationAmount.value = ''
    enteredA.value = '0.00'
    description.value = ''
    await loadViolations()
  } catch (e: unknown) {
    submitError.value = e instanceof ApiError ? e.message : '提交失败'
  } finally {
    submitLoading.value = false
  }
}

onMounted(loadViolations)
</script>

<template>
  <div class="violation-page">
    <h1>违约处理</h1>

    <ChildSelector v-if="isParent" @select="onChildSelect" />

    <!-- Entry Form (parent only) -->
    <div v-if="isParent" class="section-card">
      <h2>记录违约</h2>
      <div class="form">
        <div class="form-row">
          <label>违约金额 (元)</label>
          <input
            v-model="violationAmount"
            type="text"
            placeholder="例如 200.00"
            :disabled="submitLoading"
          />
        </div>
        <div class="form-row">
          <label>进入A账户金额 (元)</label>
          <input
            v-model="enteredA"
            type="text"
            placeholder="0.00"
            :disabled="submitLoading"
          />
        </div>
        <div class="form-row">
          <label>说明</label>
          <input
            v-model="description"
            type="text"
            placeholder="违约说明"
            :disabled="submitLoading"
          />
        </div>
        <button
          class="btn btn-danger"
          @click="submitViolation"
          :disabled="submitLoading || !violationAmount"
        >
          {{ submitLoading ? '处理中...' : '提交违约' }}
        </button>
        <p v-if="submitError" class="error">{{ submitError }}</p>
      </div>

      <!-- Result -->
      <div v-if="result" class="result-card">
        <h3>违约已处理</h3>
        <div class="detail-row">
          <span>罚金：</span>
          <span class="penalty">&yen;{{ result.penalty }}</span>
        </div>
        <div class="detail-row">
          <span>B利息池变动：</span>
          <span>&yen;{{ result.b_interest_pool_before }} -&gt; &yen;{{ result.b_interest_pool_after }}</span>
        </div>
        <div class="detail-row">
          <span>C余额变动：</span>
          <span>&yen;{{ result.c_balance_before }} -&gt; &yen;{{ result.c_balance_after }}</span>
        </div>
        <div v-if="result.is_escalated" class="escalation-notice">
          累犯升级：B账户暂停入金至 {{ result.deposit_suspend_until }}
        </div>
      </div>
    </div>

    <div v-else class="no-permission">
      仅甲方可记录违约。
    </div>

    <!-- Violation History -->
    <div class="section-card history">
      <h2>违约记录 ({{ totalViolations }})</h2>

      <p v-if="loading" class="loading-text">加载中...</p>
      <p v-else-if="error" class="error">{{ error }}</p>
      <p v-else-if="violations.length === 0" class="empty-text">暂无违约记录</p>

      <table v-else class="violation-table">
        <thead>
          <tr>
            <th>日期</th>
            <th class="text-right">违约金额</th>
            <th class="text-right">罚金</th>
            <th class="text-right">进A金额</th>
            <th>升级</th>
            <th>说明</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="v in violations" :key="v.id">
            <td class="nowrap">{{ v.violation_date }}</td>
            <td class="text-right">&yen;{{ v.violation_amount }}</td>
            <td class="text-right penalty">&yen;{{ v.penalty_amount }}</td>
            <td class="text-right">&yen;{{ v.amount_entered_a }}</td>
            <td>
              <span v-if="v.is_escalated" class="badge-danger">是</span>
              <span v-else class="badge-ok">否</span>
            </td>
            <td class="desc">{{ v.description }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
.violation-page h1 {
  margin-bottom: 20px;
}

.section-card {
  padding: 20px;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  background: white;
  margin-bottom: 20px;
}

.section-card h2 {
  margin-bottom: 16px;
  font-size: 1.1em;
}

.form {
  margin-bottom: 16px;
}

.form-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.form-row label {
  min-width: 150px;
  color: #555;
  font-size: 0.9em;
}

.form-row input {
  flex: 1;
  padding: 8px 12px;
  border: 1px solid #ccc;
  border-radius: 4px;
  font-size: 0.95em;
}

.btn {
  padding: 8px 20px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.95em;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-danger {
  background: #e74c3c;
  color: white;
}

.btn-danger:hover:not(:disabled) {
  background: #c0392b;
}

.result-card {
  margin-top: 16px;
  padding: 16px;
  border: 2px solid #ff9800;
  border-radius: 8px;
  background: #fff8e1;
}

.result-card h3 {
  margin-bottom: 12px;
  color: #e65100;
}

.detail-row {
  display: flex;
  justify-content: space-between;
  padding: 4px 0;
  font-size: 0.95em;
}

.penalty {
  color: #e74c3c;
  font-weight: 600;
}

.escalation-notice {
  margin-top: 12px;
  padding: 8px 12px;
  background: #ffebee;
  border-radius: 4px;
  color: #c62828;
  font-weight: 600;
}

.no-permission {
  padding: 20px;
  background: #f5f5f5;
  border-radius: 8px;
  color: #888;
  text-align: center;
  margin-bottom: 20px;
}

.history {
  margin-top: 4px;
}

.violation-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.9em;
}

.violation-table th,
.violation-table td {
  padding: 8px 10px;
  border-bottom: 1px solid #e0e0e0;
  text-align: left;
}

.violation-table th {
  background: #f5f5f5;
  font-weight: 600;
  font-size: 0.85em;
  color: #666;
}

.text-right {
  text-align: right;
}

.nowrap {
  white-space: nowrap;
}

.desc {
  color: #666;
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.badge-danger {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  background: #ffebee;
  color: #c62828;
  font-size: 0.85em;
}

.badge-ok {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  background: #e8f5e9;
  color: #2e7d32;
  font-size: 0.85em;
}

.loading-text,
.empty-text {
  text-align: center;
  color: #999;
  padding: 24px 0;
}

.error {
  color: #e74c3c;
}
</style>
