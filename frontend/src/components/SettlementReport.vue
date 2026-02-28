<script setup lang="ts">
interface Props {
  steps: {
    c_dividend: { amount: string }
    b_overflow: { amount: string }
    b_interest: { amount: string; tier1: string; tier2: string; tier3: string }
    violation_transfer: { amount: string }
  }
  balancesAfter: {
    A: string
    B_principal: string
    B_interest_pool: string
    C: string
  }
}

const props = defineProps<Props>()
</script>

<template>
  <div class="settlement-report">
    <h3>结算明细</h3>
    <table>
      <thead>
        <tr><th>步骤</th><th>金额</th><th>说明</th></tr>
      </thead>
      <tbody>
        <tr>
          <td>1. C派息 → A</td>
          <td>&yen;{{ props.steps.c_dividend.amount }}</td>
          <td>C本金年化5%月息</td>
        </tr>
        <tr>
          <td>2. B溢出 → C</td>
          <td>&yen;{{ props.steps.b_overflow.amount }}</td>
          <td>超出1.2×P_active部分</td>
        </tr>
        <tr>
          <td>3. B计息</td>
          <td>&yen;{{ props.steps.b_interest.amount }}</td>
          <td>
            T1=&yen;{{ props.steps.b_interest.tier1 }},
            T2=&yen;{{ props.steps.b_interest.tier2 }},
            T3=&yen;{{ props.steps.b_interest.tier3 }}
          </td>
        </tr>
        <tr>
          <td>4. 违约划转 A → C</td>
          <td>&yen;{{ props.steps.violation_transfer.amount }}</td>
          <td>本月违约等额划转</td>
        </tr>
      </tbody>
    </table>

    <h3>结算后余额</h3>
    <div class="balances">
      <span>A: &yen;{{ props.balancesAfter.A }}</span>
      <span>B本金: &yen;{{ props.balancesAfter.B_principal }}</span>
      <span>B利息池: &yen;{{ props.balancesAfter.B_interest_pool }}</span>
      <span>C: &yen;{{ props.balancesAfter.C }}</span>
    </div>
  </div>
</template>

<style scoped>
.settlement-report {
  background: #f5f5f5;
  padding: 16px;
  border-radius: 8px;
  margin-top: 16px;
}

h3 {
  margin-top: 0;
  font-size: 1em;
}

table {
  width: 100%;
  border-collapse: collapse;
  margin-bottom: 16px;
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

.balances {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
}

.balances span {
  background: white;
  padding: 6px 12px;
  border-radius: 4px;
  font-size: 0.9em;
}
</style>
