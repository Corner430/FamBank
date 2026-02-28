<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { api } from '../services/api'
import { getStoredUser } from '../services/api'
import AccountCard from '../components/AccountCard.vue'

interface AccountInfo {
  type: string
  name: string
  balance?: string
  principal?: string
  interest_pool?: string
  is_interest_suspended?: boolean
  is_deposit_suspended?: boolean
}

const accounts = ref<AccountInfo[]>([])
const totalDebt = ref('0.00')
const loading = ref(true)
const error = ref('')

// Redemption state
const redeemAmount = ref('')
const redeemReason = ref('')
const redeemLoading = ref(false)
const redeemError = ref('')
const redeemPending = ref<{
  amount: string
  fee: string
  net: string
  c_balance: string
  reason: string
  status: string
} | null>(null)
const redeemResult = ref<{
  status: string
  amount: string
  fee?: string
  net?: string
  c_balance_after?: string
  a_balance_after?: string
} | null>(null)

// Approval state (parent)
const approveAmount = ref('')
const approveLoading = ref(false)
const approveError = ref('')

const user = computed(() => getStoredUser())
const isParent = computed(() => user.value?.role === 'parent')

const cAccount = computed(() => accounts.value.find(a => a.type === 'C'))
const aAccount = computed(() => accounts.value.find(a => a.type === 'A'))

// A Spending state
const spendAmount = ref('')
const spendDesc = ref('')
const spendLoading = ref(false)
const spendError = ref('')
const spendResult = ref<{
  amount: string
  balance_before: string
  balance_after: string
} | null>(null)

async function loadAccounts() {
  loading.value = true
  error.value = ''
  try {
    const res = await api.get<{ accounts: AccountInfo[]; total_debt: string }>('/accounts')
    accounts.value = res.accounts
    totalDebt.value = res.total_debt
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : '加载失败'
  } finally {
    loading.value = false
  }
}

async function requestRedemption() {
  redeemLoading.value = true
  redeemError.value = ''
  redeemPending.value = null
  redeemResult.value = null
  try {
    const res = await api.post<{
      amount: string
      fee: string
      net: string
      c_balance: string
      reason: string
      status: string
    }>('/accounts/c/redemption/request', {
      amount: redeemAmount.value,
      reason: redeemReason.value,
    })
    redeemPending.value = res
  } catch (e: unknown) {
    redeemError.value = e instanceof Error ? e.message : '请求失败'
  } finally {
    redeemLoading.value = false
  }
}

async function handleApproval(approved: boolean) {
  if (!redeemPending.value && !approveAmount.value) return
  approveLoading.value = true
  approveError.value = ''
  redeemResult.value = null
  const amount = redeemPending.value?.amount || approveAmount.value
  try {
    const res = await api.post<{
      status: string
      amount: string
      fee?: string
      net?: string
      c_balance_after?: string
      a_balance_after?: string
    }>('/accounts/c/redemption/approve', {
      amount,
      approved,
      reason: redeemReason.value,
    })
    redeemResult.value = res
    redeemPending.value = null
    approveAmount.value = ''
    await loadAccounts()
  } catch (e: unknown) {
    approveError.value = e instanceof Error ? e.message : '审批失败'
  } finally {
    approveLoading.value = false
  }
}

async function spendFromA() {
  spendLoading.value = true
  spendError.value = ''
  spendResult.value = null
  try {
    const res = await api.post<{
      amount: string
      balance_before: string
      balance_after: string
    }>('/accounts/a/spend', {
      amount: spendAmount.value,
      description: spendDesc.value,
    })
    spendResult.value = res
    spendAmount.value = ''
    spendDesc.value = ''
    await loadAccounts()
  } catch (e: unknown) {
    spendError.value = e instanceof Error ? e.message : '消费失败'
  } finally {
    spendLoading.value = false
  }
}

onMounted(loadAccounts)
</script>

