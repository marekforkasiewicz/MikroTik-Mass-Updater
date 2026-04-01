import { computed, ref } from 'vue'
import { formatDuration } from '../utils/formatters'

export function useAutomationTasks({ store, taskApi }) {
  const loadingTasks = ref(false)
  const showTaskDetail = ref(false)
  const selectedTask = ref(null)

  const tasks = computed(() => store.tasks)
  const runningTasks = computed(() => tasks.value.filter((task) => task.status === 'running'))

  async function refreshTasks() {
    loadingTasks.value = true
    try {
      await store.fetchTasks()
    } finally {
      loadingTasks.value = false
    }
  }

  async function viewTask(task) {
    try {
      selectedTask.value = await taskApi.get(task.id)
      showTaskDetail.value = true
    } catch (error) {
      store.addNotification('error', 'Failed to load task')
    }
  }

  function cancelTask(task) {
    store.cancelTask(task.id)
  }

  async function deleteTask(task) {
    await taskApi.delete(task.id)
    await store.fetchTasks()
  }

  function getTaskStatusClass(status) {
    const classes = {
      pending: 'bg-secondary',
      running: 'bg-primary',
      completed: 'bg-success',
      failed: 'bg-danger',
      cancelled: 'bg-warning text-dark'
    }
    return classes[status] || 'bg-secondary'
  }

  function getTaskStatusIcon(status) {
    const icons = {
      pending: 'bi-hourglass',
      running: 'bi-gear spin',
      completed: 'bi-check-circle',
      failed: 'bi-x-circle',
      cancelled: 'bi-slash-circle'
    }
    return icons[status] || 'bi-question-circle'
  }

  function formatTaskType(type) {
    const labels = {
      scan: 'Full Scan',
      quick_scan: 'Quick Scan',
      update: 'Update',
      backup: 'Backup',
      firmware_upgrade: 'Firmware Upgrade'
    }
    return labels[type] || type
  }

  function getProgressPercent(task) {
    if (!task.total) return 0
    return Math.round((task.progress / task.total) * 100)
  }

  function getDuration(task) {
    if (!task.started_at) return '-'
    const start = new Date(task.started_at)
    const end = task.completed_at ? new Date(task.completed_at) : new Date()
    return formatDuration(Math.round((end - start) / 1000))
  }

  return {
    loadingTasks,
    showTaskDetail,
    selectedTask,
    tasks,
    runningTasks,
    refreshTasks,
    viewTask,
    cancelTask,
    deleteTask,
    getTaskStatusClass,
    getTaskStatusIcon,
    formatTaskType,
    getProgressPercent,
    getDuration
  }
}
