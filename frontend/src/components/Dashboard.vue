<template>
  <div>
    <h2 class="mb-4">Dashboard</h2>

    <!-- Stats Cards -->
    <div class="row g-4 mb-4">
      <div class="col-md-3">
        <div class="card stat-card h-100">
          <div class="card-body d-flex justify-content-between align-items-center">
            <div>
              <h6 class="text-muted mb-1">Configured Routers</h6>
              <div class="stat-value">{{ store.routerStats.total }}</div>
            </div>
            <i class="bi bi-hdd-network stat-icon text-primary"></i>
          </div>
        </div>
      </div>

      <div class="col-md-3">
        <div class="card stat-card h-100 border-start border-info border-4" @click="runDiscovery" style="cursor: pointer;" title="Click to scan">
          <div class="card-body d-flex justify-content-between align-items-center">
            <div>
              <h6 class="text-muted mb-1">Discovered (MNDP)</h6>
              <div class="stat-value text-info">
                <span v-if="discoveryLoading" class="spinner-border spinner-border-sm"></span>
                <span v-else>{{ discoveredCount }}</span>
              </div>
            </div>
            <i class="bi bi-broadcast stat-icon text-info"></i>
          </div>
        </div>
      </div>

      <div class="col-md-3">
        <div class="card stat-card h-100 border-start border-success border-4">
          <div class="card-body d-flex justify-content-between align-items-center">
            <div>
              <h6 class="text-muted mb-1">Online</h6>
              <div class="stat-value text-success">{{ store.routerStats.online }}</div>
            </div>
            <i class="bi bi-check-circle stat-icon text-success"></i>
          </div>
        </div>
      </div>

      <div class="col-md-3">
        <div class="card stat-card h-100 border-start border-warning border-4">
          <div class="card-body d-flex justify-content-between align-items-center">
            <div>
              <h6 class="text-muted mb-1">Needs Update</h6>
              <div class="stat-value text-warning">{{ store.routerStats.needsUpdate }}</div>
            </div>
            <i class="bi bi-arrow-repeat stat-icon text-warning"></i>
          </div>
        </div>
      </div>
    </div>

    <!-- Charts Row -->
    <div class="row g-4 mb-4">
      <div class="col-md-4">
        <div class="card h-100">
          <div class="card-header">
            <h6 class="mb-0">RouterOS Versions</h6>
          </div>
          <div class="card-body">
            <Pie v-if="versionChartData.labels.length > 0" :data="versionChartData" :options="pieOptions" />
            <div v-else class="text-center text-muted py-4">No data available</div>
          </div>
        </div>
      </div>

      <div class="col-md-4">
        <div class="card h-100">
          <div class="card-header">
            <h6 class="mb-0">Router Models</h6>
          </div>
          <div class="card-body">
            <Bar v-if="modelChartData.labels.length > 0" :data="modelChartData" :options="barOptions" />
            <div v-else class="text-center text-muted py-4">No data available</div>
          </div>
        </div>
      </div>

      <div class="col-md-4">
        <div class="card h-100">
          <div class="card-header">
            <h6 class="mb-0">Health Status</h6>
          </div>
          <div class="card-body">
            <Doughnut v-if="healthChartData.labels.length > 0" :data="healthChartData" :options="doughnutOptions" />
            <div v-else class="text-center text-muted py-4">No data available</div>
          </div>
        </div>
      </div>
    </div>

    <!-- Quick Actions -->
    <div class="row g-4 mb-4">
      <div class="col-md-6">
        <div class="card h-100">
          <div class="card-header">
            <h5 class="mb-0">Quick Actions</h5>
          </div>
          <div class="card-body">
            <div class="d-grid gap-2">
              <button class="btn btn-outline-primary" @click="importRouters" :disabled="loading">
                <i class="bi bi-upload me-2"></i>
                Import from list.txt
              </button>
              <button class="btn btn-outline-success" @click="startQuickScan" :disabled="loading">
                <i class="bi bi-lightning me-2"></i>
                Quick Scan All
              </button>
              <button class="btn btn-outline-info" @click="startFullScan" :disabled="loading">
                <i class="bi bi-search me-2"></i>
                Full Scan All
              </button>
              <router-link to="/update" class="btn btn-primary">
                <i class="bi bi-cloud-download me-2"></i>
                Start Update
              </router-link>
            </div>
          </div>
        </div>
      </div>

      <div class="col-md-6">
        <div class="card h-100">
          <div class="card-header d-flex justify-content-between align-items-center">
            <h5 class="mb-0">Recent Routers</h5>
            <router-link to="/routers" class="btn btn-sm btn-outline-primary">
              View All
            </router-link>
          </div>
          <div class="card-body p-0">
            <div class="table-responsive">
              <table class="table table-hover mb-0 router-table">
                <thead>
                  <tr>
                    <th>IP</th>
                    <th>Identity</th>
                    <th>Status</th>
                    <th>Version</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="router in recentRouters" :key="router.id">
                    <td>{{ router.ip }}</td>
                    <td>{{ router.identity || '-' }}</td>
                    <td>
                      <i
                        class="bi status-icon"
                        :class="{
                          'bi-check-circle-fill status-online': router.is_online,
                          'bi-x-circle-fill status-offline': !router.is_online
                        }"
                      ></i>
                    </td>
                    <td>{{ router.ros_version || '-' }}</td>
                  </tr>
                  <tr v-if="recentRouters.length === 0">
                    <td colspan="4" class="text-center text-muted py-3">
                      No routers found. Import from list.txt to get started.
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Discovered Routers (MNDP) -->
    <div class="card mb-4" v-if="discoveredRouters.length > 0">
      <div class="card-header d-flex justify-content-between align-items-center">
        <h5 class="mb-0">
          <i class="bi bi-broadcast me-2"></i>
          Discovered Routers (MNDP)
        </h5>
        <div>
          <button class="btn btn-sm btn-outline-info me-2" @click="runDiscovery" :disabled="discoveryLoading">
            <span v-if="discoveryLoading" class="spinner-border spinner-border-sm me-1"></span>
            <i v-else class="bi bi-arrow-clockwise me-1"></i>
            Rescan
          </button>
        </div>
      </div>
      <div class="card-body p-0">
        <div class="table-responsive">
          <table class="table table-hover mb-0">
            <thead>
              <tr>
                <th>Identity</th>
                <th>IP Address</th>
                <th>MAC Address</th>
                <th>Platform</th>
                <th>Version</th>
                <th>Uptime</th>
                <th>Status</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="device in discoveredRouters" :key="device.mac_address">
                <td><strong>{{ device.identity || '-' }}</strong></td>
                <td><code>{{ device.ipv4_address || '-' }}</code></td>
                <td><code class="text-muted">{{ device.mac_address }}</code></td>
                <td>{{ device.platform || device.board || '-' }}</td>
                <td>{{ device.version || '-' }}</td>
                <td>{{ device.uptime_formatted || '-' }}</td>
                <td>
                  <span v-if="isConfigured(device)" class="badge bg-success">Configured</span>
                  <span v-else class="badge bg-secondary">New</span>
                </td>
                <td>
                  <button
                    v-if="!isConfigured(device) && device.ipv4_address"
                    class="btn btn-sm btn-outline-primary"
                    @click="addDiscoveredRouter(device)"
                    :disabled="addingRouter === device.mac_address"
                  >
                    <span v-if="addingRouter === device.mac_address" class="spinner-border spinner-border-sm"></span>
                    <i v-else class="bi bi-plus-circle"></i>
                    Add
                  </button>
                  <span v-else-if="isConfigured(device)" class="text-success">
                    <i class="bi bi-check-circle"></i>
                  </span>
                  <span v-else class="text-muted">No IP</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- Running Tasks -->
    <div class="card" v-if="store.runningTasks.length > 0">
      <div class="card-header">
        <h5 class="mb-0">
          <i class="bi bi-gear spin me-2"></i>
          Running Tasks
        </h5>
      </div>
      <div class="card-body">
        <div v-for="task in store.runningTasks" :key="task.id" class="mb-3">
          <div class="d-flex justify-content-between mb-1">
            <span>{{ task.type }} - {{ task.current_item || 'Starting...' }}</span>
            <span>{{ task.progress }}/{{ task.total }}</span>
          </div>
          <div class="progress task-progress">
            <div
              class="progress-bar progress-bar-striped progress-bar-animated"
              :style="{ width: `${(task.progress / task.total) * 100}%` }"
            ></div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useMainStore } from '../stores/main'
