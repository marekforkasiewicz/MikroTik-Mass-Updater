<template>
  <div class="container-fluid py-4">
    <div class="d-flex justify-content-between align-items-center mb-4">
      <h2><i class="bi bi-code-square me-2"></i>Custom Scripts</h2>
      <button class="btn btn-primary" @click="newScript">
        <i class="bi bi-plus-lg me-1"></i> New Script
      </button>
    </div>

    <div class="row">
      <!-- Script List -->
      <div class="col-md-4">
        <div class="card">
          <div class="card-header">
            <input type="text" class="form-control form-control-sm" v-model="searchQuery"
                   placeholder="Search scripts..." />
          </div>
          <div class="list-group list-group-flush" style="max-height: 70vh; overflow-y: auto;">
            <a v-for="script in filteredScripts" :key="script.id" href="#"
               class="list-group-item list-group-item-action"
               :class="{ active: selectedScript?.id === script.id }"
               @click.prevent="selectScript(script)">
              <div class="d-flex justify-content-between align-items-center">
                <div>
                  <strong>{{ script.name }}</strong>
                  <div class="small text-muted">{{ script.category }}</div>
                </div>
                <span :class="script.enabled ? 'text-success' : 'text-secondary'">
                  <i :class="script.enabled ? 'bi bi-check-circle' : 'bi bi-circle'"></i>
                </span>
              </div>
            </a>
            <div v-if="filteredScripts.length === 0" class="list-group-item text-center text-muted">
              No scripts found
            </div>
          </div>
        </div>
      </div>

      <!-- Script Editor -->
      <div class="col-md-8">
        <div class="card" v-if="editingScript">
          <div class="card-header d-flex justify-content-between align-items-center">
            <h5 class="mb-0">{{ editingScript.id ? 'Edit Script' : 'New Script' }}</h5>
            <div>
              <button class="btn btn-sm btn-outline-secondary me-2" @click="validateScript">
                <i class="bi bi-check2-circle me-1"></i> Validate
              </button>
              <button class="btn btn-sm btn-primary" @click="saveScript" :disabled="saving">
                <span v-if="saving" class="spinner-border spinner-border-sm me-1"></span>
                Save
              </button>
            </div>
          </div>
          <div class="card-body">
            <div class="row mb-3">
              <div class="col-md-6">
                <label class="form-label">Name</label>
                <input type="text" class="form-control" v-model="editingScript.name" />
              </div>
              <div class="col-md-3">
                <label class="form-label">Type</label>
                <select class="form-select" v-model="editingScript.script_type">
                  <option value="routeros">RouterOS</option>
                  <option value="ssh">SSH/Bash</option>
                </select>
              </div>
              <div class="col-md-3">
                <label class="form-label">Category</label>
                <input type="text" class="form-control" v-model="editingScript.category" />
              </div>
            </div>

            <div class="mb-3">
              <label class="form-label">Description</label>
              <textarea class="form-control" v-model="editingScript.description" rows="2"></textarea>
            </div>

            <div class="mb-3">
              <label class="form-label">Script Content</label>
              <textarea class="form-control font-monospace" v-model="editingScript.content"
                        rows="15" style="font-size: 13px;"></textarea>
            </div>

            <div v-if="validationResult" class="mb-3">
              <div :class="validationResult.valid ? 'alert alert-success' : 'alert alert-danger'" class="py-2">
                <div v-if="validationResult.valid">
                  <i class="bi bi-check-circle me-2"></i>Script is valid
                </div>
                <div v-else>
                  <i class="bi bi-x-circle me-2"></i>Validation errors:
                  <ul class="mb-0 mt-2">
                    <li v-for="error in validationResult.errors" :key="error">{{ error }}</li>
                  </ul>
                </div>
                <div v-if="validationResult.warnings?.length" class="mt-2 text-warning">
                  Warnings:
                  <ul class="mb-0">
                    <li v-for="warning in validationResult.warnings" :key="warning">{{ warning }}</li>
                  </ul>
                </div>
              </div>
            </div>

            <div class="row mb-3">
              <div class="col-md-4">
                <label class="form-label">Timeout (seconds)</label>
                <input type="number" class="form-control" v-model.number="editingScript.timeout" min="1" />
              </div>
              <div class="col-md-8">
                <div class="form-check mt-4">
                  <input type="checkbox" class="form-check-input" v-model="editingScript.enabled" id="enabled" />
                  <label class="form-check-label" for="enabled">Enabled</label>
                </div>
                <div class="form-check">
                  <input type="checkbox" class="form-check-input" v-model="editingScript.dangerous" id="dangerous" />
                  <label class="form-check-label" for="dangerous">Dangerous (requires confirmation)</label>
                </div>
              </div>
            </div>
          </div>
          <div class="card-footer d-flex justify-content-between">
            <button class="btn btn-danger" @click="confirmDelete" v-if="editingScript.id">
              <i class="bi bi-trash me-1"></i> Delete
            </button>
            <div v-if="editingScript.id">
              <button class="btn btn-outline-secondary me-2" @click="loadExecutionHistory">
                <i class="bi bi-clock-history me-1"></i> History
              </button>
              <button class="btn btn-success" @click="showExecuteModal = true">
                <i class="bi bi-play me-1"></i> Execute
              </button>
            </div>
          </div>
        </div>

        <div class="card" v-else>
          <div class="card-body text-center py-5 text-muted">
            <i class="bi bi-code-square fs-1"></i>
            <p class="mt-2">Select a script to edit or create a new one</p>
          </div>
        </div>
      </div>
    </div>

    <!-- Execute Modal -->
    <div class="modal fade" id="executeModal" tabindex="-1" ref="executeModalEl">
      <div class="modal-dialog modal-lg">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">Execute Script: {{ editingScript?.name }}</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
          </div>
          <div class="modal-body">
            <!-- Router Selection -->
            <div class="mb-3" v-if="!executionResults.length">
              <label class="form-label">Select Routers</label>
              <div class="d-flex gap-2 mb-2">
                <button class="btn btn-sm btn-outline-secondary" @click="selectAllRouters">Select All</button>
                <button class="btn btn-sm btn-outline-secondary" @click="executeForm.router_ids = []">Clear</button>
              </div>
              <select class="form-select" v-model="executeForm.router_ids" multiple size="6">
                <option v-for="router in routers" :key="router.id" :value="router.id">
                  {{ router.identity || router.ip }} ({{ router.ip }})
                </option>
              </select>
              <small class="text-muted">Selected: {{ executeForm.router_ids.length }} routers</small>
            </div>
            <div class="form-check mb-3" v-if="!executionResults.length">
              <input type="checkbox" class="form-check-input" v-model="executeForm.dry_run" id="dryRun" />
              <label class="form-check-label" for="dryRun">Dry run (don't actually execute)</label>
            </div>

            <!-- Execution Results -->
            <div v-if="executionResults.length" class="execution-results">
              <h6>Execution Results</h6>
              <div class="table-responsive">
                <table class="table table-sm">
                  <thead>
                    <tr>
                      <th>Router</th>
                      <th>Status</th>
                      <th>Duration</th>
                      <th>Output</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="result in executionResults" :key="result.id">
                      <td>{{ getRouterName(result.router_id) }}</td>
                      <td>
                        <span :class="result.status === 'success' ? 'badge bg-success' : 'badge bg-danger'">
                          {{ result.status }}
                        </span>
                      </td>
                      <td>{{ result.duration_ms ? (result.duration_ms / 1000).toFixed(1) + 's' : '-' }}</td>
                      <td>
                        <button class="btn btn-sm btn-outline-info" @click="showOutput(result)">
                          <i class="bi bi-eye"></i> View
                        </button>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <div class="alert alert-secondary mt-3" v-if="selectedOutput">
                <div class="d-flex justify-content-between align-items-center mb-2">
                  <strong>{{ selectedOutput.router }}</strong>
                  <button class="btn btn-sm btn-outline-secondary" @click="selectedOutput = null">Close</button>
                </div>
                <pre class="mb-0" style="max-height: 200px; overflow-y: auto; white-space: pre-wrap;">{{ selectedOutput.output || selectedOutput.error || 'No output' }}</pre>
              </div>
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal" @click="resetExecuteModal">Close</button>
            <button type="button" class="btn btn-success" @click="executeScript"
                    :disabled="executing || executeForm.router_ids.length === 0"
                    v-if="!executionResults.length">
              <span v-if="executing" class="spinner-border spinner-border-sm me-1"></span>
              Execute on {{ executeForm.router_ids.length }} router(s)
            </button>
            <button type="button" class="btn btn-primary" @click="resetExecuteModal" v-else>
              Execute Again
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Execution History -->
    <div class="modal fade" id="historyModal" tabindex="-1" ref="historyModalEl">
      <div class="modal-dialog modal-xl">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">Execution History: {{ editingScript?.name }}</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
          </div>
          <div class="modal-body">
            <div class="table-responsive">
              <table class="table table-sm table-striped">
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Router</th>
                    <th>Status</th>
                    <th>Duration</th>
                    <th>Output / Error</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="exec in executionHistory" :key="exec.id">
                    <td>{{ formatDate(exec.started_at) }}</td>
                    <td>{{ getRouterName(exec.router_id) }}</td>
                    <td>
                      <span :class="exec.status === 'success' ? 'badge bg-success' : 'badge bg-danger'">
                        {{ exec.status }}
                      </span>
                    </td>
                    <td>{{ exec.duration_ms ? (exec.duration_ms / 1000).toFixed(1) + 's' : '-' }}</td>
                    <td>
                      <code v-if="exec.output" class="small">{{ truncate(exec.output, 100) }}</code>
                      <span v-else-if="exec.error_message" class="text-danger small">{{ truncate(exec.error_message, 100) }}</span>
                      <span v-else class="text-muted">-</span>
                    </td>
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
      title="Delete Script"
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
import { ref, computed, onMounted, nextTick, watch } from 'vue'
import { Modal } from 'bootstrap'
import { scriptsApi, routerApi } from '../services/api'
import ConfirmModal from './ConfirmModal.vue'
import { useMainStore } from '../stores/main'

const mainStore = useMainStore()

const scripts = ref([])
const routers = ref([])
const selectedScript = ref(null)
const editingScript = ref(null)
const searchQuery = ref('')
const saving = ref(false)
const executing = ref(false)
const validationResult = ref(null)
const showExecuteModal = ref(false)

const executeForm = ref({
  router_ids: [],
  variables: {},
  dry_run: false
})

const executionResults = ref([])
const executionHistory = ref([])
const selectedOutput = ref(null)

const executeModalEl = ref(null)
const historyModalEl = ref(null)
let executeModal = null
let historyModal = null

// Delete confirmation state
const showDeleteModal = ref(false)
const deleteModalMessage = ref('')
const deleting = ref(false)

const filteredScripts = computed(() => {
  if (!searchQuery.value) return scripts.value
  const query = searchQuery.value.toLowerCase()
  return scripts.value.filter(s =>
    s.name.toLowerCase().includes(query) ||
    s.category.toLowerCase().includes(query)
  )
})

onMounted(async () => {
  await loadScripts()
  await loadRouters()

  nextTick(() => {
    if (executeModalEl.value) {
      executeModal = new Modal(executeModalEl.value)
    }
    if (historyModalEl.value) {
      historyModal = new Modal(historyModalEl.value)
    }
  })
})

watch(showExecuteModal, (val) => {
  if (val) executeModal?.show()
})

async function loadScripts() {
  try {
    const response = await scriptsApi.list()
    scripts.value = response.items
  } catch (error) {
    console.error('Failed to load scripts:', error)
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

function selectScript(script) {
  selectedScript.value = script
  editingScript.value = { ...script }
  validationResult.value = null
}

function newScript() {
  selectedScript.value = null
  editingScript.value = {
    name: '',
    description: '',
    script_type: 'routeros',
    content: '',
    category: 'general',
    timeout: 60,
    enabled: true,
    dangerous: false,
    variables: []
  }
  validationResult.value = null
}

async function validateScript() {
  try {
    validationResult.value = await scriptsApi.validate({
      content: editingScript.value.content,
      script_type: editingScript.value.script_type
    })
  } catch (error) {
    console.error('Validation failed:', error)
  }
}

async function saveScript() {
  saving.value = true
  try {
    if (editingScript.value.id) {
      await scriptsApi.update(editingScript.value.id, editingScript.value)
    } else {
      const created = await scriptsApi.create(editingScript.value)
      editingScript.value.id = created.id
    }
    await loadScripts()
    selectScript(editingScript.value)
  } catch (error) {
    console.error('Failed to save script:', error)
  } finally {
    saving.value = false
  }
}

function confirmDelete() {
  if (!editingScript.value?.id) return
  deleteModalMessage.value = `Are you sure you want to delete script "${editingScript.value.name}"? This action cannot be undone.`
  showDeleteModal.value = true
}

async function handleDeleteConfirm() {
  if (!editingScript.value?.id) return
  deleting.value = true
  try {
    await scriptsApi.delete(editingScript.value.id)
    editingScript.value = null
    selectedScript.value = null
    await loadScripts()
  } catch (error) {
    console.error('Failed to delete script:', error)
    mainStore.addNotification('error', 'Failed to delete script')
  } finally {
    deleting.value = false
    showDeleteModal.value = false
  }
}

async function executeScript() {
  if (executeForm.value.router_ids.length === 0) {
    mainStore.addNotification('warning', 'Please select at least one router')
    return
  }

  executing.value = true
  executionResults.value = []

  try {
    // Execute on each router one by one (API accepts router_ids array but only 1 at a time)
    for (const routerId of executeForm.value.router_ids) {
      try {
        const result = await scriptsApi.execute(editingScript.value.id, {
          router_ids: [routerId],  // API expects router_ids as array
          variables: executeForm.value.variables || {},
          dry_run: executeForm.value.dry_run
        })
        executionResults.value.push(result)
      } catch (error) {
        executionResults.value.push({
          router_id: routerId,
          status: 'failed',
          error_message: error.message,
          duration_ms: null
        })
      }
    }
  } catch (error) {
    console.error('Failed to execute script:', error)
    mainStore.addNotification('error', 'Execution failed: ' + error.message)
  } finally {
    executing.value = false
  }
}

function selectAllRouters() {
  executeForm.value.router_ids = routers.value.map(r => r.id)
}

function resetExecuteModal() {
  executionResults.value = []
  selectedOutput.value = null
}

function getRouterName(routerId) {
  const router = routers.value.find(r => r.id === routerId)
  return router ? (router.identity || router.ip) : `Router #${routerId}`
}

function showOutput(result) {
  selectedOutput.value = {
    router: getRouterName(result.router_id),
    output: result.output,
    error: result.error_message
  }
}

async function loadExecutionHistory() {
  if (!editingScript.value?.id) return
  try {
    const response = await scriptsApi.getExecutions(editingScript.value.id)
    executionHistory.value = response.items || []
    historyModal?.show()
  } catch (error) {
    console.error('Failed to load execution history:', error)
  }
}

function formatDate(dateStr) {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  return date.toLocaleString()
}

function truncate(text, maxLen) {
  if (!text) return ''
  return text.length > maxLen ? text.substring(0, maxLen) + '...' : text
}
</script>
