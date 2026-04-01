import { ref } from 'vue'

export function useRouterCrud({ store }) {
  const showAddModal = ref(false)
  const showEditModal = ref(false)
  const editingRouter = ref(null)
  const formData = ref({
    ip: '',
    port: 8728,
    username: '',
    password: ''
  })

  const showDeleteConfirm = ref(false)
  const deleteConfirmMessage = ref('')
  const deleteTarget = ref(null)
  const deleteMode = ref('single')
  const deleting = ref(false)

  function resetForm() {
    formData.value = {
      ip: '',
      port: 8728,
      username: '',
      password: ''
    }
  }

  function openAddModal() {
    editingRouter.value = null
    resetForm()
    showAddModal.value = true
  }

  function editRouter(router) {
    editingRouter.value = router
    formData.value = {
      ip: router.ip,
      port: router.port,
      username: router.username || '',
      password: ''
    }
    showEditModal.value = true
  }

  function promptDeleteRouter(router) {
    deleteTarget.value = router
    deleteMode.value = 'single'
    deleteConfirmMessage.value = `Are you sure you want to delete router ${router.ip}? This action cannot be undone.`
    showDeleteConfirm.value = true
  }

  function promptDeleteSelected(selectedCount) {
    deleteTarget.value = null
    deleteMode.value = 'multiple'
    deleteConfirmMessage.value = `Are you sure you want to delete ${selectedCount} routers? This action cannot be undone.`
    showDeleteConfirm.value = true
  }

  async function confirmDeleteAction() {
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

  function closeModal() {
    showAddModal.value = false
    showEditModal.value = false
    editingRouter.value = null
    resetForm()
  }

  async function saveRouter() {
    if (showEditModal.value) {
      await store.updateRouter(editingRouter.value.id, formData.value)
    } else {
      await store.createRouter(formData.value)
    }
    closeModal()
  }

  return {
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
  }
}
