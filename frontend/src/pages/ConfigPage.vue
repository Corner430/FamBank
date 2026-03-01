<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { api, ApiError } from '../services/api'

interface ConfigItem {
  key: string
  value: string
  effective_from: string
}

interface AnnouncementItem {
  id: number
  config_key: string
  old_value: string
  new_value: string
  announced_at: string
  effective_from: string
}

const configs = ref<ConfigItem[]>([])
const announcements = ref<AnnouncementItem[]>([])
const loading = ref(true)
const error = ref('')

// Change form
const selectedKey = ref('')
const newValue = ref('')
const changeReason = ref('')
const submitting = ref(false)
const submitError = ref('')
const submitSuccess = ref<AnnouncementItem | null>(null)

// Display names for config keys
const keyLabels: Record<string, string> = {
  split_ratio_a: 'A分流比例 (%)',
  split_ratio_b: 'B分流比例 (%)',
  split_ratio_c: 'C分流比例 (%)',
  b_tier1_rate: 'B一档利率 (万分比)',
  b_tier1_limit: 'B一档上限 (分)',
  b_tier2_rate: 'B二档利率 (万分比)',
  b_tier3_rate: 'B三档利率 (万分比)',
  c_annual_rate: 'C年化利率 (万分比)',
  penalty_multiplier: '违约罚金倍数',
  redemption_fee_rate: 'C赎回手续费率 (%)',
  wishlist_lock_months: '愿望单锁定月数',
  wishlist_valid_months: '愿望单有效月数',
  b_suspend_months: 'B停息月数',
  c_lock_age: 'C解锁年龄',
}

function getLabel(key: string): string {
  return keyLabels[key] || key
}

async function loadConfig() {
  loading.value = true
  error.value = ''
  try {
    const res = await api.get<{ configs: ConfigItem[] }>('/config')
    configs.value = res.configs
  } catch (e: unknown) {
    error.value = e instanceof ApiError ? e.message : '加载配置失败'
  } finally {
    loading.value = false
  }
}

const announcementError = ref('')

async function loadAnnouncements() {
  announcementError.value = ''
  try {
    const res = await api.get<{ announcements: AnnouncementItem[] }>('/config/announcements')
    announcements.value = res.announcements
  } catch {
    announcementError.value = '加载公告失败'
  }
}

async function submitChange() {
  if (!selectedKey.value || !newValue.value) return
  submitting.value = true
  submitError.value = ''
  submitSuccess.value = null
  try {
    const res = await api.post<AnnouncementItem>('/config/announce', {
      key: selectedKey.value,
      new_value: newValue.value,
      reason: changeReason.value,
    })
    submitSuccess.value = res
    selectedKey.value = ''
    newValue.value = ''
    changeReason.value = ''
    await loadAnnouncements()
  } catch (e: unknown) {
    submitError.value = e instanceof ApiError ? e.message : '提交失败'
  } finally {
    submitting.value = false
  }
}

onMounted(() => {
  loadConfig()
  loadAnnouncements()
})
</script>

