<template>
  <div class="container-fluid py-4">
    <div class="d-flex justify-content-between align-items-center mb-4">
      <h2><i class="bi bi-shield-check me-2"></i>Compliance Management</h2>
      <div>
        <button class="btn btn-outline-secondary me-2" @click="showDiffModal = true">
          <i class="bi bi-file-diff me-1"></i> Compare Configs
        </button>
        <button class="btn btn-primary" @click="newBaseline">
          <i class="bi bi-plus-lg me-1"></i> New Baseline
        </button>
      </div>
    </div>

    <!-- Summary Cards -->
    <div class="row mb-4" v-if="summary">
      <div class="col-md-2">
        <div class="card text-center">
          <div class="card-body py-3">
            <h3 class="mb-0">{{ summary.total_routers }}</h3>
            <small class="text-muted">Total Checked</small>
          </div>
        </div>
      </div>
      <div class="col-md-2">
        <div class="card text-center bg-success text-white">
          <div class="card-body py-3">
            <h3 class="mb-0">{{ summary.compliant }}</h3>
            <small>Compliant</small>
          </div>
        </div>
      </div>
      <div class="col-md-2">
        <div class="card text-center bg-warning">
          <div class="card-body py-3">
            <h3 class="mb-0">{{ summary.partial }}</h3>
            <small>Partial</small>
          </div>
        </div>
      </div>
      <div class="col-md-2">
        <div class="card text-center bg-danger text-white">
          <div class="card-body py-3">
            <h3 class="mb-0">{{ summary.non_compliant }}</h3>
            <small>Non-Compliant</small>
          </div>
        </div>
      </div>
      <div class="col-md-2">
        <div class="card text-center bg-secondary text-white">
          <div class="card-body py-3">
            <h3 class="mb-0">{{ summary.error }}</h3>
            <small>Error</small>
          </div>
        </div>
      </div>
      <div class="col-md-2">
        <div class="card text-center">
          <div class="card-body py-3">
            <h3 class="mb-0">{{ summary.compliance_rate }}%</h3>
            <small class="text-muted">Rate</small>
          </div>
        </div>
      </div>
    </div>

    <div class="row">
      <!-- Baselines List -->
      <div class="col-md-4">
        <div class="card">
          <div class="card-header d-flex justify-content-between align-items-center">
            <h5 class="mb-0">Compliance Baselines</h5>
            <span class="badge bg-primary">{{ baselines.length }}</span>
          </div>
          <div class="list-group list-group-flush" style="max-height: 60vh; overflow-y: auto;">
            <a v-for="baseline in baselines" :key="baseline.id" href="#"
               class="list-group-item list-group-item-action"
               :class="{ active: selectedBaseline?.id === baseline.id }"
               @click.prevent="selectBaseline(baseline)">
              <div class="d-flex justify-content-between align-items-start">
                <div>
                  <strong>{{ baseline.name }}</strong>
                  <div class="small text-muted">
                    {{ baseline.rules?.length || 0 }} rules
                  </div>
                  <div class="small text-muted" v-if="baseline.description">
                    {{ truncate(baseline.description, 50) }}
                  </div>
                </div>
                <span :class="baseline.is_active ? 'text-success' : 'text-secondary'">
                  <i :class="baseline.is_active ? 'bi bi-check-circle-fill' : 'bi bi-circle'"></i>
                </span>
              </div>
            </a>
            <div v-if="baselines.length === 0" class="list-group-item text-center text-muted">
              <i class="bi bi-shield-x fs-4"></i>
              <p class="mb-0 mt-2">No baselines defined</p>
            </div>
          </div>
        </div>
      </div>

      <!-- Baseline Editor / Check Results -->
      <div class="col-md-8">
        <!-- Baseline Editor -->
        <div class="card" v-if="editingBaseline">
          <div class="card-header d-flex justify-content-between align-items-center">
            <h5 class="mb-0">{{ editingBaseline.id ? 'Edit Baseline' : 'New Baseline' }}</h5>
            <div>
              <button class="btn btn-sm btn-success me-2" @click="runCheck"
                      v-if="editingBaseline.id" :disabled="checking">
                <span v-if="checking" class="spinner-border spinner-border-sm me-1"></span>
                <i class="bi bi-play-fill me-1" v-else></i> Run Check
              </button>
              <button class="btn btn-sm btn-primary" @click="saveBaseline" :disabled="saving">
                <span v-if="saving" class="spinner-border spinner-border-sm me-1"></span>
                Save
              </button>
            </div>
          </div>
          <div class="card-body">
            <div class="row mb-3">
              <div class="col-md-6">
                <label class="form-label">Name <span class="text-danger">*</span></label>
                <input type="text" class="form-control" v-model="editingBaseline.name"
                       placeholder="e.g., Security Baseline" />
              </div>
              <div class="col-md-6">
                <label class="form-label">Status</label>
                <div class="form-check form-switch mt-2">
                  <input type="checkbox" class="form-check-input" v-model="editingBaseline.is_active" />
                  <label class="form-check-label">Active</label>
                </div>
              </div>
            </div>

            <div class="mb-3">
              <label class="form-label">Description</label>
              <textarea class="form-control" v-model="editingBaseline.description" rows="2"></textarea>
            </div>

            <!-- Rules -->
            <div class="mb-3">
              <div class="d-flex justify-content-between align-items-center mb-2">
                <label class="form-label mb-0">Compliance Rules</label>
                <button class="btn btn-sm btn-outline-primary" @click="addRule">
                  <i class="bi bi-plus"></i> Add Rule
                </button>
              </div>

              <div v-if="editingBaseline.rules?.length" class="rules-list">
                <div v-for="(rule, index) in editingBaseline.rules" :key="index"
                     class="card mb-2">
                  <div class="card-body py-2">
                    <div class="row g-2 align-items-center">
                      <div class="col-md-3">
                        <input type="text" class="form-control form-control-sm"
                               v-model="rule.name" placeholder="Rule name" />
                      </div>
                      <div class="col-md-2">
                        <select class="form-select form-select-sm" v-model="rule.type">
                          <option value="contains">Contains</option>
                          <option value="not_contains">Not Contains</option>
                          <option value="regex_match">Regex Match</option>
                          <option value="regex_not_match">Regex Not Match</option>
                          <option value="setting">Setting</option>
                        </select>
                      </div>
                      <div class="col-md-3">
                        <input type="text" class="form-control form-control-sm"
                               v-model="rule.pattern" placeholder="Pattern"
                               v-if="rule.type !== 'setting'" />
                        <input type="text" class="form-control form-control-sm"
                               v-model="rule.path" placeholder="Path"
                               v-else />
                      </div>
                      <div class="col-md-2">
                        <select class="form-select form-select-sm" v-model="rule.severity">
                          <option value="info">Info</option>
                          <option value="warning">Warning</option>
                          <option value="critical">Critical</option>
                        </select>
                      </div>
                      <div class="col-md-2 text-end">
                        <button class="btn btn-sm btn-outline-danger" @click="removeRule(index)">
                          <i class="bi bi-trash"></i>
                        </button>
                      </div>
                    </div>
                    <div class="row g-2 mt-1" v-if="rule.type === 'setting'">
                      <div class="col-md-4">
                        <input type="text" class="form-control form-control-sm"
                               v-model="rule.setting" placeholder="Setting name" />
                      </div>
                      <div class="col-md-4">
                        <input type="text" class="form-control form-control-sm"
                               v-model="rule.expected" placeholder="Expected value" />
                      </div>
                    </div>
                    <div class="mt-1">
                      <input type="text" class="form-control form-control-sm"
                             v-model="rule.description" placeholder="Description (optional)" />
                    </div>
                  </div>
                </div>
              </div>
              <div v-else class="text-muted small">
                No rules defined. Add rules to check router configurations.
              </div>
            </div>
          </div>
          <div class="card-footer d-flex justify-content-between">
            <button class="btn btn-danger" @click="deleteBaseline" v-if="editingBaseline.id">
              <i class="bi bi-trash me-1"></i> Delete
            </button>
            <div v-else></div>
            <button class="btn btn-outline-secondary" @click="editingBaseline = null">
              Cancel
            </button>
          </div>
        </div>

        <!-- Check Results -->
        <div class="card" v-else-if="checkResults.length">
          <div class="card-header d-flex justify-content-between align-items-center">
            <h5 class="mb-0">Compliance Check Results</h5>
            <button class="btn btn-sm btn-outline-secondary" @click="checkResults = []">
              Clear
            </button>
          </div>
          <div class="card-body" style="max-height: 60vh; overflow-y: auto;">
            <div v-for="result in checkResults" :key="result.id" class="mb-3">
              <div class="d-flex justify-content-between align-items-center">
                <h6 class="mb-0">
                  <span :class="getStatusBadge(result.status)" class="me-2">
                    {{ result.status }}
                  </span>
                  Router #{{ result.router_id }}
                </h6>
                <small class="text-muted">
                  {{ result.compliant_rules }}/{{ result.compliant_rules + result.non_compliant_rules }} rules passed
                </small>
              </div>
              <div v-if="result.error_message" class="alert alert-danger py-2 mt-2">
                {{ result.error_message }}
              </div>
              <div v-else class="mt-2">
                <div v-for="(r, idx) in result.results" :key="idx"
                     class="d-flex align-items-center py-1 border-bottom">
                  <i :class="r.status === 'compliant' ? 'bi bi-check-circle text-success' : 'bi bi-x-circle text-danger'"
                     class="me-2"></i>
                  <div class="flex-grow-1">
                    <strong>{{ r.name }}</strong>
                    <span class="badge ms-2" :class="getSeverityBadge(r.severity)">
                      {{ r.severity }}
                    </span>
                    <div v-if="r.details" class="small text-danger">{{ r.details }}</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Empty State -->
        <div class="card" v-else>
          <div class="card-body text-center py-5 text-muted">
            <i class="bi bi-shield-check fs-1"></i>
            <p class="mt-2">Select a baseline to edit or create a new one</p>
            <button class="btn btn-primary" @click="newBaseline">
              <i class="bi bi-plus-lg me-1"></i> Create Baseline
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Run Check Modal -->
    <div class="modal fade" id="checkModal" tabindex="-1" ref="checkModalEl">
      <div class="modal-dialog">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">Run Compliance Check</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
          </div>
          <div class="modal-body">
            <div class="mb-3">
              <label class="form-label">Baseline</label>
              <input type="text" class="form-control" :value="selectedBaseline?.name" disabled />
            </div>
            <div class="mb-3">
              <label class="form-label">Select Routers</label>
              <div class="d-flex gap-2 mb-2">
                <button class="btn btn-sm btn-outline-secondary" @click="selectAllRouters">All</button>
                <button class="btn btn-sm btn-outline-secondary" @click="selectOnlineRouters">Online</button>
                <button class="btn btn-sm btn-outline-secondary" @click="checkRouterIds = []">Clear</button>
              </div>
              <select class="form-select" v-model="checkRouterIds" multiple size="8">
                <option v-for="router in routers" :key="router.id" :value="router.id">
                  {{ router.identity || router.ip }} ({{ router.ip }})
                  {{ router.is_online ? '' : '- offline' }}
                </option>
              </select>
              <small class="text-muted">Selected: {{ checkRouterIds.length }}</small>
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
            <button type="button" class="btn btn-success" @click="executeCheck"
                    :disabled="checkRouterIds.length === 0 || checking">
              <span v-if="checking" class="spinner-border spinner-border-sm me-1"></span>
              Check {{ checkRouterIds.length }} Router(s)
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Diff Modal -->
    <div class="modal fade" id="diffModal" tabindex="-1" ref="diffModalEl">
      <div class="modal-dialog modal-xl">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">Compare Router Configurations</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
          </div>
          <div class="modal-body">
            <div class="row mb-3">
              <div class="col-md-5">
                <label class="form-label">Router A</label>
                <select class="form-select" v-model="diffRouterA">
                  <option :value="null">Select router...</option>
                  <option v-for="router in routers" :key="router.id" :value="router.id">
                    {{ router.identity || router.ip }} ({{ router.ip }})
                  </option>
                </select>
              </div>
              <div class="col-md-2 text-center pt-4">
                <i class="bi bi-arrow-left-right fs-4"></i>
              </div>
              <div class="col-md-5">
                <label class="form-label">Router B</label>
                <select class="form-select" v-model="diffRouterB">
                  <option :value="null">Select router...</option>
                  <option v-for="router in routers" :key="router.id" :value="router.id">
                    {{ router.identity || router.ip }} ({{ router.ip }})
                  </option>
                </select>
              </div>
            </div>
            <div class="mb-3">
              <button class="btn btn-primary" @click="runDiff"
                      :disabled="!diffRouterA || !diffRouterB || diffing">
                <span v-if="diffing" class="spinner-border spinner-border-sm me-1"></span>
                Compare Configurations
              </button>
            </div>
            <div v-if="diffResult">
              <div class="d-flex justify-content-between mb-2">
                <div>
                  <span class="badge bg-success me-2">+{{ diffResult.added_lines }} added</span>
                  <span class="badge bg-danger">-{{ diffResult.removed_lines }} removed</span>
                </div>
                <span :class="diffResult.has_changes ? 'text-warning' : 'text-success'">
                  {{ diffResult.has_changes ? 'Configs differ' : 'Configs identical' }}
                </span>
              </div>
              <pre v-if="diffResult.unified_diff" class="bg-dark text-light p-3 rounded"
                   style="max-height: 400px; overflow: auto; font-size: 12px;">{{ diffResult.unified_diff }}</pre>
              <div v-else class="alert alert-success">
                <i class="bi bi-check-circle me-2"></i>
                Configurations are identical
              </div>
              <div v-if="diffResult.error" class="alert alert-danger">
                {{ diffResult.error }}
              </div>
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick, watch } from 'vue'
import { Modal } from 'bootstrap'
import { complianceApi, routerApi } from '../services/api'
import { useMainStore } from '../stores/main'

