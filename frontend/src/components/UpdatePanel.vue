<template>
  <div>
    <h2 class="mb-4">Update Routers</h2>

    <!-- RouterOS Versions Card -->
    <div class="card mb-4">
      <div class="card-header d-flex justify-content-between align-items-center">
        <h5 class="mb-0">
          <i class="bi bi-cloud-check me-2"></i>
          Current RouterOS Versions
        </h5>
        <button
          class="btn btn-sm btn-outline-secondary"
          @click="refreshVersions"
          :disabled="loadingVersions"
        >
          <i class="bi bi-arrow-clockwise" :class="{ 'spin': loadingVersions }"></i>
          Refresh
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
              <tr v-if="loadingVersions">
                <td colspan="4" class="text-center py-3">
                  <i class="bi bi-arrow-clockwise spin me-2"></i>
                  Loading versions from MikroTik...
                </td>
              </tr>
              <tr v-else-if="versionsError">
                <td colspan="4" class="text-center py-3 text-danger">
                  <i class="bi bi-exclamation-triangle me-2"></i>
                  {{ versionsError }}
                </td>
              </tr>
              <template v-else>
                <tr
                  v-for="channel in channelOrder"
                  :key="channel"
                  :class="{ 'table-active': updateTree === channel }"
                  @click="updateTree = channel"
                  style="cursor: pointer;"
                >
                  <td>
                    <span class="badge" :class="'bg-' + (versions[channel]?.color || 'secondary')">
                      {{ versions[channel]?.name || channel }}
                    </span>
                  </td>
                  <td>
                    <code class="fs-6">{{ versions[channel]?.version || 'N/A' }}</code>
                  </td>
                  <td>
                    <small>{{ versions[channel]?.release_date || '-' }}</small>
                  </td>
                  <td>
                    <small class="text-muted">{{ versions[channel]?.description || '-' }}</small>
                  </td>
                </tr>
              </template>
            </tbody>
          </table>
        </div>
        <div class="px-3 py-2 border-top small text-muted" v-if="versionsFetchedAt">
          <i class="bi bi-clock me-1"></i>
          Last updated: {{ formatFetchedAt(versionsFetchedAt) }}
        </div>
      </div>
    </div>

    <div class="row">
      <!-- Configuration panel -->
      <div class="col-md-5">
        <div class="card mb-4">
          <div class="card-header">
            <h5 class="mb-0">Update Configuration</h5>
          </div>
          <div class="card-body">
            <form @submit.prevent="startUpdate">
              <!-- Router selection -->
              <div class="mb-3">
                <label class="form-label">Target Routers</label>
                <div class="form-check">
                  <input
                    class="form-check-input"
                    type="radio"
                    id="allRouters"
                    value="all"
                    v-model="targetSelection"
                  />
                  <label class="form-check-label" for="allRouters">
                    All routers ({{ store.routerStats.total }})
                  </label>
                </div>
                <div class="form-check">
                  <input
                    class="form-check-input"
                    type="radio"
                    id="onlineRouters"
                    value="online"
                    v-model="targetSelection"
                  />
                  <label class="form-check-label" for="onlineRouters">
                    Online routers only ({{ store.routerStats.online }})
                  </label>
                </div>
                <div class="form-check">
                  <input
                    class="form-check-input"
                    type="radio"
                    id="selectedRouters"
                    value="selected"
                    v-model="targetSelection"
                    :disabled="store.selectedRouterIds.length === 0"
                  />
                  <label class="form-check-label" for="selectedRouters">
                    Selected routers ({{ store.selectedRouterIds.length }})
                  </label>
                </div>
              </div>

              <!-- Selected channel display -->
              <div class="mb-3">
                <label class="form-label">Selected Channel</label>
                <div class="selected-channel p-3 rounded border">
                  <div class="d-flex justify-content-between align-items-center">
                    <div>
                      <span class="badge me-2" :class="'bg-' + (versions[updateTree]?.color || 'primary')">
                        {{ versions[updateTree]?.name || updateTree.toUpperCase() }}
                      </span>
                      <code class="fs-5">{{ versions[updateTree]?.version || 'N/A' }}</code>
                    </div>
                    <small class="text-muted">{{ versions[updateTree]?.release_date || '' }}</small>
                  </div>
                  <small class="text-muted d-block mt-1">
                    {{ versions[updateTree]?.description || 'Click on a channel above to select' }}
                  </small>
                </div>
              </div>

              <!-- Performance settings -->
              <div class="mb-3">
                <label class="form-label">Performance</label>
                <div class="row g-2 align-items-center">
                  <div class="col-6">
                    <div class="d-flex align-items-center justify-content-between p-2 rounded border">
                      <span class="small text-muted">Threads:</span>
                      <span class="fw-bold text-primary">{{ targetRouterCount }}</span>
                    </div>
                    <small class="text-muted">1 thread per router</small>
                  </div>
                  <div class="col-6">
                    <label class="form-label small text-muted mb-1">Timeout (s)</label>
                    <div class="input-group input-group-sm">
                      <button
                        type="button"
                        class="btn btn-outline-secondary"
                        @click="timeout = Math.max(1, timeout - 1)"
                        :disabled="timeout <= 1"
                      >-</button>
                      <input
                        type="number"
                        class="form-control text-center"
                        v-model.number="timeout"
                        min="1"
                        max="60"
                      />
                      <button
                        type="button"
                        class="btn btn-outline-secondary"
                        @click="timeout = Math.min(60, timeout + 1)"
                        :disabled="timeout >= 60"
                      >+</button>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Options -->
              <div class="mb-3">
                <label class="form-label">Options</label>
                <div class="form-check">
                  <input
                    class="form-check-input"
                    type="checkbox"
                    id="autoChangeTree"
                    v-model="autoChangeTree"
                  />
                  <label class="form-check-label" for="autoChangeTree">
                    Auto-change update tree via SSH
                  </label>
                </div>
                <div class="form-check">
                  <input
                    class="form-check-input"
                    type="checkbox"
                    id="upgradeFirmware"
                    v-model="upgradeFirmware"
                  />
                  <label class="form-check-label" for="upgradeFirmware">
                    Upgrade firmware
                  </label>
                </div>
                <div class="form-check">
                  <input
                    class="form-check-input"
                    type="checkbox"
                    id="cloudBackup"
                    v-model="cloudBackup"
                  />
                  <label class="form-check-label" for="cloudBackup">
                    Create cloud backup first
                  </label>
                </div>
                <div class="form-check">
                  <input
                    class="form-check-input"
                    type="checkbox"
                    id="generateReport"
                    v-model="generateReport"
                  />
                  <label class="form-check-label" for="generateReport">
                    Generate report
                  </label>
                </div>
                <div class="form-check">
                  <input
                    class="form-check-input"
                    type="checkbox"
                    id="dryRun"
                    v-model="dryRun"
                  />
                  <label class="form-check-label" for="dryRun">
                    <span class="text-warning">Dry run</span> (no actual changes)
                  </label>
                </div>
              </div>

              <!-- Cloud backup password -->
              <div class="mb-3" v-if="cloudBackup">
                <label class="form-label">Cloud Backup Password</label>
                <input
                  type="password"
                  class="form-control"
                  v-model="cloudPassword"
                  placeholder="Enter backup password"
                />
              </div>

              <!-- Submit button -->
              <button
                type="submit"
                class="btn w-100"
                :class="dryRun ? 'btn-warning' : 'btn-primary'"
                :disabled="updating || targetRouterCount === 0"
              >
                <i class="bi bi-cloud-download me-2"></i>
                {{ dryRun ? 'Start Dry Run' : 'Start Update' }}
                ({{ targetRouterCount }} routers)
              </button>
            </form>
          </div>
        </div>
      </div>

      <!-- Progress panel -->
      <div class="col-md-7">
        <div class="card">
          <div class="card-header d-flex justify-content-between align-items-center">
            <h5 class="mb-0">
              <i class="bi bi-gear spin me-2" v-if="updating"></i>
              {{ updating ? 'Update in Progress' : 'Update Status' }}
            </h5>
            <div class="d-flex align-items-center gap-2">
              <span v-if="updating" class="badge bg-info">
                {{ targetRouterCount }} threads
              </span>
              <button
                v-if="updating"
                class="btn btn-sm btn-danger"
                @click="cancelUpdate"
              >
                <i class="bi bi-x-circle me-1"></i>
                Cancel
              </button>
            </div>
          </div>
          <div class="card-body">
            <!-- Progress bar -->
            <div v-if="taskProgress" class="mb-4">
              <div class="d-flex justify-content-between mb-2">
                <span>{{ taskProgress.current_item || 'Processing...' }}</span>
                <span>{{ taskProgress.progress }}/{{ taskProgress.total }}</span>
              </div>
              <div class="progress task-progress">
                <div
                  class="progress-bar"
                  :class="{
                    'progress-bar-striped progress-bar-animated': updating,
                    'bg-success': !updating && updateResults?.failed === 0,
                    'bg-warning': !updating && updateResults?.failed > 0
                  }"
                  :style="{ width: `${progressPercent}%` }"
                ></div>
              </div>
              <div class="text-center mt-1 small text-muted">
                {{ progressPercent }}%
              </div>
            </div>

            <!-- Results summary -->
            <div v-if="updateResults" class="mb-4">
              <div class="row text-center">
                <div class="col">
                  <div class="fs-3 text-primary">{{ updateResults.total }}</div>
                  <small class="text-muted">Total</small>
                </div>
                <div class="col">
                  <div class="fs-3 text-success">{{ updateResults.successful }}</div>
                  <small class="text-muted">Successful</small>
                </div>
                <div class="col">
                  <div class="fs-3 text-danger">{{ updateResults.failed }}</div>
                  <small class="text-muted">Failed</small>
                </div>
              </div>
            </div>

            <!-- Console output -->
            <div class="console-output" ref="consoleOutput">
              <div v-for="(msg, index) in consoleMessages" :key="index" :class="msg.class">
                {{ msg.text }}
              </div>
              <div v-if="!consoleMessages.length" class="text-muted">
                Configure update options and click "Start Update" to begin.
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useMainStore } from '../stores/main'
import { createTaskWebSocket, versionsApi } from '../services/api'

