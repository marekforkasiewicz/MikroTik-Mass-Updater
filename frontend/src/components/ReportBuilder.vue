<template>
  <div class="container-fluid py-4">
    <h2 class="mb-4"><i class="bi bi-file-earmark-bar-graph me-2"></i>Reports</h2>

    <div class="row">
      <!-- Report Generator -->
      <div class="col-md-6">
        <div class="card">
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
                <label class="btn btn-outline-secondary" for="fPdf">
                  <i class="bi bi-file-pdf me-1"></i>PDF
                </label>
                <input type="radio" class="btn-check" v-model="reportForm.format" value="excel" id="fExcel" />
                <label class="btn btn-outline-secondary" for="fExcel">
                  <i class="bi bi-file-excel me-1"></i>Excel
                </label>
                <input type="radio" class="btn-check" v-model="reportForm.format" value="csv" id="fCsv" />
                <label class="btn btn-outline-secondary" for="fCsv">
                  <i class="bi bi-file-text me-1"></i>CSV
                </label>
                <input type="radio" class="btn-check" v-model="reportForm.format" value="json" id="fJson" />
                <label class="btn btn-outline-secondary" for="fJson">
                  <i class="bi bi-filetype-json me-1"></i>JSON
                </label>
              </div>
            </div>

            <div class="mb-3">
              <label class="form-label">Title (optional)</label>
              <input type="text" class="form-control" v-model="reportForm.title" placeholder="Auto-generated" />
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
        <div class="card mt-4">
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
      <div class="col-md-6">
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
                <div><i :class="formatIcon(report.filename)" class="me-2"></i>{{ report.filename }}</div>
                <small class="text-muted">{{ formatSize(report.file_size) }} - {{ formatDate(report.created_at) }}</small>
              </div>
              <div>
                <button class="btn btn-sm btn-primary me-1" @click="downloadReport(report.filename)">
                  <i class="bi bi-download"></i>
                </button>
                <button class="btn btn-sm btn-outline-danger" @click="deleteReport(report.filename)">
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

    <!-- Confirm Delete Modal -->
    <ConfirmModal
      :visible="showDeleteModal"
      title="Delete Report"
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
import { reportsApi } from '../services/api'
import ConfirmModal from './ConfirmModal.vue'
import { useMainStore } from '../stores/main'

const mainStore = useMainStore()

const reports = ref([])
const generating = ref(false)

// Delete confirmation state
const showDeleteModal = ref(false)
const deleteModalMessage = ref('')
const reportToDelete = ref(null)
const deleting = ref(false)

const reportForm = ref({
  report_type: 'inventory',
  format: 'pdf',
  title: '',
  include_charts: true,
  include_details: true,
  filters: {
    date_from: null,
    date_to: null
  }
})

onMounted(async () => {
  await loadReports()
})

async function loadReports() {
  try {
    const response = await reportsApi.list()
    reports.value = response.reports || []
  } catch (error) {
    console.error('Failed to load reports:', error)
  }
}

async function generateReport() {
  generating.value = true
  try {
    const response = await reportsApi.generate(reportForm.value)
    await loadReports()
    mainStore.addNotification('success', 'Report generated successfully!')
  } catch (error) {
    console.error('Failed to generate report:', error)
    mainStore.addNotification('error', 'Report generation failed: ' + error.message)
  } finally {
    generating.value = false
  }
}

async function quickExport(type) {
  try {
    const response = await reportsApi[type === 'inventory' ? 'quickInventory' : 'quickHealth']('csv')

    // Create download
    const blob = new Blob([response.content], { type: 'text/csv' })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = response.filename
    a.click()
    window.URL.revokeObjectURL(url)
  } catch (error) {
    console.error('Quick export failed:', error)
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
    console.error('Download failed:', error)
  }
}

function deleteReport(filename) {
  reportToDelete.value = filename
  deleteModalMessage.value = `Are you sure you want to delete report "${filename}"?`
  showDeleteModal.value = true
}

async function handleDeleteConfirm() {
  if (!reportToDelete.value) return
  deleting.value = true
  try {
    await reportsApi.delete(reportToDelete.value)
    await loadReports()
    mainStore.addNotification('success', 'Report deleted successfully')
  } catch (error) {
    console.error('Failed to delete report:', error)
    mainStore.addNotification('error', 'Failed to delete report')
  } finally {
    deleting.value = false
    showDeleteModal.value = false
    reportToDelete.value = null
  }
}

function formatIcon(filename) {
  if (filename.endsWith('.pdf')) return 'bi bi-file-pdf text-danger'
  if (filename.endsWith('.xlsx')) return 'bi bi-file-excel text-success'
  if (filename.endsWith('.csv')) return 'bi bi-file-text text-primary'
  return 'bi bi-file-code text-warning'
}

function formatSize(bytes) {
  if (!bytes) return '-'
  const units = ['B', 'KB', 'MB', 'GB']
  let i = 0
  while (bytes >= 1024 && i < units.length - 1) {
    bytes /= 1024
    i++
  }
  return `${bytes.toFixed(1)} ${units[i]}`
}

function formatDate(dateStr) {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString()
}
</script>
