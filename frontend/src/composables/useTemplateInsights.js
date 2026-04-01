import { ref } from 'vue'

export function useTemplateInsights({ templatesApi, notify }) {
  const previewRouterId = ref(null)
  const previewVariables = ref({})
  const previewResult = ref('')
  const previewError = ref('')
  const previewLoading = ref(false)

  const showHistoryModal = ref(false)
  const deploymentHistory = ref([])
  const loadingHistory = ref(false)
  const selectedDeployDetail = ref(null)

  async function previewTemplate(templateId, showPreviewModal) {
    if (!templateId) {
      notify('warning', 'Save the template first to preview')
      return
    }

    previewLoading.value = true
    previewError.value = ''
    previewResult.value = ''

    try {
      const response = await templatesApi.preview(templateId, {
        router_id: previewRouterId.value,
        variables: previewVariables.value
      })
      previewResult.value = response.rendered
      showPreviewModal?.()
    } catch (error) {
      previewError.value = error.message
      showPreviewModal?.()
    } finally {
      previewLoading.value = false
    }
  }

  async function showDeployments(templateId) {
    if (!templateId) return

    loadingHistory.value = true
    deploymentHistory.value = []
    selectedDeployDetail.value = null

    try {
      const response = await templatesApi.listDeployments({ template_id: templateId })
      deploymentHistory.value = response.items || []
      showHistoryModal.value = true
    } catch (error) {
      console.error('Failed to load deployment history:', error)
      notify('error', 'Failed to load history')
    } finally {
      loadingHistory.value = false
    }
  }

  function showDeployDetails(deploy) {
    selectedDeployDetail.value = deploy.rendered_content
  }

  function getDeployStatusBadge(status) {
    switch (status) {
      case 'completed': return 'badge bg-success'
      case 'failed': return 'badge bg-danger'
      case 'running': return 'badge bg-primary'
      case 'pending': return 'badge bg-warning'
      default: return 'badge bg-secondary'
    }
  }

  function formatDate(dateStr) {
    if (!dateStr) return ''
    return new Date(dateStr).toLocaleString()
  }

  return {
    previewRouterId,
    previewVariables,
    previewResult,
    previewError,
    previewLoading,
    showHistoryModal,
    deploymentHistory,
    loadingHistory,
    selectedDeployDetail,
    previewTemplate,
    showDeployments,
    showDeployDetails,
    getDeployStatusBadge,
    formatDate
  }
}
