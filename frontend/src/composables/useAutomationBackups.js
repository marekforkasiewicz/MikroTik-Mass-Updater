import { computed, ref } from 'vue'

export function useAutomationBackups({ backupsApi, routerApi, store }) {
  const backups = ref([])
  const routers = ref([])
  const showBackupModal = ref(false)
  const backupFilters = ref({ type: '', routerId: '' })
  const backupForm = ref({ router_id: '', backup_type: 'config' })

  const filteredBackups = computed(() => {
    let result = backups.value
    if (backupFilters.value.type) {
      result = result.filter((backup) => backup.backup_type === backupFilters.value.type)
    }
    if (backupFilters.value.routerId) {
      result = result.filter((backup) => backup.router_id === backupFilters.value.routerId)
    }
    return result
  })

  async function loadBackups() {
    try {
      const response = await backupsApi.list()
      backups.value = response.items || []
    } catch (error) {
      console.error('Failed to load backups:', error)
    }
  }

  async function loadRouters() {
    try {
      const response = await routerApi.list()
      routers.value = response.routers || response.items || []
    } catch (error) {
      console.error('Failed to load routers:', error)
    }
  }

  function resetBackupForm() {
    backupForm.value = { router_id: '', backup_type: 'config' }
  }

  async function createBackup() {
    await backupsApi.create(backupForm.value)
    await loadBackups()
    store.addNotification('success', 'Backup created')
  }

  async function downloadBackup(backup) {
    try {
      const blob = await backupsApi.download(backup.id)
      const url = window.URL.createObjectURL(blob)
      const anchor = document.createElement('a')
      anchor.href = url
      anchor.download = backup.name
      anchor.click()
      window.URL.revokeObjectURL(url)
    } catch (error) {
      store.addNotification('error', 'Download failed')
    }
  }

  async function restoreBackup(backup) {
    await backupsApi.restore({
      router_id: backup.router_id,
      backup_id: backup.id,
      rollback_type: 'restore'
    })
    store.addNotification('success', 'Restore initiated')
  }

  async function removeBackup(backup) {
    await backupsApi.delete(backup.id)
    await loadBackups()
  }

  return {
    backups,
    routers,
    showBackupModal,
    backupFilters,
    backupForm,
    filteredBackups,
    loadBackups,
    loadRouters,
    resetBackupForm,
    createBackup,
    downloadBackup,
    restoreBackup,
    removeBackup
  }
}
