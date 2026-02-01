<template>
  <div class="container-fluid py-4">
    <h2 class="mb-4"><i class="bi bi-bell me-2"></i>Notification Settings</h2>

    <!-- Channels -->
    <div class="card mb-4">
      <div class="card-header d-flex justify-content-between align-items-center">
        <h5 class="mb-0">Notification Channels</h5>
        <button class="btn btn-primary btn-sm" @click="showChannelModal = true">
          <i class="bi bi-plus-lg me-1"></i> Add Channel
        </button>
      </div>
      <div class="card-body">
        <div class="row g-3">
          <div v-for="channel in channels" :key="channel.id" class="col-md-6 col-lg-4">
            <div class="card h-100">
              <div class="card-body">
                <div class="d-flex justify-content-between align-items-start mb-2">
                  <div>
                    <i :class="channelIcon(channel.channel_type)" class="me-2"></i>
                    <strong>{{ channel.name }}</strong>
                  </div>
                  <span :class="channel.enabled ? 'badge bg-success' : 'badge bg-secondary'">
                    {{ channel.enabled ? 'Active' : 'Disabled' }}
                  </span>
                </div>
                <p class="text-muted small mb-2">{{ channel.channel_type }}</p>
                <div class="d-flex gap-2">
                  <button class="btn btn-sm btn-outline-primary" @click="testChannel(channel)">
                    <i class="bi bi-send me-1"></i>Test
                  </button>
                  <button class="btn btn-sm btn-outline-secondary" @click="editChannel(channel)">
                    <i class="bi bi-pencil"></i>
                  </button>
                  <button class="btn btn-sm btn-outline-danger" @click="deleteChannel(channel)">
                    <i class="bi bi-trash"></i>
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Rules -->
    <div class="card mb-4">
      <div class="card-header d-flex justify-content-between align-items-center">
        <h5 class="mb-0">Notification Rules</h5>
        <button class="btn btn-primary btn-sm" @click="showRuleModal = true" :disabled="channels.length === 0">
          <i class="bi bi-plus-lg me-1"></i> Add Rule
        </button>
      </div>
      <div class="card-body">
        <div class="table-responsive">
          <table class="table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Channel</th>
                <th>Events</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="rule in rules" :key="rule.id">
                <td>{{ rule.name }}</td>
                <td>{{ getChannelName(rule.channel_id) }}</td>
                <td>
                  <span v-for="event in rule.event_types?.slice(0, 3)" :key="event"
                        class="badge bg-info me-1">{{ event }}</span>
                  <span v-if="rule.event_types?.length > 3" class="text-muted">
                    +{{ rule.event_types.length - 3 }}
                  </span>
                </td>
                <td>
                  <span :class="rule.enabled ? 'text-success' : 'text-secondary'">
                    <i :class="rule.enabled ? 'bi bi-check-circle' : 'bi bi-circle'"></i>
                  </span>
                </td>
                <td>
                  <button class="btn btn-sm btn-outline-secondary me-1" @click="editRule(rule)">
                    <i class="bi bi-pencil"></i>
                  </button>
                  <button class="btn btn-sm btn-outline-danger" @click="deleteRule(rule)">
                    <i class="bi bi-trash"></i>
                  </button>
                </td>
              </tr>
              <tr v-if="rules.length === 0">
                <td colspan="5" class="text-center text-muted py-3">No rules configured</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- Channel Modal -->
    <div class="modal fade" id="channelModal" tabindex="-1" ref="channelModalEl">
      <div class="modal-dialog">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">{{ editingChannel?.id ? 'Edit' : 'Add' }} Channel</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
          </div>
          <div class="modal-body">
            <div class="mb-3">
              <label class="form-label">Name</label>
              <input type="text" class="form-control" v-model="channelForm.name" />
            </div>
            <div class="mb-3">
              <label class="form-label">Type</label>
              <select class="form-select" v-model="channelForm.channel_type">
                <option value="email">Email</option>
                <option value="slack">Slack</option>
                <option value="telegram">Telegram</option>
                <option value="discord">Discord</option>
                <option value="webhook">Webhook</option>
              </select>
            </div>

            <!-- Email Config -->
            <div v-if="channelForm.channel_type === 'email'">
              <div class="mb-3">
                <label class="form-label">SMTP Host</label>
                <input type="text" class="form-control" v-model="channelForm.config.smtp_host" />
              </div>
              <div class="mb-3">
                <label class="form-label">To Addresses (comma-separated)</label>
                <input type="text" class="form-control" v-model="channelForm.config.to_addresses_str" />
              </div>
            </div>

            <!-- Slack/Discord Config -->
            <div v-if="['slack', 'discord'].includes(channelForm.channel_type)">
              <div class="mb-3">
                <label class="form-label">Webhook URL</label>
                <input type="url" class="form-control" v-model="channelForm.config.webhook_url" />
              </div>
            </div>

            <!-- Telegram Config -->
            <div v-if="channelForm.channel_type === 'telegram'">
              <div class="mb-3">
                <label class="form-label">Bot Token</label>
                <input type="text" class="form-control" v-model="channelForm.config.bot_token" />
              </div>
              <div class="mb-3">
                <label class="form-label">Chat IDs (comma-separated)</label>
                <input type="text" class="form-control" v-model="channelForm.config.chat_ids_str" />
              </div>
            </div>

            <div class="form-check">
              <input type="checkbox" class="form-check-input" v-model="channelForm.enabled" id="chEnabled" />
              <label class="form-check-label" for="chEnabled">Enabled</label>
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
            <button type="button" class="btn btn-primary" @click="saveChannel">Save</button>
          </div>
        </div>
      </div>
    </div>

    <!-- Rule Modal -->
    <div class="modal fade" id="ruleModal" tabindex="-1" ref="ruleModalEl">
      <div class="modal-dialog">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">{{ editingRule?.id ? 'Edit' : 'Add' }} Rule</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
          </div>
          <div class="modal-body">
            <div class="mb-3">
              <label class="form-label">Name</label>
              <input type="text" class="form-control" v-model="ruleForm.name" />
            </div>
            <div class="mb-3">
              <label class="form-label">Channel</label>
              <select class="form-select" v-model="ruleForm.channel_id">
                <option v-for="ch in channels" :key="ch.id" :value="ch.id">{{ ch.name }}</option>
              </select>
            </div>
            <div class="mb-3">
              <label class="form-label">Events</label>
              <select class="form-select" v-model="ruleForm.event_types" multiple size="5">
                <option v-for="evt in eventTypes" :key="evt.value" :value="evt.value">{{ evt.label }}</option>
              </select>
            </div>
            <div class="form-check">
              <input type="checkbox" class="form-check-input" v-model="ruleForm.enabled" id="ruleEnabled" />
              <label class="form-check-label" for="ruleEnabled">Enabled</label>
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
            <button type="button" class="btn btn-primary" @click="saveRule">Save</button>
          </div>
        </div>
      </div>
    </div>
    <!-- Confirm Modal -->
    <ConfirmModal
      :visible="showConfirmModal"
      :title="confirmModalTitle"
      :message="confirmModalMessage"
      :variant="confirmModalVariant"
      :confirmText="confirmModalAction"
      :loading="confirmLoading"
      @confirm="handleConfirmAction"
      @cancel="showConfirmModal = false"
    />
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick, watch } from 'vue'
import { Modal } from 'bootstrap'
import { useNotificationsStore } from '../stores/notifications'
import { useMainStore } from '../stores/main'
import { notificationsApi } from '../services/api'
import ConfirmModal from './ConfirmModal.vue'

