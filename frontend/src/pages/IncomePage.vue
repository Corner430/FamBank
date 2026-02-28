<script setup lang="ts">
import { ref } from 'vue'
import { api, ApiError } from '../services/api'

interface SplitResult {
  total: string
  splits: { A: string; B: string; C: string }
  balances: { A: string; B_principal: string; B_interest_pool: string; C: string }
  escrow_note: string | null
}

const amount = ref('')
const description = ref('')
const loading = ref(false)
const error = ref('')
const result = ref<SplitResult | null>(null)

async function submitIncome() {
  error.value = ''
  result.value = null
  loading.value = true

  try {
    const res = await api.post<SplitResult>('/income', {
      amount: amount.value,
      description: description.value,
    })
    result.value = res
    amount.value = ''
    description.value = ''
  } catch (e: unknown) {
    if (e instanceof ApiError) {
      error.value = e.message
    } else {
      error.value = '录入失败'
    }
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="income-page">
    <h1>录入收入</h1>

    <div class="form">
      <div class="form-group">
        <label>金额（元）</label>
        <input
          v-model="amount"
          type="text"
          inputmode="decimal"
          placeholder="如：100.00"
          @keyup.enter="submitIncome"
        />
      </div>
      <div class="form-group">
        <label>备注（可选）</label>
        <input v-model="description" type="text" placeholder="如：压岁钱" />
      </div>
      <button @click="submitIncome" :disabled="loading || !amount">
        {{ loading ? '处理中...' : '录入' }}
      </button>
    </div>

    <p v-if="error" class="error">{{ error }}</p>

    <div v-if="result" class="result">
      <h2>分流结果</h2>
      <table>
        <thead>
          <tr><th>账户</th><th>入账金额</th><th>当前余额</th></tr>
        </thead>
        <tbody>
          <tr>
            <td>A 零钱宝</td>
            <td>&yen;{{ result.splits.A }}</td>
            <td>&yen;{{ result.balances.A }}</td>
          </tr>
          <tr>
            <td>B 梦想金</td>
            <td>&yen;{{ result.splits.B }}</td>
            <td>&yen;{{ result.balances.B_principal }} (利息池: &yen;{{ result.balances.B_interest_pool }})</td>
          </tr>
          <tr>
            <td>C 牛马金</td>
            <td>&yen;{{ result.splits.C }}</td>
            <td>&yen;{{ result.balances.C }}</td>
          </tr>
        </tbody>
      </table>
      <p v-if="result.escrow_note" class="escrow-note">{{ result.escrow_note }}</p>
    </div>
  </div>
</template>

<style scoped>
.income-page {
  max-width: 600px;
}

.form {
  margin-bottom: 24px;
}

.form-group {
  margin-bottom: 12px;
}

.form-group label {
  display: block;
  margin-bottom: 4px;
  font-size: 0.9em;
  color: #666;
}

.form-group input {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 1em;
  box-sizing: border-box;
}

button {
  padding: 10px 24px;
  background: #4a90d9;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 1em;
}

button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.error {
  color: #e74c3c;
}

.result {
  background: #f5f5f5;
  padding: 16px;
  border-radius: 8px;
}

.result h2 {
  margin-top: 0;
  font-size: 1.1em;
}

table {
  width: 100%;
  border-collapse: collapse;
}

th, td {
  padding: 8px 12px;
  text-align: left;
  border-bottom: 1px solid #ddd;
}

th {
  font-weight: 600;
  color: #555;
}

.escrow-note {
  margin-top: 12px;
  padding: 8px;
  background: #fff3e0;
  border-radius: 4px;
  color: #e65100;
}
</style>
