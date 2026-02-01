<template>
  <div class="container-fluid py-4">
    <div class="d-flex justify-content-between align-items-center mb-4">
      <h2><i class="bi bi-link-45deg me-2"></i>Webhooks</h2>
      <button class="btn btn-primary" @click="showModal = true">
        <i class="bi bi-plus-lg me-1"></i> Add Webhook
      </button>
    </div>

    <!-- Webhooks List -->
    <div class="card">
      <div class="card-body">
        <div class="table-responsive">
          <table class="table table-hover">
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
                <td>
                  <code class="small">{{ truncateUrl(webhook.url) }}</code>
                </td>
                <td>
                  <span v-for="event in webhook.events?.slice(0, 2)" :key="event"
                        class="badge bg-info me-1">{{ event }}</span>
                  <span v-if="webhook.events?.length > 2" class="text-muted small">
                    +{{ webhook.events.length - 2 }}
                  </span>
                </td>
                <td>
                  <span :class="webhook.enabled ? 'badge bg-success' : 'badge bg-secondary'">
                    {{ webhook.enabled ? 'Active' : 'Disabled' }}
                  </span>
                  <span v-if="webhook.verified" class="ms-1 text-success">
                    <i class="bi bi-check-circle-fill"></i>
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
                    <button class="btn btn-outline-secondary" @click="viewDeliveries(webhook)" title="Deliveries">
                      <i class="bi bi-clock-history"></i>
                    </button>
                    <button class="btn btn-outline-secondary" @click="editWebhook(webhook)" title="Edit">
                      <i class="bi bi-pencil"></i>
                    </button>
                    <button class="btn btn-outline-danger" @click="deleteWebhook(webhook)" title="Delete">
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
              <label class="form-label">Description</label>
              <textarea class="form-control" v-model="webhookForm.description" rows="2"></textarea>
            </div>

            <div class="mb-3">
              <label class="form-label">Events</label>
              <select class="form-select" v-model="webhookForm.events" multiple size="5">
                <option v-for="event in availableEvents" :key="event.event" :value="event.event">
                  {{ event.event }} - {{ event.description }}
                </option>
              </select>
            </div>

            <div class="row mb-3">
              <div class="col-md-4">
                <label class="form-label">Retry Count</label>
                <input type="number" class="form-control" v-model.number="webhookForm.retry_count" min="0" max="10" />
              </div>
              <div class="col-md-4">
                <label class="form-label">Retry Delay (s)</label>
                <input type="number" class="form-control" v-model.number="webhookForm.retry_delay" min="0" />
              </div>
              <div class="col-md-4">
                <label class="form-label">Timeout (s)</label>
                <input type="number" class="form-control" v-model.number="webhookForm.timeout" min="1" max="300" />
              </div>
            </div>

            <div class="form-check mb-3">
              <input type="checkbox" class="form-check-input" v-model="webhookForm.enabled" id="whEnabled" />
              <label class="form-check-label" for="whEnabled">Enabled</label>
            </div>
            <div class="form-check">
              <input type="checkbox" class="form-check-input" v-model="webhookForm.include_signature" id="whSign" />
              <label class="form-check-label" for="whSign">Include HMAC signature</label>
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
            <button type="button" class="btn btn-primary" @click="saveWebhook" :disabled="saving">
              <span v-if="saving" class="spinner-border spinner-border-sm me-1"></span>
              Save
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Deliveries Modal -->
    <div class="modal fade" id="deliveriesModal" tabindex="-1" ref="deliveriesModalEl">
      <div class="modal-dialog modal-lg">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">Delivery History</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
          </div>
          <div class="modal-body">
            <div class="table-responsive">
              <table class="table table-sm">
                <thead>
                  <tr>
                    <th>Event</th>
                    <th>Status</th>
                    <th>Response</th>
                    <th>Duration</th>
                    <th>Time</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="delivery in deliveries" :key="delivery.id">
                    <td>{{ delivery.event_type }}</td>
                    <td>
                      <span :class="deliveryStatusClass(delivery.status)">{{ delivery.status }}</span>
                    </td>
                    <td>{{ delivery.response_status || '-' }}</td>
                    <td>{{ delivery.duration_ms ? `${delivery.duration_ms}ms` : '-' }}</td>
                    <td><small>{{ formatDate(delivery.created_at) }}</small></td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Confirm Delete Modal -->
    <ConfirmModal
      :visible="showDeleteModal"
      title="Delete Webhook"
      :message="deleteModalMessage"
      variant="danger"
      confirmText="Delete"
      :loading="deleting"
      @confirm="handleDeleteConfirm"
      @cancel="showDeleteModal = false"
    />
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick, watch } from 'vue'
import { Modal } from 'bootstrap'
import { webhooksApi } from '../services/api'
import ConfirmModal from './ConfirmModal.vue'
import { useMainStore } from '../stores/main'

