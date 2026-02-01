<template>
  <div class="container-fluid py-4">
    <div class="d-flex justify-content-between align-items-center mb-4">
      <h2><i class="bi bi-folder me-2"></i>Router Groups</h2>
      <button class="btn btn-primary" @click="showCreateModal = true" v-if="canModify">
        <i class="bi bi-plus-lg me-1"></i> New Group
      </button>
    </div>

    <!-- Groups Grid -->
    <div class="row g-4">
      <div v-for="group in groups" :key="group.id" class="col-md-6 col-lg-4">
        <div class="card h-100">
          <div class="card-header d-flex align-items-center"
               :style="{ borderLeft: `4px solid ${group.color}` }">
            <i :class="`bi bi-${group.icon || 'folder'} me-2`" :style="{ color: group.color }"></i>
            <h5 class="mb-0 flex-grow-1">{{ group.name }}</h5>
            <div class="dropdown" v-if="canModify">
              <button class="btn btn-sm btn-outline-secondary" data-bs-toggle="dropdown">
                <i class="bi bi-three-dots-vertical"></i>
              </button>
              <ul class="dropdown-menu dropdown-menu-end">
                <li><a class="dropdown-item" href="#" @click.prevent="editGroup(group)">
                  <i class="bi bi-pencil me-2"></i>Edit
                </a></li>
                <li><a class="dropdown-item" href="#" @click.prevent="manageRouters(group)">
                  <i class="bi bi-router me-2"></i>Manage Routers
                </a></li>
                <li><hr class="dropdown-divider"></li>
                <li><a class="dropdown-item text-danger" href="#" @click.prevent="confirmDelete(group)">
                  <i class="bi bi-trash me-2"></i>Delete
                </a></li>
              </ul>
            </div>
          </div>
          <div class="card-body">
            <p class="text-muted mb-3">{{ group.description || 'No description' }}</p>
            <div class="d-flex align-items-center">
              <span class="badge bg-primary me-2">
                <i class="bi bi-router me-1"></i>{{ group.router_count || 0 }} routers
              </span>
              <span v-if="group.parent_id" class="badge bg-secondary">
                <i class="bi bi-diagram-3 me-1"></i>Subgroup
              </span>
            </div>
          </div>
          <div class="card-footer bg-transparent">
            <small class="text-muted">
              Created {{ formatDate(group.created_at) }}
            </small>
          </div>
        </div>
      </div>

      <div v-if="groups.length === 0 && !loading" class="col-12">
        <div class="text-center py-5 text-muted">
          <i class="bi bi-folder fs-1"></i>
          <p class="mt-2">No groups created yet</p>
          <button class="btn btn-primary" @click="showCreateModal = true" v-if="canModify">
            Create your first group
          </button>
        </div>
      </div>
    </div>

    <!-- Create/Edit Modal -->
    <div class="modal fade" id="groupModal" tabindex="-1" ref="groupModalEl">
      <div class="modal-dialog">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">{{ editingGroup ? 'Edit Group' : 'Create Group' }}</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
          </div>
          <div class="modal-body">
            <div class="mb-3">
              <label class="form-label">Name</label>
              <input type="text" class="form-control" v-model="groupForm.name" required />
            </div>
            <div class="mb-3">
              <label class="form-label">Description</label>
              <textarea class="form-control" v-model="groupForm.description" rows="2"></textarea>
            </div>
            <div class="row">
              <div class="col-6 mb-3">
                <label class="form-label">Color</label>
                <input type="color" class="form-control form-control-color w-100"
                       v-model="groupForm.color" />
              </div>
              <div class="col-6 mb-3">
                <label class="form-label">Icon</label>
                <select class="form-select" v-model="groupForm.icon">
                  <option value="folder">Folder</option>
                  <option value="building">Building</option>
                  <option value="globe">Globe</option>
                  <option value="router">Router</option>
                  <option value="server">Server</option>
                  <option value="hdd-network">Network</option>
                </select>
              </div>
            </div>
            <div class="mb-3">
              <label class="form-label">Parent Group</label>
              <select class="form-select" v-model="groupForm.parent_id">
                <option :value="null">None (Root Level)</option>
                <option v-for="g in groups" :key="g.id" :value="g.id"
                        :disabled="editingGroup && g.id === editingGroup.id">
                  {{ g.name }}
                </option>
              </select>
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
            <button type="button" class="btn btn-primary" @click="saveGroup" :disabled="saving">
              <span v-if="saving" class="spinner-border spinner-border-sm me-1"></span>
              {{ saving ? 'Saving...' : 'Save' }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Manage Routers Modal -->
    <div class="modal fade" id="routersModal" tabindex="-1" ref="routersModalEl">
      <div class="modal-dialog modal-lg">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">Manage Routers - {{ selectedGroup?.name }}</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
          </div>
          <div class="modal-body">
            <p>Select routers to add to this group:</p>
            <div class="list-group" style="max-height: 400px; overflow-y: auto;">
              <label v-for="router in allRouters" :key="router.id"
                     class="list-group-item list-group-item-action d-flex align-items-center">
                <input type="checkbox" class="form-check-input me-3"
                       v-model="selectedRouterIds" :value="router.id" />
                <div class="flex-grow-1">
                  <div>{{ router.identity || router.ip }}</div>
                  <small class="text-muted">{{ router.ip }}</small>
                </div>
                <span :class="router.is_online ? 'text-success' : 'text-danger'">
                  <i :class="router.is_online ? 'bi bi-circle-fill' : 'bi bi-circle'"></i>
                </span>
              </label>
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
            <button type="button" class="btn btn-primary" @click="saveRouterAssignment">
              Save Changes
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Confirm Delete Modal -->
    <ConfirmModal
      :visible="showDeleteModal"
      title="Delete Group"
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
import { ref, computed, onMounted, nextTick } from 'vue'
import { Modal } from 'bootstrap'
import { useGroupsStore } from '../stores/groups'
import { useAuthStore } from '../stores/auth'
import { routerApi } from '../services/api'
import ConfirmModal from './ConfirmModal.vue'

const groupsStore = useGroupsStore()
const authStore = useAuthStore()

const groups = computed(() => groupsStore.groups)
const loading = computed(() => groupsStore.loading)
const canModify = computed(() => authStore.isOperator)

const showCreateModal = ref(false)
const editingGroup = ref(null)
const selectedGroup = ref(null)
const saving = ref(false)

const groupForm = ref({
  name: '',
  description: '',
  color: '#3498db',
  icon: 'folder',
  parent_id: null
})

const allRouters = ref([])
const selectedRouterIds = ref([])

const groupModalEl = ref(null)
const routersModalEl = ref(null)
let groupModal = null
let routersModal = null

// Delete confirmation state
const showDeleteModal = ref(false)
const deleteModalMessage = ref('')
const groupToDelete = ref(null)
const deleting = ref(false)

onMounted(async () => {
  await groupsStore.fetchGroups()

  // Initialize modals
  nextTick(() => {
    if (groupModalEl.value) {
      groupModal = new Modal(groupModalEl.value)
    }
    if (routersModalEl.value) {
      routersModal = new Modal(routersModalEl.value)
    }
  })
})

function editGroup(group) {
  editingGroup.value = group
  groupForm.value = { ...group }
  groupModal?.show()
}

async function manageRouters(group) {
  selectedGroup.value = group
  try {
    const response = await routerApi.list()
    allRouters.value = response.items

    const groupDetail = await groupsStore.groups.find(g => g.id === group.id)
    selectedRouterIds.value = groupDetail.router_ids || []

    routersModal?.show()
  } catch (error) {
    console.error('Failed to load routers:', error)
  }
}

async function saveGroup() {
  saving.value = true
  try {
    if (editingGroup.value) {
      await groupsStore.updateGroup(editingGroup.value.id, groupForm.value)
    } else {
      await groupsStore.createGroup(groupForm.value)
    }
    groupModal?.hide()
    resetForm()
  } catch (error) {
    console.error('Failed to save group:', error)
  } finally {
    saving.value = false
  }
}

async function saveRouterAssignment() {
  if (!selectedGroup.value) return

  try {
    // Get current routers
    const currentIds = selectedGroup.value.router_ids || []
    const newIds = selectedRouterIds.value

    // Find routers to add and remove
    const toAdd = newIds.filter(id => !currentIds.includes(id))
    const toRemove = currentIds.filter(id => !newIds.includes(id))

    if (toAdd.length > 0) {
      await groupsStore.addRoutersToGroup(selectedGroup.value.id, toAdd)
    }
    if (toRemove.length > 0) {
      await groupsStore.removeRoutersFromGroup(selectedGroup.value.id, toRemove)
    }

    await groupsStore.fetchGroups()
    routersModal?.hide()
  } catch (error) {
    console.error('Failed to update routers:', error)
  }
}

function confirmDelete(group) {
  groupToDelete.value = group
  deleteModalMessage.value = `Are you sure you want to delete the group "${group.name}"? Routers assigned to this group will not be deleted.`
  showDeleteModal.value = true
}

async function handleDeleteConfirm() {
  if (!groupToDelete.value) return
  deleting.value = true
  try {
    await groupsStore.deleteGroup(groupToDelete.value.id)
  } catch (error) {
    console.error('Failed to delete group:', error)
  } finally {
    deleting.value = false
    showDeleteModal.value = false
    groupToDelete.value = null
  }
}

function resetForm() {
  editingGroup.value = null
  groupForm.value = {
    name: '',
    description: '',
    color: '#3498db',
    icon: 'folder',
    parent_id: null
  }
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleDateString()
}
</script>
