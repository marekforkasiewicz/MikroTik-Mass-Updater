<template>
  <div>
    <div class="d-flex justify-content-between align-items-center mb-4">
      <h2>Routers</h2>
      <div>
        <button class="btn btn-outline-secondary me-2" @click="refreshRouters" :disabled="loading">
          <i class="bi bi-arrow-clockwise" :class="{ 'spin': loading }"></i>
          Refresh
        </button>
        <button class="btn btn-primary" @click="showAddModal = true">
          <i class="bi bi-plus-lg me-1"></i>
          Add Router
        </button>
      </div>
    </div>

    <!-- Filters and actions -->
    <div class="card mb-4">
      <div class="card-body">
        <div class="row g-3 align-items-center">
          <div class="col-md-4">
            <input
              type="text"
              class="form-control"
              placeholder="Search by IP or identity..."
              v-model="searchQuery"
            />
          </div>
          <div class="col-md-2">
            <select class="form-select" v-model="statusFilter">
              <option value="">All Status</option>
              <option value="online">Online</option>
              <option value="offline">Offline</option>
              <option value="updates">Needs Update</option>
            </select>
          </div>
          <div class="col-md-6 text-end">
            <span class="me-3" v-if="store.selectedRouterIds.length > 0">
              {{ store.selectedRouterIds.length }} selected
            </span>
            <button
              class="btn btn-outline-success me-2"
              @click="scanSelected"
              :disabled="store.selectedRouterIds.length === 0"
            >
              <i class="bi bi-search me-1"></i>
              Scan Selected
            </button>
            <button
              class="btn btn-outline-danger"
              @click="deleteSelected"
              :disabled="store.selectedRouterIds.length === 0"
            >
              <i class="bi bi-trash me-1"></i>
              Delete Selected
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Router table -->
    <div class="card">
      <div class="table-responsive">
        <table class="table table-hover mb-0 router-table">
          <thead>
            <tr>
              <th>
                <input
                  type="checkbox"
                  class="form-check-input"
                  @change="toggleSelectAll"
                  :checked="allSelected"
                />
              </th>
              <th>Status</th>
              <th>IP Address</th>
              <th>Identity</th>
              <th>Model</th>
              <th>RouterOS</th>
              <th>Firmware</th>
              <th>Update Channel</th>
              <th>Last Seen</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="router in filteredRouters" :key="router.id">
              <td>
                <input
                  type="checkbox"
                  class="form-check-input"
                  :checked="store.selectedRouterIds.includes(router.id)"
                  @change="store.toggleRouterSelection(router.id)"
                />
              </td>
              <td>
                <i
                  class="bi fs-5"
                  :class="{
                    'bi-check-circle-fill status-online': router.is_online,
                    'bi-x-circle-fill status-offline': !router.is_online
                  }"
                  :title="router.is_online ? 'Online' : 'Offline'"
                ></i>
                <i
                  v-if="router.has_updates"
                  class="bi bi-exclamation-triangle-fill text-warning ms-1"
                  title="Updates available"
                ></i>
              </td>
              <td>
                <code>{{ router.ip }}</code>
                <small class="text-muted" v-if="router.port !== 8728">:{{ router.port }}</small>
              </td>
              <td>{{ router.identity || '-' }}</td>
              <td>{{ router.model || '-' }}</td>
              <td>{{ router.ros_version || '-' }}</td>
              <td>
                {{ router.firmware || '-' }}
                <small class="text-warning d-block" v-if="router.has_firmware_update">
                  → {{ router.upgrade_firmware }}
                </small>
              </td>
              <td>
                <span class="badge" :class="getChannelBadgeClass(router.update_channel)">
                  {{ router.update_channel || '-' }}
                </span>
              </td>
              <td>
                <small>{{ formatDate(router.last_seen) }}</small>
              </td>
              <td>
                <div class="btn-group btn-group-sm">
                  <button
                    class="btn btn-outline-primary"
                    @click="scanRouter(router)"
                    title="Quick Scan"
                  >
                    <i class="bi bi-lightning"></i>
                  </button>
                  <button
                    class="btn btn-outline-secondary"
                    @click="editRouter(router)"
                    title="Edit"
                  >
                    <i class="bi bi-pencil"></i>
                  </button>
                  <button
                    class="btn btn-outline-danger"
                    @click="deleteRouter(router)"
                    title="Delete"
                  >
                    <i class="bi bi-trash"></i>
                  </button>
                </div>
              </td>
            </tr>
            <tr v-if="filteredRouters.length === 0">
              <td colspan="10" class="text-center py-4 text-muted">
                <i class="bi bi-inbox fs-1 d-block mb-2"></i>
                No routers found
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Add/Edit Modal -->
    <div class="modal fade" :class="{ show: showAddModal || showEditModal }" tabindex="-1"
         :style="{ display: (showAddModal || showEditModal) ? 'block' : 'none' }">
      <div class="modal-dialog">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">{{ showEditModal ? 'Edit Router' : 'Add Router' }}</h5>
            <button type="button" class="btn-close" @click="closeModal"></button>
          </div>
          <div class="modal-body">
            <form @submit.prevent="saveRouter">
              <div class="mb-3">
                <label class="form-label">IP Address *</label>
                <input type="text" class="form-control" v-model="formData.ip" required />
              </div>
              <div class="mb-3">
                <label class="form-label">Port</label>
                <input type="number" class="form-control" v-model="formData.port" />
              </div>
              <div class="mb-3">
                <label class="form-label">Username</label>
                <input type="text" class="form-control" v-model="formData.username" />
              </div>
              <div class="mb-3">
                <label class="form-label">Password</label>
                <input type="password" class="form-control" v-model="formData.password" />
              </div>
            </form>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" @click="closeModal">Cancel</button>
            <button type="button" class="btn btn-primary" @click="saveRouter">
              {{ showEditModal ? 'Update' : 'Add' }}
            </button>
          </div>
        </div>
      </div>
    </div>
    <div class="modal-backdrop fade show" v-if="showAddModal || showEditModal"></div>

    <!-- Confirm Delete Modal -->
    <ConfirmModal
      :visible="showDeleteConfirm"
      title="Delete Router"
      :message="deleteConfirmMessage"
      variant="danger"
      confirmText="Delete"
      :loading="deleting"
      @confirm="confirmDeleteAction"
      @cancel="showDeleteConfirm = false"
    />
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useMainStore } from '../stores/main'
import { scanApi } from '../services/api'
import ConfirmModal from './ConfirmModal.vue'

