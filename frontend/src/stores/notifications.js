import { defineStore } from 'pinia'
import { ref } from 'vue'
import { notificationsApi } from '../services/api'

export const useNotificationsStore = defineStore('notifications', () => {
  // State
  const channels = ref([])
  const rules = ref([])
  const logs = ref([])
  const loading = ref(false)

  // Actions
  async function fetchChannels() {
    loading.value = true
    try {
      const response = await notificationsApi.listChannels()
      channels.value = response.items
      return channels.value
    } catch (error) {
      console.error('Failed to fetch channels:', error)
      throw error
    } finally {
      loading.value = false
    }
  }

  async function createChannel(data) {
    try {
      const channel = await notificationsApi.createChannel(data)
      channels.value.push(channel)
      return channel
    } catch (error) {
      console.error('Failed to create channel:', error)
      throw error
    }
  }

  async function updateChannel(id, data) {
    try {
      const channel = await notificationsApi.updateChannel(id, data)
      const index = channels.value.findIndex(c => c.id === id)
      if (index !== -1) {
        channels.value[index] = channel
      }
      return channel
    } catch (error) {
      console.error('Failed to update channel:', error)
      throw error
    }
  }

  async function deleteChannel(id) {
    try {
      await notificationsApi.deleteChannel(id)
      channels.value = channels.value.filter(c => c.id !== id)
    } catch (error) {
      console.error('Failed to delete channel:', error)
      throw error
    }
  }

  async function testChannel(id, message) {
    try {
      return await notificationsApi.testChannel(id, message)
    } catch (error) {
      console.error('Failed to test channel:', error)
      throw error
    }
  }

  async function fetchRules(channelId = null) {
    try {
      const response = await notificationsApi.listRules({ channel_id: channelId })
      rules.value = response.items
      return rules.value
    } catch (error) {
      console.error('Failed to fetch rules:', error)
      throw error
    }
  }

  async function createRule(data) {
    try {
      const rule = await notificationsApi.createRule(data)
      rules.value.push(rule)
      return rule
    } catch (error) {
      console.error('Failed to create rule:', error)
      throw error
    }
  }

  async function updateRule(id, data) {
    try {
      const rule = await notificationsApi.updateRule(id, data)
      const index = rules.value.findIndex(r => r.id === id)
      if (index !== -1) {
        rules.value[index] = rule
      }
      return rule
    } catch (error) {
      console.error('Failed to update rule:', error)
      throw error
    }
  }

  async function deleteRule(id) {
    try {
      await notificationsApi.deleteRule(id)
      rules.value = rules.value.filter(r => r.id !== id)
    } catch (error) {
      console.error('Failed to delete rule:', error)
      throw error
    }
  }

  async function fetchLogs(params = {}) {
    try {
      const response = await notificationsApi.getLogs(params)
      logs.value = response.items
      return logs.value
    } catch (error) {
      console.error('Failed to fetch logs:', error)
      throw error
    }
  }

  return {
    channels,
    rules,
    logs,
    loading,
    fetchChannels,
    createChannel,
    updateChannel,
    deleteChannel,
    testChannel,
    fetchRules,
    createRule,
    updateRule,
    deleteRule,
    fetchLogs
  }
})
