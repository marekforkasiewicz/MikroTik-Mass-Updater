<template>
  <div>
    <div class="d-flex justify-content-between align-items-center mb-4">
      <h2>Network Scan</h2>
      <div>
        <button class="btn btn-success me-2" @click="startQuickScan" :disabled="scanning">
          <i class="bi bi-lightning me-1"></i>
          Quick Scan
        </button>
        <button class="btn btn-primary" @click="startFullScan" :disabled="scanning">
          <i class="bi bi-search me-1"></i>
          Full Scan
        </button>
      </div>
    </div>

    <!-- Scan progress -->
    <div class="card mb-4" v-if="scanning || taskProgress">
      <div class="card-header">
        <h5 class="mb-0">
          <i class="bi bi-gear spin me-2" v-if="scanning"></i>
          {{ scanning ? 'Scanning...' : 'Scan Complete' }}
        </h5>
      </div>
      <div class="card-body">
        <div class="d-flex justify-content-between mb-2">
          <span>{{ taskProgress?.current_item || 'Starting...' }}</span>
          <span>{{ taskProgress?.progress || 0 }}/{{ taskProgress?.total || 0 }}</span>
        </div>
        <div class="progress task-progress">
          <div
            class="progress-bar"
            :class="{ 'progress-bar-striped progress-bar-animated': scanning }"
            :style="{ width: `${progressPercent}%` }"
          ></div>
        </div>
      </div>
    </div>

    <!-- Scan results -->
    <div class="card" v-if="scanResults">
      <div class="card-header d-flex justify-content-between align-items-center">
        <h5 class="mb-0">Scan Results</h5>
        <div>
          <span class="badge bg-success me-2">{{ scanResults.online || scanResults.successful }} Online</span>
          <span class="badge bg-danger">{{ (scanResults.total - (scanResults.online || scanResults.successful)) }} Offline</span>
        </div>
      </div>
      <div class="table-responsive">
        <table class="table table-hover mb-0 router-table">
          <thead>
            <tr>
              <th>IP Address</th>
              <th>Ping</th>
              <th>Latency</th>
              <th v-if="isQuickScan">API Port</th>
              <th v-if="isQuickScan">SSH Port</th>
              <th>Identity</th>
              <th>RouterOS</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="result in scanResults.results" :key="result.ip">
              <td><code>{{ result.ip }}</code></td>
              <td>
                <i
                  class="bi"
                  :class="{
                    'bi-check-circle-fill status-online': result.ping_ok || result.success,
                    'bi-x-circle-fill status-offline': !(result.ping_ok || result.success)
                  }"
                ></i>
              </td>
              <td>
                <span v-if="result.ping_ms">{{ result.ping_ms.toFixed(1) }} ms</span>
                <span v-else>-</span>
              </td>
              <td v-if="isQuickScan">
                <i
                  class="bi"
                  :class="{
                    'bi-check-circle-fill status-online': result.port_api_open,
                    'bi-x-circle-fill status-offline': !result.port_api_open
                  }"
                ></i>
              </td>
              <td v-if="isQuickScan">
                <i
                  class="bi"
                  :class="{
                    'bi-check-circle-fill status-online': result.port_ssh_open,
                    'bi-x-circle-fill status-offline': !result.port_ssh_open
                  }"
                ></i>
              </td>
              <td>{{ result.identity || '-' }}</td>
              <td>{{ result.ros_version || '-' }}</td>
              <td>
                <span
                  class="badge"
                  :class="getStatusBadgeClass(result)"
                >
                  {{ result.status || (result.success ? 'OK' : result.error || 'Error') }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Empty state -->
    <div class="card" v-else-if="!scanning">
      <div class="card-body text-center py-5">
        <i class="bi bi-wifi-off fs-1 text-muted mb-3 d-block"></i>
        <h5>No Scan Results</h5>
        <p class="text-muted">Start a scan to check your network routers</p>
        <button class="btn btn-primary" @click="startQuickScan">
          <i class="bi bi-lightning me-1"></i>
          Start Quick Scan
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onUnmounted } from 'vue'
import { useMainStore } from '../stores/main'
import { createTaskWebSocket } from '../services/api'

const store = useMainStore()

const scanning = ref(false)
const taskProgress = ref(null)
const scanResults = ref(null)
const isQuickScan = ref(true)
let ws = null

const progressPercent = computed(() => {
  if (!taskProgress.value || !taskProgress.value.total) return 0
  return Math.round((taskProgress.value.progress / taskProgress.value.total) * 100)
})

const startQuickScan = async () => {
  scanning.value = true
  isQuickScan.value = true
  taskProgress.value = null
  scanResults.value = null

  try {
    const task = await store.startQuickScan()
    connectWebSocket(task.id)
  } catch (error) {
    scanning.value = false
  }
}

const startFullScan = async () => {
  scanning.value = true
  isQuickScan.value = false
  taskProgress.value = null
  scanResults.value = null

  try {
    const task = await store.startFullScan()
    connectWebSocket(task.id)
  } catch (error) {
    scanning.value = false
  }
}

const connectWebSocket = (taskId) => {
  if (ws) {
    ws.close()
  }

  ws = createTaskWebSocket(
    taskId,
    (data) => {
      taskProgress.value = data

      if (data.complete || data.status === 'completed' || data.status === 'failed') {
        scanning.value = false
        if (data.results) {
          scanResults.value = data.results
        }
        // Refresh router list
        store.fetchRouters()
      }
    },
    (error) => {
      scanning.value = false
      store.addNotification('error', 'WebSocket connection failed')
    }
  )
}

const getStatusBadgeClass = (result) => {
  if (result.success || (result.ping_ok && result.port_api_open)) {
    return 'bg-success'
  } else if (result.ping_ok) {
    return 'bg-warning text-dark'
  }
  return 'bg-danger'
}

onUnmounted(() => {
  if (ws) {
    ws.close()
  }
})
</script>
