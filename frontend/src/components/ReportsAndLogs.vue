<template>
  <div class="container-fluid py-4">
    <div class="d-flex justify-content-between align-items-center mb-4">
      <h2><i class="bi bi-file-earmark-bar-graph me-2"></i>Reports & Logs</h2>
    </div>

    <!-- Tabs -->
    <ul class="nav nav-tabs mb-4">
      <li class="nav-item">
        <a class="nav-link" :class="{ active: activeTab === 'reports' }" href="#"
           @click.prevent="activeTab = 'reports'">
          <i class="bi bi-file-earmark-bar-graph me-1"></i> Reports
        </a>
      </li>
      <li class="nav-item">
        <a class="nav-link" :class="{ active: activeTab === 'logs' }" href="#"
           @click.prevent="activeTab = 'logs'">
          <i class="bi bi-file-text me-1"></i> Operation Logs
        </a>
      </li>
    </ul>

    <!-- REPORTS TAB -->
    <div v-show="activeTab === 'reports'">
      <div class="row">
        <!-- Report Generator -->
        <div class="col-md-5">
          <div class="card mb-4">
            <div class="card-header">
              <h5 class="mb-0">Generate Report</h5>
            </div>
            <div class="card-body">
              <div class="mb-3">
                <label class="form-label">Report Type</label>
                <select class="form-select" v-model="reportForm.report_type">
                  <option value="inventory">Router Inventory</option>
                  <option value="updates">Update History</option>
                  <option value="health">Health Report</option>
                  <option value="activity">Activity Log</option>
                  <option value="backups">Backup Report</option>
                </select>
              </div>

              <div class="mb-3">
                <label class="form-label">Export Format</label>
                <div class="btn-group w-100">
                  <input type="radio" class="btn-check" v-model="reportForm.format" value="pdf" id="fPdf" />
                  <label class="btn btn-outline-secondary" for="fPdf"><i class="bi bi-file-pdf me-1"></i>PDF</label>
                  <input type="radio" class="btn-check" v-model="reportForm.format" value="excel" id="fExcel" />
                  <label class="btn btn-outline-secondary" for="fExcel"><i class="bi bi-file-excel me-1"></i>Excel</label>
                  <input type="radio" class="btn-check" v-model="reportForm.format" value="csv" id="fCsv" />
                  <label class="btn btn-outline-secondary" for="fCsv"><i class="bi bi-file-text me-1"></i>CSV</label>
                  <input type="radio" class="btn-check" v-model="reportForm.format" value="json" id="fJson" />
                  <label class="btn btn-outline-secondary" for="fJson"><i class="bi bi-filetype-json me-1"></i>JSON</label>
                </div>
              </div>

              <div class="row mb-3">
                <div class="col-6">
                  <label class="form-label">Date From</label>
                  <input type="date" class="form-control" v-model="reportForm.filters.date_from" />
                </div>
                <div class="col-6">
                  <label class="form-label">Date To</label>
                  <input type="date" class="form-control" v-model="reportForm.filters.date_to" />
                </div>
              </div>

              <div class="form-check mb-3">
                <input type="checkbox" class="form-check-input" v-model="reportForm.include_charts" id="incCharts" />
                <label class="form-check-label" for="incCharts">Include charts (PDF only)</label>
              </div>

              <button class="btn btn-primary w-100" @click="generateReport" :disabled="generating">
                <span v-if="generating" class="spinner-border spinner-border-sm me-1"></span>
                <i v-else class="bi bi-file-earmark-arrow-down me-1"></i>
                Generate Report
              </button>
            </div>
          </div>

          <!-- Quick Exports -->
          <div class="card">
            <div class="card-header">
              <h5 class="mb-0">Quick Export</h5>
            </div>
            <div class="card-body">
              <div class="d-grid gap-2">
                <button class="btn btn-outline-primary" @click="quickExport('inventory')">
                  <i class="bi bi-router me-2"></i>Export Router Inventory (CSV)
                </button>
                <button class="btn btn-outline-primary" @click="quickExport('health')">
                  <i class="bi bi-heart-pulse me-2"></i>Export Health Status (CSV)
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- Generated Reports -->
        <div class="col-md-7">
          <div class="card">
            <div class="card-header d-flex justify-content-between align-items-center">
              <h5 class="mb-0">Generated Reports</h5>
              <button class="btn btn-sm btn-outline-secondary" @click="loadReports">
                <i class="bi bi-arrow-clockwise"></i>
              </button>
            </div>
            <div class="list-group list-group-flush" style="max-height: 500px; overflow-y: auto;">
              <div v-for="report in reports" :key="report.filename"
                   class="list-group-item d-flex align-items-center">
                <div class="flex-grow-1">
                  <div><i :class="getFormatIcon(report.filename)" class="me-2"></i>{{ report.filename }}</div>
                  <small class="text-muted">{{ formatSize(report.file_size) }} - {{ formatDate(report.created_at) }}</small>
                </div>
                <div>
                  <button class="btn btn-sm btn-primary me-1" @click="downloadReport(report.filename)">
                    <i class="bi bi-download"></i>
                  </button>
                  <button class="btn btn-sm btn-outline-danger" @click="deleteReportConfirm(report.filename)">
                    <i class="bi bi-trash"></i>
                  </button>
                </div>
              </div>
              <div v-if="reports.length === 0" class="list-group-item text-center text-muted py-4">
                No reports generated yet
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- LOGS TAB -->
    <div v-show="activeTab === 'logs'">
      <!-- Statistics -->
      <div class="row mb-4" v-if="logStatistics">
        <div class="col-md-3">
          <StatCard label="Log Files" :value="logStatistics.total_log_files" icon="bi bi-file-text" variant="primary" />
        </div>
        <div class="col-md-3">
          <StatCard label="Routers Processed" :value="logStatistics.total_routers_processed" icon="bi bi-router" variant="info" />
        </div>
        <div class="col-md-3">
          <StatCard label="Successful" :value="logStatistics.total_successful" icon="bi bi-check-circle" variant="success" />
        </div>
        <div class="col-md-3">
          <StatCard label="Failed" :value="logStatistics.total_failed" icon="bi bi-x-circle" variant="danger" />
        </div>
      </div>

      <!-- Log Files -->
      <div class="card">
        <div class="card-header d-flex justify-content-between align-items-center">
          <span>Log Files</span>
          <div>
            <small class="text-muted me-3" v-if="logStatistics">Total size: {{ logStatistics.total_size_human }}</small>
            <button class="btn btn-sm btn-outline-secondary me-2" @click="fetchLogs" :disabled="loadingLogs">
              <i class="bi bi-arrow-clockwise" :class="{ spin: loadingLogs }"></i>
            </button>
            <button class="btn btn-sm btn-outline-danger" @click="showCleanupModal = true">
              <i class="bi bi-trash me-1"></i> Cleanup
            </button>
          </div>
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
                <td><small>{{ formatDate(file.modified) }}</small></td>
                <td><small>{{ file.size_human }}</small></td>
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
                    <button class="btn btn-outline-danger" @click="deleteLogConfirm(file)" title="Delete">
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
    </div>

    <!-- Log Viewer Modal -->
    <div class="modal fade" :class="{ show: showLogViewer }" tabindex="-1"
         :style="{ display: showLogViewer ? 'block' : 'none' }">
      <div class="modal-dialog modal-xl">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title"><i class="bi bi-file-text me-2"></i>{{ selectedLogFile?.filename }}</h5>
            <div class="ms-auto me-3">
              <div class="btn-group btn-group-sm">
                <button class="btn" :class="logViewMode === 'parsed' ? 'btn-primary' : 'btn-outline-primary'"
                        @click="logViewMode = 'parsed'">Parsed</button>
                <button class="btn" :class="logViewMode === 'raw' ? 'btn-primary' : 'btn-outline-primary'"
                        @click="logViewMode = 'raw'">Raw</button>
              </div>
            </div>
            <button type="button" class="btn-close" @click="showLogViewer = false"></button>
          </div>
          <div class="modal-body">
            <!-- Parsed View -->
            <div v-if="logViewMode === 'parsed' && parsedLog">
              <ResultsSummary v-if="parsedLog.summary" class="mb-4"
                :total="parsedLog.summary.total"
                :successful="parsedLog.summary.successful"
                :failed="parsedLog.summary.failed"
              />

              <div class="card" v-if="parsedLog.routers?.length">
                <div class="card-header">Router Results</div>
                <div class="list-group list-group-flush" style="max-height: 400px; overflow-y: auto;">
                  <div class="list-group-item" v-for="router in parsedLog.routers" :key="router.ip"
                       :class="{ 'list-group-item-danger': !router.success }">
                    <div class="d-flex justify-content-between">
                      <div>
                        <strong>{{ router.ip }}</strong>
                        <span class="text-muted ms-2" v-if="router.identity">{{ router.identity }}</span>
                      </div>
                      <span :class="router.success ? 'badge bg-success' : 'badge bg-danger'">
                        {{ router.success ? 'SUCCESS' : 'FAILED' }}
                      </span>
                    </div>
                    <div class="text-danger mt-1" v-if="router.error">
                      <small><i class="bi bi-exclamation-circle me-1"></i>{{ router.error }}</small>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Raw View -->
            <div v-if="logViewMode === 'raw'">
              <pre class="bg-dark text-light p-3 rounded" style="max-height: 500px; overflow: auto; font-size: 12px;">{{ rawLog }}</pre>
            </div>
          </div>
          <div class="modal-footer">
            <button class="btn btn-secondary" @click="downloadLog(selectedLogFile)">
              <i class="bi bi-download me-1"></i>Download
            </button>
            <button class="btn btn-primary" @click="showLogViewer = false">Close</button>
          </div>
        </div>
      </div>
    </div>
    <div class="modal-backdrop fade" :class="{ show: showLogViewer }" v-if="showLogViewer"></div>

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

    <!-- Confirm Modal -->
    <ConfirmModal
      :visible="showConfirm"
      :title="confirmTitle"
      :message="confirmMessage"
      variant="danger"
      :loading="confirmLoading"
      @confirm="handleConfirm"
      @cancel="showConfirm = false"
    />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { reportsApi } from '../services/api'