const mainStore = useMainStore()

// Data
const baselines = ref([])
const routers = ref([])
const selectedBaseline = ref(null)
const editingBaseline = ref(null)
const summary = ref(null)
const checkResults = ref([])
const saving = ref(false)
const checking = ref(false)
const checkRouterIds = ref([])

// Diff
const showDiffModal = ref(false)
const diffRouterA = ref(null)
const diffRouterB = ref(null)
const diffResult = ref(null)
const diffing = ref(false)

// Modal refs
const checkModalEl = ref(null)
const diffModalEl = ref(null)
let checkModal = null
let diffModal = null

// Lifecycle
onMounted(async () => {
  await Promise.all([
    loadBaselines(),
    loadRouters(),
    loadSummary()
  ])

  nextTick(() => {
    if (checkModalEl.value) checkModal = new Modal(checkModalEl.value)
    if (diffModalEl.value) diffModal = new Modal(diffModalEl.value)
  })
})

watch(showDiffModal, (val) => {
  if (val) {
    diffResult.value = null
    diffModal?.show()
  }
})

// Methods
async function loadBaselines() {
  try {
    const response = await complianceApi.listBaselines()
    baselines.value = response.items || []
  } catch (error) {
    console.error('Failed to load baselines:', error)
    mainStore.addNotification('error', 'Failed to load baselines')
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

async function loadSummary() {
  try {
    summary.value = await complianceApi.getSummary()
  } catch (error) {
    console.error('Failed to load summary:', error)
  }
}

function selectBaseline(baseline) {
  selectedBaseline.value = baseline
  editingBaseline.value = {
    ...baseline,
    rules: JSON.parse(JSON.stringify(baseline.rules || []))
  }
}

function newBaseline() {
  selectedBaseline.value = null
  editingBaseline.value = {
    name: '',
    description: '',
    rules: [],
    tags: [],
    is_active: true
  }
}

function addRule() {
  if (!editingBaseline.value.rules) {
    editingBaseline.value.rules = []
  }
  editingBaseline.value.rules.push({
    name: '',
    type: 'contains',
    pattern: '',
    severity: 'warning',
    description: ''
  })
}

function removeRule(index) {
  editingBaseline.value.rules.splice(index, 1)
}

async function saveBaseline() {
  if (!editingBaseline.value.name) {
    mainStore.addNotification('warning', 'Name is required')
    return
  }

  saving.value = true
  try {
    if (editingBaseline.value.id) {
      await complianceApi.updateBaseline(editingBaseline.value.id, editingBaseline.value)
    } else {
      const created = await complianceApi.createBaseline(editingBaseline.value)
      editingBaseline.value = created
    }
    await loadBaselines()
    mainStore.addNotification('success', 'Baseline saved')
    selectBaseline(editingBaseline.value)
  } catch (error) {
    console.error('Failed to save baseline:', error)
    mainStore.addNotification('error', 'Failed to save: ' + error.message)
  } finally {
    saving.value = false
  }
}

async function deleteBaseline() {
  if (!confirm(`Delete baseline "${editingBaseline.value.name}"?`)) return

  try {
    await complianceApi.deleteBaseline(editingBaseline.value.id)
    editingBaseline.value = null
    selectedBaseline.value = null
    await loadBaselines()
    await loadSummary()
    mainStore.addNotification('success', 'Baseline deleted')
  } catch (error) {
    console.error('Failed to delete baseline:', error)
    mainStore.addNotification('error', 'Failed to delete baseline')
  }
}

function runCheck() {
  if (!selectedBaseline.value) return
  checkRouterIds.value = []
  checkModal?.show()
}

function selectAllRouters() {
  checkRouterIds.value = routers.value.map(r => r.id)
}

function selectOnlineRouters() {
  checkRouterIds.value = routers.value.filter(r => r.is_online).map(r => r.id)
}

async function executeCheck() {
  if (checkRouterIds.value.length === 0) return

  checking.value = true
  try {
    const results = await complianceApi.runCheck({
      router_ids: checkRouterIds.value,
      baseline_id: selectedBaseline.value.id
    })
    checkResults.value = results
    editingBaseline.value = null
    checkModal?.hide()
    await loadSummary()
    mainStore.addNotification('success', `Checked ${results.length} router(s)`)
  } catch (error) {
    console.error('Failed to run check:', error)
    mainStore.addNotification('error', 'Check failed: ' + error.message)
  } finally {
    checking.value = false
  }
}

async function runDiff() {
  if (!diffRouterA.value || !diffRouterB.value) return

  diffing.value = true
  diffResult.value = null

  try {
    diffResult.value = await complianceApi.diffConfigs({
      router_a_id: diffRouterA.value,
      router_b_id: diffRouterB.value,
      hide_sensitive: true
    })
  } catch (error) {
    console.error('Failed to diff configs:', error)
    diffResult.value = { error: error.message }
  } finally {
    diffing.value = false
  }
}

function getStatusBadge(status) {
  switch (status) {
    case 'compliant': return 'badge bg-success'
    case 'partial': return 'badge bg-warning'
    case 'non_compliant': return 'badge bg-danger'
    case 'error': return 'badge bg-secondary'
    default: return 'badge bg-secondary'
  }
}

function getSeverityBadge(severity) {
  switch (severity) {
    case 'critical': return 'bg-danger'
    case 'warning': return 'bg-warning text-dark'
    case 'info': return 'bg-info'
    default: return 'bg-secondary'
  }
}

function truncate(text, maxLen) {
  if (!text) return ''
  return text.length > maxLen ? text.substring(0, maxLen) + '...' : text
}
</script>

<style scoped>
.list-group-item.active .text-muted {
  color: rgba(255, 255, 255, 0.7) !important;
}
</style>
