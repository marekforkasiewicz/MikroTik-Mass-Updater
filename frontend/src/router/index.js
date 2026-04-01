import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { appRoutes } from './routes'

const router = createRouter({
  history: createWebHistory(),
  routes: appRoutes
})

router.beforeEach(async (to) => {
  const authStore = useAuthStore()

  if (to.meta.public) {
    return true
  }

  if (!authStore.isAuthenticated) {
    const isAuth = await authStore.checkAuth()
    if (!isAuth) {
      return { name: 'login', query: { redirect: to.fullPath } }
    }
  }

  if (to.meta.requiresAdmin && !authStore.isAdmin) {
    return { name: 'dashboard' }
  }

  if (to.meta.requiresOperator && !authStore.isOperator) {
    return { name: 'dashboard' }
  }

  return true
})

export default router