const notificationsStore = useNotificationsStore()
const mainStore = useMainStore()

const channels = ref([])
const rules = ref([])
const eventTypes = ref([])

const showChannelModal = ref(false)
const showRuleModal = ref(false)
const editingChannel = ref(null)
const editingRule = ref(null)

const channelForm = ref({
  name: '',
  channel_type: 'email',
  config: {},
  enabled: true
})

const ruleForm = ref({
  name: '',
  channel_id: null,
  event_types: [],
  enabled: true
})

const channelModalEl = ref(null)
const ruleModalEl = ref(null)
let channelModal = null
let ruleModal = null

// Confirm modal state
const showConfirmModal = ref(false)
const confirmModalTitle = ref('')
const confirmModalMessage = ref('')
const confirmModalVariant = ref('danger')
const confirmModalAction = ref('Confirm')
const confirmLoading = ref(false)
const pendingAction = ref(null)
const pendingItem = ref(null)

onMounted(async () => {
  await loadData()

  nextTick(() => {
    if (channelModalEl.value) channelModal = new Modal(channelModalEl.value)
    if (ruleModalEl.value) ruleModal = new Modal(ruleModalEl.value)
  })
})

watch(showChannelModal, (val) => {
  if (val) {
    resetChannelForm()
    channelModal?.show()
  }
})