const store = useMainStore()

// Channel order for display
const channelOrder = ['stable', 'long-term', 'testing', 'development']

// Versions state
const versions = ref({})
const versionsFetchedAt = ref(null)
const loadingVersions = ref(false)
const versionsError = ref(null)

// Form state
const targetSelection = ref('all')
const updateTree = ref('stable')
const autoChangeTree = ref(true)
const upgradeFirmware = ref(true)
const cloudBackup = ref(false)
const cloudPassword = ref('')
const generateReport = ref(true)
const dryRun = ref(false)
const timeout = ref(5)

// Progress state
const updating = ref(false)
const taskProgress = ref(null)
const updateResults = ref(null)
const consoleMessages = ref([])
const consoleOutput = ref(null)

let ws = null
let currentTaskId = null

const targetRouterCount = computed(() => {
  if (targetSelection.value === 'all') return store.routerStats.total
  if (targetSelection.value === 'online') return store.routerStats.online
  if (targetSelection.value === 'selected') return store.selectedRouterIds.length
  return 0
})

const progressPercent = computed(() => {
  if (!taskProgress.value || !taskProgress.value.total) return 0
  return Math.round((taskProgress.value.progress / taskProgress.value.total) * 100)
})

const fetchVersions = async () => {
  loadingVersions.value = true
  versionsError.value = null
  try {
    const data = await versionsApi.get()
    versions.value = data.versions || {}
    versionsFetchedAt.value = data.fetched_at
  } catch (error) {
    versionsError.value = error.message || 'Failed to fetch versions'
  } finally {
    loadingVersions.value = false
  }
}