<template>
  <div class="dashboard">
    <h1>账户总览</h1>

    <p v-if="loading">加载中...</p>
    <p v-else-if="error" class="error">{{ error }}</p>

    <div v-else class="accounts-grid">
      <AccountCard
        v-for="acc in accounts"
        :key="acc.type"
        :type="acc.type"
        :name="acc.name"
        :balance="acc.balance"
        :principal="acc.principal"
        :interest-pool="acc.interest_pool"
        :is-interest-suspended="acc.is_interest_suspended"
        :is-deposit-suspended="acc.is_deposit_suspended"
      />
    </div>

    <div v-if="totalDebt !== '0.00'" class="debt-notice">
      欠款余额：&yen;{{ totalDebt }}
    </div>

    <!-- A Spending Section -->
    <div class="section-card" v-if="aAccount">
      <h2>A 零钱宝消费</h2>
      <div class="redeem-form">
        <div class="form-row">
          <label>消费金额 (元)</label>
          <input
            v-model="spendAmount"
            type="text"
            placeholder="例如 50.00"
            :disabled="spendLoading"
          />
        </div>
        <div class="form-row">
          <label>消费说明 (选填)</label>
          <input
            v-model="spendDesc"
            type="text"
            placeholder="消费说明"
            :disabled="spendLoading"
          />
        </div>
        <button
          class="btn btn-spend"
          @click="spendFromA"
          :disabled="spendLoading || !spendAmount"
        >
          {{ spendLoading ? '处理中...' : '确认消费' }}
        </button>
        <p v-if="spendError" class="error">{{ spendError }}</p>
      </div>
      <div v-if="spendResult" class="result-card approved">
        <h3>消费成功</h3>
        <div class="detail-row">
          <span>消费金额：</span><span>&yen;{{ spendResult.amount }}</span>
        </div>
        <div class="detail-row">
          <span>变动前余额：</span><span>&yen;{{ spendResult.balance_before }}</span>
        </div>
        <div class="detail-row">
          <span>变动后余额：</span><span class="highlight">&yen;{{ spendResult.balance_after }}</span>
        </div>
      </div>
    </div>

    <!-- C Redemption Section -->
    <div class="section-card" v-if="cAccount">
      <h2>C账户赎回</h2>

      <!-- Request Form -->
      <div class="redeem-form">
        <div class="form-row">
          <label>赎回金额 (元)</label>
          <input
            v-model="redeemAmount"
            type="text"
            placeholder="例如 500.00"
            :disabled="redeemLoading"
          />
        </div>
        <div class="form-row">
          <label>原因 (选填)</label>
          <input
            v-model="redeemReason"
            type="text"
            placeholder="赎回原因"
            :disabled="redeemLoading"
          />
        </div>
        <button
          class="btn btn-primary"
          @click="requestRedemption"
          :disabled="redeemLoading || !redeemAmount"
        >
          {{ redeemLoading ? '提交中...' : '申请赎回' }}
        </button>
        <p v-if="redeemError" class="error">{{ redeemError }}</p>
      </div>

      <!-- Pending Status -->
      <div v-if="redeemPending" class="pending-card">
        <h3>待审批</h3>
        <div class="detail-row">
          <span>赎回金额：</span><span>&yen;{{ redeemPending.amount }}</span>
        </div>
        <div class="detail-row">
          <span>手续费 (10%)：</span><span>&yen;{{ redeemPending.fee }}</span>
        </div>
        <div class="detail-row">
          <span>实际到账：</span><span class="highlight">&yen;{{ redeemPending.net }}</span>
        </div>
        <div class="detail-row">
          <span>C当前余额：</span><span>&yen;{{ redeemPending.c_balance }}</span>
        </div>
        <div v-if="redeemPending.reason" class="detail-row">
          <span>原因：</span><span>{{ redeemPending.reason }}</span>
        </div>

        <!-- Parent Approve/Reject Panel -->
        <div v-if="isParent" class="approval-panel">
          <button
            class="btn btn-approve"
            @click="handleApproval(true)"
            :disabled="approveLoading"
          >
            批准
          </button>
          <button
            class="btn btn-reject"
            @click="handleApproval(false)"
            :disabled="approveLoading"
          >
            拒绝
          </button>
          <p v-if="approveError" class="error">{{ approveError }}</p>
        </div>
        <p v-else class="info-text">等待甲方审批...</p>
      </div>

      <!-- Parent Direct Approve Panel (when no pending from child) -->
      <div v-if="isParent && !redeemPending" class="approve-direct">
        <h3>直接审批赎回</h3>
        <div class="form-row">
          <label>金额 (元)</label>
          <input
            v-model="approveAmount"
            type="text"
            placeholder="输入待审批的赎回金额"
          />
        </div>
        <div class="approval-panel">
          <button
            class="btn btn-approve"
            @click="handleApproval(true)"
            :disabled="approveLoading || !approveAmount"
          >
            批准
          </button>
          <button
            class="btn btn-reject"
            @click="handleApproval(false)"
            :disabled="approveLoading || !approveAmount"
          >
            拒绝
          </button>
          <p v-if="approveError" class="error">{{ approveError }}</p>
        </div>
      </div>

      <!-- Result -->
      <div v-if="redeemResult" class="result-card" :class="redeemResult.status">
        <h3>{{ redeemResult.status === 'approved' ? '赎回成功' : '赎回被拒绝' }}</h3>
        <div v-if="redeemResult.status === 'approved'">
          <div class="detail-row">
            <span>赎回金额：</span><span>&yen;{{ redeemResult.amount }}</span>
          </div>
          <div class="detail-row">
            <span>手续费：</span><span>&yen;{{ redeemResult.fee }}</span>
          </div>
          <div class="detail-row">
            <span>到账A：</span><span class="highlight">&yen;{{ redeemResult.net }}</span>
          </div>
          <div class="detail-row">
            <span>C余额：</span><span>&yen;{{ redeemResult.c_balance_after }}</span>
          </div>
          <div class="detail-row">
            <span>A余额：</span><span>&yen;{{ redeemResult.a_balance_after }}</span>
          </div>
        </div>
        <div v-else>
          <p>金额：&yen;{{ redeemResult.amount }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.dashboard h1 {
  margin-bottom: 24px;
}

.accounts-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 16px;
}

