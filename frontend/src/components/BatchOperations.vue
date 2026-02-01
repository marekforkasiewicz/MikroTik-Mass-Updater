<template>
  <div class="container-fluid py-4">
    <div class="d-flex justify-content-between align-items-center mb-4">
      <h2><i class="bi bi-collection-play me-2"></i>Batch Operations</h2>
    </div>

    <!-- Operation Tabs -->
    <ul class="nav nav-tabs mb-4">
      <li class="nav-item">
        <a class="nav-link" :class="{ active: activeTab === 'scan' }" href="#"
           @click.prevent="activeTab = 'scan'">
          <i class="bi bi-search me-1"></i> Network Scan
        </a>
      </li>
      <li class="nav-item">
        <a class="nav-link" :class="{ active: activeTab === 'update' }" href="#"
           @click.prevent="activeTab = 'update'">
          <i class="bi bi-cloud-download me-1"></i> Update Routers
        </a>
      </li>
      <li class="nav-item">
        <a class="nav-link" :class="{ active: activeTab === 'scripts' }" href="#"
           @click.prevent="activeTab = 'scripts'">
          <i class="bi bi-terminal me-1"></i> Execute Scripts
        </a>
      </li>
    </ul>

    <!-- SCAN TAB -->
    <div v-show="activeTab === 'scan'">
      <div class="row">
        <div class="col-md-4">
          <div class="card mb-4">
            <div class="card-header">
              <h5 class="mb-0">Scan Configuration</h5>
            </div>
            <div class="card-body">
              <div class="mb-3">
                <label class="form-label">Scan Type</label>
                <div class="d-grid gap-2">
                  <button class="btn btn-outline-success" :class="{ active: scanType === 'quick' }"
                          @click="scanType = 'quick'">
                    <i class="bi bi-lightning me-1"></i> Quick Scan
                    <small class="d-block text-muted">Ping + Port check only</small>
                  </button>
                  <button class="btn btn-outline-primary" :class="{ active: scanType === 'full' }"
                          @click="scanType = 'full'">
                    <i class="bi bi-search me-1"></i> Full Scan
                    <small class="d-block text-muted">Complete router info</small>
                  </button>
                </div>
              </div>
              <button class="btn btn-primary w-100" @click="startScan" :disabled="isOperating">
                <span v-if="scanRunning" class="spinner-border spinner-border-sm me-1"></span>
                <i v-else class="bi bi-play me-1"></i>
                Start Scan
              </button>
            </div>
          </div>
        </div>

        <div class="col-md-8">
          <!-- Progress -->
          <div class="card mb-4" v-if="scanRunning || scanProgress">
            <div class="card-header">
              <h5 class="mb-0">
                <i class="bi bi-gear spin me-2" v-if="scanRunning"></i>
                {{ scanRunning ? 'Scanning...' : 'Scan Complete' }}
              </h5>
            </div>
            <div class="card-body">
              <ProgressTracker
                :progress="scanProgress?.progress || 0"
                :total="scanProgress?.total || 0"
                :currentItem="scanProgress?.current_item"
                :isRunning="scanRunning"
              />
            </div>
          </div>

          <!-- Results -->
          <div class="card" v-if="scanResults">
            <div class="card-header d-flex justify-content-between align-items-center">
              <h5 class="mb-0">Scan Results</h5>
              <ResultsSummary
                :total="scanResults.total"
                :successful="scanResults.online || scanResults.successful || 0"
                :failed="scanResults.total - (scanResults.online || scanResults.successful || 0)"
              />
            </div>
            <div class="table-responsive">
              <table class="table table-hover mb-0">
                <thead>
                  <tr>
                    <th>IP Address</th>
                    <th>Ping</th>
                    <th>Latency</th>
                    <th>Identity</th>
                    <th>RouterOS</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="result in scanResults.results" :key="result.ip">
                    <td><code>{{ result.ip }}</code></td>
                    <td>
                      <i class="bi" :class="result.ping_ok || result.success ? 'bi-check-circle-fill text-success' : 'bi-x-circle-fill text-danger'"></i>
                    </td>
                    <td>{{ result.ping_ms ? result.ping_ms.toFixed(1) + ' ms' : '-' }}</td>
                    <td>{{ result.identity || '-' }}</td>
                    <td>{{ result.ros_version || '-' }}</td>
                    <td>
                      <span class="badge" :class="getScanStatusClass(result)">
                        {{ result.status || (result.success ? 'OK' : result.error || 'Error') }}
                      </span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <!-- Empty state -->
          <div class="card" v-else-if="!scanRunning">
            <div class="card-body text-center py-5">
              <i class="bi bi-wifi-off fs-1 text-muted mb-3 d-block"></i>
              <h5>No Scan Results</h5>
              <p class="text-muted">Configure and start a scan to check your network routers</p>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- UPDATE TAB -->
    <div v-show="activeTab === 'update'">
      <div class="row">
        <!-- Version Selection -->
        <div class="col-12 mb-4">
          <div class="card">
            <div class="card-header d-flex justify-content-between align-items-center">
              <h5 class="mb-0"><i class="bi bi-cloud-check me-2"></i>RouterOS Versions</h5>
              <button class="btn btn-sm btn-outline-secondary" @click="refreshVersions" :disabled="loadingVersions">
                <i class="bi bi-arrow-clockwise" :class="{ spin: loadingVersions }"></i> Refresh
              </button>
            </div>
            <div class="card-body p-0">
              <div class="table-responsive">
                <table class="table table-hover mb-0">
                  <thead>
                    <tr>
                      <th>Channel</th>
                      <th>Version</th>
                      <th>Release Date</th>
                      <th>Description</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="channel in channelOrder" :key="channel"
                        :class="{ 'table-active': updateConfig.channel === channel }"
                        @click="updateConfig.channel = channel" style="cursor: pointer;">
                      <td>
                        <span class="badge" :class="'bg-' + (versions[channel]?.color || 'secondary')">
                          {{ versions[channel]?.name || channel }}
                        </span>
                      </td>
                      <td><code class="fs-6">{{ versions[channel]?.version || 'N/A' }}</code></td>
                      <td><small>{{ versions[channel]?.release_date || '-' }}</small></td>
                      <td><small class="text-muted">{{ versions[channel]?.description || '-' }}</small></td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>

        <!-- Update Config -->
        <div class="col-md-5">
          <div class="card mb-4">
            <div class="card-header">
              <h5 class="mb-0">Update Configuration</h5>
            </div>
            <div class="card-body">
              <div class="mb-3">
                <label class="form-label">Target Routers</label>
                <div class="form-check">
                  <input class="form-check-input" type="radio" v-model="updateConfig.target" value="all" id="tAll">
                  <label class="form-check-label" for="tAll">All routers ({{ routerStats.total }})</label>
                </div>
                <div class="form-check">
                  <input class="form-check-input" type="radio" v-model="updateConfig.target" value="online" id="tOnline">
                  <label class="form-check-label" for="tOnline">Online only ({{ routerStats.online }})</label>
                </div>
                <div class="form-check">
                  <input class="form-check-input" type="radio" v-model="updateConfig.target" value="selected" id="tSelected"
                         :disabled="selectedRouterIds.length === 0">
                  <label class="form-check-label" for="tSelected">Selected ({{ selectedRouterIds.length }})</label>
                </div>
              </div>

              <div class="mb-3">
                <label class="form-label">Selected Channel</label>
                <div class="p-3 rounded border bg-light">
                  <span class="badge me-2" :class="'bg-' + (versions[updateConfig.channel]?.color || 'primary')">
                    {{ updateConfig.channel.toUpperCase() }}
                  </span>
                  <code class="fs-5">{{ versions[updateConfig.channel]?.version || 'N/A' }}</code>
                </div>
              </div>

              <div class="mb-3">
                <label class="form-label">Options</label>
                <div class="form-check">
                  <input class="form-check-input" type="checkbox" v-model="updateConfig.autoChangeTree" id="optTree">
                  <label class="form-check-label" for="optTree">Auto-change update tree</label>
                </div>
                <div class="form-check">
                  <input class="form-check-input" type="checkbox" v-model="updateConfig.upgradeFirmware" id="optFw">
                  <label class="form-check-label" for="optFw">Upgrade firmware</label>
                </div>
                <div class="form-check">
                  <input class="form-check-input" type="checkbox" v-model="updateConfig.cloudBackup" id="optBackup">
                  <label class="form-check-label" for="optBackup">Create cloud backup first</label>
                </div>
                <div class="form-check">
                  <input class="form-check-input" type="checkbox" v-model="updateConfig.dryRun" id="optDry">
                  <label class="form-check-label text-warning" for="optDry">Dry run (no changes)</label>
                </div>
              </div>

              <button class="btn w-100" :class="updateConfig.dryRun ? 'btn-warning' : 'btn-primary'"
                      @click="startUpdate" :disabled="isOperating || targetRouterCount === 0">
                <span v-if="updateRunning" class="spinner-border spinner-border-sm me-1"></span>
                <i v-else class="bi bi-cloud-download me-1"></i>
                {{ updateConfig.dryRun ? 'Start Dry Run' : 'Start Update' }} ({{ targetRouterCount }})
              </button>
            </div>
          </div>
        </div>

        <!-- Update Progress -->
        <div class="col-md-7">
          <div class="card">
            <div class="card-header d-flex justify-content-between align-items-center">
              <h5 class="mb-0">
                <i class="bi bi-gear spin me-2" v-if="updateRunning"></i>
                {{ updateRunning ? 'Update in Progress' : 'Update Status' }}
              </h5>
              <button v-if="updateRunning" class="btn btn-sm btn-danger" @click="cancelUpdate">
                <i class="bi bi-x-circle me-1"></i> Cancel
              </button>
            </div>
            <div class="card-body">
              <ProgressTracker v-if="updateProgress"
                :progress="updateProgress?.progress || 0"
                :total="updateProgress?.total || 0"
                :currentItem="updateProgress?.current_item"
                :isRunning="updateRunning"
                :hasErrors="updateResults?.failed > 0"
              />

              <ResultsSummary v-if="updateResults" class="my-4"
                :total="updateResults.total"
                :successful="updateResults.successful"
                :failed="updateResults.failed"
              />

              <ConsoleOutput
                :messages="consoleMessages"
                placeholder="Configure update options and click Start to begin."
              />
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- SCRIPTS TAB -->
    <div v-show="activeTab === 'scripts'">
      <div class="row">
        <div class="col-md-4">
          <div class="card mb-4">
            <div class="card-header d-flex justify-content-between align-items-center">
              <h5 class="mb-0">Scripts</h5>
              <input type="text" class="form-control form-control-sm w-50" v-model="scriptSearch" placeholder="Search...">
            </div>
            <div class="list-group list-group-flush" style="max-height: 400px; overflow-y: auto;">
              <a v-for="script in filteredScripts" :key="script.id" href="#"
                 class="list-group-item list-group-item-action"
                 :class="{ active: selectedScript?.id === script.id }"
                 @click.prevent="selectedScript = script">
                <div class="d-flex justify-content-between">
                  <strong>{{ script.name }}</strong>
                  <span :class="script.enabled ? 'text-success' : 'text-muted'">
                    <i :class="script.enabled ? 'bi bi-check-circle' : 'bi bi-circle'"></i>
                  </span>
                </div>
                <small class="text-muted">{{ script.category }}</small>
              </a>
              <div v-if="filteredScripts.length === 0" class="list-group-item text-muted text-center">
                No scripts found
              </div>
            </div>
          </div>
        </div>

        <div class="col-md-8">
          <div class="card" v-if="selectedScript">
            <div class="card-header">
              <h5 class="mb-0">Execute: {{ selectedScript.name }}</h5>
            </div>
            <div class="card-body">
              <div class="mb-3">
                <label class="form-label">Description</label>
                <p class="text-muted">{{ selectedScript.description || 'No description' }}</p>
              </div>

              <div class="mb-3">
                <label class="form-label">Select Target Routers</label>
                <select class="form-select" v-model="scriptConfig.routerIds" multiple size="5">
                  <option v-for="router in routers" :key="router.id" :value="router.id">
                    {{ router.identity || router.ip }} ({{ router.ip }})
                  </option>
                </select>
                <small class="text-muted">Selected: {{ scriptConfig.routerIds.length }} routers</small>
              </div>

              <div class="form-check mb-3">
                <input type="checkbox" class="form-check-input" v-model="scriptConfig.dryRun" id="scriptDry">
                <label class="form-check-label" for="scriptDry">Dry run</label>
              </div>

              <button class="btn btn-success w-100" @click="executeScript"
                      :disabled="isOperating || scriptConfig.routerIds.length === 0">
                <span v-if="scriptRunning" class="spinner-border spinner-border-sm me-1"></span>
                <i v-else class="bi bi-play me-1"></i>
                Execute on {{ scriptConfig.routerIds.length }} router(s)
              </button>

              <!-- Script Results -->
              <div v-if="scriptResults.length" class="mt-4">
                <h6>Execution Results</h6>
                <div class="table-responsive">
                  <table class="table table-sm">
                    <thead>
                      <tr>
                        <th>Router</th>
                        <th>Status</th>
                        <th>Duration</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="result in scriptResults" :key="result.router_id">
                        <td>{{ getRouterName(result.router_id) }}</td>
                        <td>
                          <span :class="result.status === 'success' ? 'badge bg-success' : 'badge bg-danger'">
                            {{ result.status }}
                          </span>
                        </td>
                        <td>{{ result.duration_ms ? (result.duration_ms / 1000).toFixed(1) + 's' : '-' }}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </div>

          <div class="card" v-else>
            <div class="card-body text-center py-5 text-muted">
              <i class="bi bi-terminal fs-1"></i>
              <p class="mt-2">Select a script from the list to execute</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useMainStore } from '../stores/main'
