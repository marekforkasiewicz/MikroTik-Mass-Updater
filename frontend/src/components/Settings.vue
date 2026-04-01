<template>
  <div class="container-fluid py-4">
    <div class="d-flex justify-content-between align-items-center mb-4">
      <h2><i class="bi bi-gear me-2"></i>Settings</h2>
    </div>

    <!-- Tabs -->
    <ul class="nav nav-tabs mb-4">
      <li class="nav-item">
        <a class="nav-link" :class="{ active: activeTab === 'notifications' }" href="#"
           @click.prevent="activeTab = 'notifications'">
          <i class="bi bi-bell me-1"></i> Notifications
        </a>
      </li>
      <li class="nav-item">
        <a class="nav-link" :class="{ active: activeTab === 'webhooks' }" href="#"
           @click.prevent="activeTab = 'webhooks'">
          <i class="bi bi-link-45deg me-1"></i> Webhooks
        </a>
      </li>
      <li class="nav-item" v-if="isAdmin">
        <a class="nav-link" :class="{ active: activeTab === 'users' }" href="#"
           @click.prevent="activeTab = 'users'">
          <i class="bi bi-people me-1"></i> Users
        </a>
      </li>
    </ul>

    <!-- NOTIFICATIONS TAB -->
    <div v-show="activeTab === 'notifications'">
      <!-- Channels -->
      <div class="card mb-4">
        <div class="card-header d-flex justify-content-between align-items-center">
          <h5 class="mb-0">Notification Channels</h5>
          <button class="btn btn-primary btn-sm" @click="openChannelEditor()">
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
                      <i :class="getChannelIcon(channel.channel_type)" class="me-2"></i>
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
                    <button class="btn btn-sm btn-outline-secondary" @click="openChannelEditor(channel)">
                      <i class="bi bi-pencil"></i>
                    </button>
                    <button class="btn btn-sm btn-outline-danger" @click="deleteChannel(channel)">
                      <i class="bi bi-trash"></i>
                    </button>
                  </div>
                </div>
              </div>
            </div>
            <div v-if="channels.length === 0" class="col-12 text-center text-muted py-4">
              No notification channels configured
            </div>
          </div>
        </div>
      </div>

      <!-- Rules -->
      <div class="card">
        <div class="card-header d-flex justify-content-between align-items-center">
          <h5 class="mb-0">Notification Rules</h5>
          <button class="btn btn-primary btn-sm" @click="openRuleEditor()" :disabled="channels.length === 0">
            <i class="bi bi-plus-lg me-1"></i> Add Rule
          </button>
        </div>
        <div class="card-body">
          <div class="table-responsive">
            <table class="table table-hover mb-0">
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
                    <span v-for="event in rule.event_types?.slice(0, 3)" :key="event" class="badge bg-info me-1">{{ event }}</span>
                    <span v-if="rule.event_types?.length > 3" class="text-muted">+{{ rule.event_types.length - 3 }}</span>
                  </td>
                  <td>
                    <i :class="rule.enabled ? 'bi bi-check-circle text-success' : 'bi bi-circle text-secondary'"></i>
                  </td>
                  <td>
                    <button class="btn btn-sm btn-outline-secondary me-1" @click="openRuleEditor(rule)">
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
    </div>

    <!-- WEBHOOKS TAB -->
    <div v-show="activeTab === 'webhooks'">
      <div class="card">
        <div class="card-header d-flex justify-content-between align-items-center">
          <h5 class="mb-0">Webhooks</h5>
          <button class="btn btn-primary btn-sm" @click="openWebhookEditor()">
            <i class="bi bi-plus-lg me-1"></i> Add Webhook
          </button>
        </div>
        <div class="card-body">
          <div class="table-responsive">
            <table class="table table-hover mb-0">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>URL</th>
                  <th>Events</th>
                  <th>Status</th>
                  <th>Deliveries</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="webhook in webhooks" :key="webhook.id">
                  <td>
                    <strong>{{ webhook.name }}</strong>
                    <div class="small text-muted">{{ webhook.description }}</div>
                  </td>
                  <td><code class="small">{{ truncate(webhook.url, 40) }}</code></td>
                  <td>
                    <span v-for="event in webhook.events?.slice(0, 2)" :key="event" class="badge bg-info me-1">{{ event }}</span>
                    <span v-if="webhook.events?.length > 2" class="text-muted small">+{{ webhook.events.length - 2 }}</span>
                  </td>
                  <td>
                    <span :class="webhook.enabled ? 'badge bg-success' : 'badge bg-secondary'">
                      {{ webhook.enabled ? 'Active' : 'Disabled' }}
                    </span>
                  </td>
                  <td>
                    <span class="text-success">{{ webhook.successful_deliveries }}</span> /
                    <span class="text-danger">{{ webhook.failed_deliveries }}</span>
                  </td>
                  <td>
                    <div class="btn-group btn-group-sm">
                      <button class="btn btn-outline-primary" @click="testWebhook(webhook)" title="Test">
                        <i class="bi bi-send"></i>
                      </button>
                      <button class="btn btn-outline-secondary" @click="openWebhookEditor(webhook)" title="Edit">
                        <i class="bi bi-pencil"></i>
                      </button>
                      <button class="btn btn-outline-danger" @click="deleteWebhookConfirm(webhook)" title="Delete">
                        <i class="bi bi-trash"></i>
                      </button>
                    </div>
                  </td>
                </tr>
                <tr v-if="webhooks.length === 0">
                  <td colspan="6" class="text-center py-4 text-muted">No webhooks configured</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>

    <!-- USERS TAB -->
    <div v-show="activeTab === 'users'" v-if="isAdmin">
      <div class="card">
        <div class="card-header d-flex justify-content-between align-items-center">
          <h5 class="mb-0">Users</h5>
          <button class="btn btn-primary btn-sm" @click="openUserEditor()">
            <i class="bi bi-plus-lg me-1"></i> Add User
          </button>
        </div>
        <div class="card-body">
          <div class="table-responsive">
            <table class="table table-hover mb-0">
              <thead>
                <tr>
                  <th>Username</th>
                  <th>Email</th>
                  <th>Full Name</th>
                  <th>Role</th>
                  <th>Status</th>
                  <th>Last Login</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="user in users" :key="user.id">
                  <td>
                    <strong>{{ user.username }}</strong>
                    <span v-if="user.is_superuser" class="badge bg-warning ms-1">Super</span>
                  </td>
                  <td>{{ user.email }}</td>
                  <td>{{ user.full_name || '-' }}</td>
                  <td><span :class="getRoleBadge(user.role)">{{ user.role }}</span></td>
                  <td>
                    <span :class="user.is_active ? 'text-success' : 'text-danger'">
                      <i :class="user.is_active ? 'bi bi-check-circle-fill' : 'bi bi-x-circle-fill'"></i>
                      {{ user.is_active ? 'Active' : 'Inactive' }}
                    </span>
                  </td>
                  <td>{{ user.last_login ? formatDate(user.last_login) : 'Never' }}</td>
                  <td>
                    <div class="btn-group btn-group-sm">
                      <button class="btn btn-outline-secondary" @click="openUserEditor(user)" title="Edit">
                        <i class="bi bi-pencil"></i>
                      </button>
                      <button class="btn btn-outline-danger" @click="deleteUserConfirm(user)" title="Delete"
                              :disabled="user.id === currentUser.id">
                        <i class="bi bi-trash"></i>
                      </button>
                    </div>
                  </td>
                </tr>
                <tr v-if="users.length === 0">
                  <td colspan="7" class="text-center py-4 text-muted">No users found</td>
                </tr>
              </tbody>
            </table>
          </div>
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
            <div v-if="channelForm.channel_type === 'email'" class="mb-3">
              <label class="form-label">SMTP Host</label>
              <input type="text" class="form-control" v-model="channelForm.config.smtp_host" />
            </div>
            <div v-if="['slack', 'discord'].includes(channelForm.channel_type)" class="mb-3">
              <label class="form-label">Webhook URL</label>
              <input type="url" class="form-control" v-model="channelForm.config.webhook_url" />
            </div>
            <div v-if="channelForm.channel_type === 'telegram'" class="mb-3">
              <label class="form-label">Bot Token</label>
              <input type="text" class="form-control" v-model="channelForm.config.bot_token" />
            </div>
            <div class="form-check">
              <input type="checkbox" class="form-check-input" v-model="channelForm.enabled" id="chEnabled" />
              <label class="form-check-label" for="chEnabled">Enabled</label>
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
            <button type="button" class="btn btn-primary" @click="saveChannel" :disabled="saving">
              <span v-if="saving" class="spinner-border spinner-border-sm me-1"></span> Save
            </button>
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
            <button type="button" class="btn btn-primary" @click="saveRule" :disabled="saving">
              <span v-if="saving" class="spinner-border spinner-border-sm me-1"></span> Save
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Webhook Modal -->
    <div class="modal fade" id="webhookModal" tabindex="-1" ref="webhookModalEl">
      <div class="modal-dialog modal-lg">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">{{ editingWebhook?.id ? 'Edit' : 'Add' }} Webhook</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
          </div>
          <div class="modal-body">
            <div class="row mb-3">
              <div class="col-md-6">
                <label class="form-label">Name</label>
                <input type="text" class="form-control" v-model="webhookForm.name" />
              </div>
              <div class="col-md-6">
                <label class="form-label">Method</label>
                <select class="form-select" v-model="webhookForm.method">
                  <option value="POST">POST</option>
                  <option value="PUT">PUT</option>
                </select>
              </div>
            </div>
            <div class="mb-3">
              <label class="form-label">URL</label>
              <input type="url" class="form-control" v-model="webhookForm.url" placeholder="https://..." />
            </div>
            <div class="mb-3">
              <label class="form-label">Events</label>
              <select class="form-select" v-model="webhookForm.events" multiple size="5">
                <option v-for="event in availableEvents" :key="event.event" :value="event.event">
                  {{ event.event }} - {{ event.description }}
                </option>
              </select>
            </div>
            <div class="form-check">
              <input type="checkbox" class="form-check-input" v-model="webhookForm.enabled" id="whEnabled" />
              <label class="form-check-label" for="whEnabled">Enabled</label>
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
            <button type="button" class="btn btn-primary" @click="saveWebhook" :disabled="saving">
              <span v-if="saving" class="spinner-border spinner-border-sm me-1"></span> Save
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- User Modal -->
    <div class="modal fade" id="userModal" tabindex="-1" ref="userModalEl">
      <div class="modal-dialog">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">{{ editingUser?.id ? 'Edit' : 'Add' }} User</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
          </div>
          <div class="modal-body">
            <div class="mb-3">
              <label class="form-label">Username</label>
              <input type="text" class="form-control" v-model="userForm.username" :disabled="editingUser?.id" />
            </div>
            <div class="mb-3">
              <label class="form-label">Email</label>
              <input type="email" class="form-control" v-model="userForm.email" />
            </div>
            <div class="mb-3">
              <label class="form-label">Full Name</label>
              <input type="text" class="form-control" v-model="userForm.full_name" />
            </div>
            <div class="mb-3">
              <label class="form-label">Role</label>
              <select class="form-select" v-model="userForm.role">
                <option value="admin">Admin</option>
                <option value="operator">Operator</option>
                <option value="viewer">Viewer</option>
              </select>
            </div>
            <div class="mb-3">
              <label class="form-label">{{ editingUser?.id ? 'New Password (optional)' : 'Password' }}</label>
              <input type="password" class="form-control" v-model="userForm.password" />
            </div>
            <div class="form-check">
              <input type="checkbox" class="form-check-input" v-model="userForm.is_active" id="userActive" />
              <label class="form-check-label" for="userActive">Active</label>
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
            <button type="button" class="btn btn-primary" @click="saveUser" :disabled="saving">
              <span v-if="saving" class="spinner-border spinner-border-sm me-1"></span> Save
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Confirm Modal -->
    <ConfirmModal
      :visible="showConfirm"
      :title="confirmTitle"
      :message="confirmMessage"
      :variant="confirmVariant"
      :loading="confirmLoading"
      @confirm="handleConfirm"
      @cancel="showConfirm = false"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick, watch } from 'vue'
