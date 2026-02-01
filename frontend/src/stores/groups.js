import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { groupsApi } from '../services/api'

export const useGroupsStore = defineStore('groups', () => {
  // State
  const groups = ref([])
  const groupTree = ref([])
  const currentGroup = ref(null)
  const loading = ref(false)

  // Computed
  const groupCount = computed(() => groups.value.length)

  // Actions
  async function fetchGroups() {
    loading.value = true
    try {
      const response = await groupsApi.list()
      groups.value = response.items
      return groups.value
    } catch (error) {
      console.error('Failed to fetch groups:', error)
      throw error
    } finally {
      loading.value = false
    }
  }

  async function fetchGroupTree() {
    try {
      groupTree.value = await groupsApi.getTree()
      return groupTree.value
    } catch (error) {
      console.error('Failed to fetch group tree:', error)
      throw error
    }
  }

  async function createGroup(data) {
    try {
      const group = await groupsApi.create(data)
      groups.value.push(group)
      return group
    } catch (error) {
      console.error('Failed to create group:', error)
      throw error
    }
  }

  async function updateGroup(id, data) {
    try {
      const group = await groupsApi.update(id, data)
      const index = groups.value.findIndex(g => g.id === id)
      if (index !== -1) {
        groups.value[index] = group
      }
      return group
    } catch (error) {
      console.error('Failed to update group:', error)
      throw error
    }
  }

  async function deleteGroup(id) {
    try {
      await groupsApi.delete(id)
      groups.value = groups.value.filter(g => g.id !== id)
    } catch (error) {
      console.error('Failed to delete group:', error)
      throw error
    }
  }

  async function addRoutersToGroup(groupId, routerIds) {
    try {
      const group = await groupsApi.addRouters(groupId, routerIds)
      const index = groups.value.findIndex(g => g.id === groupId)
      if (index !== -1) {
        groups.value[index] = group
      }
      return group
    } catch (error) {
      console.error('Failed to add routers to group:', error)
      throw error
    }
  }

  async function removeRoutersFromGroup(groupId, routerIds) {
    try {
      const group = await groupsApi.removeRouters(groupId, routerIds)
      const index = groups.value.findIndex(g => g.id === groupId)
      if (index !== -1) {
        groups.value[index] = group
      }
      return group
    } catch (error) {
      console.error('Failed to remove routers from group:', error)
      throw error
    }
  }

  return {
    groups,
    groupTree,
    currentGroup,
    loading,
    groupCount,
    fetchGroups,
    fetchGroupTree,
    createGroup,
    updateGroup,
    deleteGroup,
    addRoutersToGroup,
    removeRoutersFromGroup
  }
})