import { createTaskWebSocket, versionsApi, scriptsApi, routerApi } from '../services/api'
import ProgressTracker from './shared/ProgressTracker.vue'
import ResultsSummary from './shared/ResultsSummary.vue'
import ConsoleOutput from './shared/ConsoleOutput.vue'

const store = useMainStore()

// Common state
const activeTab = ref('scan')
let ws = null

// Scan state
const scanType = ref('quick')
const scanRunning = ref(false)
const scanProgress = ref(null)
const scanResults = ref(null)

// Update state
const channelOrder = ['stable', 'long-term', 'testing', 'development']
const versions = ref({})
const loadingVersions = ref(false)
const updateRunning = ref(false)
const updateProgress = ref(null)
const updateResults = ref(null)
const consoleMessages = ref([])
const updateConfig = ref({
  target: 'all',
  channel: 'stable',
  autoChangeTree: true,
  upgradeFirmware: true,
  cloudBackup: false,
  dryRun: false
})

// Script state
const scripts = ref([])
const routers = ref([])
const selectedScript = ref(null)
const scriptSearch = ref('')
const scriptRunning = ref(false)
const scriptResults = ref([])
const scriptConfig = ref({
  routerIds: [],
  dryRun: false
})

// Computed
const routerStats = computed(() => store.routerStats)
const selectedRouterIds = computed(() => store.selectedRouterIds)
const isOperating = computed(() => scanRunning.value || updateRunning.value || scriptRunning.value)

