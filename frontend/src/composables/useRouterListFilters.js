import { computed, ref } from 'vue'

export function useRouterListFilters({ store, scanApi }) {
  const searchQuery = ref('')
  const statusFilter = ref('')

  const filteredRouters = computed(() => {
    let routers = store.routers

    if (searchQuery.value) {
      const query = searchQuery.value.toLowerCase()
      routers = routers.filter((router) =>
        router.ip.toLowerCase().includes(query) ||
        (router.identity && router.identity.toLowerCase().includes(query))
      )
    }

    if (statusFilter.value === 'online') {
      routers = routers.filter((router) => router.is_online)
    } else if (statusFilter.value === 'offline') {
      routers = routers.filter((router) => !router.is_online)
    } else if (statusFilter.value === 'updates') {
      routers = routers.filter((router) => router.has_updates)
    }

    return routers
  })

  const allSelected = computed(() =>
    filteredRouters.value.length > 0 &&
    filteredRouters.value.every((router) => store.selectedRouterIds.includes(router.id))
  )

  function toggleSelectAll() {
    if (allSelected.value) {
      store.clearSelection()
      return
    }

    filteredRouters.value.forEach((router) => {
      if (!store.selectedRouterIds.includes(router.id)) {
        store.toggleRouterSelection(router.id)
      }
    })
  }

  async function scanRouter(router) {
    try {
      await scanApi.quickScanSingle(router.id)
      await store.fetchRouters()
      store.addNotification('success', `Scan completed for ${router.ip}`)
    } catch (error) {
      store.addNotification('error', `Scan failed: ${error.message}`)
    }
  }

  async function scanSelected() {
    await store.startQuickScan(store.selectedRouterIds)
  }

  return {
    searchQuery,
    statusFilter,
    filteredRouters,
    allSelected,
    toggleSelectAll,
    scanRouter,
    scanSelected
  }
}