import { discoveryApi, routerApi, dashboardApi } from '../services/api'
import { Pie, Bar, Doughnut } from 'vue-chartjs'
import {
  Chart as ChartJS,
  Title,
  Tooltip,
  Legend,
  ArcElement,
  CategoryScale,
  LinearScale,
  BarElement
} from 'chart.js'

// Register Chart.js components
ChartJS.register(Title, Tooltip, Legend, ArcElement, CategoryScale, LinearScale, BarElement)

const store = useMainStore()
const loading = ref(false)

// Discovery state
const discoveryLoading = ref(false)
const discoveredRouters = ref([])
const addingRouter = ref(null)

// Chart data
const versionChartData = ref({ labels: [], datasets: [] })
const modelChartData = ref({ labels: [], datasets: [] })
const healthChartData = ref({ labels: [], datasets: [] })

// Chart colors
const chartColors = [
  '#0d6efd', '#6610f2', '#6f42c1', '#d63384', '#dc3545',
  '#fd7e14', '#ffc107', '#198754', '#20c997', '#0dcaf0'
]

const healthColors = {
  'Healthy': '#198754',
  'Warning': '#ffc107',
  'Critical': '#dc3545',
  'Unknown': '#6c757d'
}

// Chart options
const pieOptions = {
  responsive: true,
  maintainAspectRatio: true,
  plugins: {
    legend: { position: 'bottom', labels: { boxWidth: 12 } }
  }
}

