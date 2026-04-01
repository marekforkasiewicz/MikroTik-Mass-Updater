import { ref } from 'vue'

export function useSettingsWebhooks({ webhooksApi, mainStore }) {
  const webhooks = ref([])
  const availableEvents = ref([])
  const showWebhookModal = ref(false)
  const editingWebhook = ref(null)
  const webhookForm = ref({ name: '', url: '', method: 'POST', events: [], enabled: true })

  async function loadWebhooks() {
    try {
      const [webhooksRes, eventsRes] = await Promise.all([
        webhooksApi.list(),
        webhooksApi.getEvents()
      ])
      webhooks.value = webhooksRes.items || []
      availableEvents.value = eventsRes.events || []
    } catch (error) {
      console.error('Failed to load webhooks:', error)
    }
  }

  function resetWebhookForm() {
    editingWebhook.value = null
    webhookForm.value = { name: '', url: '', method: 'POST', events: [], enabled: true }
  }

  function editWebhook(webhook, showModal) {
    editingWebhook.value = webhook
    webhookForm.value = { ...webhook }
    showModal?.()
  }

  async function saveWebhook() {
    if (editingWebhook.value?.id) {
      await webhooksApi.update(editingWebhook.value.id, webhookForm.value)
    } else {
      await webhooksApi.create(webhookForm.value)
    }

    await loadWebhooks()
  }

  async function testWebhook(webhook) {
    try {
      const result = await webhooksApi.test(webhook.id, {
        event_type: 'test',
        data: { message: 'Test' }
      })
      mainStore.addNotification(
        result.success ? 'success' : 'error',
        result.success ? 'Test successful!' : `Test failed: ${result.error}`
      )
    } catch (error) {
      mainStore.addNotification('error', `Test failed: ${error.message}`)
    }
  }

  return {
    webhooks,
    availableEvents,
    showWebhookModal,
    editingWebhook,
    webhookForm,
    loadWebhooks,
    resetWebhookForm,
    editWebhook,
    saveWebhook,
    testWebhook
  }
}