import { Modal } from 'bootstrap'
import { useAuthStore } from '../stores/auth'
import { useNotificationsStore } from '../stores/notifications'
import { useMainStore } from '../stores/main'
import { webhooksApi, usersApi, notificationsApi } from '../services/api'
import { formatDate, truncate } from '../utils/formatters'
import { getRoleBadgeClass } from '../utils/badges'
import ConfirmModal from './ConfirmModal.vue'
import { useSettingsNotifications } from '../composables/useSettingsNotifications'
import { useSettingsWebhooks } from '../composables/useSettingsWebhooks'
import { useSettingsUsers } from '../composables/useSettingsUsers'

const authStore = useAuthStore()
const notificationsStore = useNotificationsStore()
const mainStore = useMainStore()

// State
const activeTab = ref('notifications')
const saving = ref(false)

// Confirmation
const showConfirm = ref(false)
const confirmTitle = ref('')
const confirmMessage = ref('')
const confirmVariant = ref('danger')
const confirmLoading = ref(false)
const pendingAction = ref(null)

// Modals
const channelModalEl = ref(null)
const ruleModalEl = ref(null)
const webhookModalEl = ref(null)
const userModalEl = ref(null)
let channelModal = null
let ruleModal = null
let webhookModal = null
let userModal = null

const notificationsManager = useSettingsNotifications({
  notificationsStore,
  notificationsApi,
  mainStore
})

