import { defineStore } from 'pinia'
import { routerApi, scanApi, taskApi } from '../services/api'

export const useMainStore = defineStore('main', {
  state: () => ({
    // Routers
    routers: [],
    routersLoading: false,
    routerStats: {
      total: 0,
      online: 0,
      offline: 0,
      needsUpdate: 0
    },

    // Selected routers for operations
    selectedRouterIds: [],

    // Tasks
    tasks: [],
    tasksLoading: false,
    currentTask: null,

    // UI state
    notifications: [],
    sidebarOpen: true,
    theme: localStorage.getItem('theme') || 'dark'
  }),

  getters: {
    onlineRouters: (state) => state.routers.filter(r => r.is_online),
    offlineRouters: (state) => state.routers.filter(r => !r.is_online),
    routersNeedingUpdate: (state) => state.routers.filter(r => r.has_updates),
    selectedRouters: (state) => state.routers.filter(r => state.selectedRouterIds.includes(r.id)),

    runningTasks: (state) => state.tasks.filter(t => t.status === 'running'),
    completedTasks: (state) => state.tasks.filter(t => t.status === 'completed'),
    failedTasks: (state) => state.tasks.filter(t => t.status === 'failed')
  },

  actions: {
    // Router actions
    async fetchRouters() {
      this.routersLoading = true
      try {
        const response = await routerApi.list()
        this.routers = response.routers
        this.routerStats = {
          total: response.total,
          online: response.online,
          offline: response.offline,
          needsUpdate: response.needs_update
        }
      } catch (error) {
        this.addNotification('error', `Failed to fetch routers: ${error.message}`)
        throw error
      } finally {
        this.routersLoading = false
      }
    },

    async createRouter(data) {
      try {
        const router = await routerApi.create(data)
        this.routers.push(router)
        this.routerStats.total++
        this.routerStats.offline++
        this.addNotification('success', `Router ${data.ip} added successfully`)
        return router
      } catch (error) {
        this.addNotification('error', `Failed to add router: ${error.message}`)
        throw error
      }
    },

    async updateRouter(id, data) {
      try {
        const router = await routerApi.update(id, data)
        const index = this.routers.findIndex(r => r.id === id)
        if (index !== -1) {
          this.routers[index] = router
        }
        this.addNotification('success', 'Router updated successfully')
        return router
      } catch (error) {
        this.addNotification('error', `Failed to update router: ${error.message}`)
        throw error
      }
    },

    async deleteRouter(id) {
      try {
        await routerApi.delete(id)
        const index = this.routers.findIndex(r => r.id === id)
        if (index !== -1) {
          const router = this.routers[index]
          this.routers.splice(index, 1)
          this.routerStats.total--
          if (router.is_online) {
            this.routerStats.online--
          } else {
            this.routerStats.offline--
          }
        }
        this.addNotification('success', 'Router deleted successfully')
      } catch (error) {
        this.addNotification('error', `Failed to delete router: ${error.message}`)
        throw error
      }
    },

    async importRoutersFromFile() {
      try {
        const result = await routerApi.importFile()
        await this.fetchRouters()
        this.addNotification('success', result.message)
        return result
      } catch (error) {
        this.addNotification('error', `Failed to import routers: ${error.message}`)
        throw error
      }
    },

    // Selection actions
    toggleRouterSelection(id) {
      const index = this.selectedRouterIds.indexOf(id)
      if (index === -1) {
        this.selectedRouterIds.push(id)
      } else {
        this.selectedRouterIds.splice(index, 1)
      }
    },

    selectAllRouters() {
      this.selectedRouterIds = this.routers.map(r => r.id)
    },

    clearSelection() {
      this.selectedRouterIds = []
    },

    // Scan actions
    async startQuickScan(routerIds = null) {
      try {
        const task = await scanApi.quickScan(routerIds)
        this.currentTask = task
        this.addNotification('info', 'Quick scan started')
        return task
      } catch (error) {
        this.addNotification('error', `Failed to start scan: ${error.message}`)
        throw error
      }
    },

    async startFullScan(routerIds = null) {
      try {
        const task = await scanApi.fullScan(routerIds)
        this.currentTask = task
        this.addNotification('info', 'Full scan started')
        return task
      } catch (error) {
        this.addNotification('error', `Failed to start scan: ${error.message}`)
        throw error
      }
    },

    // Task actions
    async fetchTasks() {
      this.tasksLoading = true
      try {
        const response = await taskApi.list()
        this.tasks = response.tasks
      } catch (error) {
        this.addNotification('error', `Failed to fetch tasks: ${error.message}`)
        throw error
      } finally {
        this.tasksLoading = false
      }
    },

    async getTask(id) {
      try {
        return await taskApi.get(id)
      } catch (error) {
        throw error
      }
    },

    async startUpdate(config) {
      try {
        const task = await taskApi.startUpdate(config)
        this.currentTask = task
        this.tasks.unshift(task)
        this.addNotification('info', 'Update task started')
        return task
      } catch (error) {
        this.addNotification('error', `Failed to start update: ${error.message}`)
        throw error
      }
    },

    async cancelTask(id) {
      try {
        await taskApi.cancel(id)
        const task = this.tasks.find(t => t.id === id)
        if (task) {
          task.status = 'cancelled'
        }
        if (this.currentTask?.id === id) {
          this.currentTask.status = 'cancelled'
        }
        this.addNotification('info', 'Task cancelled')
      } catch (error) {
        this.addNotification('error', `Failed to cancel task: ${error.message}`)
        throw error
      }
    },

    updateTaskProgress(taskId, progress) {
      const task = this.tasks.find(t => t.id === taskId)
      if (task) {
        Object.assign(task, progress)
      }
      if (this.currentTask?.id === taskId) {
        Object.assign(this.currentTask, progress)
      }
    },

    // Notification actions
    addNotification(type, message) {
      const id = Date.now()
      this.notifications.push({ id, type, message })

      // Auto-remove after 5 seconds
      setTimeout(() => {
        this.removeNotification(id)
      }, 5000)
    },

    removeNotification(id) {
      const index = this.notifications.findIndex(n => n.id === id)
      if (index !== -1) {
        this.notifications.splice(index, 1)
      }
    },

    // UI actions
    toggleSidebar() {
      this.sidebarOpen = !this.sidebarOpen
    },

    toggleTheme() {
      this.theme = this.theme === 'dark' ? 'light' : 'dark'
      localStorage.setItem('theme', this.theme)
      document.documentElement.setAttribute('data-theme', this.theme)
    },

    initTheme() {
      document.documentElement.setAttribute('data-theme', this.theme)
    }
  }
})
