<template>
  <div>
    <div class="d-flex justify-content-between align-items-center mb-4">
      <h2><i class="bi bi-file-text me-2"></i>Operation Logs</h2>
      <div class="btn-group">
        <button class="btn btn-outline-secondary" @click="fetchLogs" :disabled="loading">
          <i class="bi bi-arrow-clockwise" :class="{ 'spin': loading }"></i>
          Refresh
        </button>
        <button class="btn btn-outline-danger" @click="showCleanupModal = true">
          <i class="bi bi-trash"></i>
          Cleanup
        </button>
      </div>
    </div>

    <!-- Statistics Cards -->
    <div class="row mb-4" v-if="statistics">
      <div class="col-md-3">
        <div class="card bg-primary text-white">
          <div class="card-body">
            <h5 class="card-title">Log Files</h5>
            <h2>{{ statistics.total_log_files }}</h2>
          </div>
        </div>
      </div>
      <div class="col-md-3">
        <div class="card bg-info text-white">
          <div class="card-body">
            <h5 class="card-title">Routers Processed</h5>
            <h2>{{ statistics.total_routers_processed }}</h2>
          </div>
        </div>
      </div>
      <div class="col-md-3">
        <div class="card bg-success text-white">
          <div class="card-body">
            <h5 class="card-title">Successful</h5>
            <h2>{{ statistics.total_successful }}</h2>
          </div>
        </div>
      </div>
      <div class="col-md-3">
        <div class="card bg-danger text-white">
          <div class="card-body">
            <h5 class="card-title">Failed</h5>
            <h2>{{ statistics.total_failed }}</h2>
          </div>
        </div>
      </div>
    </div>

    <!-- Log Files List -->
    <div class="card">
      <div class="card-header d-flex justify-content-between align-items-center">
        <span>Log Files</span>
        <small class="text-muted">Total size: {{ statistics?.total_size_human }}</small>
      </div>
      <div class="table-responsive">
        <table class="table table-hover mb-0">
          <thead>
            <tr>
              <th>Filename</th>
              <th>Date</th>
              <th>Size</th>
              <th>Summary</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="file in logFiles" :key="file.filename">
              <td>
                <i class="bi bi-file-text me-2 text-muted"></i>
                <code>{{ file.filename }}</code>
              </td>
              <td>
                <small>{{ formatDate(file.modified) }}</small>
              </td>
              <td>
                <small>{{ file.size_human }}</small>
              </td>
              <td>
                <span v-if="file.summary && file.summary.total > 0">
                  <span class="badge bg-success me-1">{{ file.summary.successful }}</span>
                  <span class="badge bg-danger" v-if="file.summary.failed > 0">{{ file.summary.failed }}</span>
                </span>
                <span v-else class="text-muted">-</span>
              </td>
              <td>
                <div class="btn-group btn-group-sm">
                  <button class="btn btn-outline-primary" @click="viewLog(file)" title="View">
                    <i class="bi bi-eye"></i>
                  </button>
                  <button class="btn btn-outline-secondary" @click="downloadLog(file)" title="Download">
                    <i class="bi bi-download"></i>
                  </button>
                  <button class="btn btn-outline-danger" @click="deleteLog(file)" title="Delete">
                    <i class="bi bi-trash"></i>
                  </button>
                </div>
              </td>
            </tr>
            <tr v-if="logFiles.length === 0">
              <td colspan="5" class="text-center py-4 text-muted">
                <i class="bi bi-inbox fs-1 d-block mb-2"></i>
                No log files found
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Log Viewer Modal -->
    <div class="modal fade" :class="{ show: showViewer }" tabindex="-1"
         :style="{ display: showViewer ? 'block' : 'none' }">
      <div class="modal-dialog modal-xl">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">
              <i class="bi bi-file-text me-2"></i>
              {{ selectedFile?.filename }}
            </h5>
            <div class="ms-auto me-3">
              <div class="btn-group btn-group-sm">
                <button class="btn" :class="viewMode === 'parsed' ? 'btn-primary' : 'btn-outline-primary'"
                        @click="viewMode = 'parsed'">
                  Parsed
                </button>
                <button class="btn" :class="viewMode === 'raw' ? 'btn-primary' : 'btn-outline-primary'"
                        @click="viewMode = 'raw'">
                  Raw
                </button>
              </div>
            </div>
            <button type="button" class="btn-close" @click="showViewer = false"></button>
          </div>
          <div class="modal-body">
            <!-- Parsed View -->
            <div v-if="viewMode === 'parsed' && parsedLog">
              <!-- Summary -->
              <div class="alert" :class="parsedLog.summary?.failed > 0 ? 'alert-warning' : 'alert-success'">
                <div class="row text-center">
                  <div class="col">
                    <strong>Total:</strong> {{ parsedLog.summary?.total }}
                  </div>
                  <div class="col">
                    <strong>Success:</strong> {{ parsedLog.summary?.successful }}
                  </div>
                  <div class="col">
                    <strong>Failed:</strong> {{ parsedLog.summary?.failed }}
                  </div>
                </div>
              </div>

              <!-- Config -->
              <div class="card mb-3" v-if="Object.keys(parsedLog.config || {}).length > 0">
                <div class="card-header">
                  <i class="bi bi-gear me-2"></i>Configuration
                </div>
                <div class="card-body">
                  <div class="row">
                    <div class="col-md-4" v-for="(value, key) in parsedLog.config" :key="key">
                      <small class="text-muted">{{ key }}:</small>
                      <strong class="ms-1">{{ value }}</strong>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Router Results -->
              <div class="card">
                <div class="card-header">
                  <i class="bi bi-router me-2"></i>Router Results
                </div>
                <div class="list-group list-group-flush" style="max-height: 400px; overflow-y: auto;">
                  <div class="list-group-item" v-for="router in parsedLog.routers" :key="router.ip"
                       :class="{ 'list-group-item-danger': !router.success }">
                    <div class="d-flex justify-content-between align-items-start">
                      <div>
                        <strong>{{ router.ip }}</strong>
                        <span class="text-muted ms-2" v-if="router.identity">{{ router.identity }}</span>
                        <span class="badge bg-secondary ms-2" v-if="router.model">{{ router.model }}</span>
                      </div>
                      <span class="badge" :class="router.success ? 'bg-success' : 'bg-danger'">
                        {{ router.success ? 'SUCCESS' : 'FAILED' }}
                      </span>
                    </div>
                    <div class="mt-2" v-if="router.ros_version || router.installed_version">
                      <small class="text-muted">
                        <span v-if="router.ros_version">ROS: {{ router.ros_version }}</span>
                        <span v-if="router.installed_version" class="ms-2">Ver: {{ router.installed_version }}</span>
                        <span v-if="router.latest_version" class="ms-2">Latest: {{ router.latest_version }}</span>
                      </small>
                    </div>
                    <div class="mt-1 text-danger" v-if="router.error">
                      <small><i class="bi bi-exclamation-circle me-1"></i>{{ router.error }}</small>
                    </div>
                    <div class="mt-2" v-if="router.messages?.length > 0">
                      <button class="btn btn-sm btn-outline-secondary"
                              @click="toggleMessages(router.ip)">
                        <i class="bi" :class="expandedRouters.includes(router.ip) ? 'bi-chevron-up' : 'bi-chevron-down'"></i>
                        Messages ({{ router.messages.length }})
                      </button>
                      <div v-if="expandedRouters.includes(router.ip)" class="mt-2">
                        <pre class="bg-dark text-light p-2 rounded small" style="max-height: 150px; overflow-y: auto;">{{ router.messages.join('\n') }}</pre>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Failed Hosts -->
              <div class="card mt-3" v-if="parsedLog.summary?.failed_hosts?.length > 0">
                <div class="card-header bg-danger text-white">
                  <i class="bi bi-exclamation-triangle me-2"></i>Failed Hosts
                </div>
                <ul class="list-group list-group-flush">
                  <li class="list-group-item" v-for="host in parsedLog.summary.failed_hosts" :key="host">
                    {{ host }}
                  </li>
                </ul>
              </div>
            </div>

            <!-- Raw View -->
            <div v-if="viewMode === 'raw'">
              <pre class="bg-dark text-light p-3 rounded"
                   style="max-height: 500px; overflow: auto; font-size: 12px;">{{ rawLog }}</pre>
            </div>
          </div>
          <div class="modal-footer">
            <button class="btn btn-secondary" @click="downloadLog(selectedFile)">
              <i class="bi bi-download me-1"></i>Download
            </button>
            <button class="btn btn-primary" @click="showViewer = false">Close</button>
          </div>
        </div>
      </div>
    </div>
    <div class="modal-backdrop fade" :class="{ show: showViewer }" v-if="showViewer"></div>

    <!-- Cleanup Modal -->
    <div class="modal fade" :class="{ show: showCleanupModal }" tabindex="-1"
         :style="{ display: showCleanupModal ? 'block' : 'none' }">
      <div class="modal-dialog">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">Cleanup Old Logs</h5>
            <button type="button" class="btn-close" @click="showCleanupModal = false"></button>
          </div>
          <div class="modal-body">
            <p>Delete log files older than:</p>
            <div class="input-group">
              <input type="number" class="form-control" v-model="cleanupDays" min="1">
              <span class="input-group-text">days</span>
            </div>
          </div>
          <div class="modal-footer">
            <button class="btn btn-secondary" @click="showCleanupModal = false">Cancel</button>
            <button class="btn btn-danger" @click="cleanupLogs">
              <i class="bi bi-trash me-1"></i>Delete Old Logs
            </button>
          </div>
        </div>
      </div>
    </div>
    <div class="modal-backdrop fade" :class="{ show: showCleanupModal }" v-if="showCleanupModal"></div>

    <!-- Confirm Delete Modal -->
    <ConfirmModal
      :visible="showDeleteModal"
      title="Delete Log File"
      :message="deleteModalMessage"
      variant="danger"
      confirmText="Delete"
      :loading="deleting"
      @confirm="handleDeleteConfirm"
      @cancel="showDeleteModal = false"
    />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useMainStore } from '../stores/main'
