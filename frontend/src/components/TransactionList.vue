<script setup lang="ts">
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

interface Props {
  items: TransactionItem[]
  loading?: boolean
}

defineProps<Props>()

const typeLabels: Record<string, string> = {
  income_split_a: '收入分流A',
  income_split_b: '收入分流B',
  income_split_c: '收入分流C',
  a_spend: 'A消费',
  violation_penalty: '违约罚金',
  violation_penalty_credit: '罚金入C',
  debt_repayment: '偿还欠款',
  escrow_in: '暂存入金',
  b_interest: 'B利息',
  b_overflow: 'B溢出',
  c_dividend: 'C分红',
  settlement: '结算',
  purchase_a: '购买(A)',
  purchase_c: '购买(C)',
  refund_a: '退款(A)',
  refund_c: '退款(C)',
}

function formatType(type: string): string {
  return typeLabels[type] || type
}

function formatTime(ts: string): string {
  const d = new Date(ts)
  return d.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function accountDisplay(src: string | null, tgt: string | null): string {
  if (src && tgt) return `${src} -> ${tgt}`
  if (src) return src
  if (tgt) return tgt
  return '-'
}
</script>

<template>
  <div class="transaction-list">
    <p v-if="loading" class="loading-text">加载中...</p>
    <p v-else-if="items.length === 0" class="empty-text">暂无交易记录</p>
    <table v-else class="txn-table">
      <thead>
        <tr>
          <th>时间</th>
          <th>类型</th>
          <th>账户</th>
          <th class="text-right">金额</th>
          <th class="text-right">变动前</th>
          <th class="text-right">变动后</th>
          <th>条款</th>
          <th>说明</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="txn in items" :key="txn.id">
          <td class="nowrap">{{ formatTime(txn.timestamp) }}</td>
          <td>{{ formatType(txn.type) }}</td>
          <td>{{ accountDisplay(txn.source_account, txn.target_account) }}</td>
          <td class="text-right amount">&yen;{{ txn.amount }}</td>
          <td class="text-right">&yen;{{ txn.balance_before }}</td>
          <td class="text-right">&yen;{{ txn.balance_after }}</td>
          <td class="clause">{{ txn.charter_clause }}</td>
          <td class="desc">{{ txn.description || '-' }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.transaction-list {
  overflow-x: auto;
}

.txn-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.9em;
}

.txn-table th,
.txn-table td {
  padding: 8px 10px;
  border-bottom: 1px solid #e0e0e0;
  text-align: left;
}

.txn-table th {
  background: #f5f5f5;
  font-weight: 600;
  font-size: 0.85em;
  color: #666;
}

.text-right {
  text-align: right;
}

.amount {
  font-weight: 600;
}

.nowrap {
  white-space: nowrap;
}

.clause {
  color: #888;
  font-size: 0.85em;
}

.desc {
  color: #666;
  max-width: 150px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.loading-text,
.empty-text {
  text-align: center;
  color: #999;
  padding: 24px 0;
}
</style>
