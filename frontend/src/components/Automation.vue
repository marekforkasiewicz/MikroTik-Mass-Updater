<template>
  <div class="container-fluid py-4">
    <div class="d-flex justify-content-between align-items-center mb-4">
      <h2><i class="bi bi-robot me-2"></i>Automation</h2>
    </div>

    <!-- Tabs -->
    <ul class="nav nav-tabs mb-4">
      <li class="nav-item">
        <a class="nav-link" :class="{ active: activeTab === 'schedules' }" href="#"
           @click.prevent="activeTab = 'schedules'">
          <i class="bi bi-calendar-check me-1"></i> Schedules
          <span class="badge bg-primary ms-1" v-if="schedules.length">{{ schedules.length }}</span>
        </a>
      </li>
      <li class="nav-item">
        <a class="nav-link" :class="{ active: activeTab === 'backups' }" href="#"
           @click.prevent="activeTab = 'backups'">
          <i class="bi bi-archive me-1"></i> Backups
          <span class="badge bg-info ms-1" v-if="backups.length">{{ backups.length }}</span>
        </a>
      </li>
      <li class="nav-item">
        <a class="nav-link" :class="{ active: activeTab === 'tasks' }" href="#"
           @click.prevent="activeTab = 'tasks'">
          <i class="bi bi-list-task me-1"></i> Task History
          <span class="badge bg-secondary ms-1" v-if="runningTasks.length">{{ runningTasks.length }} running</span>
        </a>
      </li>
    </ul>

    <!-- SCHEDULES TAB -->
    <div v-show="activeTab === 'schedules'">
      <div class="d-flex justify-content-end mb-3">
        <button class="btn btn-primary" @click="showScheduleModal = true">
          <i class="bi bi-plus-lg me-1"></i> New Schedule
        </button>
      </div>

      <div class="card">
        <div class="table-responsive">
          <table class="table table-hover mb-0">
            <thead>
              <tr>
                <th>Name</th>
                <th>Type</th>
                <th>Schedule</th>
                <th>Next Run</th>
                <th>Last Status</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="schedule in schedules" :key="schedule.id">
                <td>
                  <strong>{{ schedule.name }}</strong>
                  <div class="small text-muted">{{ schedule.description }}</div>
                </td>
                <td><span class="badge bg-info">{{ schedule.task_type }}</span></td>
                <td>
                  <code>{{ schedule.cron_expression || `Every ${schedule.interval_seconds}s` }}</code>
                  <div class="small text-muted" v-if="schedule.cron_expression">
                    {{ getCronDescription(schedule.cron_expression) }}
                  </div>
                </td>
                <td>{{ schedule.next_run ? formatDate(schedule.next_run) : '-' }}</td>
                <td>
                  <span v-if="schedule.last_status" :class="getStatusBadgeClass(schedule.last_status)">
                    {{ schedule.last_status }}
                  </span>
                  <span v-else class="text-muted">Never run</span>
                </td>
                <td>
                  <span :class="schedule.enabled ? 'badge bg-success' : 'badge bg-secondary'">
                    {{ schedule.enabled ? 'Enabled' : 'Disabled' }}
                  </span>
                </td>
                <td>
                  <div class="btn-group btn-group-sm">
                    <button class="btn btn-outline-primary" @click="runScheduleNow(schedule)" title="Run Now">
                      <i class="bi bi-play"></i>
                    </button>
                    <button class="btn btn-outline-secondary" @click="toggleSchedule(schedule)"
                            :title="schedule.enabled ? 'Disable' : 'Enable'">
                      <i :class="schedule.enabled ? 'bi bi-pause' : 'bi bi-play-circle'"></i>
                    </button>
                    <button class="btn btn-outline-secondary" @click="openScheduleEditor(schedule)" title="Edit">
                      <i class="bi bi-pencil"></i>
                    </button>
                    <button class="btn btn-outline-danger" @click="deleteSchedule(schedule)" title="Delete">
                      <i class="bi bi-trash"></i>
                    </button>
                  </div>
                </td>
              </tr>
              <tr v-if="schedules.length === 0">
                <td colspan="7" class="text-center py-4 text-muted">No schedules configured</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- BACKUPS TAB -->
    <div v-show="activeTab === 'backups'">
      <div class="d-flex justify-content-between mb-3">
        <div class="d-flex gap-2">
          <select class="form-select form-select-sm" v-model="backupFilters.type" style="width: auto;">
            <option value="">All Types</option>
            <option value="config">Configuration</option>
            <option value="export">Export</option>
            <option value="cloud">Cloud</option>
          </select>
          <select class="form-select form-select-sm" v-model="backupFilters.routerId" style="width: auto;">
            <option value="">All Routers</option>
            <option v-for="router in routers" :key="router.id" :value="router.id">
              {{ router.identity || router.ip }}
            </option>
          </select>
        </div>
        <button class="btn btn-primary" @click="showBackupModal = true">
          <i class="bi bi-plus-lg me-1"></i> Create Backup
        </button>
      </div>

      <div class="card">
        <div class="table-responsive">
          <table class="table table-hover mb-0">
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
              <tr v-for="backup in filteredBackups" :key="backup.id">
                <td>
                  <div>{{ backup.router_identity || 'Unknown' }}</div>
                  <small class="text-muted">v{{ backup.router_version }}</small>
                </td>
                <td>{{ backup.name }}</td>
                <td><span :class="getBackupTypeBadge(backup.backup_type)">{{ backup.backup_type }}</span></td>
                <td>{{ formatSize(backup.file_size) }}</td>
                <td><span :class="getStatusBadgeClass(backup.status)">{{ backup.status }}</span></td>
                <td>{{ formatDate(backup.created_at) }}</td>
                <td>
                  <div class="btn-group btn-group-sm">
                    <button class="btn btn-outline-primary" @click="downloadBackup(backup)" title="Download"
                            v-if="backup.file_path">
                      <i class="bi bi-download"></i>
                    </button>
                    <button class="btn btn-outline-warning" @click="restoreBackup(backup)" title="Restore">
                      <i class="bi bi-arrow-counterclockwise"></i>
                    </button>
                    <button class="btn btn-outline-danger" @click="deleteBackup(backup)" title="Delete">
                      <i class="bi bi-trash"></i>
                    </button>
                  </div>
                </td>
              </tr>
              <tr v-if="filteredBackups.length === 0">
                <td colspan="7" class="text-center py-4 text-muted">No backups found</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- TASKS TAB -->
    <div v-show="activeTab === 'tasks'">
      <div class="d-flex justify-content-end mb-3">
        <button class="btn btn-outline-secondary" @click="refreshTasks" :disabled="loadingTasks">
          <i class="bi bi-arrow-clockwise" :class="{ spin: loadingTasks }"></i> Refresh
        </button>
      </div>

      <div class="card">
        <div class="table-responsive">
          <table class="table table-hover mb-0">
            <thead>
              <tr>
                <th>Status</th>
                <th>Type</th>
                <th>Progress</th>
                <th>Created</th>
                <th>Duration</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="task in tasks" :key="task.id">
                <td>
                  <span class="badge" :class="getTaskStatusClass(task.status)">
                    <i class="bi me-1" :class="getTaskStatusIcon(task.status)"></i>
                    {{ task.status }}
                  </span>
                </td>
                <td>{{ formatTaskType(task.type) }}</td>
                <td>
                  <div class="d-flex align-items-center">
                    <div class="progress flex-grow-1 me-2" style="height: 8px; width: 100px;">
                      <div class="progress-bar"
                           :class="{ 'progress-bar-animated progress-bar-striped': task.status === 'running' }"
                           :style="{ width: `${getProgressPercent(task)}%` }"></div>
                    </div>
                    <small>{{ task.progress }}/{{ task.total }}</small>
                  </div>
                </td>
                <td><small>{{ formatDate(task.created_at) }}</small></td>
                <td><small>{{ getDuration(task) }}</small></td>
                <td>
                  <div class="btn-group btn-group-sm">
                    <button class="btn btn-outline-primary" @click="viewTask(task)" title="View">
                      <i class="bi bi-eye"></i>
                    </button>
                    <button v-if="task.status === 'running'" class="btn btn-outline-danger"
                            @click="cancelTask(task)" title="Cancel">
                      <i class="bi bi-x-circle"></i>
                    </button>
                    <button v-else class="btn btn-outline-danger" @click="deleteTask(task)" title="Delete">
                      <i class="bi bi-trash"></i>
                    </button>
                  </div>
                </td>
              </tr>
              <tr v-if="tasks.length === 0">
                <td colspan="6" class="text-center py-4 text-muted">
                  <i class="bi bi-inbox fs-1 d-block mb-2"></i>
                  No tasks found
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- Schedule Modal -->
    <div class="modal fade" id="scheduleModal" tabindex="-1" ref="scheduleModalEl">
      <div class="modal-dialog modal-lg">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">{{ editingSchedule ? 'Edit Schedule' : 'Create Schedule' }}</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
          </div>
          <div class="modal-body">
            <div class="row">
              <div class="col-md-6 mb-3">
                <label class="form-label">Name</label>
                <input type="text" class="form-control" v-model="scheduleForm.name" required />
              </div>
              <div class="col-md-6 mb-3">
                <label class="form-label">Task Type</label>
                <select class="form-select" v-model="scheduleForm.task_type">
                  <option value="scan">Full Scan</option>
                  <option value="quick_scan">Quick Scan</option>
                  <option value="update">Update</option>
                  <option value="backup">Backup</option>
                  <option value="health_check">Health Check</option>
                </select>
              </div>
            </div>
            <div class="mb-3">
              <label class="form-label">Cron Expression</label>
              <input type="text" class="form-control" v-model="scheduleForm.cron_expression" placeholder="0 2 * * *" />
              <small class="text-muted">{{ getCronDescription(scheduleForm.cron_expression) }}</small>
            </div>
            <div class="form-check mb-3">
              <input type="checkbox" class="form-check-input" v-model="scheduleForm.enabled" id="schedEnabled" />
              <label class="form-check-label" for="schedEnabled">Enable schedule</label>
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
            <button type="button" class="btn btn-primary" @click="saveSchedule" :disabled="saving">
              <span v-if="saving" class="spinner-border spinner-border-sm me-1"></span>
              Save
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Backup Modal -->
    <div class="modal fade" id="backupModal" tabindex="-1" ref="backupModalEl">
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
              <label class="form-label">Backup Type</label>
              <select class="form-select" v-model="backupForm.backup_type">
                <option value="config">Configuration (binary)</option>
                <option value="export">Export (text)</option>
                <option value="cloud">Cloud Backup</option>
              </select>
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

    <!-- Task Detail Modal -->
    <div class="modal fade" :class="{ show: showTaskDetail }" tabindex="-1"
         :style="{ display: showTaskDetail ? 'block' : 'none' }">
      <div class="modal-dialog modal-lg">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">Task Details</h5>
            <button type="button" class="btn-close" @click="showTaskDetail = false"></button>
          </div>
          <div class="modal-body" v-if="selectedTask">
            <ResultsSummary v-if="selectedTask.results"
              :total="selectedTask.results.total || 0"
              :successful="selectedTask.results.successful || selectedTask.results.online || 0"
              :failed="selectedTask.results.failed || 0"
            />
            <div v-if="selectedTask.results?.results" class="table-responsive mt-3" style="max-height: 300px;">
              <table class="table table-sm">
                <thead>
                  <tr><th>IP</th><th>Status</th><th>Details</th></tr>
                </thead>
                <tbody>
                  <tr v-for="result in selectedTask.results.results" :key="result.ip">
                    <td>{{ result.ip }}</td>
                    <td>
                      <i class="bi" :class="result.success || result.ping_ok ? 'bi-check-circle-fill text-success' : 'bi-x-circle-fill text-danger'"></i>
                    </td>
                    <td><small>{{ result.error || result.status || 'OK' }}</small></td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" @click="showTaskDetail = false">Close</button>
          </div>
        </div>
      </div>
    </div>
    <div class="modal-backdrop fade show" v-if="showTaskDetail"></div>

    <!-- Confirm Modal -->
    <ConfirmModal
      :visible="showConfirm"
      :title="confirmTitle"
      :message="confirmMessage"
      :variant="confirmVariant"
      :loading="confirmLoading"
      @confirm="confirmPendingAction"
      @cancel="handleCancel"
    />
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { useMainStore } from '../stores/main'
import { useSchedulesStore } from '../stores/schedules'
import { backupsApi, routerApi, taskApi } from '../services/api'
import { formatDate, formatSize, formatDuration } from '../utils/formatters'
import { getStatusBadgeClass, getBackupTypeBadge } from '../utils/badges'
import ConfirmModal from './ConfirmModal.vue'
import ResultsSummary from './shared/ResultsSummary.vue'
import { useAutomationSchedules } from '../composables/useAutomationSchedules'
import { useAutomationBackups } from '../composables/useAutomationBackups'
import { useAutomationTasks } from '../composables/useAutomationTasks'
import { useModalManager } from '../composables/useModalManager'
import { useConfirmation } from '../composables/useConfirmation'

