<template>
  <div class="container-fluid py-4">
    <div class="d-flex justify-content-between align-items-center mb-4">
      <h2><i class="bi bi-heart-pulse me-2"></i>Monitoring</h2>
      <button class="btn btn-outline-primary" @click="refresh" :disabled="loading">
        <i class="bi bi-arrow-clockwise me-1"></i> Refresh
      </button>
    </div>

    <!-- Alert Banner -->
    <div v-if="hasActiveAlerts" class="alert alert-danger d-flex align-items-center mb-4">
      <i class="bi bi-exclamation-triangle-fill me-2 fs-4"></i>
      <div class="flex-grow-1">
        <strong>{{ criticalCount }} Critical</strong> and
        <strong>{{ warningCount }} Warning</strong> alerts active
      </div>
      <button class="btn btn-sm btn-outline-danger" @click="showAlertsModal = true">
        View Alerts
      </button>
    </div>

    <!-- Stats Cards -->
    <div class="row g-4 mb-4">
      <div class="col-md-3">
        <div class="card bg-primary text-white">
          <div class="card-body">
            <div class="d-flex justify-content-between">
              <div>
                <h3 class="mb-0">{{ overview?.total_routers || 0 }}</h3>
                <small>Total Routers</small>
              </div>
              <i class="bi bi-router fs-1 opacity-50"></i>
            </div>
          </div>
        </div>
      </div>
      <div class="col-md-3">
        <div class="card bg-success text-white">
          <div class="card-body">
            <div class="d-flex justify-content-between">
              <div>
                <h3 class="mb-0">{{ overview?.online_routers || 0 }}</h3>
                <small>Online</small>
              </div>
              <i class="bi bi-check-circle fs-1 opacity-50"></i>
            </div>
          </div>
        </div>
      </div>
      <div class="col-md-3">
        <div class="card bg-danger text-white">
          <div class="card-body">
            <div class="d-flex justify-content-between">
              <div>
                <h3 class="mb-0">{{ overview?.offline_routers || 0 }}</h3>
                <small>Offline</small>
              </div>
              <i class="bi bi-x-circle fs-1 opacity-50"></i>
            </div>
          </div>
        </div>
      </div>
      <div class="col-md-3">
        <div class="card bg-warning text-dark">
          <div class="card-body">
            <div class="d-flex justify-content-between">
              <div>
                <h3 class="mb-0">{{ overview?.active_alerts || 0 }}</h3>
                <small>Active Alerts</small>
              </div>
              <i class="bi bi-bell fs-1 opacity-50"></i>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Router Status Grid -->
    <div class="card">
      <div class="card-header d-flex justify-content-between align-items-center">
        <h5 class="mb-0">Router Health Status</h5>
        <div class="btn-group btn-group-sm">
          <button class="btn btn-outline-secondary" :class="{ active: filter === 'all' }"
                  @click="filter = 'all'">All</button>
          <button class="btn btn-outline-danger" :class="{ active: filter === 'critical' }"
                  @click="filter = 'critical'">Critical</button>
          <button class="btn btn-outline-warning" :class="{ active: filter === 'warning' }"
                  @click="filter = 'warning'">Warning</button>
          <button class="btn btn-outline-secondary" :class="{ active: filter === 'offline' }"
                  @click="filter = 'offline'">Offline</button>
        </div>
      </div>
      <div class="card-body">
        <div class="table-responsive">
          <table class="table table-hover">
            <thead>
              <tr>
                <th>Router</th>
                <th>Status</th>
                <th>Latency</th>
                <th>CPU</th>
                <th>Memory</th>
                <th>Disk</th>
                <th>Alerts</th>
                <th>Last Check</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="router in filteredRouters" :key="router.router_id">
                <td>
                  <div>{{ router.identity || router.ip }}</div>
                  <small class="text-muted">{{ router.ip }}</small>
                </td>
                <td>
                  <span :class="statusBadgeClass(router.status)">
                    {{ router.status }}
                  </span>
                </td>
                <td>
                  <span v-if="router.latency_ms" :class="latencyClass(router.latency_ms)">
                    {{ router.latency_ms.toFixed(1) }}ms
                  </span>
                  <span v-else class="text-muted">-</span>
                </td>
                <td>
                  <div v-if="router.cpu_usage !== null" class="progress" style="height: 20px;">
                    <div class="progress-bar" :class="usageClass(router.cpu_usage)"
                         :style="{ width: router.cpu_usage + '%' }">
                      {{ router.cpu_usage.toFixed(0) }}%
                    </div>
                  </div>
                  <span v-else class="text-muted">-</span>
                </td>
                <td>
                  <div v-if="router.memory_usage !== null" class="progress" style="height: 20px;">
                    <div class="progress-bar" :class="usageClass(router.memory_usage)"
                         :style="{ width: router.memory_usage + '%' }">
                      {{ router.memory_usage.toFixed(0) }}%
                    </div>
                  </div>
                  <span v-else class="text-muted">-</span>
                </td>
                <td>
                  <div v-if="router.disk_usage !== null" class="progress" style="height: 20px;">
                    <div class="progress-bar" :class="usageClass(router.disk_usage)"
                         :style="{ width: router.disk_usage + '%' }">
                      {{ router.disk_usage.toFixed(0) }}%
                    </div>
                  </div>
                  <span v-else class="text-muted">-</span>
                </td>
                <td>
                  <span v-if="router.active_alerts > 0" class="badge bg-danger">
                    {{ router.active_alerts }}
                  </span>
                  <span v-else class="text-muted">0</span>
                </td>
                <td>
                  <small>{{ formatTime(router.last_check) }}</small>
                </td>
                <td>
                  <button class="btn btn-sm btn-outline-primary" @click="checkNow(router)"
                          :disabled="checkingRouter === router.router_id"
                          title="Check Now">
                    <span v-if="checkingRouter === router.router_id" class="spinner-border spinner-border-sm"></span>
                    <i v-else class="bi bi-arrow-repeat"></i>
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- Alerts Modal -->
    <div class="modal fade" id="alertsModal" tabindex="-1" ref="alertsModalEl">
      <div class="modal-dialog modal-lg">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">Active Alerts</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
          </div>
          <div class="modal-body">
            <div class="list-group">
              <div v-for="alert in activeAlerts" :key="alert.id"
                   class="list-group-item d-flex align-items-start">
                <div class="me-3">
                  <i :class="alertIcon(alert.severity)" class="fs-4"></i>
                </div>
                <div class="flex-grow-1">
                  <h6 class="mb-1">{{ alert.title }}</h6>
                  <p class="mb-1 text-muted small">{{ alert.message }}</p>
                  <small class="text-muted">{{ formatTime(alert.created_at) }}</small>
                </div>
                <div>
                  <button class="btn btn-sm btn-outline-secondary" @click="acknowledgeAlert(alert.id)"
                          v-if="alert.status === 'active'">
                    Acknowledge
                  </button>
                </div>
              </div>
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
            <button type="button" class="btn btn-success" @click="resolveAllAlerts">
              Resolve All
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick, watch } from 'vue'
import { Modal } from 'bootstrap'
import { useMonitoringStore } from '../stores/monitoring'
import { useMainStore } from '../stores/main'