const {
  channels,
  rules,
  eventTypes,
  showChannelModal,
  showRuleModal,
  editingChannel,
  editingRule,
  channelForm,
  ruleForm,
  loadEventTypes,
  getChannelIcon,
  getChannelName,
  resetChannelForm,
  editChannel,
  saveChannel: persistChannel,
  testChannel: runChannelTest,
  resetRuleForm,
  editRule,
  saveRule: persistRule
} = notificationsManager

const webhooksManager = useSettingsWebhooks({
  webhooksApi,
  mainStore
})

const {
  webhooks,
  availableEvents,
  showWebhookModal,
  editingWebhook,
  webhookForm,
  loadWebhooks,
  resetWebhookForm,
  editWebhook,
  saveWebhook: persistWebhook,
  testWebhook: runWebhookTest
} = webhooksManager

const usersManager = useSettingsUsers({
  usersApi,
  authStore,
  mainStore
})

const {
  users,
  showUserModal,
  editingUser,
  userForm,
  isAdmin,
  currentUser,
  loadUsers,
  getRoleBadge,
  resetUserForm,
  editUser,
  saveUser: persistUser
} = usersManager

// Lifecycle
onMounted(async () => {
  await Promise.all([
    notificationsStore.fetchChannels(),
    notificationsStore.fetchRules(),
    loadEventTypes(),
    loadWebhooks(),
    loadUsers()
  ])

  nextTick(() => {
    if (channelModalEl.value) channelModal = new Modal(channelModalEl.value)
    if (ruleModalEl.value) ruleModal = new Modal(ruleModalEl.value)
    if (webhookModalEl.value) webhookModal = new Modal(webhookModalEl.value)
    if (userModalEl.value) userModal = new Modal(userModalEl.value)
  })
})