import api from '../services/api'
import { useMainStore } from '../stores/main'
import { formatDate, formatSize } from '../utils/formatters'
import StatCard from './shared/StatCard.vue'
import ResultsSummary from './shared/ResultsSummary.vue'
import ConfirmModal from './ConfirmModal.vue'

const store = useMainStore()

// State
const activeTab = ref('reports')
const generating = ref(false)
const loadingLogs = ref(false)

// Reports
const reports = ref([])
const reportForm = ref({
  report_type: 'inventory',
  format: 'pdf',
  title: '',
  include_charts: true,
  filters: { date_from: null, date_to: null }
})

// Logs
const logFiles = ref([])
const logStatistics = ref(null)
const showLogViewer = ref(false)
const selectedLogFile = ref(null)
const parsedLog = ref(null)
const rawLog = ref('')
const logViewMode = ref('parsed')
const showCleanupModal = ref(false)
const cleanupDays = ref(30)

// Confirmation
const showConfirm = ref(false)
const confirmTitle = ref('')
const confirmMessage = ref('')
const confirmLoading = ref(false)
const pendingAction = ref(null)

// Lifecycle
onMounted(async () => {
  await Promise.all([loadReports(), fetchLogs()])
})

// Report methods
async function loadReports() {
  try {
    const response = await reportsApi.list()
    reports.value = response.reports || []
  } catch (error) { console.error('Failed to load reports:', error) }
}

