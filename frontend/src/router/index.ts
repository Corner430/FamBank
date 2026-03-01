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
      path: '/onboarding',
      name: 'onboarding',
      component: () => import('../pages/OnboardingPage.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/',
      name: 'home',
      component: () => import('../pages/DashboardPage.vue'),
      meta: { requiresAuth: true, requiresFamily: true },
    },
    {
      path: '/dashboard',
      name: 'dashboard',
      component: () => import('../pages/DashboardPage.vue'),
      meta: { requiresAuth: true, requiresFamily: true },
    },
    {
      path: '/child/:childId',
      name: 'child-detail',
      component: () => import('../pages/ChildDetailPage.vue'),
      meta: { requiresAuth: true, requiresFamily: true, requiresParent: true },
    },
    {
      path: '/income',
      name: 'income',
      component: () => import('../pages/IncomePage.vue'),
      meta: { requiresAuth: true, requiresFamily: true },
    },
    {
      path: '/wishlist',
      name: 'wishlist',
      component: () => import('../pages/WishListPage.vue'),
      meta: { requiresAuth: true, requiresFamily: true },
    },
    {
      path: '/transactions',
      name: 'transactions',
      component: () => import('../pages/TransactionsPage.vue'),
      meta: { requiresAuth: true, requiresFamily: true },
    },
    {
      path: '/settlement',
      name: 'settlement',
      component: () => import('../pages/SettlementPage.vue'),
      meta: { requiresAuth: true, requiresFamily: true, requiresParent: true },
    },
    {
      path: '/violations',
      name: 'violations',
      component: () => import('../pages/ViolationPage.vue'),
      meta: { requiresAuth: true, requiresFamily: true, requiresParent: true },
    },
    {
      path: '/config',
      name: 'config',
      component: () => import('../pages/ConfigPage.vue'),
      meta: { requiresAuth: true, requiresFamily: true, requiresParent: true },
    },
    {
      path: '/settings',
      name: 'settings',
      component: () => import('../pages/SettingsPage.vue'),
      meta: { requiresAuth: true, requiresFamily: true },
    },
  ],
})

router.beforeEach((to) => {
  const user = getStoredUser()

  // Redirect to login if auth required and not logged in
  if (to.meta.requiresAuth && !user) {
    return { name: 'login' }
  }

  // Redirect logged-in users without family to onboarding (except login page)
  if (to.meta.requiresFamily && user && user.family_id === null) {
    return { name: 'onboarding' }
  }

  // Redirect parent-only routes for non-parent users
  if (to.meta.requiresParent && user?.role !== 'parent') {
    return { name: 'home' }
  }

  // Redirect logged-in users away from login page
  if (to.name === 'login' && user) {
    if (user.family_id === null) {
      return { name: 'onboarding' }
    }
    return user.role === 'parent' ? { name: 'dashboard' } : { name: 'home' }
  }
})

export default router
