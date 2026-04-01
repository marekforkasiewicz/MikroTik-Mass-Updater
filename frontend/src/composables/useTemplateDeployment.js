import { computed, onUnmounted, ref } from 'vue'

export function useTemplateDeployment({ templatesApi, taskApi, createTaskWebSocket, notify }) {
  const deploying = ref(false)
  const deployForm = ref({
    router_ids: [],
    variables: {},
    dry_run: false,
    backup_before: true
  })
  const deployResults = ref([])
  const selectedRendered = ref(null)
  const deployTaskId = ref(null)
  const deployTaskStatus = ref(null)
  const deployProgress = ref({ current: 0, total: 0, currentItem: '', message: '' })

  let deployWebSocket = null
  let pollInterval = null

  const deployProgressPercent = computed(() => {
    if (deployProgress.value.total === 0) return 0
    return Math.round((deployProgress.value.current / deployProgress.value.total) * 100)
  })

  function cleanupDeploymentTracking() {
    if (deployWebSocket) {
      deployWebSocket.close()
      deployWebSocket = null
    }
    if (pollInterval) {
      clearInterval(pollInterval)
      pollInterval = null
    }
  }

  function resetDeployModal() {
    deployResults.value = []
    selectedRendered.value = null
    deployTaskId.value = null
    deployTaskStatus.value = null
    deployProgress.value = { current: 0, total: 0, currentItem: '', message: '' }
    cleanupDeploymentTracking()
  }

  function selectAllRouters(routers) {
    deployForm.value.router_ids = routers.map((router) => router.id)
  }

  function selectOnlineRouters(routers) {
    deployForm.value.router_ids = routers.filter((router) => router.is_online).map((router) => router.id)
  }

  async function loadTaskResults(taskId) {
    try {
      const task = await taskApi.get(taskId)
      if (task.results?.routers) {
        deployResults.value = task.results.routers
      }

      const succeeded = deployResults.value.filter((result) => result.status === 'completed').length
      const failed = deployResults.value.filter((result) => result.status === 'failed').length

      if (task.status === 'completed' && failed === 0) {
        notify('success', `Deployed to ${succeeded} router(s)`)
      } else if (task.status === 'completed') {
        notify('warning', `Deployed to ${succeeded} router(s), ${failed} failed`)
      } else if (task.status === 'failed') {
        notify('error', `Deployment failed: ${task.error || 'Unknown error'}`)
      }
    } catch (error) {
      console.error('Failed to load task results:', error)
    }
  }

  function startTaskPolling(taskId) {
    cleanupDeploymentTracking()

    pollInterval = setInterval(async () => {
      try {
        const task = await taskApi.get(taskId)

        deployProgress.value.current = task.progress || 0
        deployProgress.value.total = task.total || 0
        deployProgress.value.currentItem = task.current_item || ''
        deployProgress.value.message = task.current_message || ''
        deployTaskStatus.value = task.status

        if (task.status === 'completed' || task.status === 'failed') {
          cleanupDeploymentTracking()
          deploying.value = false
          loadTaskResults(taskId)
        }
      } catch (error) {
        console.error('Polling error:', error)
        cleanupDeploymentTracking()
        deploying.value = false
      }
    }, 2000)
  }

  function connectToDeployWebSocket(taskId) {
    cleanupDeploymentTracking()

    deployWebSocket = createTaskWebSocket(
      taskId,
      (data) => {
        if (data.progress !== undefined) {
          deployProgress.value.current = data.progress
        }
        if (data.total !== undefined) {
          deployProgress.value.total = data.total
        }
        if (data.current_item) {
          deployProgress.value.currentItem = data.current_item
        }
        if (data.current_message) {
          deployProgress.value.message = data.current_message
        }
        if (data.status) {
          deployTaskStatus.value = data.status
        }
        if (data.results) {
          deployResults.value = data.results.routers || []
        }
        if (data.status === 'completed' || data.status === 'failed') {
          deploying.value = false
          cleanupDeploymentTracking()
          loadTaskResults(taskId)
        }
      },
      (error) => {
        console.error('WebSocket error:', error)
        startTaskPolling(taskId)
      }
    )
  }

  async function deployTemplate(templateId) {
    if (deployForm.value.router_ids.length === 0) {
      notify('warning', 'Please select at least one router')
      return
    }

    deploying.value = true
    deployResults.value = []
    deployTaskId.value = null
    deployTaskStatus.value = null
    deployProgress.value = { current: 0, total: 0, currentItem: '', message: '' }

    try {
      const response = await templatesApi.deploy(templateId, {
        router_ids: deployForm.value.router_ids,
        variables: deployForm.value.variables,
        dry_run: deployForm.value.dry_run,
        backup_before: deployForm.value.backup_before
      })

      if (deployForm.value.dry_run) {
        deployResults.value = response.results || []
        deploying.value = false
        const succeeded = deployResults.value.filter((result) => result.status === 'dry_run').length
        notify('success', `Preview generated for ${succeeded} router(s)`)
        return
      }

      if (response.task_id) {
        deployTaskId.value = response.task_id
        deployTaskStatus.value = 'running'
        deployProgress.value.total = response.total_routers
        deployResults.value = response.results || []
        connectToDeployWebSocket(response.task_id)
      } else {
        deployResults.value = response.results || []
        deploying.value = false
      }
    } catch (error) {
      console.error('Failed to deploy template:', error)
      notify('error', `Deployment failed: ${error.message}`)
      deploying.value = false
    }
  }

  async function cancelDeployment() {
    if (!deployTaskId.value) return

    try {
      await taskApi.cancel(deployTaskId.value)
      notify('info', 'Deployment cancelled')
      deploying.value = false
      deployTaskStatus.value = 'cancelled'
      cleanupDeploymentTracking()
    } catch (error) {
      console.error('Failed to cancel deployment:', error)
      notify('error', 'Failed to cancel deployment')
    }
  }

  function showRenderedContent(result) {
    selectedRendered.value = {
      router: result.router_identity || result.router_ip,
      content: result.rendered_content
    }
  }

  function getStatusBadgeClass(status) {
    switch (status) {
      case 'completed': return 'badge bg-success'
      case 'dry_run': return 'badge bg-info'
      case 'failed': return 'badge bg-danger'
      case 'pending': return 'badge bg-warning'
      default: return 'badge bg-secondary'
    }
  }

  onUnmounted(() => {
    cleanupDeploymentTracking()
  })

  return {
    deploying,
    deployForm,
    deployResults,
    selectedRendered,
    deployTaskId,
    deployTaskStatus,
    deployProgress,
    deployProgressPercent,
    selectAllRouters,
    selectOnlineRouters,
    resetDeployModal,
    deployTemplate,
    cancelDeployment,
    showRenderedContent,
    getStatusBadgeClass
  }
}
