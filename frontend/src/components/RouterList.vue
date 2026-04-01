<template>
  <div>
    <div class="d-flex justify-content-between align-items-center mb-4">
      <h2>Routers</h2>
      <div>
        <button class="btn btn-outline-secondary me-2" @click="refreshRouters" :disabled="loading">
          <i class="bi bi-arrow-clockwise" :class="{ 'spin': loading }"></i>
          Refresh
        </button>
        <button class="btn btn-primary" @click="openAddModal()">
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
            <tr v-for="router in filteredRouters" :key="`${router.id}-${router.update_channel}-${router.latest_version}`" :class="{ 'row-loading': changingChannel[router.id] }">
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
              <td>
                {{ router.ros_version || '-' }}
                <small class="text-success d-block" v-if="router.has_updates && router.latest_version">
                  → {{ router.latest_version }}
                </small>
              </td>
              <td>
                {{ router.firmware || '-' }}
                <small class="text-warning d-block" v-if="router.has_firmware_update">
                  → {{ router.upgrade_firmware }}
                </small>
              </td>
              <td>
                <select
                  class="form-select form-select-sm channel-select"
                  :class="getChannelSelectClass(router.update_channel)"
                  :value="router.update_channel || ''"
                  @change="changeChannel(router, $event.target.value)"
                  :disabled="!router.is_online || changingChannel[router.id]"
                  :title="router.is_online ? 'Click to change update channel' : 'Router offline'"
                >
                  <option value="" disabled>-</option>
                  <option value="stable">stable</option>
                  <option value="long-term">long-term</option>
                  <option value="testing">testing</option>
                  <option value="development">development</option>
                </select>
                <i v-if="changingChannel[router.id]" class="bi bi-hourglass-split spin ms-1 text-muted"></i>
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
                    class="btn btn-outline-warning"
                    @click="upgradeFirmware(router)"
                    :disabled="!router.is_online || !router.has_firmware_update || upgradingFirmware[router.id]"
                    title="Upgrade Firmware"
                  >
                    <i class="bi" :class="upgradingFirmware[router.id] ? 'bi-hourglass-split spin' : 'bi-cpu'"></i>
                    <span class="d-none d-xl-inline ms-1">FW</span>
                  </button>
                  <button
                    class="btn btn-outline-success"
                    @click="upgradeRouterOS(router)"
                    :disabled="!router.is_online || !router.has_updates || upgradingRouterOS[router.id]"
                    title="Upgrade RouterOS"
                  >
                    <i class="bi" :class="upgradingRouterOS[router.id] ? 'bi-hourglass-split spin' : 'bi-arrow-up-circle'"></i>
                    <span class="d-none d-xl-inline ms-1">ROS</span>
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

    <!-- Upgrade Modal -->
    <UpgradeModal
      :visible="showUpgradeModal"
      :router="upgradeModalRouter"
      :taskId="upgradeModalTaskId"
      :upgradeType="upgradeModalType"
      @close="closeUpgradeModal"
      @complete="onUpgradeComplete"
    />
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useMainStore } from '../stores/main'
import { scanApi, taskApi, routerApi } from '../services/api'
import ConfirmModal from './ConfirmModal.vue'
import UpgradeModal from './UpgradeModal.vue'
import { useRouterOperations } from '../composables/useRouterOperations'
import { useRouterCrud } from '../composables/useRouterCrud'
import { useRouterListFilters } from '../composables/useRouterListFilters'

const store = useMainStore()

const loading = ref(false)

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

const formatDate = (dateStr) => {
  if (!dateStr) return 'Never'
  const date = new Date(dateStr)
  return date.toLocaleString()
}

const {
  searchQuery,
  statusFilter,
  filteredRouters,
  allSelected,
  toggleSelectAll,
  scanRouter,
  scanSelected
} = useRouterListFilters({
  store,
  scanApi
})

const {
  showAddModal,
  showEditModal,
  editingRouter,
  formData,
  showDeleteConfirm,
  deleteConfirmMessage,
  deleting,
  openAddModal,
  editRouter,
  promptDeleteRouter,
  promptDeleteSelected,
  confirmDeleteAction,
  closeModal,
  saveRouter
} = useRouterCrud({ store })

const deleteRouter = (router) => {
  promptDeleteRouter(router)
}

const deleteSelected = () => {
  promptDeleteSelected(store.selectedRouterIds.length)
}

const {
  upgradingFirmware,
  upgradingRouterOS,
  changingChannel,
  showUpgradeModal,
  upgradeModalRouter,
  upgradeModalTaskId,
  upgradeModalType,
  getChannelSelectClass,
  upgradeFirmware,
  upgradeRouterOS,
  closeUpgradeModal,
  onUpgradeComplete,
  changeChannel
} = useRouterOperations({
  store,
  taskApi,
  routerApi
})
</script>

<style scoped>
.channel-select {
  width: auto;
  min-width: 110px;
  font-size: 0.75rem;
  padding: 0.2rem 0.4rem;
  cursor: pointer;
}

.channel-select:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.channel-stable {
  background-color: rgba(25, 135, 84, 0.15);
  border-color: #198754;
  color: #198754;
}

.channel-longterm {
  background-color: rgba(13, 110, 253, 0.15);
  border-color: #0d6efd;
  color: #0d6efd;
}

.channel-testing {
  background-color: rgba(255, 193, 7, 0.15);
  border-color: #ffc107;
  color: #856404;
}

.channel-development {
  background-color: rgba(220, 53, 69, 0.15);
  border-color: #dc3545;
  color: #dc3545;
}

.spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.row-loading {
  opacity: 0.5;
  pointer-events: none;
  position: relative;
}

.row-loading::after {
  content: "Updating...";
  position: absolute;
  left: 50%;
  top: 50%;
  transform: translate(-50%, -50%);
  background: rgba(0, 0, 0, 0.7);
  color: white;
  padding: 4px 12px;
  border-radius: 4px;
  font-size: 0.8rem;
}
</style>
