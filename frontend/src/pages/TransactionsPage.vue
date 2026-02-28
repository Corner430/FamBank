<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { api } from '../services/api'
import TransactionList from '../components/TransactionList.vue'

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

interface TransactionListResponse {
  items: TransactionItem[]
  total: number
  page: number
  per_page: number
  total_pages: number
}

const items = ref<TransactionItem[]>([])
const loading = ref(false)
const error = ref('')
const page = ref(1)
const perPage = ref(20)
const totalPages = ref(1)
const total = ref(0)

// Filters
const filterAccount = ref('')
const filterType = ref('')
const filterFromDate = ref('')
const filterToDate = ref('')

async function loadTransactions() {
  loading.value = true
  error.value = ''
  try {
    const params = new URLSearchParams()
    if (filterAccount.value) params.set('account', filterAccount.value)
    if (filterType.value) params.set('type', filterType.value)
    if (filterFromDate.value) params.set('from_date', filterFromDate.value)
    if (filterToDate.value) params.set('to_date', filterToDate.value)
    params.set('page', String(page.value))
    params.set('per_page', String(perPage.value))

    const qs = params.toString()
    const res = await api.get<TransactionListResponse>(`/transactions?${qs}`)
    items.value = res.items
    total.value = res.total
    totalPages.value = res.total_pages
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : '加载失败'
  } finally {
    loading.value = false
  }
}

function applyFilters() {
  page.value = 1
  loadTransactions()
}

function resetFilters() {
  filterAccount.value = ''
  filterType.value = ''
  filterFromDate.value = ''
  filterToDate.value = ''
  page.value = 1
  loadTransactions()
}

function prevPage() {
  if (page.value > 1) {
    page.value--
    loadTransactions()
  }
}

function nextPage() {
  if (page.value < totalPages.value) {
    page.value++
    loadTransactions()
  }
}

onMounted(loadTransactions)
</script>

<template>
  <div class="transactions-page">
    <h1>交易记录</h1>

    <div class="filters">
      <div class="filter-row">
        <label>
          账户
          <select v-model="filterAccount">
            <option value="">全部</option>
            <option value="A">A 零钱宝</option>
            <option value="B">B 梦想金</option>
            <option value="C">C 牛马金</option>
          </select>
        </label>

        <label>
          类型
          <select v-model="filterType">
            <option value="">全部</option>
            <option value="income_split_a">收入分流A</option>
            <option value="income_split_b">收入分流B</option>
            <option value="income_split_c">收入分流C</option>
            <option value="a_spend">A消费</option>
            <option value="violation_penalty">违约罚金</option>
            <option value="debt_repayment">偿还欠款</option>
            <option value="b_interest">B利息</option>
            <option value="b_overflow">B溢出</option>
            <option value="c_dividend">C分红</option>
          </select>
        </label>

        <label>
          开始日期
          <input type="date" v-model="filterFromDate" />
        </label>

        <label>
          结束日期
          <input type="date" v-model="filterToDate" />
        </label>

        <div class="filter-actions">
          <button class="btn-primary" @click="applyFilters">筛选</button>
          <button class="btn-secondary" @click="resetFilters">重置</button>
        </div>
      </div>
    </div>

    <p v-if="error" class="error">{{ error }}</p>

    <TransactionList :items="items" :loading="loading" />

    <div v-if="total > 0" class="pagination">
      <span class="page-info">共 {{ total }} 条，第 {{ page }}/{{ totalPages }} 页</span>
      <div class="page-controls">
        <button :disabled="page <= 1" @click="prevPage">上一页</button>
        <button :disabled="page >= totalPages" @click="nextPage">下一页</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.transactions-page h1 {
  margin-bottom: 16px;
}

.filters {
  background: #f9f9f9;
  padding: 16px;
  border-radius: 8px;
  margin-bottom: 16px;
}

.filter-row {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: flex-end;
}

.filter-row label {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 0.85em;
  color: #666;
}

.filter-row select,
.filter-row input {
  padding: 6px 10px;
  border: 1px solid #ccc;
  border-radius: 4px;
  font-size: 0.95em;
}

.filter-actions {
  display: flex;
  gap: 8px;
  align-items: flex-end;
}

.btn-primary {
  padding: 6px 16px;
  background: #2196f3;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.btn-primary:hover {
  background: #1976d2;
}

.btn-secondary {
  padding: 6px 16px;
  background: #e0e0e0;
  color: #333;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.btn-secondary:hover {
  background: #bdbdbd;
}

.error {
  color: #e74c3c;
  margin-bottom: 12px;
}

.pagination {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 16px;
  padding: 8px 0;
}

.page-info {
  color: #666;
  font-size: 0.9em;
}

.page-controls {
  display: flex;
  gap: 8px;
}

.page-controls button {
  padding: 4px 12px;
  border: 1px solid #ccc;
  border-radius: 4px;
  background: white;
  cursor: pointer;
}

.page-controls button:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.page-controls button:not(:disabled):hover {
  background: #f5f5f5;
}
</style>
