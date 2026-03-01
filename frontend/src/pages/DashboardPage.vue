<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { api, getStoredUser, ApiError } from '../services/api'
import AccountCard from '../components/AccountCard.vue'

interface ChildSummary {
  user_id: number
  name: string | null
  accounts: {
    A: string
    B_principal: string
    B_interest_pool: string
    C: string
  }
  total: string
}

interface DashboardData {
  family_name: string
  total_assets: string
  children: ChildSummary[]
}

interface AccountInfo {
  type: string
  name: string
  balance?: string
  principal?: string
  interest_pool?: string
  is_interest_suspended?: boolean
  is_deposit_suspended?: boolean
}

const router = useRouter()
const user = computed(() => getStoredUser())
const isParent = computed(() => user.value?.role === 'parent')

// Parent dashboard state
const dashboard = ref<DashboardData | null>(null)
const dashboardLoading = ref(false)
const dashboardError = ref('')

// Child account state (for child view)
const accounts = ref<AccountInfo[]>([])
const totalDebt = ref('0.00')
const childLoading = ref(false)
const childError = ref('')

// A Spending state (child)
const spendAmount = ref('')
const spendDesc = ref('')
const spendLoading = ref(false)
const spendError = ref('')
const spendResult = ref<{ amount: string; balance_before: string; balance_after: string } | null>(null)

// Redemption state (child)
const redeemAmount = ref('')
const redeemReason = ref('')
const redeemLoading = ref(false)
const redeemError = ref('')
const redeemSuccess = ref(false)

async function loadParentDashboard() {
  dashboardLoading.value = true
  dashboardError.value = ''
  try {
    dashboard.value = await api.get<DashboardData>('/family/dashboard')
  } catch (e) {
    dashboardError.value = e instanceof ApiError ? e.message : '加载失败'
  } finally {
    dashboardLoading.value = false
  }
}

async function loadChildAccounts() {
  childLoading.value = true
  childError.value = ''
  try {
    const res = await api.get<{ accounts: AccountInfo[]; total_debt: string }>('/accounts')
    accounts.value = res.accounts
    totalDebt.value = res.total_debt
  } catch (e) {
    childError.value = e instanceof ApiError ? e.message : '加载失败'
  } finally {
    childLoading.value = false
  }
}

async function spendFromA() {
  spendLoading.value = true
  spendError.value = ''
  spendResult.value = null
  try {
    spendResult.value = await api.post('/accounts/a/spend', {
      amount: spendAmount.value,
      description: spendDesc.value,
    })
    spendAmount.value = ''
    spendDesc.value = ''
    await loadChildAccounts()
  } catch (e) {
    spendError.value = e instanceof ApiError ? e.message : '消费失败'
  } finally {
    spendLoading.value = false
  }
}

async function requestRedemption() {
  redeemLoading.value = true
  redeemError.value = ''
  redeemSuccess.value = false
  try {
    await api.post('/accounts/c/redemption/request', {
      amount: redeemAmount.value,
      reason: redeemReason.value,
    })
    redeemAmount.value = ''
    redeemReason.value = ''
    redeemSuccess.value = true
    await loadChildAccounts()
  } catch (e) {
    redeemError.value = e instanceof ApiError ? e.message : '申请失败'
  } finally {
    redeemLoading.value = false
  }
}

function goToChild(childId: number) {
  router.push(`/child/${childId}`)
}

onMounted(() => {
  if (isParent.value) {
    loadParentDashboard()
  } else {
    loadChildAccounts()
  }
})
</script>