async function generateReport() {
  generating.value = true
  try {
    await reportsApi.generate(reportForm.value)
    await loadReports()
    store.addNotification('success', 'Report generated successfully!')
  } catch (error) {
    store.addNotification('error', 'Report generation failed: ' + error.message)
  } finally { generating.value = false }
}

async function quickExport(type) {
  try {
    const response = await reportsApi[type === 'inventory' ? 'quickInventory' : 'quickHealth']('csv')
    const blob = new Blob([response.content], { type: 'text/csv' })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = response.filename
    a.click()
    window.URL.revokeObjectURL(url)
  } catch (error) {
    store.addNotification('error', 'Export failed')
  }
}

async function downloadReport(filename) {
  try {
    const blob = await reportsApi.download(filename)
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    a.click()
    window.URL.revokeObjectURL(url)
  } catch (error) {
    store.addNotification('error', 'Download failed')
  }
}

function deleteReportConfirm(filename) {
  confirmTitle.value = 'Delete Report'
  confirmMessage.value = `Delete report "${filename}"?`
  pendingAction.value = async () => { await reportsApi.delete(filename); await loadReports() }
  showConfirm.value = true
}

function getFormatIcon(filename) {
  if (filename.endsWith('.pdf')) return 'bi bi-file-pdf text-danger'
  if (filename.endsWith('.xlsx')) return 'bi bi-file-excel text-success'
  if (filename.endsWith('.csv')) return 'bi bi-file-text text-primary'
  return 'bi bi-file-code text-warning'
}

// Log methods
async function fetchLogs() {
  loadingLogs.value = true
  try {
    const response = await api.get('/tasks/logs/files')
    logFiles.value = response.files || []
    logStatistics.value = response.statistics || null
  } catch (error) {
    store.addNotification('error', 'Failed to fetch logs')
  } finally { loadingLogs.value = false }
}

async function viewLog(file) {
  try {
    const [parsed, raw] = await Promise.all([
      api.get(`/tasks/logs/files/${file.filename}`),
      api.get(`/tasks/logs/files/${file.filename}/raw`)
    ])
    selectedLogFile.value = file
    parsedLog.value = parsed
    rawLog.value = raw
    showLogViewer.value = true
    logViewMode.value = 'parsed'
  } catch (error) {
    store.addNotification('error', 'Failed to load log file')
  }
}

function downloadLog(file) {
  const url = `/api/tasks/logs/files/${file.filename}/raw`
  const link = document.createElement('a')
  link.href = url
  link.download = file.filename
  link.click()
}

function deleteLogConfirm(file) {
  confirmTitle.value = 'Delete Log File'
  confirmMessage.value = `Delete log file "${file.filename}"?`
  pendingAction.value = async () => {
    await api.delete(`/tasks/logs/files/${file.filename}`)
    store.addNotification('success', 'Log file deleted')
    fetchLogs()
  }
  showConfirm.value = true
}

async function cleanupLogs() {
  try {
    const response = await api.delete(`/tasks/logs/cleanup?days=${cleanupDays.value}`)
    store.addNotification('success', response.message || 'Cleanup completed')
    showCleanupModal.value = false
    fetchLogs()
  } catch (error) {
    store.addNotification('error', 'Failed to cleanup logs')
  }
}

// Confirmation handler
async function handleConfirm() {
  if (!pendingAction.value) return
  confirmLoading.value = true
  try { await pendingAction.value() }
  finally { confirmLoading.value = false; showConfirm.value = false; pendingAction.value = null }
}
</script>

<style scoped>
.nav-tabs .nav-link { color: var(--text-secondary); }
.nav-tabs .nav-link.active { font-weight: 600; }
</style>