<template>
  <div class="config-page">
    <h1>参数配置</h1>

    <!-- Current Parameters Table -->
    <section class="section-card">
      <h2>当前参数</h2>
      <p v-if="loading">加载中...</p>
      <p v-else-if="error" class="error">{{ error }}</p>
      <table v-else class="config-table">
        <thead>
          <tr>
            <th>参数</th>
            <th>当前值</th>
            <th>生效日期</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="c in configs" :key="c.key">
            <td class="key-cell">{{ getLabel(c.key) }}</td>
            <td class="value-cell">{{ c.value }}</td>
            <td class="date-cell">{{ c.effective_from }}</td>
          </tr>
        </tbody>
      </table>
    </section>

    <!-- Change Form -->
    <section class="section-card">
      <h2>修改参数</h2>
      <p class="hint">修改将在下月1日生效 (S8)</p>

      <div class="change-form">
        <div class="form-row">
          <label>选择参数</label>
          <select v-model="selectedKey" :disabled="submitting">
            <option value="" disabled>请选择</option>
            <option v-for="c in configs" :key="c.key" :value="c.key">
              {{ getLabel(c.key) }}
            </option>
          </select>
        </div>
        <div class="form-row">
          <label>新值</label>
          <input
            v-model="newValue"
            type="text"
            placeholder="输入新的参数值"
            :disabled="submitting"
          />
        </div>
        <div class="form-row">
          <label>原因 (选填)</label>
          <input
            v-model="changeReason"
            type="text"
            placeholder="修改原因"
            :disabled="submitting"
          />
        </div>
        <button
          class="btn btn-primary"
          @click="submitChange"
          :disabled="submitting || !selectedKey || !newValue"
        >
          {{ submitting ? '提交中...' : '发布公告' }}
        </button>

        <p v-if="submitError" class="error">{{ submitError }}</p>

        <div v-if="submitSuccess" class="success-card">
          <p>公告已发布</p>
          <div class="detail-row">
            <span>参数：</span><span>{{ getLabel(submitSuccess.config_key) }}</span>
          </div>
          <div class="detail-row">
            <span>旧值：</span><span>{{ submitSuccess.old_value }}</span>
          </div>
          <div class="detail-row">
            <span>新值：</span><span>{{ submitSuccess.new_value }}</span>
          </div>
          <div class="detail-row">
            <span>生效日期：</span><span>{{ submitSuccess.effective_from }}</span>
          </div>
        </div>
      </div>
    </section>

    <!-- Announcement History -->
    <section class="section-card">
      <h2>公告历史</h2>
      <p v-if="announcementError" class="error-text">{{ announcementError }}</p>
      <p v-else-if="announcements.length === 0" class="empty-text">暂无公告</p>
      <table v-else class="config-table">
        <thead>
          <tr>
            <th>参数</th>
            <th>旧值</th>
            <th>新值</th>
            <th>公告日</th>
            <th>生效日</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="a in announcements" :key="a.id">
            <td>{{ getLabel(a.config_key) }}</td>
            <td>{{ a.old_value }}</td>
            <td class="new-value">{{ a.new_value }}</td>
            <td>{{ a.announced_at }}</td>
            <td>{{ a.effective_from }}</td>
          </tr>
        </tbody>
      </table>
    </section>
  </div>
</template>

<style scoped>
.config-page h1 {
  margin-bottom: 24px;
}

.section-card {
  margin-bottom: 24px;
  padding: 20px;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  background: white;
}

.section-card h2 {
  margin-bottom: 16px;
  font-size: 1.1em;
  color: #333;
}

.hint {
  font-size: 0.85em;
  color: #888;
  margin-bottom: 16px;
}

.config-table {
  width: 100%;
  border-collapse: collapse;
}

.config-table th,
.config-table td {
  padding: 10px 12px;
  text-align: left;
  border-bottom: 1px solid #eee;
}

.config-table th {
  background: #f5f5f5;
  font-weight: 600;
  font-size: 0.9em;
  color: #555;
}

.key-cell {
  font-weight: 500;
}

.value-cell {
  font-family: monospace;
  color: #1565c0;
}

.date-cell {
  color: #888;
  font-size: 0.9em;
}

.new-value {
  font-family: monospace;
  color: #2e7d32;
  font-weight: 500;
}

.change-form {
  max-width: 500px;
}

.form-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.form-row label {
  min-width: 100px;
  color: #555;
  font-size: 0.9em;
}

.form-row input,
.form-row select {
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

.error {
  color: #e74c3c;
  margin-top: 8px;
}

.success-card {
  margin-top: 16px;
  padding: 12px 16px;
  border: 2px solid #4caf50;
  border-radius: 6px;
  background: #e8f5e9;
}

.success-card p {
  font-weight: 600;
  color: #2e7d32;
  margin-bottom: 8px;
}

.detail-row {
  display: flex;
  justify-content: space-between;
  padding: 3px 0;
  font-size: 0.9em;
}

.empty-text {
  color: #aaa;
  font-style: italic;
}

.error-text {
  color: #e74c3c;
  font-size: 0.9em;
}
</style>