const mainStore = useMainStore()

const monitoringStore = useMonitoringStore()

const overview = computed(() => monitoringStore.overview)
const activeAlerts = computed(() => monitoringStore.activeAlerts)
const loading = computed(() => monitoringStore.loading)
const hasActiveAlerts = computed(() => monitoringStore.hasActiveAlerts)
const criticalCount = computed(() => monitoringStore.criticalCount)
const warningCount = computed(() => monitoringStore.warningCount)

const filter = ref('all')
const showAlertsModal = ref(false)
const alertsModalEl = ref(null)
const checkingRouter = ref(null)
let alertsModal = null

const filteredRouters = computed(() => {
  const routers = overview.value?.routers || []
  if (filter.value === 'all') return routers
  if (filter.value === 'offline') return routers.filter(r => !r.is_online)
  return routers.filter(r => r.status === filter.value)
})

onMounted(async () => {
  await refresh()

  nextTick(() => {
    if (alertsModalEl.value) {
      alertsModal = new Modal(alertsModalEl.value)
    }
  })
})

watch(showAlertsModal, (val) => {
  if (val) {
    monitoringStore.fetchActiveAlerts()
    alertsModal?.show()
  }
})

async function refresh() {
  await Promise.all([
    monitoringStore.fetchOverview(),
    monitoringStore.fetchActiveAlerts()
  ])
}

async function checkNow(router) {
  checkingRouter.value = router.router_id
  try {
    await monitoringStore.triggerHealthCheck(router.router_id, 'full')
    await monitoringStore.fetchOverview()
    mainStore.addNotification('success', 'Health check completed')
  } catch (error) {
    console.error('Health check failed:', error)
    mainStore.addNotification('error', 'Health check failed: ' + error.message)
  } finally {
    checkingRouter.value = null
  }
}

async function acknowledgeAlert(alertId) {
  try {
    await monitoringStore.acknowledgeAlerts([alertId])
  } catch (error) {
    console.error('Failed to acknowledge alert:', error)
  }
}

async function resolveAllAlerts() {
  const ids = activeAlerts.value.map(a => a.id)
  if (ids.length > 0) {
    try {
      await monitoringStore.resolveAlerts(ids)
      alertsModal?.hide()
    } catch (error) {
      console.error('Failed to resolve alerts:', error)
    }
  }
}

function statusBadgeClass(status) {
  const classes = {
    ok: 'badge bg-success',
    warning: 'badge bg-warning text-dark',
    critical: 'badge bg-danger',
    unknown: 'badge bg-secondary'
  }
  return classes[status] || 'badge bg-secondary'
}

function latencyClass(latency) {
  if (latency > 500) return 'text-danger'
  if (latency > 100) return 'text-warning'
  return 'text-success'
}

function usageClass(usage) {
  if (usage > 90) return 'bg-danger'
  if (usage > 70) return 'bg-warning'
  return 'bg-success'
}

function alertIcon(severity) {
  const icons = {
    critical: 'bi bi-exclamation-triangle-fill text-danger',
    warning: 'bi bi-exclamation-circle-fill text-warning',
    info: 'bi bi-info-circle-fill text-info'
  }
  return icons[severity] || 'bi bi-bell text-secondary'
}

function formatTime(dateStr) {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  const now = new Date()
  const diff = (now - date) / 1000

  if (diff < 60) return 'Just now'
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
  return date.toLocaleDateString()
}
</script>