import api from '../services/api'
import ConfirmModal from './ConfirmModal.vue'

const store = useMainStore()

const loading = ref(false)
const logFiles = ref([])
const statistics = ref(null)
const showViewer = ref(false)
const showCleanupModal = ref(false)
const selectedFile = ref(null)
const parsedLog = ref(null)
const rawLog = ref('')
const viewMode = ref('parsed')
const cleanupDays = ref(30)
const expandedRouters = ref([])

// Delete confirmation state
const showDeleteModal = ref(false)
const deleteModalMessage = ref('')
const fileToDelete = ref(null)
const deleting = ref(false)

function formatDate(dateStr) {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  return date.toLocaleString()
}

function toggleMessages(ip) {
  const idx = expandedRouters.value.indexOf(ip)
  if (idx >= 0) {
    expandedRouters.value.splice(idx, 1)
  } else {
    expandedRouters.value.push(ip)
  }
}

async function fetchLogs() {
  loading.value = true
  try {
    const response = await api.get('/tasks/logs/files')
    logFiles.value = response.files || []
    statistics.value = response.statistics || null
  } catch (error) {
    console.error('Failed to fetch logs:', error)
    store.addNotification('Failed to fetch logs', 'error')
  } finally {
    loading.value = false
  }
}

async function viewLog(file) {
  selectedFile.value = file
  expandedRouters.value = []
  showViewer.value = true
  viewMode.value = 'parsed'

  try {
    // Fetch parsed data
    const parsed = await api.get(`/tasks/logs/files/${file.filename}`)
    parsedLog.value = parsed

    // Fetch raw data
    const raw = await api.get(`/tasks/logs/files/${file.filename}/raw`)
    rawLog.value = raw
  } catch (error) {
    console.error('Failed to load log file:', error)
    store.addNotification('Failed to load log file', 'error')
  }
}