const store = useMainStore()

const loading = ref(false)
const searchQuery = ref('')
const statusFilter = ref('')
const showAddModal = ref(false)
const showEditModal = ref(false)
const editingRouter = ref(null)

const formData = ref({
  ip: '',
  port: 8728,
  username: '',
  password: ''
})

// Delete confirmation state
const showDeleteConfirm = ref(false)
const deleteConfirmMessage = ref('')
const deleteTarget = ref(null)
const deleteMode = ref('single') // 'single' or 'multiple'
const deleting = ref(false)

const filteredRouters = computed(() => {
  let routers = store.routers

  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    routers = routers.filter(r =>
      r.ip.toLowerCase().includes(query) ||
      (r.identity && r.identity.toLowerCase().includes(query))
    )
  }

  if (statusFilter.value === 'online') {
    routers = routers.filter(r => r.is_online)
  } else if (statusFilter.value === 'offline') {
    routers = routers.filter(r => !r.is_online)
  } else if (statusFilter.value === 'updates') {
    routers = routers.filter(r => r.has_updates)
  }

  return routers
})

const allSelected = computed(() => {
  return filteredRouters.value.length > 0 &&
         filteredRouters.value.every(r => store.selectedRouterIds.includes(r.id))
})

const toggleSelectAll = () => {
  if (allSelected.value) {
    store.clearSelection()
  } else {
    filteredRouters.value.forEach(r => {
      if (!store.selectedRouterIds.includes(r.id)) {
        store.toggleRouterSelection(r.id)
      }
    })
  }
}

const refreshRouters = async () => {
  loading.value = true
  try {
    await store.fetchRouters()
    store.addNotification('success', `Refreshed: ${store.routerStats.total} routers (${store.routerStats.online} online)`)
  } catch (error) {
    store.addNotification('error', `Refresh failed: ${error.message}`)
  } finally {
    loading.value = false
  }
}

const scanRouter = async (router) => {
  try {
    await scanApi.quickScanSingle(router.id)
    await store.fetchRouters()
    store.addNotification('success', `Scan completed for ${router.ip}`)
  } catch (error) {
    store.addNotification('error', `Scan failed: ${error.message}`)
  }
}

const scanSelected = async () => {
  await store.startQuickScan(store.selectedRouterIds)
}

const editRouter = (router) => {
  editingRouter.value = router
  formData.value = {
    ip: router.ip,
    port: router.port,
    username: router.username || '',
    password: ''
  }
  showEditModal.value = true
}

const deleteRouter = (router) => {
  deleteTarget.value = router
  deleteMode.value = 'single'
  deleteConfirmMessage.value = `Are you sure you want to delete router ${router.ip}? This action cannot be undone.`
  showDeleteConfirm.value = true
}

const deleteSelected = () => {
  deleteTarget.value = null
  deleteMode.value = 'multiple'
  deleteConfirmMessage.value = `Are you sure you want to delete ${store.selectedRouterIds.length} routers? This action cannot be undone.`
  showDeleteConfirm.value = true
}

const confirmDeleteAction = async () => {
  deleting.value = true
  try {
    if (deleteMode.value === 'single' && deleteTarget.value) {
      await store.deleteRouter(deleteTarget.value.id)
    } else {
      for (const id of store.selectedRouterIds) {
        await store.deleteRouter(id)
      }
      store.clearSelection()
    }
  } finally {
    deleting.value = false
    showDeleteConfirm.value = false
    deleteTarget.value = null
  }
}

const closeModal = () => {
  showAddModal.value = false
  showEditModal.value = false
  editingRouter.value = null
  formData.value = { ip: '', port: 8728, username: '', password: '' }
}

const saveRouter = async () => {
  if (showEditModal.value) {
    await store.updateRouter(editingRouter.value.id, formData.value)
  } else {
    await store.createRouter(formData.value)
  }
  closeModal()
}

const getChannelBadgeClass = (channel) => {
  if (!channel) return 'bg-secondary'
  const ch = channel.toLowerCase()
  if (ch.includes('stable')) return 'bg-success'
  if (ch.includes('testing')) return 'bg-warning text-dark'
  if (ch.includes('development')) return 'bg-info'
  return 'bg-secondary'
}

const formatDate = (dateStr) => {
  if (!dateStr) return 'Never'
  const date = new Date(dateStr)
  return date.toLocaleString()
}
</script>