const store = useMainStore()
const schedulesStore = useSchedulesStore()
const { registerModal, showModal, hideModal } = useModalManager()
const {
  showConfirm,
  confirmTitle,
  confirmMessage,
  confirmVariant,
  confirmLoading,
  handleConfirm,
  handleCancel
} = useConfirmation()

// State
const activeTab = ref('schedules')
const saving = ref(false)
const pendingAction = ref(null)

// Modals
const scheduleModalEl = ref(null)
const backupModalEl = ref(null)

const schedulesManager = useAutomationSchedules({ schedulesStore })

const {
  schedules,
  showScheduleModal,
  editingSchedule,
  scheduleForm,
  getCronDescription,
  resetScheduleForm,
  editSchedule,
  saveSchedule: persistSchedule,
  toggleSchedule
} = schedulesManager

const backupsManager = useAutomationBackups({
  backupsApi,
  routerApi,
  store
})

const {
  backups,
  routers,
  showBackupModal,
  backupFilters,
  backupForm,
  filteredBackups,
  loadBackups,
  loadRouters,
  resetBackupForm,
  createBackup: runCreateBackup,
  downloadBackup,
  restoreBackup: runRestoreBackup,
  removeBackup
} = backupsManager

const tasksManager = useAutomationTasks({
  store,
  taskApi
})

