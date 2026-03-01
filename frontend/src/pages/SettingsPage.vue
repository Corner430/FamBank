<script setup lang="ts">
import { ref } from 'vue'
import { api, ApiError } from '../services/api'

// Change own PIN
const oldPin = ref('')
const newPin = ref('')
const confirmPin = ref('')
const changePinLoading = ref(false)
const changePinError = ref('')
const changePinSuccess = ref('')

// Reset child PIN
const parentPin = ref('')
const newChildPin = ref('')
const resetLoading = ref(false)
const resetError = ref('')
const resetSuccess = ref('')

async function changePin() {
  changePinError.value = ''
  changePinSuccess.value = ''

  if (newPin.value.length < 4) {
    changePinError.value = '新密码至少4位'
    return
  }
  if (newPin.value !== confirmPin.value) {
    changePinError.value = '两次输入的新密码不一致'
    return
  }

  changePinLoading.value = true
  try {
    const res = await api.put<{ message: string }>('/auth/pin', {
      old_pin: oldPin.value,
      new_pin: newPin.value,
    })
    changePinSuccess.value = res.message
    oldPin.value = ''
    newPin.value = ''
    confirmPin.value = ''
  } catch (e: unknown) {
    changePinError.value = e instanceof ApiError ? e.message : '修改失败'
  } finally {
    changePinLoading.value = false
  }
}

async function resetChildPin() {
  resetError.value = ''
  resetSuccess.value = ''

  if (newChildPin.value.length < 4) {
    resetError.value = '新PIN码至少4位'
    return
  }

  resetLoading.value = true
  try {
    const res = await api.put<{ message: string }>('/auth/child-pin', {
      parent_pin: parentPin.value,
      new_child_pin: newChildPin.value,
    })
    resetSuccess.value = res.message
    parentPin.value = ''
    newChildPin.value = ''
  } catch (e: unknown) {
    resetError.value = e instanceof ApiError ? e.message : '重置失败'
  } finally {
    resetLoading.value = false
  }
}
</script>

<template>
  <div class="settings-page">
    <h1>设置</h1>

    <!-- Change own PIN -->
    <section class="section-card">
      <h2>修改管理密码</h2>
      <div class="change-form">
        <div class="form-row">
          <label>原密码</label>
          <input
            v-model="oldPin"
            type="password"
            placeholder="输入当前密码"
            :disabled="changePinLoading"
          />
        </div>
        <div class="form-row">
          <label>新密码</label>
          <input
            v-model="newPin"
            type="password"
            placeholder="至少4位"
            :disabled="changePinLoading"
          />
        </div>
        <div class="form-row">
          <label>确认新密码</label>
          <input
            v-model="confirmPin"
            type="password"
            placeholder="再次输入新密码"
            :disabled="changePinLoading"
          />
        </div>
        <button
          class="btn btn-primary"
          @click="changePin"
          :disabled="changePinLoading || !oldPin || !newPin || !confirmPin"
        >
          {{ changePinLoading ? '提交中...' : '修改密码' }}
        </button>
        <p v-if="changePinError" class="error">{{ changePinError }}</p>
        <p v-if="changePinSuccess" class="success">{{ changePinSuccess }}</p>
      </div>
    </section>

    <!-- Reset child PIN -->
    <section class="section-card">
      <h2>重置乙方 PIN 码</h2>
      <p class="hint">需要输入管理密码进行二次认证</p>
      <div class="change-form">
        <div class="form-row">
          <label>管理密码</label>
          <input
            v-model="parentPin"
            type="password"
            placeholder="输入您的管理密码"
            :disabled="resetLoading"
          />
        </div>
        <div class="form-row">
          <label>新 PIN 码</label>
          <input
            v-model="newChildPin"
            type="password"
            placeholder="至少4位"
            :disabled="resetLoading"
          />
        </div>
        <button
          class="btn btn-primary"
          @click="resetChildPin"
          :disabled="resetLoading || !parentPin || !newChildPin"
        >
          {{ resetLoading ? '提交中...' : '重置 PIN 码' }}
        </button>
        <p v-if="resetError" class="error">{{ resetError }}</p>
        <p v-if="resetSuccess" class="success">{{ resetSuccess }}</p>
      </div>
    </section>
  </div>
</template>

<style scoped>
.settings-page h1 {
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

.error {
  color: #e74c3c;
  margin-top: 8px;
}

.success {
  color: #2e7d32;
  margin-top: 8px;
  font-weight: 500;
}
</style>