const targetRouterCount = computed(() => {
  if (updateConfig.value.target === 'all') return routerStats.value.total
  if (updateConfig.value.target === 'online') return routerStats.value.online
  return selectedRouterIds.value.length
})

const filteredScripts = computed(() => {
  if (!scriptSearch.value) return scripts.value
  const q = scriptSearch.value.toLowerCase()
  return scripts.value.filter(s => s.name.toLowerCase().includes(q) || s.category?.toLowerCase().includes(q))
})

// Lifecycle
onMounted(async () => {
  await Promise.all([
    fetchVersions(),
    loadScripts(),
    loadRouters()
  ])
})

onUnmounted(() => {
  if (ws) ws.close()
})

// Scan methods
async function startScan() {
  scanRunning.value = true
  scanProgress.value = null
  scanResults.value = null

  try {
    const task = scanType.value === 'quick' ? await store.startQuickScan() : await store.startFullScan()
    connectWebSocket(task.id, 'scan')
  } catch (error) {
    scanRunning.value = false
    store.addNotification('error', 'Failed to start scan')
  }
}

function getScanStatusClass(result) {
  if (result.success || (result.ping_ok && result.port_api_open)) return 'bg-success'
  if (result.ping_ok) return 'bg-warning text-dark'
  return 'bg-danger'
}