const {
  loadingTasks,
  tasks,
  runningTasks,
  showTaskDetail,
  selectedTask,
  refreshTasks,
  viewTask,
  cancelTask,
  deleteTask: removeTask,
  getTaskStatusClass,
  getTaskStatusIcon,
  formatTaskType,
  getProgressPercent,
  getDuration
} = tasksManager

// Lifecycle
onMounted(async () => {
  registerModal('schedule', scheduleModalEl)
  registerModal('backup', backupModalEl)

  await Promise.all([
    schedulesStore.fetchSchedules(),
    loadBackups(),
    loadRouters(),
    store.fetchTasks()
  ])
})

watch(showScheduleModal, (val) => { if (val) { resetScheduleForm(); showModal('schedule') } })
watch(showBackupModal, (val) => { if (val) { resetBackupForm(); showModal('backup') } })

function openScheduleEditor(schedule) {
  editSchedule(schedule, () => showModal('schedule'))
}

async function saveSchedule() {
  saving.value = true
  try {
    await persistSchedule()
    hideModal('schedule')
  } finally {
    saving.value = false
  }
}

function runScheduleNow(schedule) {
  confirmTitle.value = 'Run Schedule'
  confirmMessage.value = `Run "${schedule.name}" now?`
  confirmVariant.value = 'primary'
  pendingAction.value = () => schedulesStore.runNow(schedule.id)
  showConfirm.value = true
}