function downloadLog(file) {
  const url = `/api/tasks/logs/files/${file.filename}/raw`
  const link = document.createElement('a')
  link.href = url
  link.download = file.filename
  link.click()
}

function deleteLog(file) {
  fileToDelete.value = file
  deleteModalMessage.value = `Are you sure you want to delete log file: ${file.filename}?`
  showDeleteModal.value = true
}

async function handleDeleteConfirm() {
  if (!fileToDelete.value) return
  deleting.value = true
  try {
    await api.delete(`/tasks/logs/files/${fileToDelete.value.filename}`)
    store.addNotification('success', 'Log file deleted')
    fetchLogs()
  } catch (error) {
    store.addNotification('error', 'Failed to delete log file')
  } finally {
    deleting.value = false
    showDeleteModal.value = false
    fileToDelete.value = null
  }
}

async function cleanupLogs() {
  try {
    const response = await api.delete(`/tasks/logs/cleanup?days=${cleanupDays.value}`)
    store.addNotification(response.message || 'Cleanup completed', 'success')
    showCleanupModal.value = false
    fetchLogs()
  } catch (error) {
    console.error('Failed to cleanup logs:', error)
    store.addNotification('Failed to cleanup logs', 'error')
  }
}

onMounted(() => {
  fetchLogs()
})
</script>

<style scoped>
.spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

pre {
  white-space: pre-wrap;
  word-wrap: break-word;
}
</style>