<template>
  <div class="dashboard">
    <!-- Parent Dashboard -->
    <template v-if="isParent">
      <h1>家庭总览</h1>

      <p v-if="dashboardLoading">加载中...</p>
      <p v-else-if="dashboardError" class="error">{{ dashboardError }}</p>

      <template v-else-if="dashboard">
        <div class="family-summary">
          <span class="family-name">{{ dashboard.family_name }}</span>
          <span class="total-assets">总资产：&yen;{{ dashboard.total_assets }}</span>
        </div>

        <div v-if="dashboard.children.length === 0" class="empty-state">
          还没有孩子加入，请生成邀请码邀请成员
        </div>

        <div v-else class="children-grid">
          <div
            v-for="child in dashboard.children"
            :key="child.user_id"
            class="child-card"
            @click="goToChild(child.user_id)"
          >
            <div class="child-name">{{ child.name || '未命名' }}</div>
            <div class="child-accounts">
              <div class="acct-row"><span>A 零钱宝</span><span>&yen;{{ child.accounts.A }}</span></div>
              <div class="acct-row"><span>B 梦想金</span><span>&yen;{{ child.accounts.B_principal }}</span></div>
              <div class="acct-row sub"><span>利息池</span><span>&yen;{{ child.accounts.B_interest_pool }}</span></div>
              <div class="acct-row"><span>C 牛马金</span><span>&yen;{{ child.accounts.C }}</span></div>
            </div>
            <div class="child-total">合计：&yen;{{ child.total }}</div>
          </div>
        </div>
      </template>
    </template>

    <!-- Child Dashboard -->
    <template v-else>
      <h1>我的账户</h1>

      <p v-if="childLoading">加载中...</p>
      <p v-else-if="childError" class="error">{{ childError }}</p>

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

      <!-- A Spending (child) -->
      <div class="section-card">
        <h2>A 零钱宝消费</h2>
        <div class="inline-form">
          <input v-model="spendAmount" type="text" inputmode="decimal" placeholder="金额" :disabled="spendLoading" />
          <input v-model="spendDesc" type="text" placeholder="说明（选填）" :disabled="spendLoading" />
          <button @click="spendFromA" :disabled="spendLoading || !spendAmount">
            {{ spendLoading ? '...' : '消费' }}
          </button>
        </div>
        <p v-if="spendError" class="error">{{ spendError }}</p>
        <div v-if="spendResult" class="result-msg">
          消费 &yen;{{ spendResult.amount }}，余额 &yen;{{ spendResult.balance_after }}
        </div>
      </div>

      <!-- C Redemption Request (child) -->
      <div class="section-card">
        <h2>C 牛马金赎回申请</h2>
        <div class="inline-form">
          <input v-model="redeemAmount" type="text" inputmode="decimal" placeholder="金额" :disabled="redeemLoading" />
          <input v-model="redeemReason" type="text" placeholder="原因（选填）" :disabled="redeemLoading" />
          <button @click="requestRedemption" :disabled="redeemLoading || !redeemAmount">
            {{ redeemLoading ? '...' : '申请' }}
          </button>
        </div>
        <p v-if="redeemError" class="error">{{ redeemError }}</p>
        <p v-if="redeemSuccess" class="result-msg">赎回申请已提交</p>
      </div>
    </template>
  </div>
</template>

<style scoped>
.dashboard h1 { margin-bottom: 24px; }

.family-summary {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  padding: 16px;
  background: #f0f7ff;
  border-radius: 8px;
}
.family-name { font-size: 1.2em; font-weight: 600; }
.total-assets { font-size: 1.1em; color: #4a90d9; font-weight: 500; }

.empty-state {
  text-align: center;
  padding: 40px;
  color: #999;
}

.children-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 16px;
}

.child-card {
  padding: 16px;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  background: white;
  cursor: pointer;
  transition: box-shadow 0.2s;
}
.child-card:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
.child-name { font-size: 1.1em; font-weight: 600; margin-bottom: 12px; }
.child-accounts { margin-bottom: 8px; }
.acct-row { display: flex; justify-content: space-between; padding: 4px 0; font-size: 0.9em; }
.acct-row.sub { padding-left: 16px; color: #888; font-size: 0.85em; }
.child-total { text-align: right; font-weight: 600; color: #4a90d9; border-top: 1px solid #eee; padding-top: 8px; }

.accounts-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 16px;
}

.debt-notice {
  margin-top: 16px;
  padding: 12px;
  background: #fff3e0;
  border-radius: 6px;
  color: #e65100;
}

.section-card {
  margin-top: 20px;
  padding: 16px;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  background: white;
}
.section-card h2 { margin-bottom: 12px; font-size: 1em; }

.inline-form {
  display: flex;
  gap: 8px;
}
.inline-form input {
  padding: 8px 12px;
  border: 1px solid #ccc;
  border-radius: 4px;
  font-size: 0.9em;
  flex: 1;
}
.inline-form button {
  padding: 8px 16px;
  background: #4a90d9;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  white-space: nowrap;
}
.inline-form button:disabled { opacity: 0.6; cursor: not-allowed; }

.error { color: #e74c3c; margin-top: 8px; }
.result-msg { color: #2e7d32; margin-top: 8px; }
</style>