// Update methods
async function fetchVersions() {
  loadingVersions.value = true
  try {
    const data = await versionsApi.get()
    versions.value = data.versions || {}
  } catch (error) {
    store.addNotification('error', 'Failed to fetch versions')
  } finally {
    loadingVersions.value = false
  }
}

async function refreshVersions() {
  loadingVersions.value = true
  try {
    const data = await versionsApi.refresh()
    versions.value = data.versions || {}
  } finally {
    loadingVersions.value = false
  }
}

function getRouterIds() {
  if (updateConfig.value.target === 'selected') return selectedRouterIds.value
  if (updateConfig.value.target === 'online') return store.onlineRouters.map(r => r.id)
  return store.routers.map(r => r.id)
}

function addConsoleMessage(text, type = 'normal') {
  consoleMessages.value.push({
    text: `[${new Date().toLocaleTimeString()}] ${text}`,
    type
  })
}

async function startUpdate() {
  updateRunning.value = true
  updateProgress.value = null
  updateResults.value = null
  consoleMessages.value = []

  const config = {
    router_ids: getRouterIds(),
    update_tree: updateConfig.value.channel,
    auto_change_tree: updateConfig.value.autoChangeTree,
    upgrade_firmware: updateConfig.value.upgradeFirmware,
    cloud_backup: updateConfig.value.cloudBackup,
    dry_run: updateConfig.value.dryRun,
    threads: targetRouterCount.value
  }

  addConsoleMessage(`Starting ${updateConfig.value.dryRun ? 'dry run' : 'update'} for ${config.router_ids.length} routers...`)
  addConsoleMessage(`Channel: ${updateConfig.value.channel.toUpperCase()} | Threads: ${targetRouterCount.value}`)

  try {
    const task = await store.startUpdate(config)
    connectWebSocket(task.id, 'update')
  } catch (error) {
    updateRunning.value = false
    addConsoleMessage(`Error: ${error.message}`, 'error')
  }
}

