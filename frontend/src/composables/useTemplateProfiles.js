import { ref } from 'vue'

export function useTemplateProfiles({ templatesApi, notify }) {
  const profiles = ref([])
  const showProfilesModal = ref(false)
  const showProfileEditModal = ref(false)
  const editingProfile = ref(null)
  const savingProfile = ref(false)
  const profileModelFilter = ref('')
  const profileArchFilter = ref('')
  const profileVariablesJson = ref('{}')
  const matchingRouters = ref([])

  async function loadProfiles() {
    try {
      const response = await templatesApi.listProfiles()
      profiles.value = response.items || []
    } catch (error) {
      console.error('Failed to load profiles:', error)
    }
  }

  function newProfile() {
    editingProfile.value = {
      name: '',
      description: '',
      device_filter: { model: [], architecture: [] },
      template_ids: [],
      variables: {},
      is_active: true
    }
    profileModelFilter.value = ''
    profileArchFilter.value = ''
    profileVariablesJson.value = '{}'
    matchingRouters.value = []
    showProfileEditModal.value = true
  }

  async function loadMatchingRouters(profileId) {
    try {
      const response = await templatesApi.getProfileRouters(profileId)
      matchingRouters.value = response.routers || []
    } catch (error) {
      matchingRouters.value = []
    }
  }

  function editProfile(profile) {
    editingProfile.value = {
      ...profile,
      template_ids: profile.template_ids || []
    }
    profileModelFilter.value = (profile.device_filter?.model || []).join(', ')
    profileArchFilter.value = (profile.device_filter?.architecture || []).join(', ')
    profileVariablesJson.value = JSON.stringify(profile.variables || {}, null, 2)
    loadMatchingRouters(profile.id)
    showProfileEditModal.value = true
  }

  async function saveProfile(hideModal) {
    if (!editingProfile.value?.name) {
      notify('warning', 'Name is required')
      return
    }

    const modelPatterns = profileModelFilter.value
      ? profileModelFilter.value.split(',').map((value) => value.trim()).filter(Boolean)
      : []
    const archPatterns = profileArchFilter.value
      ? profileArchFilter.value.split(',').map((value) => value.trim()).filter(Boolean)
      : []

    let variables = {}
    try {
      if (profileVariablesJson.value.trim()) {
        variables = JSON.parse(profileVariablesJson.value)
      }
    } catch {
      notify('error', 'Invalid JSON in variables')
      return
    }

    const profileData = {
      name: editingProfile.value.name,
      description: editingProfile.value.description,
      device_filter: { model: modelPatterns, architecture: archPatterns },
      template_ids: editingProfile.value.template_ids,
      variables,
      is_active: editingProfile.value.is_active
    }

    savingProfile.value = true
    try {
      if (editingProfile.value.id) {
        await templatesApi.updateProfile(editingProfile.value.id, profileData)
      } else {
        await templatesApi.createProfile(profileData)
      }
      await loadProfiles()
      hideModal?.()
      showProfileEditModal.value = false
      notify('success', 'Profile saved')
    } catch (error) {
      console.error('Failed to save profile:', error)
      notify('error', `Failed to save profile: ${error.message}`)
    } finally {
      savingProfile.value = false
    }
  }

  async function deleteProfile(profile) {
    if (!confirm(`Delete profile "${profile.name}"?`)) return

    try {
      await templatesApi.deleteProfile(profile.id)
      await loadProfiles()
      notify('success', 'Profile deleted')
    } catch (error) {
      console.error('Failed to delete profile:', error)
      notify('error', 'Failed to delete profile')
    }
  }

  return {
    profiles,
    showProfilesModal,
    showProfileEditModal,
    editingProfile,
    savingProfile,
    profileModelFilter,
    profileArchFilter,
    profileVariablesJson,
    matchingRouters,
    loadProfiles,
    newProfile,
    editProfile,
    saveProfile,
    deleteProfile
  }
}