const barOptions = {
  responsive: true,
  maintainAspectRatio: true,
  indexAxis: 'y',
  plugins: {
    legend: { display: false }
  },
  scales: {
    x: { beginAtZero: true, ticks: { stepSize: 1 } }
  }
}

const doughnutOptions = {
  responsive: true,
  maintainAspectRatio: true,
  plugins: {
    legend: { position: 'bottom', labels: { boxWidth: 12 } }
  }
}

const discoveredCount = computed(() => discoveredRouters.value.length)

const recentRouters = computed(() => {
  return store.routers.slice(0, 5)
})

// Load chart data
const loadChartData = async () => {
  try {
    // Version distribution
    const versionData = await dashboardApi.getChart('version_pie')
    if (versionData.data && versionData.data.length > 0) {
      versionChartData.value = {
        labels: versionData.data.map(d => d.label),
        datasets: [{
          data: versionData.data.map(d => d.value),
          backgroundColor: chartColors.slice(0, versionData.data.length)
        }]
      }
    }

    // Model distribution
    const modelData = await dashboardApi.getChart('model_bar')
    if (modelData.data && modelData.data.length > 0) {
      modelChartData.value = {
        labels: modelData.data.map(d => d.label),
        datasets: [{
          label: 'Count',
          data: modelData.data.map(d => d.value),
          backgroundColor: '#0d6efd'
        }]
      }
    }

    // Health distribution
    const healthData = await dashboardApi.getChart('health_pie')
    if (healthData.data && healthData.data.length > 0) {
      healthChartData.value = {
        labels: healthData.data.map(d => d.label),
        datasets: [{
          data: healthData.data.map(d => d.value),
          backgroundColor: healthData.data.map(d => healthColors[d.label] || '#6c757d')
        }]
      }
    }
  } catch (error) {
    console.error('Failed to load chart data:', error)
  }
}

// Check if a discovered device is already configured
const isConfigured = (device) => {
  if (!device.ipv4_address) return false
  return store.routers.some(r => r.ip === device.ipv4_address)
}

// Run MNDP discovery
const runDiscovery = async () => {
  discoveryLoading.value = true
  try {
    const result = await discoveryApi.discover(5, true)
    discoveredRouters.value = result.discovered || []
    if (result.count > 0) {
      store.addNotification('info', `Discovered ${result.count} MikroTik device(s)`)
    }
  } catch (error) {
    console.error('Discovery failed:', error)
    store.addNotification('error', 'Discovery failed: ' + error.message)
  } finally {
    discoveryLoading.value = false
  }
}

// Add a discovered router to configured list
const addDiscoveredRouter = async (device) => {
  if (!device.ipv4_address) return

  addingRouter.value = device.mac_address
  try {
    await routerApi.create({
      ip: device.ipv4_address,
      username: 'admin',
      password: '',
      port: 8728
    })
    await store.fetchRouters()
    store.addNotification('success', `Added router ${device.identity || device.ipv4_address}`)
  } catch (error) {
    console.error('Failed to add router:', error)
    store.addNotification('error', 'Failed to add router: ' + error.message)
  } finally {
    addingRouter.value = null
  }
}

const importRouters = async () => {
  loading.value = true
  try {
    await store.importRoutersFromFile()
  } finally {
    loading.value = false
  }
}

const startQuickScan = async () => {
  loading.value = true
  try {
    await store.startQuickScan()
  } finally {
    loading.value = false
  }
}

const startFullScan = async () => {
  loading.value = true
  try {
    await store.startFullScan()
  } finally {
    loading.value = false
  }
}

// Run discovery on mount (use cached results first)
onMounted(async () => {
  // Load chart data
  loadChartData()

  // Load cached discovery results
  try {
    const cached = await discoveryApi.getCached()
    discoveredRouters.value = cached.discovered || []
  } catch (error) {
    // Ignore errors on cached fetch
  }
})
</script>