async function cancelUpdate() {
  if (ws) ws.close()
  updateRunning.value = false
  addConsoleMessage('Update cancelled', 'warning')
}

// Script methods
async function loadScripts() {
  try {
    const response = await scriptsApi.list()
    scripts.value = response.items || []
  } catch (error) {
    console.error('Failed to load scripts:', error)
  }
}

async function loadRouters() {
  try {
    const response = await routerApi.list()
    routers.value = response.routers || response.items || []
  } catch (error) {
    console.error('Failed to load routers:', error)
  }
}

function getRouterName(routerId) {
  const router = routers.value.find(r => r.id === routerId)
  return router ? (router.identity || router.ip) : `Router #${routerId}`
}

async function executeScript() {
  if (!selectedScript.value) return
  scriptRunning.value = true
  scriptResults.value = []

  try {
    for (const routerId of scriptConfig.value.routerIds) {
      try {
        const result = await scriptsApi.execute(selectedScript.value.id, {
          router_ids: [routerId],
          dry_run: scriptConfig.value.dryRun
        })
        scriptResults.value.push(result)
      } catch (error) {
        scriptResults.value.push({
          router_id: routerId,
          status: 'failed',
          error_message: error.message
        })
      }
    }
  } finally {
    scriptRunning.value = false
  }
}

// WebSocket
function connectWebSocket(taskId, type) {
  if (ws) ws.close()

  ws = createTaskWebSocket(
    taskId,
    (data) => {
      if (type === 'scan') {
        scanProgress.value = data
        if (data.complete || data.status === 'completed' || data.status === 'failed') {
          scanRunning.value = false
          if (data.results) scanResults.value = data.results
          store.fetchRouters()
        }
      } else if (type === 'update') {
        updateProgress.value = data
        if (data.current_item) addConsoleMessage(`Processing: ${data.current_item}`)

        if (data.complete || data.status === 'completed' || data.status === 'failed') {
          updateRunning.value = false
          if (data.results) {
            updateResults.value = data.results
            data.results.results?.forEach(r => {
              addConsoleMessage(`${r.ip}: ${r.success ? 'Success' : 'Failed - ' + r.error}`, r.success ? 'success' : 'error')
            })
            addConsoleMessage(`Completed: ${data.results.successful} successful, ${data.results.failed} failed`)
          }
          store.fetchRouters()
        }
      }
    },
    () => {
      if (type === 'scan') scanRunning.value = false
      else updateRunning.value = false
      store.addNotification('error', 'Connection lost')
    }
  )
}
</script>

<style scoped>
.nav-tabs .nav-link {
  color: var(--text-secondary);
}
.nav-tabs .nav-link.active {
  font-weight: 600;
}
.table tbody tr.table-active {
  background-color: rgba(59, 130, 246, 0.15) !important;
}
</style>
