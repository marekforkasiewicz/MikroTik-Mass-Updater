import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { schedulesApi } from '../services/api'

export const useSchedulesStore = defineStore('schedules', () => {
  // State
  const schedules = ref([])
  const currentSchedule = ref(null)
  const executions = ref([])
  const loading = ref(false)

  // Computed
  const enabledSchedules = computed(() =>
    schedules.value.filter(s => s.enabled)
  )
  const upcomingSchedules = computed(() =>
    schedules.value
      .filter(s => s.enabled && s.next_run)
      .sort((a, b) => new Date(a.next_run) - new Date(b.next_run))
      .slice(0, 5)
  )

  // Actions
  async function fetchSchedules() {
    loading.value = true
    try {
      const response = await schedulesApi.list()
      schedules.value = response.items
      return schedules.value
    } catch (error) {
      console.error('Failed to fetch schedules:', error)
      throw error
    } finally {
      loading.value = false
    }
  }

  async function createSchedule(data) {
    try {
      const schedule = await schedulesApi.create(data)
      schedules.value.push(schedule)
      return schedule
    } catch (error) {
      console.error('Failed to create schedule:', error)
      throw error
    }
  }

  async function updateSchedule(id, data) {
    try {
      const schedule = await schedulesApi.update(id, data)
      const index = schedules.value.findIndex(s => s.id === id)
      if (index !== -1) {
        schedules.value[index] = schedule
      }
      return schedule
    } catch (error) {
      console.error('Failed to update schedule:', error)
      throw error
    }
  }

  async function deleteSchedule(id) {
    try {
      await schedulesApi.delete(id)
      schedules.value = schedules.value.filter(s => s.id !== id)
    } catch (error) {
      console.error('Failed to delete schedule:', error)
      throw error
    }
  }

  async function enableSchedule(id) {
    try {
      const schedule = await schedulesApi.enable(id)
      const index = schedules.value.findIndex(s => s.id === id)
      if (index !== -1) {
        schedules.value[index] = schedule
      }
      return schedule
    } catch (error) {
      console.error('Failed to enable schedule:', error)
      throw error
    }
  }

  async function disableSchedule(id) {
    try {
      const schedule = await schedulesApi.disable(id)
      const index = schedules.value.findIndex(s => s.id === id)
      if (index !== -1) {
        schedules.value[index] = schedule
      }
      return schedule
    } catch (error) {
      console.error('Failed to disable schedule:', error)
      throw error
    }
  }

  async function runNow(id) {
    try {
      return await schedulesApi.runNow(id)
    } catch (error) {
      console.error('Failed to run schedule:', error)
      throw error
    }
  }

  async function fetchExecutions(scheduleId) {
    try {
      const response = await schedulesApi.getExecutions(scheduleId)
      executions.value = response.items
      return executions.value
    } catch (error) {
      console.error('Failed to fetch executions:', error)
      throw error
    }
  }

  async function describeCron(expression) {
    try {
      return await schedulesApi.describeCron(expression)
    } catch (error) {
      console.error('Failed to describe cron:', error)
      throw error
    }
  }

  return {
    schedules,
    currentSchedule,
    executions,
    loading,
    enabledSchedules,
    upcomingSchedules,
    fetchSchedules,
    createSchedule,
    updateSchedule,
    deleteSchedule,
    enableSchedule,
    disableSchedule,
    runNow,
    fetchExecutions,
    describeCron
  }
})