watch(showRuleModal, (val) => {
  if (val) {
    resetRuleForm()
    ruleModal?.show()
  }
})

async function loadData() {
  try {
    await notificationsStore.fetchChannels()
    await notificationsStore.fetchRules()
    channels.value = notificationsStore.channels
    rules.value = notificationsStore.rules

    // Load event types
    const eventTypesResponse = await notificationsApi.getEventTypes()
    eventTypes.value = eventTypesResponse?.event_types || []
  } catch (error) {
    console.error('Failed to load data:', error)
    mainStore.addNotification('Failed to load notification settings', 'error')
  }
}

function channelIcon(type) {
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
  return channels.value.find(c => c.id === id)?.name || 'Unknown'
}

function editChannel(channel) {
  editingChannel.value = channel
  channelForm.value = { ...channel, config: { ...channel.config } }
  channelModal?.show()
}

async function saveChannel() {
  try {
    // Process config for arrays
    if (channelForm.value.config.to_addresses_str) {
      channelForm.value.config.to_addresses = channelForm.value.config.to_addresses_str.split(',').map(s => s.trim())
    }
    if (channelForm.value.config.chat_ids_str) {
      channelForm.value.config.chat_ids = channelForm.value.config.chat_ids_str.split(',').map(s => s.trim())
    }

    if (editingChannel.value?.id) {
      await notificationsStore.updateChannel(editingChannel.value.id, channelForm.value)
    } else {
      await notificationsStore.createChannel(channelForm.value)
    }
    channelModal?.hide()
    channels.value = notificationsStore.channels
  } catch (error) {
    console.error('Failed to save channel:', error)
  }
}

function deleteChannel(channel) {
  pendingItem.value = channel
  pendingAction.value = 'deleteChannel'
  confirmModalTitle.value = 'Delete Channel'
  confirmModalMessage.value = `Are you sure you want to delete channel "${channel.name}"?`
  confirmModalVariant.value = 'danger'
  confirmModalAction.value = 'Delete'
  showConfirmModal.value = true
}

async function testChannel(channel) {
  try {
    const result = await notificationsStore.testChannel(channel.id, 'Test notification from MikroTik Updater')
    if (result.success) {
      mainStore.addNotification('success', 'Test notification sent successfully!')
    } else {
      mainStore.addNotification('error', `Test failed: ${result.error}`)
    }
  } catch (error) {
    mainStore.addNotification('error', 'Test failed: ' + error.message)
  }
}

function editRule(rule) {
  editingRule.value = rule
  ruleForm.value = { ...rule }
  ruleModal?.show()
}

async function saveRule() {
  try {
    if (editingRule.value?.id) {
      await notificationsStore.updateRule(editingRule.value.id, ruleForm.value)
    } else {
      await notificationsStore.createRule(ruleForm.value)
    }
    ruleModal?.hide()
    rules.value = notificationsStore.rules
  } catch (error) {
    console.error('Failed to save rule:', error)
  }
}

function deleteRule(rule) {
  pendingItem.value = rule
  pendingAction.value = 'deleteRule'
  confirmModalTitle.value = 'Delete Rule'
  confirmModalMessage.value = `Are you sure you want to delete rule "${rule.name}"?`
  confirmModalVariant.value = 'danger'
  confirmModalAction.value = 'Delete'
  showConfirmModal.value = true
}

async function handleConfirmAction() {
  confirmLoading.value = true
  try {
    if (pendingAction.value === 'deleteChannel' && pendingItem.value) {
      await notificationsStore.deleteChannel(pendingItem.value.id)
      channels.value = notificationsStore.channels
    } else if (pendingAction.value === 'deleteRule' && pendingItem.value) {
      await notificationsStore.deleteRule(pendingItem.value.id)
      rules.value = notificationsStore.rules
    }
  } catch (error) {
    console.error(`Failed to ${pendingAction.value}:`, error)
  } finally {
    confirmLoading.value = false
    showConfirmModal.value = false
    pendingAction.value = null
    pendingItem.value = null
  }
}

function resetChannelForm() {
  editingChannel.value = null
  channelForm.value = {
    name: '',
    channel_type: 'email',
    config: {},
    enabled: true
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
</script>
