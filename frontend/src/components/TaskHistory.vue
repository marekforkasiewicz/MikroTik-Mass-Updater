<template>
  <div>
    <div class="d-flex justify-content-between align-items-center mb-4">
      <h2>Task History</h2>
      <button class="btn btn-outline-secondary" @click="refreshTasks" :disabled="loading">
        <i class="bi bi-arrow-clockwise" :class="{ 'spin': loading }"></i>
        Refresh
      </button>
    </div>

    <!-- Task list -->
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
                <span class="badge" :class="getStatusBadgeClass(task.status)">
                  <i class="bi me-1" :class="getStatusIcon(task.status)"></i>
                  {{ task.status }}
                </span>
              </td>
              <td>{{ formatTaskType(task.type) }}</td>
              <td>
                <div class="d-flex align-items-center">
                  <div class="progress flex-grow-1 me-2" style="height: 8px; width: 100px;">
                    <div
                      class="progress-bar"
                      :class="{ 'progress-bar-animated progress-bar-striped': task.status === 'running' }"
                      :style="{ width: `${getProgressPercent(task)}%` }"
                    ></div>
                  </div>
                  <small>{{ task.progress }}/{{ task.total }}</small>
                </div>
              </td>
              <td>
                <small>{{ formatDate(task.created_at) }}</small>
              </td>
              <td>
                <small>{{ getDuration(task) }}</small>
              </td>
              <td>
                <div class="btn-group btn-group-sm">
                  <button
                    class="btn btn-outline-primary"
                    @click="viewTask(task)"
                    title="View Details"
                  >
                    <i class="bi bi-eye"></i>
                  </button>
                  <button
                    v-if="task.status === 'running'"
                    class="btn btn-outline-danger"
                    @click="cancelTask(task)"
                    title="Cancel"
                  >
                    <i class="bi bi-x-circle"></i>
                  </button>
                  <button
                    v-else
                    class="btn btn-outline-danger"
                    @click="deleteTask(task)"
                    title="Delete"
                  >
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

    <!-- Task details modal -->
    <div class="modal fade" :class="{ show: showDetails }" tabindex="-1"
         :style="{ display: showDetails ? 'block' : 'none' }">
      <div class="modal-dialog modal-lg">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">Task Details</h5>
            <button type="button" class="btn-close" @click="showDetails = false"></button>
          </div>
          <div class="modal-body" v-if="selectedTask">
            <div class="row mb-3">
              <div class="col-md-6">
                <strong>Type:</strong> {{ formatTaskType(selectedTask.type) }}
              </div>
              <div class="col-md-6">
                <strong>Status:</strong>
                <span class="badge ms-2" :class="getStatusBadgeClass(selectedTask.status)">
                  {{ selectedTask.status }}
                </span>
              </div>
            </div>

            <div class="row mb-3">
              <div class="col-md-6">
                <strong>Progress:</strong> {{ selectedTask.progress }}/{{ selectedTask.total }}
              </div>
              <div class="col-md-6">
                <strong>Duration:</strong> {{ getDuration(selectedTask) }}
              </div>
            </div>

            <div v-if="selectedTask.error" class="alert alert-danger">
              <strong>Error:</strong> {{ selectedTask.error }}
            </div>

            <div v-if="selectedTask.results">
              <h6>Results Summary</h6>
              <div class="row text-center mb-3">
                <div class="col">
                  <div class="fs-4 text-primary">{{ selectedTask.results.total || 0 }}</div>
                  <small>Total</small>
                </div>
                <div class="col">
                  <div class="fs-4 text-success">{{ selectedTask.results.successful || selectedTask.results.online || 0 }}</div>
                  <small>Successful</small>
                </div>
                <div class="col">
                  <div class="fs-4 text-danger">{{ selectedTask.results.failed || 0 }}</div>
                  <small>Failed</small>
                </div>
              </div>

              <div v-if="selectedTask.results.results" class="table-responsive" style="max-height: 300px;">
                <table class="table table-sm">
                  <thead>
                    <tr>
                      <th>IP</th>
                      <th>Status</th>
                      <th>Details</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="result in selectedTask.results.results" :key="result.ip">
                      <td>{{ result.ip }}</td>
                      <td>
                        <i
                          class="bi"
                          :class="{
                            'bi-check-circle-fill text-success': result.success || result.ping_ok,
                            'bi-x-circle-fill text-danger': !(result.success || result.ping_ok)
                          }"
                        ></i>
                      </td>
                      <td>
                        <small>{{ result.error || result.status || 'OK' }}</small>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" @click="showDetails = false">Close</button>
          </div>
        </div>
      </div>
    </div>
    <div class="modal-backdrop fade show" v-if="showDetails"></div>

    <!-- Confirm Delete Modal -->
    <ConfirmModal
      :visible="showDeleteConfirm"
      title="Delete Task"
      message="Are you sure you want to delete this task? This action cannot be undone."
      variant="danger"
      confirmText="Delete"
      :loading="deleting"
      @confirm="handleDeleteConfirm"
      @cancel="showDeleteConfirm = false"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useMainStore } from '../stores/main'
