import { createRouter, createWebHistory } from 'vue-router'
import { getStoredUser } from '../services/api'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('../pages/LoginPage.vue'),
    },
    {
      path: '/',
      name: 'dashboard',
      component: () => import('../pages/DashboardPage.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/income',
      name: 'income',
      component: () => import('../pages/IncomePage.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/wishlist',
      name: 'wishlist',
      component: () => import('../pages/WishListPage.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/transactions',
      name: 'transactions',
      component: () => import('../pages/TransactionsPage.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/settlement',
      name: 'settlement',
      component: () => import('../pages/SettlementPage.vue'),
      meta: { requiresAuth: true, requiresParent: true },
    },
    {
      path: '/violations',
      name: 'violations',
      component: () => import('../pages/ViolationPage.vue'),
      meta: { requiresAuth: true, requiresParent: true },
    },
    {
      path: '/config',
      name: 'config',
      component: () => import('../pages/ConfigPage.vue'),
      meta: { requiresAuth: true, requiresParent: true },
    },
  ],
})

router.beforeEach((to) => {
  const user = getStoredUser()

  if (to.meta.requiresAuth && !user) {
    return { name: 'login' }
  }

  if (to.meta.requiresParent && user?.role !== 'parent') {
    return { name: 'dashboard' }
  }
})

export default router
