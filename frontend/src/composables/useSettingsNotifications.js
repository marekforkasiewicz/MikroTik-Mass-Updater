import { computed, ref } from 'vue'

export function useSettingsNotifications({ notificationsStore, notificationsApi, mainStore }) {
  const eventTypes = ref([])
  const showChannelModal = ref(false)
  const showRuleModal = ref(false)
  const editingChannel = ref(null)
  const editingRule = ref(null)
  const channelForm = ref({ name: '', channel_type: 'email', config: {}, enabled: true })
  const ruleForm = ref({ name: '', channel_id: null, event_types: [], enabled: true })

  const channels = computed(() => notificationsStore.channels)
  const rules = computed(() => notificationsStore.rules)

  async function loadEventTypes() {
    try {
      const response = await notificationsApi.getEventTypes()
      eventTypes.value = response?.event_types || []
    } catch (error) {
      console.error('Failed to load event types:', error)
    }
  }

  function getChannelIcon(type) {
    const icons = {
      email: 'bi bi-envelope',
      slack: 'bi bi-slack',
      telegram: 'bi bi-telegram',
      discord: 'bi bi-discord',
      webhook: 'bi bi-link-45deg'
    }
    return icons[type] || 'bi bi-bell'
  }

  function getChannelName(id) {
    return channels.value.find((channel) => channel.id === id)?.name || 'Unknown'
  }

  function resetChannelForm() {
    editingChannel.value = null
    channelForm.value = { name: '', channel_type: 'email', config: {}, enabled: true }
  }

  function editChannel(channel, showModal) {
    editingChannel.value = channel
    channelForm.value = { ...channel, config: { ...channel.config } }
    showModal?.()
  }

  async function saveChannel() {
    if (editingChannel.value?.id) {
      await notificationsStore.updateChannel(editingChannel.value.id, channelForm.value)
    } else {
      await notificationsStore.createChannel(channelForm.value)
    }
  }

  async function testChannel(channel) {
    try {
      const result = await notificationsStore.testChannel(channel.id, 'Test notification')
      mainStore.addNotification(
        result.success ? 'success' : 'error',
        result.success ? 'Test sent!' : `Test failed: ${result.error}`
      )
    } catch (error) {
      mainStore.addNotification('error', `Test failed: ${error.message}`)
    }
  }

  function resetRuleForm() {
    editingRule.value = null
    ruleForm.value = {
      name: '',
      channel_id: channels.value[0]?.id,
      event_types: [],
      enabled: true
    }
  }

  function editRule(rule, showModal) {
    editingRule.value = rule
    ruleForm.value = { ...rule }
    showModal?.()
  }

  async function saveRule() {
    if (editingRule.value?.id) {
      await notificationsStore.updateRule(editingRule.value.id, ruleForm.value)
    } else {
      await notificationsStore.createRule(ruleForm.value)
    }
  }

  return {
    eventTypes,
    showChannelModal,
    showRuleModal,
    editingChannel,
    editingRule,
    channelForm,
    ruleForm,
    channels,
    rules,
    loadEventTypes,
    getChannelIcon,
    getChannelName,
    resetChannelForm,
    editChannel,
    saveChannel,
    testChannel,
    resetRuleForm,
    editRule,
    saveRule
  }
}