import { taskApi } from '../services/api'
import ConfirmModal from './ConfirmModal.vue'

const store = useMainStore()

const loading = ref(false)
const showDetails = ref(false)
const selectedTask = ref(null)

// Delete confirmation state
const showDeleteConfirm = ref(false)
const taskToDelete = ref(null)
const deleting = ref(false)

const tasks = computed(() => store.tasks)

const refreshTasks = async () => {
  loading.value = true
  try {
    await store.fetchTasks()
  } finally {
    loading.value = false
  }
}

const viewTask = async (task) => {
  try {
    selectedTask.value = await taskApi.get(task.id)
    showDetails.value = true
  } catch (error) {
    store.addNotification('error', `Failed to load task details: ${error.message}`)
  }
}

const cancelTask = async (task) => {
  await store.cancelTask(task.id)
}

const deleteTask = (task) => {
  taskToDelete.value = task
  showDeleteConfirm.value = true
}

const handleDeleteConfirm = async () => {
  if (!taskToDelete.value) return
  deleting.value = true
  try {
    await taskApi.delete(taskToDelete.value.id)
    await store.fetchTasks()
    store.addNotification('success', 'Task deleted')
  } catch (error) {
    store.addNotification('error', `Failed to delete task: ${error.message}`)
  } finally {
    deleting.value = false
    showDeleteConfirm.value = false
    taskToDelete.value = null
  }
}

const getStatusBadgeClass = (status) => {
  const classes = {
    pending: 'bg-secondary',
    running: 'bg-primary',
    completed: 'bg-success',
    failed: 'bg-danger',
    cancelled: 'bg-warning text-dark'
  }
  return classes[status] || 'bg-secondary'
}

const getStatusIcon = (status) => {
  const icons = {
    pending: 'bi-hourglass',
    running: 'bi-gear spin',
    completed: 'bi-check-circle',
    failed: 'bi-x-circle',
    cancelled: 'bi-slash-circle'
  }
  return icons[status] || 'bi-question-circle'
}

const formatTaskType = (type) => {
  const types = {
    scan: 'Full Scan',
    quick_scan: 'Quick Scan',
    update: 'Update',
    backup: 'Backup',
    firmware_upgrade: 'Firmware Upgrade'
  }
  return types[type] || type
}

const getProgressPercent = (task) => {
  if (!task.total) return 0
  return Math.round((task.progress / task.total) * 100)
}

const formatDate = (dateStr) => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString()
}

const getDuration = (task) => {
  if (!task.started_at) return '-'
  const start = new Date(task.started_at)
  const end = task.completed_at ? new Date(task.completed_at) : new Date()
  const diff = Math.round((end - start) / 1000)

  if (diff < 60) return `${diff}s`
  if (diff < 3600) return `${Math.floor(diff / 60)}m ${diff % 60}s`
  return `${Math.floor(diff / 3600)}h ${Math.floor((diff % 3600) / 60)}m`
}

onMounted(() => {
  refreshTasks()
})
</script>
