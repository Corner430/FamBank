<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, ApiError } from '../services/api'
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

interface TransactionItem {
  id: number
  timestamp: string
  type: string
  source_account: string | null
  target_account: string | null
  amount: string
  balance_before: string
  balance_after: string
  charter_clause: string
  description: string | null
}

const route = useRoute()
const router = useRouter()
const childId = computed(() => Number(route.params.childId))
const childName = ref('')
const accounts = ref<AccountInfo[]>([])
const totalDebt = ref('0.00')
const recentTx = ref<TransactionItem[]>([])
const loading = ref(false)
const error = ref('')

async function loadChildData() {
  loading.value = true
  error.value = ''
  try {
    const [acctRes, txRes] = await Promise.all([
      api.get<{ accounts: AccountInfo[]; total_debt: string }>(`/accounts?child_id=${childId.value}`),
      api.get<{ items: TransactionItem[] }>(`/transactions?child_id=${childId.value}&per_page=10`),
    ])
    accounts.value = acctRes.accounts
    totalDebt.value = acctRes.total_debt
    recentTx.value = txRes.items
  } catch (e) {
    error.value = e instanceof ApiError ? e.message : '加载失败'
  } finally {
    loading.value = false
  }
}

async function loadChildName() {
  try {
    const res = await api.get<{ family: { id: number; name: string }; members: { id: number; name: string | null; role: string | null }[] }>('/family')
    const child = res.members.find(m => m.id === childId.value)
    childName.value = child?.name || `孩子 ${childId.value}`
  } catch {
    childName.value = `孩子 ${childId.value}`
  }
}

function goBack() {
  router.push('/dashboard')
}

function formatType(type: string): string {
  const map: Record<string, string> = {
    income_split_a: '收入分流A',
    income_split_b: '收入分流B',
    income_split_c: '收入分流C',
    a_spend: 'A消费',
    violation_penalty: '违约罚金',
    debt_repayment: '偿还欠款',
    b_interest: 'B利息',
    b_overflow: 'B溢出',
    c_dividend: 'C分红',
    b_purchase: 'B购买',
    c_redemption: 'C赎回',
  }
  return map[type] || type
}

onMounted(() => {
  loadChildData()
  loadChildName()
})
</script>

<template>
  <div class="child-detail">
    <div class="header">
      <button class="back-btn" @click="goBack">&larr; 返回</button>
      <h1>{{ childName }}</h1>
    </div>

    <p v-if="loading">加载中...</p>
    <p v-else-if="error" class="error">{{ error }}</p>

    <template v-else>
      <div class="accounts-grid">
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

      <div class="section-card">
        <h2>最近交易</h2>
        <p v-if="recentTx.length === 0" class="empty">暂无交易记录</p>
        <table v-else class="tx-table">
          <thead>
            <tr>
              <th>时间</th>
              <th>类型</th>
              <th>金额</th>
              <th>说明</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="tx in recentTx" :key="tx.id">
              <td class="nowrap">{{ tx.timestamp.slice(0, 16).replace('T', ' ') }}</td>
              <td>{{ formatType(tx.type) }}</td>
              <td>&yen;{{ tx.amount }}</td>
              <td class="desc">{{ tx.description || '-' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>
  </div>
</template>

<style scoped>
.child-detail h1 { margin: 0; }

.header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 24px;
}

.back-btn {
  padding: 6px 12px;
  background: #f0f0f0;
  border: 1px solid #ddd;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9em;
}
.back-btn:hover { background: #e0e0e0; }

.accounts-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 16px;
  margin-bottom: 16px;
}

.debt-notice {
  margin-bottom: 16px;
  padding: 12px;
  background: #fff3e0;
  border-radius: 6px;
  color: #e65100;
}

.section-card {
  padding: 16px;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  background: white;
}
.section-card h2 { margin-bottom: 12px; font-size: 1em; }

.tx-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.9em;
}
.tx-table th, .tx-table td {
  padding: 8px 10px;
  text-align: left;
  border-bottom: 1px solid #eee;
}
.tx-table th { font-weight: 600; color: #555; background: #fafafa; }
.nowrap { white-space: nowrap; }
.desc { color: #666; max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.empty { color: #999; text-align: center; padding: 20px 0; }
.error { color: #e74c3c; }
</style>
