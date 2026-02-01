<template>
  <div class="container-fluid py-4">
    <div class="d-flex justify-content-between align-items-center mb-4">
      <h2><i class="bi bi-cloud-arrow-up me-2"></i>Backups</h2>
      <button class="btn btn-primary" @click="showCreateModal = true" v-if="canModify">
        <i class="bi bi-plus-lg me-1"></i> Create Backup
      </button>
    </div>

    <!-- Filters -->
    <div class="card mb-4">
      <div class="card-body">
        <div class="row g-3">
          <div class="col-md-4">
            <select class="form-select" v-model="filters.backup_type">
              <option value="">All Types</option>
              <option value="config">Configuration</option>
              <option value="export">Export</option>
              <option value="cloud">Cloud</option>
            </select>
          </div>
          <div class="col-md-4">
            <select class="form-select" v-model="filters.router_id">
              <option value="">All Routers</option>
              <option v-for="router in routers" :key="router.id" :value="router.id">
                {{ router.identity || router.ip }}
              </option>
            </select>
          </div>
          <div class="col-md-4">
            <button class="btn btn-outline-secondary w-100" @click="loadBackups">
              <i class="bi bi-funnel me-1"></i> Apply Filters
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Backups Table -->
    <div class="card">
      <div class="card-body">
        <div class="table-responsive">
          <table class="table table-hover">
            <thead>
              <tr>
                <th>Router</th>
                <th>Name</th>
                <th>Type</th>
                <th>Size</th>
                <th>Status</th>
                <th>Created</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="backup in backups" :key="backup.id">
                <td>
                  <div>{{ backup.router_identity || 'Unknown' }}</div>
                  <small class="text-muted">v{{ backup.router_version }}</small>
                </td>
                <td>{{ backup.name }}</td>
                <td>
                  <span :class="typeBadge(backup.backup_type)">
                    {{ backup.backup_type }}
                  </span>
                </td>
                <td>{{ formatSize(backup.file_size) }}</td>
                <td>
                  <span :class="statusBadge(backup.status)">
                    {{ backup.status }}
                  </span>
                </td>
                <td>{{ formatDate(backup.created_at) }}</td>
                <td>
                  <div class="btn-group btn-group-sm">
                    <button class="btn btn-outline-primary" @click="downloadBackup(backup)"
                            title="Download" v-if="backup.file_path">
                      <i class="bi bi-download"></i>
                    </button>
                    <button class="btn btn-outline-warning" @click="restoreBackup(backup)"
                            title="Restore" v-if="canModify">
                      <i class="bi bi-arrow-counterclockwise"></i>
                    </button>
                    <button class="btn btn-outline-danger" @click="confirmDelete(backup)"
                            title="Delete" v-if="canModify">
                      <i class="bi bi-trash"></i>
                    </button>
                  </div>
                </td>
              </tr>
              <tr v-if="backups.length === 0 && !loading">
                <td colspan="7" class="text-center py-4 text-muted">
                  No backups found
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- Create Backup Modal -->
    <div class="modal fade" id="createModal" tabindex="-1" ref="createModalEl">
      <div class="modal-dialog">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">Create Backup</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
          </div>
          <div class="modal-body">
            <div class="mb-3">
              <label class="form-label">Router</label>
              <select class="form-select" v-model="backupForm.router_id" required>
                <option value="">Select router...</option>
                <option v-for="router in routers" :key="router.id" :value="router.id">
                  {{ router.identity || router.ip }}
                </option>
              </select>
            </div>
            <div class="mb-3">
              <label class="form-label">Backup Name</label>
              <input type="text" class="form-control" v-model="backupForm.name"
                     placeholder="Auto-generated if empty" />
            </div>
            <div class="mb-3">
              <label class="form-label">Backup Type</label>
              <select class="form-select" v-model="backupForm.backup_type">
                <option value="config">Configuration (binary)</option>
                <option value="export">Export (text)</option>
                <option value="cloud">Cloud Backup</option>
              </select>
            </div>
            <div class="form-check mb-3">
              <input type="checkbox" class="form-check-input" v-model="backupForm.includes_passwords" id="incPwd" />
              <label class="form-check-label" for="incPwd">Include passwords</label>
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
            <button type="button" class="btn btn-primary" @click="createBackup" :disabled="saving">
              <span v-if="saving" class="spinner-border spinner-border-sm me-1"></span>
              Create Backup
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Restore Modal -->
    <div class="modal fade" id="restoreModal" tabindex="-1" ref="restoreModalEl">
      <div class="modal-dialog">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">Restore Backup</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
          </div>
          <div class="modal-body">
            <div class="alert alert-warning">
              <i class="bi bi-exclamation-triangle me-2"></i>
              Restoring will reboot the router. Are you sure?
            </div>
            <p>
              <strong>Router:</strong> {{ selectedBackup?.router_identity }}<br>
              <strong>Backup:</strong> {{ selectedBackup?.name }}<br>
              <strong>Created:</strong> {{ formatDate(selectedBackup?.created_at) }}
            </p>
            <div class="mb-3">
              <label class="form-label">Reason (optional)</label>
              <textarea class="form-control" v-model="restoreReason" rows="2"></textarea>
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
            <button type="button" class="btn btn-warning" @click="confirmRestore" :disabled="restoring">
              <span v-if="restoring" class="spinner-border spinner-border-sm me-1"></span>
              Restore Backup
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Confirm Delete Modal -->
    <ConfirmModal
      :visible="showDeleteModal"
      title="Delete Backup"
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
import { ref, computed, onMounted, nextTick, watch } from 'vue'
import { Modal } from 'bootstrap'
import { backupsApi, routerApi } from '../services/api'
import { useAuthStore } from '../stores/auth'
import { useMainStore } from '../stores/main'
import ConfirmModal from './ConfirmModal.vue'