const refreshVersions = async () => {
  loadingVersions.value = true
  versionsError.value = null
  try {
    const data = await versionsApi.refresh()
    versions.value = data.versions || {}
    versionsFetchedAt.value = data.fetched_at
  } catch (error) {
    versionsError.value = error.message || 'Failed to refresh versions'
  } finally {
    loadingVersions.value = false
  }
}

const formatFetchedAt = (isoString) => {
  if (!isoString) return ''
  const date = new Date(isoString)
  return date.toLocaleString()
}

const getRouterIds = () => {
  if (targetSelection.value === 'selected') {
    return store.selectedRouterIds
  }
  if (targetSelection.value === 'online') {
    return store.onlineRouters.map(r => r.id)
  }
  return store.routers.map(r => r.id)
}

const addConsoleMessage = (text, type = 'normal') => {
  const classMap = {
    success: 'line-success',
    error: 'line-error',
    warning: 'line-warning',
    normal: ''
  }
  consoleMessages.value.push({
    text: `[${new Date().toLocaleTimeString()}] ${text}`,
    class: classMap[type] || ''
  })

  // Auto-scroll
  nextTick(() => {
    if (consoleOutput.value) {
      consoleOutput.value.scrollTop = consoleOutput.value.scrollHeight
    }
  })
}