.error {
  color: #e74c3c;
}

.debt-notice {
  margin-top: 16px;
  padding: 12px;
  background: #fff3e0;
  border-radius: 6px;
  color: #e65100;
}

.section-card {
  margin-top: 24px;
  padding: 20px;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  background: white;
}

.section-card h2 {
  margin-bottom: 16px;
  font-size: 1.2em;
}

.redeem-form {
  margin-bottom: 16px;
}

.form-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.form-row label {
  min-width: 110px;
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

.btn-primary {
  background: #2196f3;
  color: white;
}

.btn-spend {
  background: #4caf50;
  color: white;
}

.btn-approve {
  background: #4caf50;
  color: white;
}

.btn-reject {
  background: #e74c3c;
  color: white;
}

.pending-card {
  margin-top: 16px;
  padding: 16px;
  border: 2px solid #ff9800;
  border-radius: 8px;
  background: #fff8e1;
}

.pending-card h3 {
  margin-bottom: 12px;
  color: #e65100;
}

.detail-row {
  display: flex;
  justify-content: space-between;
  padding: 4px 0;
  font-size: 0.95em;
}

.highlight {
  font-weight: bold;
  color: #2e7d32;
}

.approval-panel {
  display: flex;
  gap: 12px;
  margin-top: 16px;
  align-items: center;
}

.info-text {
  margin-top: 12px;
  color: #888;
  font-style: italic;
}

.approve-direct {
  margin-top: 16px;
  padding: 16px;
  border: 1px dashed #ccc;
  border-radius: 8px;
}

.approve-direct h3 {
  margin-bottom: 12px;
  color: #555;
  font-size: 1em;
}

.result-card {
  margin-top: 16px;
  padding: 16px;
  border-radius: 8px;
}

.result-card.approved {
  border: 2px solid #4caf50;
  background: #e8f5e9;
}

.result-card.approved h3 {
  color: #2e7d32;
}

.result-card.rejected {
  border: 2px solid #e74c3c;
  background: #ffebee;
}

.result-card.rejected h3 {
  color: #c62828;
}
</style>