function deleteSchedule(schedule) {
  confirmTitle.value = 'Delete Schedule'
  confirmMessage.value = `Delete "${schedule.name}"?`
  confirmVariant.value = 'danger'
  pendingAction.value = () => schedulesStore.deleteSchedule(schedule.id)
  showConfirm.value = true
}


async function createBackup() {
  saving.value = true
  try {
    await runCreateBackup()
    hideModal('backup')
  } finally {
    saving.value = false
  }
}

function restoreBackup(backup) {
  confirmTitle.value = 'Restore Backup'
  confirmMessage.value = `Restore "${backup.name}"? Router will reboot.`
  confirmVariant.value = 'warning'
  pendingAction.value = async () => {
    await runRestoreBackup(backup)
  }
  showConfirm.value = true
}

function deleteBackup(backup) {
  confirmTitle.value = 'Delete Backup'
  confirmMessage.value = `Delete "${backup.name}"?`
  confirmVariant.value = 'danger'
  pendingAction.value = async () => {
    await removeBackup(backup)
  }
  showConfirm.value = true
}

function deleteTask(task) {
  confirmTitle.value = 'Delete Task'
  confirmMessage.value = 'Delete this task?'
  confirmVariant.value = 'danger'
  pendingAction.value = async () => {
    await removeTask(task)
  }
  showConfirm.value = true
}

// Confirmation handler
async function confirmPendingAction() {
  if (!pendingAction.value) return
  await handleConfirm(async () => {
    await pendingAction.value()
    pendingAction.value = null
  })
}
</script>

<style scoped>
.nav-tabs .nav-link { color: var(--text-secondary); }
.nav-tabs .nav-link.active { font-weight: 600; }
</style>