const startUpdate = async () => {
  updating.value = true
  taskProgress.value = null
  updateResults.value = null
  consoleMessages.value = []

  const selectedVersion = versions.value[updateTree.value]?.version || 'N/A'

  const config = {
    router_ids: getRouterIds(),
    update_tree: updateTree.value,
    auto_change_tree: autoChangeTree.value,
    upgrade_firmware: upgradeFirmware.value,
    cloud_backup: cloudBackup.value,
    cloud_password: cloudBackup.value ? cloudPassword.value : null,
    generate_report: generateReport.value,
    dry_run: dryRun.value,
    threads: targetRouterCount.value,
    timeout: timeout.value
  }

  addConsoleMessage(`Starting ${dryRun.value ? 'dry run' : 'update'} for ${config.router_ids.length} routers...`, 'normal')
  addConsoleMessage(`Channel: ${updateTree.value.toUpperCase()} (v${selectedVersion}) | Threads: ${targetRouterCount.value} | Timeout: ${timeout.value}s`, 'normal')

  if (autoChangeTree.value) {
    addConsoleMessage('Auto-change tree via SSH: enabled', 'normal')
  }
  if (upgradeFirmware.value) {
    addConsoleMessage('Firmware upgrade: enabled', 'normal')
  }

  try {
    const task = await store.startUpdate(config)
    currentTaskId = task.id
    connectWebSocket(task.id)
  } catch (error) {
    updating.value = false
    addConsoleMessage(`Error: ${error.message}`, 'error')
  }
}

const connectWebSocket = (taskId) => {
  if (ws) {
    ws.close()
  }

  ws = createTaskWebSocket(
    taskId,
    (data) => {
      taskProgress.value = data

      if (data.current_item) {
        addConsoleMessage(`Processing: ${data.current_item}`, 'normal')
      }

      if (data.complete || data.status === 'completed' || data.status === 'failed') {
        updating.value = false
        if (data.results) {
          updateResults.value = data.results

          // Log individual results
          if (data.results.results) {
            data.results.results.forEach(result => {
              if (result.success) {
                addConsoleMessage(`${result.ip}: Success`, 'success')
              } else {
                addConsoleMessage(`${result.ip}: Failed - ${result.error}`, 'error')
              }
            })
          }

          addConsoleMessage(`Completed: ${data.results.successful} successful, ${data.results.failed} failed`, 'normal')
        }

        if (data.error) {
          addConsoleMessage(`Task error: ${data.error}`, 'error')
        }

        // Refresh router list
        store.fetchRouters()
      }
    },
    (error) => {
      updating.value = false
      addConsoleMessage('WebSocket connection failed', 'error')
    }
  )
}

const cancelUpdate = async () => {
  if (currentTaskId) {
    await store.cancelTask(currentTaskId)
    updating.value = false
    addConsoleMessage('Update cancelled', 'warning')
  }
}

onMounted(() => {
  fetchVersions()
})

onUnmounted(() => {
  if (ws) {
    ws.close()
  }
})
</script>

<style scoped>
.selected-channel {
  background-color: var(--bg-surface-hover);
  transition: all 0.2s;
}

.table tbody tr {
  transition: background-color 0.15s;
}

.table tbody tr:hover {
  background-color: var(--table-hover-bg);
}

.table tbody tr.table-active {
  background-color: rgba(59, 130, 246, 0.15) !important;
}

.input-group-sm .form-control {
  max-width: 60px;
}

.input-group-sm .btn {
  padding: 0.25rem 0.5rem;
}
</style>
