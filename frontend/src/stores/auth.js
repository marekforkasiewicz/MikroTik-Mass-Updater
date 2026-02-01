import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '../services/api'

export const useAuthStore = defineStore('auth', () => {
  // State
  const user = ref(null)
  const isAuthenticated = ref(false)
  const loading = ref(false)

  // Computed
  const isAdmin = computed(() => user.value?.role === 'admin')
  const isOperator = computed(() => user.value?.role === 'operator' || isAdmin.value)
  const canModify = computed(() => isOperator.value)

  // Actions
  async function login(username, password) {
    loading.value = true
    try {
      const response = await authApi.login(username, password)
      user.value = response.user
      isAuthenticated.value = true
      localStorage.setItem('isAuthenticated', 'true')
      return true
    } catch (error) {
      console.error('Login failed:', error)
      return false
    } finally {
      loading.value = false
    }
  }

  async function logout() {
    try {
      await authApi.logout()
    } catch (error) {
      console.error('Logout error:', error)
    } finally {
      user.value = null
      isAuthenticated.value = false
      localStorage.removeItem('isAuthenticated')
    }
  }

  async function checkAuth() {
    if (localStorage.getItem('isAuthenticated')) {
      try {
        const userData = await authApi.me()
        user.value = userData
        isAuthenticated.value = true
        return true
      } catch (error) {
        localStorage.removeItem('isAuthenticated')
        isAuthenticated.value = false
        return false
      }
    }
    return false
  }

  async function refreshToken() {
    try {
      await authApi.refresh()
      return true
    } catch (error) {
      await logout()
      return false
    }
  }

  function hasPermission(permission) {
    if (!user.value) return false
    if (user.value.role === 'admin') return true

    const operatorPermissions = [
      'view_routers', 'add_routers', 'edit_routers',
      'run_scan', 'run_updates',
      'view_scripts', 'execute_scripts',
      'view_schedules', 'manage_schedules',
      'view_backups', 'create_backups', 'restore_backups',
      'view_groups', 'manage_groups',
      'view_notifications', 'view_monitoring',
      'view_reports', 'export_reports',
      'view_webhooks', 'view_api_keys', 'manage_api_keys'
    ]

    const viewerPermissions = [
      'view_routers', 'view_scripts', 'view_schedules',
      'view_backups', 'view_groups', 'view_notifications',
      'view_monitoring', 'view_reports', 'view_webhooks'
    ]

    if (user.value.role === 'operator') {
      return operatorPermissions.includes(permission)
    }

    return viewerPermissions.includes(permission)
  }

  return {
    user,
    isAuthenticated,
    loading,
    isAdmin,
    isOperator,
    canModify,
    login,
    logout,
    checkAuth,
    refreshToken,
    hasPermission
  }
})
