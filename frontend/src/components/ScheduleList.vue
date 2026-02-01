<template>
  <div class="container-fluid py-4">
    <div class="d-flex justify-content-between align-items-center mb-4">
      <h2><i class="bi bi-calendar-check me-2"></i>Schedules</h2>
      <button class="btn btn-primary" @click="showCreateModal = true">
        <i class="bi bi-plus-lg me-1"></i> New Schedule
      </button>
    </div>

    <!-- Schedules Table -->
    <div class="card">
      <div class="card-body">
        <div class="table-responsive">
          <table class="table table-hover">
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
                <td>
                  <span class="badge bg-info">{{ schedule.task_type }}</span>
                </td>
                <td>
                  <code>{{ schedule.cron_expression || `Every ${schedule.interval_seconds}s` }}</code>
                  <div class="small text-muted" v-if="schedule.cron_expression">
                    {{ getCronDescription(schedule.cron_expression) }}
                  </div>
                </td>
                <td>
                  <span v-if="schedule.next_run">{{ formatDateTime(schedule.next_run) }}</span>
                  <span v-else class="text-muted">-</span>
                </td>
                <td>
                  <span v-if="schedule.last_status" :class="statusClass(schedule.last_status)">
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
                    <button class="btn btn-outline-primary" @click="runNow(schedule)"
                            title="Run Now">
                      <i class="bi bi-play"></i>
                    </button>
                    <button class="btn btn-outline-secondary" @click="toggleSchedule(schedule)"
                            :title="schedule.enabled ? 'Disable' : 'Enable'">
                      <i :class="schedule.enabled ? 'bi bi-pause' : 'bi bi-play-circle'"></i>
                    </button>
                    <button class="btn btn-outline-secondary" @click="editSchedule(schedule)"
                            title="Edit">
                      <i class="bi bi-pencil"></i>
                    </button>
                    <button class="btn btn-outline-info" @click="viewHistory(schedule)"
                            title="History">
                      <i class="bi bi-clock-history"></i>
                    </button>
                    <button class="btn btn-outline-danger" @click="confirmDelete(schedule)"
                            title="Delete">
                      <i class="bi bi-trash"></i>
                    </button>
                  </div>
                </td>
              </tr>
              <tr v-if="schedules.length === 0 && !loading">
                <td colspan="7" class="text-center py-4 text-muted">
                  No schedules configured
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- Create/Edit Modal -->
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
              <label class="form-label">Description</label>
              <textarea class="form-control" v-model="scheduleForm.description" rows="2"></textarea>
            </div>

            <div class="row">
              <div class="col-md-6 mb-3">
                <label class="form-label">Schedule Type</label>
                <select class="form-select" v-model="scheduleType">
                  <option value="cron">Cron Expression</option>
                  <option value="interval">Interval</option>
                </select>
              </div>
              <div class="col-md-6 mb-3">
                <label class="form-label" v-if="scheduleType === 'cron'">Cron Expression</label>
                <label class="form-label" v-else>Interval (seconds)</label>
                <input v-if="scheduleType === 'cron'" type="text" class="form-control"
                       v-model="scheduleForm.cron_expression" placeholder="0 2 * * *" />
                <input v-else type="number" class="form-control"
                       v-model.number="scheduleForm.interval_seconds" min="60" />
              </div>
            </div>

            <div v-if="cronPreview" class="alert alert-info py-2 mb-3">
              <i class="bi bi-info-circle me-2"></i>{{ cronPreview }}
            </div>

            <div class="row">
              <div class="col-md-6 mb-3">
                <label class="form-label">Target</label>
                <select class="form-select" v-model="scheduleForm.target_type">
                  <option value="all">All Routers</option>
                  <option value="group">Specific Groups</option>
                  <option value="specific">Specific Routers</option>
                </select>
              </div>
              <div class="col-md-6 mb-3">
                <label class="form-label">Timezone</label>
                <select class="form-select" v-model="scheduleForm.timezone">
                  <option value="UTC">UTC</option>
                  <option value="Europe/Warsaw">Europe/Warsaw</option>
                  <option value="America/New_York">America/New_York</option>
                </select>
              </div>
            </div>

            <div class="form-check mb-3">
              <input type="checkbox" class="form-check-input" v-model="scheduleForm.enabled" id="enabled" />
              <label class="form-check-label" for="enabled">Enable schedule</label>
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
            <button type="button" class="btn btn-primary" @click="saveSchedule" :disabled="saving">
              <span v-if="saving" class="spinner-border spinner-border-sm me-1"></span>
              {{ saving ? 'Saving...' : 'Save' }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- History Modal -->
    <div class="modal fade" id="historyModal" tabindex="-1" ref="historyModalEl">
      <div class="modal-dialog modal-lg">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">Execution History - {{ selectedSchedule?.name }}</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
          </div>
          <div class="modal-body">
            <div class="table-responsive">
              <table class="table table-sm">
                <thead>
                  <tr>
                    <th>Started</th>
                    <th>Duration</th>
                    <th>Status</th>
                    <th>Routers</th>
                    <th>Trigger</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="exec in executions" :key="exec.id">
                    <td>{{ formatDateTime(exec.started_at) }}</td>
                    <td>{{ exec.duration_seconds ? `${exec.duration_seconds}s` : '-' }}</td>
                    <td>
                      <span :class="statusClass(exec.status)">{{ exec.status }}</span>
                    </td>
                    <td>
                      <span class="text-success">{{ exec.routers_success }}</span> /
                      <span class="text-danger">{{ exec.routers_failed }}</span>
                    </td>
                    <td>{{ exec.trigger_type }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Confirm Modal -->
    <ConfirmModal
      :visible="showConfirmModal"
      :title="confirmModalTitle"
      :message="confirmModalMessage"
      :variant="confirmModalVariant"
      :confirmText="confirmModalAction"
      :loading="confirmLoading"
      @confirm="handleConfirmAction"
      @cancel="showConfirmModal = false"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick, watch } from 'vue'
import { Modal } from 'bootstrap'
import { useSchedulesStore } from '../stores/schedules'
import cronstrue from 'cronstrue'
import ConfirmModal from './ConfirmModal.vue'

const schedulesStore = useSchedulesStore()

const schedules = computed(() => schedulesStore.schedules)
const loading = computed(() => schedulesStore.loading)
const executions = computed(() => schedulesStore.executions)

const showCreateModal = ref(false)
const editingSchedule = ref(null)
const selectedSchedule = ref(null)
const saving = ref(false)
const scheduleType = ref('cron')

const scheduleForm = ref({
  name: '',
  description: '',
  task_type: 'scan',
  cron_expression: '0 2 * * *',
  interval_seconds: null,
  timezone: 'UTC',
  target_type: 'all',
  target_ids: [],
  enabled: true
})

const scheduleModalEl = ref(null)
const historyModalEl = ref(null)
let scheduleModal = null
let historyModal = null

// Confirm modal state
const showConfirmModal = ref(false)
const confirmModalTitle = ref('')
const confirmModalMessage = ref('')
const confirmModalVariant = ref('danger')
const confirmModalAction = ref('Confirm')
const confirmLoading = ref(false)
const pendingAction = ref(null)
const pendingSchedule = ref(null)

const cronPreview = computed(() => {
  if (scheduleType.value !== 'cron' || !scheduleForm.value.cron_expression) return null
  try {
    return cronstrue.toString(scheduleForm.value.cron_expression)
  } catch {
    return 'Invalid cron expression'
  }
})

onMounted(async () => {
  await schedulesStore.fetchSchedules()

  nextTick(() => {
    if (scheduleModalEl.value) {
      scheduleModal = new Modal(scheduleModalEl.value)
    }
    if (historyModalEl.value) {
      historyModal = new Modal(historyModalEl.value)
    }
  })
})

watch(showCreateModal, (val) => {
  if (val) {
    resetForm()
    scheduleModal?.show()
  }
})

function editSchedule(schedule) {
  editingSchedule.value = schedule
  scheduleForm.value = { ...schedule }
  scheduleType.value = schedule.cron_expression ? 'cron' : 'interval'
  scheduleModal?.show()
}

async function viewHistory(schedule) {
  selectedSchedule.value = schedule
  await schedulesStore.fetchExecutions(schedule.id)
  historyModal?.show()
}

async function saveSchedule() {
  saving.value = true
  try {
    const data = { ...scheduleForm.value }
    if (scheduleType.value === 'interval') {
      data.cron_expression = null
    } else {
      data.interval_seconds = null
    }

    if (editingSchedule.value) {
      await schedulesStore.updateSchedule(editingSchedule.value.id, data)
    } else {
      await schedulesStore.createSchedule(data)
    }
    scheduleModal?.hide()
    resetForm()
  } catch (error) {
    console.error('Failed to save schedule:', error)
  } finally {
    saving.value = false
  }
}

async function toggleSchedule(schedule) {
  try {
    if (schedule.enabled) {
      await schedulesStore.disableSchedule(schedule.id)
    } else {
      await schedulesStore.enableSchedule(schedule.id)
    }
  } catch (error) {
    console.error('Failed to toggle schedule:', error)
  }
}

function runNow(schedule) {
  pendingSchedule.value = schedule
  pendingAction.value = 'run'
  confirmModalTitle.value = 'Run Schedule Now'
  confirmModalMessage.value = `Are you sure you want to run "${schedule.name}" immediately?`
  confirmModalVariant.value = 'primary'
  confirmModalAction.value = 'Run Now'
  showConfirmModal.value = true
}

function confirmDelete(schedule) {
  pendingSchedule.value = schedule
  pendingAction.value = 'delete'
  confirmModalTitle.value = 'Delete Schedule'
  confirmModalMessage.value = `Are you sure you want to delete "${schedule.name}"? This action cannot be undone.`
  confirmModalVariant.value = 'danger'
  confirmModalAction.value = 'Delete'
  showConfirmModal.value = true
}

async function handleConfirmAction() {
  confirmLoading.value = true
  try {
    if (pendingAction.value === 'run' && pendingSchedule.value) {
      await schedulesStore.runNow(pendingSchedule.value.id)
    } else if (pendingAction.value === 'delete' && pendingSchedule.value) {
      await schedulesStore.deleteSchedule(pendingSchedule.value.id)
    }
  } catch (error) {
    console.error(`Failed to ${pendingAction.value} schedule:`, error)
  } finally {
    confirmLoading.value = false
    showConfirmModal.value = false
    pendingAction.value = null
    pendingSchedule.value = null
  }
}

function resetForm() {
  editingSchedule.value = null
  scheduleType.value = 'cron'
  scheduleForm.value = {
    name: '',
    description: '',
    task_type: 'scan',
    cron_expression: '0 2 * * *',
    interval_seconds: null,
    timezone: 'UTC',
    target_type: 'all',
    target_ids: [],
    enabled: true
  }
}

function getCronDescription(cron) {
  try {
    return cronstrue.toString(cron)
  } catch {
    return ''
  }
}

function formatDateTime(dateStr) {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleString()
}

function statusClass(status) {
  const classes = {
    success: 'badge bg-success',
    completed: 'badge bg-success',
    running: 'badge bg-primary',
    failed: 'badge bg-danger',
    pending: 'badge bg-warning'
  }
  return classes[status] || 'badge bg-secondary'
}
</script>
