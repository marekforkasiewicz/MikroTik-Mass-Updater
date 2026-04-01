import { computed, ref } from 'vue'

export function useSettingsUsers({ usersApi, authStore, mainStore }) {
  const users = ref([])
  const showUserModal = ref(false)
  const editingUser = ref(null)
  const userForm = ref({
    username: '',
    email: '',
    full_name: '',
    role: 'viewer',
    password: '',
    is_active: true
  })

  const isAdmin = computed(() => authStore.isAdmin)
  const currentUser = computed(() => authStore.user)

  async function loadUsers() {
    if (!isAdmin.value) return

    try {
      const response = await usersApi.list()
      users.value = response.items || []
    } catch (error) {
      console.error('Failed to load users:', error)
    }
  }

  function getRoleBadge(role) {
    const badges = {
      admin: 'badge bg-danger',
      operator: 'badge bg-primary',
      viewer: 'badge bg-secondary'
    }
    return badges[role] || 'badge bg-secondary'
  }

  function resetUserForm() {
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

  function editUser(user, showModal) {
    editingUser.value = user
    userForm.value = { ...user, password: '' }
    showModal?.()
  }

  async function saveUser() {
    const data = { ...userForm.value }
    if (!data.password) {
      delete data.password
    }

    if (editingUser.value?.id) {
      await usersApi.update(editingUser.value.id, data)
    } else {
      await usersApi.create(data)
    }

    await loadUsers()
    mainStore.addNotification('success', 'User saved')
  }

  return {
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
    saveUser
  }
}