const mainStore = useMainStore()

const webhooks = ref([])
const deliveries = ref([])
const availableEvents = ref([])
const showModal = ref(false)
const editingWebhook = ref(null)
const saving = ref(false)

const webhookForm = ref({
  name: '',
  description: '',
  url: '',
  method: 'POST',
  events: [],
  retry_count: 3,
  retry_delay: 60,
  timeout: 30,
  enabled: true,
  include_signature: true
})

const webhookModalEl = ref(null)
const deliveriesModalEl = ref(null)
let webhookModal = null
let deliveriesModal = null

// Delete confirmation state
const showDeleteModal = ref(false)
const deleteModalMessage = ref('')
const webhookToDelete = ref(null)
const deleting = ref(false)

onMounted(async () => {
  await loadData()

  nextTick(() => {
    if (webhookModalEl.value) webhookModal = new Modal(webhookModalEl.value)
    if (deliveriesModalEl.value) deliveriesModal = new Modal(deliveriesModalEl.value)
  })
})

watch(showModal, (val) => {
  if (val) {
    resetForm()
    webhookModal?.show()
  }
})

async function loadData() {
  try {
    const [webhooksRes, eventsRes] = await Promise.all([
      webhooksApi.list(),
      webhooksApi.getEvents()
    ])
    webhooks.value = webhooksRes.items
    availableEvents.value = eventsRes.events
  } catch (error) {
    console.error('Failed to load data:', error)
  }
}

function editWebhook(webhook) {
  editingWebhook.value = webhook
  webhookForm.value = { ...webhook }
  webhookModal?.show()
}

async function saveWebhook() {
  saving.value = true
  try {
    if (editingWebhook.value?.id) {
      await webhooksApi.update(editingWebhook.value.id, webhookForm.value)
    } else {
      await webhooksApi.create(webhookForm.value)
    }
    webhookModal?.hide()
    await loadData()
  } catch (error) {
    console.error('Failed to save webhook:', error)
  } finally {
    saving.value = false
  }
}

function deleteWebhook(webhook) {
  webhookToDelete.value = webhook
  deleteModalMessage.value = `Are you sure you want to delete webhook "${webhook.name}"?`
  showDeleteModal.value = true
}

async function handleDeleteConfirm() {
  if (!webhookToDelete.value) return
  deleting.value = true
  try {
    await webhooksApi.delete(webhookToDelete.value.id)
    await loadData()
    mainStore.addNotification('success', 'Webhook deleted successfully')
  } catch (error) {
    console.error('Failed to delete webhook:', error)
    mainStore.addNotification('error', 'Failed to delete webhook')
  } finally {
    deleting.value = false
    showDeleteModal.value = false
    webhookToDelete.value = null
  }
}

async function testWebhook(webhook) {
  try {
    const result = await webhooksApi.test(webhook.id, {
      event_type: 'test',
      data: { message: 'Test webhook delivery' }
    })
    if (result.success) {
      mainStore.addNotification('success', 'Test successful! Response: ' + result.status_code)
    } else {
      mainStore.addNotification('error', 'Test failed: ' + result.error)
    }
    await loadData()
  } catch (error) {
    mainStore.addNotification('error', 'Test failed: ' + error.message)
  }
}

async function viewDeliveries(webhook) {
  try {
    const response = await webhooksApi.getDeliveries(webhook.id)
    deliveries.value = response.items
    deliveriesModal?.show()
  } catch (error) {
    console.error('Failed to load deliveries:', error)
  }
}

function resetForm() {
  editingWebhook.value = null
  webhookForm.value = {
    name: '',
    description: '',
    url: '',
    method: 'POST',
    events: [],
    retry_count: 3,
    retry_delay: 60,
    timeout: 30,
    enabled: true,
    include_signature: true
  }
}

function truncateUrl(url) {
  if (!url) return ''
  return url.length > 50 ? url.substring(0, 50) + '...' : url
}

function deliveryStatusClass(status) {
  const classes = {
    success: 'badge bg-success',
    failed: 'badge bg-danger',
    pending: 'badge bg-warning',
    retrying: 'badge bg-info'
  }
  return classes[status] || 'badge bg-secondary'
}

function formatDate(dateStr) {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString()
}
</script>
