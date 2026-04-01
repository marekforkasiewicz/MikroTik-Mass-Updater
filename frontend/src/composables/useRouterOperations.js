import { ref } from 'vue'

export function useRouterOperations({ store, taskApi, routerApi }) {
  const upgradingFirmware = ref({})
  const upgradingRouterOS = ref({})
  const changingChannel = ref({})

  const showUpgradeModal = ref(false)
  const upgradeModalRouter = ref(null)
  const upgradeModalTaskId = ref(null)
  const upgradeModalType = ref('firmware')

  function getChannelSelectClass(channel) {
    const classes = {
      stable: 'channel-stable',
      'long-term': 'channel-longterm',
      testing: 'channel-testing',
      development: 'channel-development'
    }
    return classes[channel] || ''
  }

  async function upgradeFirmware(router) {
    if (!router?.id) {
      store.addNotification('error', 'Invalid router data')
      return
    }
    if (!router.is_online) {
      store.addNotification('error', `Router ${router.ip} is offline`)
      return
    }
    if (!router.has_firmware_update) {
      store.addNotification('warning', `Router ${router.ip} has no firmware update available`)
      return
    }

    upgradeModalRouter.value = router
    upgradeModalType.value = 'firmware'
    showUpgradeModal.value = true

    upgradingFirmware.value[router.id] = true
    try {
      const response = await taskApi.startUpdate({
        router_ids: [router.id],
        upgrade_firmware: true,
        dry_run: false
      })
      if (response?.id) {
        upgradeModalTaskId.value = response.id
      } else {
        throw new Error('Invalid response from server')
      }
    } catch (error) {
      console.error('Firmware upgrade error:', error)
      const errorMsg = error.response?.data?.detail
        ? (typeof error.response.data.detail === 'string'
            ? error.response.data.detail
            : JSON.stringify(error.response.data.detail))
        : (error.message || 'Unknown error')
      store.addNotification('error', `Firmware upgrade failed: ${errorMsg}`)
      showUpgradeModal.value = false
      upgradingFirmware.value[router.id] = false
    }
  }

  async function upgradeRouterOS(router) {
    if (!router?.id) {
      store.addNotification('error', 'Invalid router data')
      return
    }
    if (!router.is_online) {
      store.addNotification('error', `Router ${router.ip} is offline`)
      return
    }
    if (!router.has_updates) {
      store.addNotification('warning', `Router ${router.ip} has no RouterOS update available`)
      return
    }

    upgradeModalRouter.value = router
    upgradeModalType.value = 'routeros'
    showUpgradeModal.value = true

    upgradingRouterOS.value[router.id] = true
    try {
      const response = await taskApi.startUpdate({
        router_ids: [router.id],
        upgrade_firmware: false,
        dry_run: false
      })
      if (response?.id) {
        upgradeModalTaskId.value = response.id
      } else {
        throw new Error('Invalid response from server')
      }
    } catch (error) {
      console.error('RouterOS upgrade error:', error)
      const errorMsg = error.response?.data?.detail
        ? (typeof error.response.data.detail === 'string'
            ? error.response.data.detail
            : JSON.stringify(error.response.data.detail))
        : (error.message || 'Unknown error')
      store.addNotification('error', `RouterOS upgrade failed: ${errorMsg}`)
      showUpgradeModal.value = false
      upgradingRouterOS.value[router.id] = false
    }
  }

  async function closeUpgradeModal() {
    showUpgradeModal.value = false
    upgradeModalTaskId.value = null
    if (upgradeModalRouter.value) {
      upgradingFirmware.value[upgradeModalRouter.value.id] = false
      upgradingRouterOS.value[upgradeModalRouter.value.id] = false
    }
    upgradeModalRouter.value = null
    await store.fetchRouters()
  }

  async function onUpgradeComplete(data) {
    await store.fetchRouters()
    if (data?.success) {
      store.addNotification('success', `Upgrade completed for ${data.router?.identity || data.router?.ip || 'router'}`)
    }
  }

  async function changeChannel(router, newChannel) {
    if (!router?.id || !newChannel) return
    if (newChannel === router.update_channel) return

    const routerId = router.id
    changingChannel.value[routerId] = true

    try {
      const result = await routerApi.changeChannel(routerId, newChannel)
      const index = store.routers.findIndex((item) => item.id === routerId)
      if (index !== -1) {
        const updatedRouter = {
          ...store.routers[index],
          update_channel: newChannel,
          latest_version: result.latest_version,
          has_updates: result.has_updates
        }
        store.routers.splice(index, 1, updatedRouter)
      }

      const message = result.has_updates
        ? `Channel "${newChannel}" - update available: ${result.latest_version}`
        : `Channel "${newChannel}" - up to date (${result.latest_version})`
      store.addNotification('success', `${router.identity || router.ip}: ${message}`)
    } catch (error) {
      store.addNotification('error', `Failed to change channel: ${error.message}`)
      await store.fetchRouters()
    } finally {
      changingChannel.value[routerId] = false
    }
  }

  return {
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
  }
}
