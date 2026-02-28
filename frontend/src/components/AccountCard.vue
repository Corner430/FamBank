<script setup lang="ts">
interface Props {
  type: string
  name: string
  balance?: string
  principal?: string
  interestPool?: string
  isInterestSuspended?: boolean
  isDepositSuspended?: boolean
}

const props = defineProps<Props>()

const colorMap: Record<string, string> = {
  A: '#4caf50',
  B: '#ff9800',
  C: '#2196f3',
}
</script>

<template>
  <div class="account-card" :style="{ borderTopColor: colorMap[props.type] || '#999' }">
    <div class="card-header">
      <span class="account-type">{{ props.type }}</span>
      <span class="account-name">{{ props.name }}</span>
    </div>
    <div class="card-body">
      <template v-if="props.type === 'B'">
        <div class="balance-row">
          <span class="label">本金</span>
          <span class="amount">&yen;{{ props.principal || '0.00' }}</span>
        </div>
        <div class="balance-row">
          <span class="label">利息池</span>
          <span class="amount secondary">&yen;{{ props.interestPool || '0.00' }}</span>
        </div>
        <div v-if="props.isInterestSuspended" class="status-badge warning">停息中</div>
        <div v-if="props.isDepositSuspended" class="status-badge danger">暂停入金</div>
      </template>
      <template v-else>
        <div class="balance-row">
          <span class="label">余额</span>
          <span class="amount">&yen;{{ props.balance || '0.00' }}</span>
        </div>
      </template>
    </div>
  </div>
</template>

<style scoped>
.account-card {
  border: 1px solid #e0e0e0;
  border-top: 4px solid;
  border-radius: 8px;
  padding: 16px;
  background: white;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.account-type {
  font-weight: bold;
  font-size: 1.2em;
}

.account-name {
  color: #666;
  font-size: 0.9em;
}

.balance-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.label {
  color: #888;
  font-size: 0.85em;
}

.amount {
  font-size: 1.3em;
  font-weight: bold;
}

.amount.secondary {
  font-size: 1em;
  color: #666;
}

.status-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 0.8em;
  margin-top: 8px;
}

.status-badge.warning {
  background: #fff3e0;
  color: #e65100;
}

.status-badge.danger {
  background: #ffebee;
  color: #c62828;
}
</style>