const authStore = useAuthStore()
const mainStore = useMainStore()
const canModify = computed(() => authStore.isOperator)

const backups = ref([])
const routers = ref([])
const loading = ref(false)
const saving = ref(false)
const restoring = ref(false)

const filters = ref({
  backup_type: '',
  router_id: ''
})

const backupForm = ref({
  router_id: '',
  name: '',
  backup_type: 'config',
  includes_passwords: false
})

const selectedBackup = ref(null)
const restoreReason = ref('')
const showCreateModal = ref(false)

const createModalEl = ref(null)
const restoreModalEl = ref(null)
let createModal = null
let restoreModal = null

// Delete confirmation state
const showDeleteModal = ref(false)
const deleteModalMessage = ref('')
const backupToDelete = ref(null)
const deleting = ref(false)

onMounted(async () => {
  await loadRouters()
  await loadBackups()

  nextTick(() => {
    if (createModalEl.value) createModal = new Modal(createModalEl.value)
    if (restoreModalEl.value) restoreModal = new Modal(restoreModalEl.value)
  })
})

watch(showCreateModal, (val) => {
  if (val) createModal?.show()
})

async function loadRouters() {
  try {
    const response = await routerApi.list()
    routers.value = response.routers || response.items || []
  } catch (error) {
    console.error('Failed to load routers:', error)
    mainStore.addNotification('Failed to load routers', 'error')
  }
}

async function loadBackups() {
  loading.value = true
  try {
    const params = {}
    if (filters.value.backup_type) params.backup_type = filters.value.backup_type
    if (filters.value.router_id) params.router_id = filters.value.router_id

    const response = await backupsApi.list(params)
    backups.value = response.items || []
  } catch (error) {
    console.error('Failed to load backups:', error)
    mainStore.addNotification('Failed to load backups', 'error')
  } finally {
    loading.value = false
  }
}

async function createBackup() {
  saving.value = true
  try {
    const data = { ...backupForm.value }
    if (!data.name) {
      data.name = `backup_${new Date().toISOString().replace(/[:.]/g, '-')}`
    }
    await backupsApi.create(data)
    mainStore.addNotification('Backup created successfully', 'success')
    createModal?.hide()
    resetForm()
    await loadBackups()
  } catch (error) {
    console.error('Failed to create backup:', error)
    mainStore.addNotification('Failed to create backup: ' + error.message, 'error')
  } finally {
    saving.value = false
  }
}

async function downloadBackup(backup) {
  try {
    const blob = await backupsApi.download(backup.id)
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = backup.name
    a.click()
    window.URL.revokeObjectURL(url)
  } catch (error) {
    console.error('Failed to download backup:', error)
  }
}

function restoreBackup(backup) {
  selectedBackup.value = backup
  restoreReason.value = ''
  restoreModal?.show()
}

async function confirmRestore() {
  if (!selectedBackup.value) return

  restoring.value = true
  try {
    await backupsApi.restore({
      router_id: selectedBackup.value.router_id,
      backup_id: selectedBackup.value.id,
      rollback_type: 'restore',
      reason: restoreReason.value
    })
    restoreModal?.hide()
    mainStore.addNotification('success', 'Restore initiated. Router will reboot.')
  } catch (error) {
    console.error('Failed to restore backup:', error)
    mainStore.addNotification('error', 'Failed to restore backup: ' + error.message)
  } finally {
    restoring.value = false
  }
}

function confirmDelete(backup) {
  backupToDelete.value = backup
  deleteModalMessage.value = `Are you sure you want to delete backup "${backup.name}"? This action cannot be undone.`
  showDeleteModal.value = true
}

async function handleDeleteConfirm() {
  if (!backupToDelete.value) return
  deleting.value = true
  try {
    await backupsApi.delete(backupToDelete.value.id)
    await loadBackups()
    mainStore.addNotification('success', 'Backup deleted successfully')
  } catch (error) {
    console.error('Failed to delete backup:', error)
    mainStore.addNotification('error', 'Failed to delete backup')
  } finally {
    deleting.value = false
    showDeleteModal.value = false
    backupToDelete.value = null
  }
}

function resetForm() {
  backupForm.value = {
    router_id: '',
    name: '',
    backup_type: 'config',
    includes_passwords: false
  }
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

function typeBadge(type) {
  const badges = {
    config: 'badge bg-primary',
    export: 'badge bg-info',
    cloud: 'badge bg-success'
  }
  return badges[type] || 'badge bg-secondary'
}

function statusBadge(status) {
  const badges = {
    completed: 'badge bg-success',
    in_progress: 'badge bg-warning',
    failed: 'badge bg-danger'
  }
  return badges[status] || 'badge bg-secondary'
}
</script>
