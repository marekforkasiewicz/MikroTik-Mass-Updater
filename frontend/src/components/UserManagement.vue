<template>
  <div class="container-fluid py-4">
    <div class="d-flex justify-content-between align-items-center mb-4">
      <h2><i class="bi bi-people me-2"></i>User Management</h2>
      <button class="btn btn-primary" @click="showModal = true">
        <i class="bi bi-plus-lg me-1"></i> Add User
      </button>
    </div>

    <!-- Users Table -->
    <div class="card">
      <div class="card-body">
        <div class="table-responsive">
          <table class="table table-hover">
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
                <td>
                  <span :class="roleBadge(user.role)">{{ user.role }}</span>
                </td>
                <td>
                  <span :class="user.is_active ? 'text-success' : 'text-danger'">
                    <i :class="user.is_active ? 'bi bi-check-circle-fill' : 'bi bi-x-circle-fill'"></i>
                    {{ user.is_active ? 'Active' : 'Inactive' }}
                  </span>
                </td>
                <td>{{ formatDate(user.last_login) }}</td>
                <td>
                  <div class="btn-group btn-group-sm">
                    <button class="btn btn-outline-secondary" @click="editUser(user)" title="Edit">
                      <i class="bi bi-pencil"></i>
                    </button>
                    <button class="btn btn-outline-danger" @click="deleteUser(user)" title="Delete"
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
              <input type="text" class="form-control" v-model="userForm.username"
                     :disabled="editingUser?.id" />
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
            <div class="mb-3" v-if="!editingUser?.id">
              <label class="form-label">Password</label>
              <input type="password" class="form-control" v-model="userForm.password" />
            </div>
            <div class="mb-3" v-else>
              <label class="form-label">New Password (leave empty to keep current)</label>
              <input type="password" class="form-control" v-model="userForm.password" />
            </div>
            <div class="form-check">
              <input type="checkbox" class="form-check-input" v-model="userForm.is_active" id="isActive" />
              <label class="form-check-label" for="isActive">Active</label>
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
            <button type="button" class="btn btn-primary" @click="saveUser" :disabled="saving">
              <span v-if="saving" class="spinner-border spinner-border-sm me-1"></span>
              Save
            </button>
          </div>
        </div>
      </div>
    </div>
    <!-- Confirm Delete Modal -->
    <ConfirmModal
      :visible="showDeleteModal"
      title="Delete User"
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
import { usersApi } from '../services/api'
import { useAuthStore } from '../stores/auth'
import { useMainStore } from '../stores/main'
import ConfirmModal from './ConfirmModal.vue'

const mainStore = useMainStore()

const authStore = useAuthStore()
const currentUser = computed(() => authStore.user)

const users = ref([])
const showModal = ref(false)
const editingUser = ref(null)
const saving = ref(false)

const userForm = ref({
  username: '',
  email: '',
  full_name: '',
  role: 'viewer',
  password: '',
  is_active: true
})

const userModalEl = ref(null)
let userModal = null

// Delete confirmation state
const showDeleteModal = ref(false)
const deleteModalMessage = ref('')
const userToDelete = ref(null)
const deleting = ref(false)

onMounted(async () => {
  await loadUsers()

  nextTick(() => {
    if (userModalEl.value) userModal = new Modal(userModalEl.value)
  })
})

watch(showModal, (val) => {
  if (val) {
    resetForm()
    userModal?.show()
  }
})

async function loadUsers() {
  try {
    const response = await usersApi.list()
    users.value = response.items
  } catch (error) {
    console.error('Failed to load users:', error)
  }
}

function editUser(user) {
  editingUser.value = user
  userForm.value = {
    username: user.username,
    email: user.email,
    full_name: user.full_name,
    role: user.role,
    password: '',
    is_active: user.is_active
  }
  userModal?.show()
}

async function saveUser() {
  saving.value = true
  try {
    const data = { ...userForm.value }
    if (!data.password) delete data.password

    if (editingUser.value?.id) {
      await usersApi.update(editingUser.value.id, data)
    } else {
      await usersApi.create(data)
    }
    userModal?.hide()
    await loadUsers()
    mainStore.addNotification('success', 'User saved successfully')
  } catch (error) {
    console.error('Failed to save user:', error)
    mainStore.addNotification('error', 'Failed to save user: ' + error.message)
  } finally {
    saving.value = false
  }
}

function deleteUser(user) {
  userToDelete.value = user
  deleteModalMessage.value = `Are you sure you want to delete user "${user.username}"? This action cannot be undone.`
  showDeleteModal.value = true
}

async function handleDeleteConfirm() {
  if (!userToDelete.value) return
  deleting.value = true
  try {
    await usersApi.delete(userToDelete.value.id)
    await loadUsers()
    mainStore.addNotification('success', 'User deleted successfully')
  } catch (error) {
    console.error('Failed to delete user:', error)
    mainStore.addNotification('error', 'Failed to delete user')
  } finally {
    deleting.value = false
    showDeleteModal.value = false
    userToDelete.value = null
  }
}

function resetForm() {
  editingUser.value = null
  userForm.value = {
    username: '',
    email: '',
    full_name: '',
    role: 'viewer',
    password: '',
    is_active: true
  }
}

function roleBadge(role) {
  const badges = {
    admin: 'badge bg-danger',
    operator: 'badge bg-primary',
    viewer: 'badge bg-secondary'
  }
  return badges[role] || 'badge bg-secondary'
}

function formatDate(dateStr) {
  if (!dateStr) return 'Never'
  return new Date(dateStr).toLocaleString()
}
</script>
