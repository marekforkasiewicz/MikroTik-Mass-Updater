import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { monitoringApi } from '../services/api'

export const useMonitoringStore = defineStore('monitoring', () => {
  // State
  const overview = ref(null)
  const alerts = ref([])
  const activeAlerts = ref([])
  const healthHistory = ref({})
  const loading = ref(false)

  // Computed
  const criticalCount = computed(() =>
    activeAlerts.value.filter(a => a.severity === 'critical').length
  )
  const warningCount = computed(() =>
    activeAlerts.value.filter(a => a.severity === 'warning').length
  )
  const hasActiveAlerts = computed(() => activeAlerts.value.length > 0)

  // Actions
  async function fetchOverview() {
    loading.value = true
    try {
      overview.value = await monitoringApi.getOverview()
      return overview.value
    } catch (error) {
      console.error('Failed to fetch monitoring overview:', error)
      throw error
    } finally {
      loading.value = false
    }
  }

  async function fetchAlerts(params = {}) {
    try {
      const response = await monitoringApi.getAlerts(params)
      alerts.value = response.items
      return alerts.value
    } catch (error) {
      console.error('Failed to fetch alerts:', error)
      throw error
    }
  }

  async function fetchActiveAlerts() {
    try {
      const response = await monitoringApi.getActiveAlerts()
      activeAlerts.value = response.alerts
      return activeAlerts.value
    } catch (error) {
      console.error('Failed to fetch active alerts:', error)
      throw error
    }
  }

  async function acknowledgeAlerts(alertIds) {
    try {
      const result = await monitoringApi.acknowledgeAlerts(alertIds)
      await fetchActiveAlerts()
      return result
    } catch (error) {
      console.error('Failed to acknowledge alerts:', error)
      throw error
    }
  }

  async function resolveAlerts(alertIds) {
    try {
      const result = await monitoringApi.resolveAlerts(alertIds)
      await fetchActiveAlerts()
      return result
    } catch (error) {
      console.error('Failed to resolve alerts:', error)
      throw error
    }
  }

  async function fetchHealthHistory(routerId, hours = 24) {
    try {
      const response = await monitoringApi.getHealthHistory(routerId, { hours })
      healthHistory.value[routerId] = response.items
      return response.items
    } catch (error) {
      console.error('Failed to fetch health history:', error)
      throw error
    }
  }

  async function triggerHealthCheck(routerId, checkType = 'full') {
    try {
      return await monitoringApi.triggerCheck(routerId, checkType)
    } catch (error) {
      console.error('Failed to trigger health check:', error)
      throw error
    }
  }

  return {
    overview,
    alerts,
    activeAlerts,
    healthHistory,
    loading,
    criticalCount,
    warningCount,
    hasActiveAlerts,
    fetchOverview,
    fetchAlerts,
    fetchActiveAlerts,
    acknowledgeAlerts,
    resolveAlerts,
    fetchHealthHistory,
    triggerHealthCheck
  }
})
