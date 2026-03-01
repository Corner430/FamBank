<script setup lang="ts">
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { currentUser, logout as doLogout } from './services/api'

const router = useRouter()
const route = useRoute()
const user = currentUser

const showNav = computed(() => {
  if (!user.value) return false
  if (!user.value.family_id) return false
  if (route.name === 'login' || route.name === 'onboarding') return false
  return true
})

const roleLabel = computed(() => {
  if (user.value?.role === 'parent') return '甲方'
  if (user.value?.role === 'child') return '乙方'
  return ''
})

function logout() {
  doLogout()
  router.push('/login')
}
</script>

<template>
  <div id="app-root">
    <nav v-if="showNav" class="navbar">
      <div class="nav-brand">
        <router-link to="/">FamBank</router-link>
      </div>
      <div class="nav-links">
        <router-link to="/">总览</router-link>
        <router-link to="/income">入账</router-link>
        <router-link to="/wishlist">愿望清单</router-link>
        <router-link to="/transactions">交易记录</router-link>
        <router-link v-if="user?.role === 'parent'" to="/settlement">结算</router-link>
        <router-link v-if="user?.role === 'parent'" to="/violations">违约</router-link>
        <router-link v-if="user?.role === 'parent'" to="/config">配置</router-link>
        <router-link v-if="user?.role === 'parent'" to="/settings">设置</router-link>
      </div>
      <div class="nav-user">
        <span>{{ user?.name || '用户' }} ({{ roleLabel }})</span>
        <button @click="logout" class="btn-logout">退出</button>
      </div>
    </nav>
    <main class="content">
      <router-view />
    </main>
  </div>
</template>

<style scoped>
.navbar {
  display: flex;
  align-items: center;
  padding: 12px 24px;
  background: white;
  border-bottom: 1px solid #e0e0e0;
  gap: 24px;
  flex-wrap: wrap;
}

.nav-brand a {
  font-weight: bold;
  font-size: 1.2em;
  text-decoration: none;
  color: #333;
}

.nav-links {
  display: flex;
  gap: 8px;
  flex: 1;
  flex-wrap: wrap;
}

.nav-links a {
  text-decoration: none;
  color: #555;
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 0.9em;
  white-space: nowrap;
}

.nav-links a.router-link-active {
  background: #e3f2fd;
  color: #1976d2;
}

.nav-user {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 0.9em;
  color: #666;
}

.btn-logout {
  padding: 4px 12px;
  background: none;
  border: 1px solid #ccc;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.85em;
  color: #666;
}

.btn-logout:hover {
  background: #f5f5f5;
}

.content {
  max-width: 960px;
  margin: 24px auto;
  padding: 0 24px;
}

@media (max-width: 768px) {
  .navbar {
    padding: 10px 12px;
    gap: 12px;
  }

  .nav-links {
    order: 3;
    flex-basis: 100%;
    gap: 4px;
  }

  .content {
    margin: 16px auto;
    padding: 0 12px;
  }
}
</style>