watch(showChannelModal, (val) => { if (val) { resetChannelForm(); channelModal?.show() } })
watch(showRuleModal, (val) => { if (val) { resetRuleForm(); ruleModal?.show() } })
watch(showWebhookModal, (val) => { if (val) { resetWebhookForm(); webhookModal?.show() } })
watch(showUserModal, (val) => { if (val) { resetUserForm(); userModal?.show() } })

// Channel methods
function openChannelEditor(channel = null) {
  if (channel) {
    editChannel(channel, () => channelModal?.show())
    return
  }
  showChannelModal.value = true
}

async function saveChannel() {
  saving.value = true
  try {
    await persistChannel()
    channelModal?.hide()
  } finally { saving.value = false }
}
function deleteChannel(channel) {
  confirmTitle.value = 'Delete Channel'
  confirmMessage.value = `Delete channel "${channel.name}"?`
  confirmVariant.value = 'danger'
  pendingAction.value = () => notificationsStore.deleteChannel(channel.id)
  showConfirm.value = true
}
async function testChannel(channel) {
  await runChannelTest(channel)
}

// Rule methods
function openRuleEditor(rule = null) {
  if (rule) {
    editRule(rule, () => ruleModal?.show())
    return
  }
  showRuleModal.value = true
}

async function saveRule() {
  saving.value = true
  try {
    await persistRule()
    ruleModal?.hide()
  } finally { saving.value = false }
}
function deleteRule(rule) {
  confirmTitle.value = 'Delete Rule'
  confirmMessage.value = `Delete rule "${rule.name}"?`
  confirmVariant.value = 'danger'
  pendingAction.value = () => notificationsStore.deleteRule(rule.id)
  showConfirm.value = true
}

// Webhook methods
function openWebhookEditor(webhook = null) {
  if (webhook) {
    editWebhook(webhook, () => webhookModal?.show())
    return
  }
  showWebhookModal.value = true
}

async function saveWebhook() {
  saving.value = true
  try {
    await persistWebhook()
    webhookModal?.hide()
  } finally { saving.value = false }
}
function deleteWebhookConfirm(webhook) {
  confirmTitle.value = 'Delete Webhook'
  confirmMessage.value = `Delete webhook "${webhook.name}"?`
  confirmVariant.value = 'danger'
  pendingAction.value = async () => { await webhooksApi.delete(webhook.id); await loadWebhooks() }
  showConfirm.value = true
}
async function testWebhook(webhook) {
  await runWebhookTest(webhook)
}

// User methods
function openUserEditor(user = null) {
  if (user) {
    editUser(user, () => userModal?.show())
    return
  }
  showUserModal.value = true
}

async function saveUser() {
  saving.value = true
  try {
    await persistUser()
    userModal?.hide()
  } catch (error) { mainStore.addNotification('error', 'Failed to save user: ' + error.message) }
  finally { saving.value = false }
}
function deleteUserConfirm(user) {
  confirmTitle.value = 'Delete User'
  confirmMessage.value = `Delete user "${user.username}"?`
  confirmVariant.value = 'danger'
  pendingAction.value = async () => { await usersApi.delete(user.id); await loadUsers() }
  showConfirm.value = true
}

// Confirmation handler
async function handleConfirm() {
  if (!pendingAction.value) return
  confirmLoading.value = true
  try { await pendingAction.value() }
  finally { confirmLoading.value = false; showConfirm.value = false; pendingAction.value = null }
}
</script>

<style scoped>
.nav-tabs .nav-link { color: var(--text-secondary); }
.nav-tabs .nav-link.active { font-weight: 600; }
</style>
