<template>
  <Teleport to="body">
    <div v-if="visible" class="modal fade show" tabindex="-1" style="display: block;">
      <div class="modal-dialog modal-lg modal-dialog-centered">
        <div class="modal-content">
          <div class="modal-header" :class="headerClass">
            <h5 class="modal-title">
              <i :class="iconClass" class="me-2"></i>
              {{ title }}
            </h5>
            <button
              type="button"
              class="btn-close btn-close-white"
              @click="handleClose"
              :disabled="isRunning && !canClose"
            ></button>
          </div>

          <div class="modal-body p-0">
            <!-- Progress bar -->
            <div class="progress rounded-0" style="height: 4px;" v-if="isRunning">
              <div
                class="progress-bar progress-bar-striped progress-bar-animated"
                :class="progressBarClass"
                :style="{ width: progressPercent + '%' }"
              ></div>
            </div>

            <!-- Status banner -->
            <div class="status-banner px-3 py-2" :class="statusBannerClass">
              <div class="d-flex align-items-center justify-content-between">
                <div>
                  <span class="fw-semibold">{{ statusText }}</span>
                  <span v-if="currentStep" class="ms-2 text-muted">{{ currentStep }}</span>
                </div>
                <div v-if="isRunning">
                  <span class="spinner-border spinner-border-sm me-1"></span>
                  {{ elapsedTime }}
                </div>
                <div v-else-if="isComplete">
                  <i class="bi bi-check-circle-fill text-success me-1"></i>
                  {{ elapsedTime }}
                </div>
                <div v-else-if="isFailed">
                  <i class="bi bi-x-circle-fill text-danger me-1"></i>
                  {{ elapsedTime }}
                </div>
              </div>
            </div>

            <!-- Console output -->
            <div class="console-output" ref="consoleRef">
              <div
                v-for="(line, index) in consoleLines"
                :key="index"
                class="console-line"
                :class="'console-' + line.type"
              >
                <span class="console-time">{{ line.time }}</span>
                <span class="console-text">{{ line.text }}</span>
              </div>
              <div v-if="consoleLines.length === 0" class="console-line console-muted">
                Waiting for operation to start...
              </div>
            </div>
          </div>

          <div class="modal-footer">
            <div class="me-auto" v-if="waitingForReboot">
              <span class="text-warning">
                <i class="bi bi-hourglass-split spin me-1"></i>
                Waiting for router to come back online...
              </span>
            </div>
            <button
              type="button"
              class="btn btn-secondary"
              @click="handleClose"
              :disabled="isRunning && !canClose"
            >
              {{ closeButtonText }}
            </button>
            <button
              v-if="isComplete || isFailed"
              type="button"
              class="btn btn-primary"
              @click="refreshAndClose"
            >
              <i class="bi bi-arrow-clockwise me-1"></i>
              Refresh & Close
            </button>
          </div>
        </div>
      </div>
    </div>
    <div v-if="visible" class="modal-backdrop fade show"></div>
  </Teleport>
</template>

<script setup>
import { ref, computed, watch, onUnmounted, nextTick } from 'vue'
import { createTaskWebSocket, scanApi } from '../services/api'
import { useMainStore } from '../stores/main'

const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  router: {
    type: Object,
    default: null
  },
  taskId: {
    type: String,
    default: null
  },
  upgradeType: {
    type: String,
    default: 'firmware', // 'firmware' or 'routeros'
    validator: (v) => ['firmware', 'routeros'].includes(v)
  }
})

const emit = defineEmits(['close', 'complete'])

const store = useMainStore()
const consoleRef = ref(null)
const consoleLines = ref([])
const status = ref('pending') // pending, running, complete, failed
const currentStep = ref('')
const startTime = ref(null)
const elapsedTime = ref('0s')
const elapsedTimer = ref(null)
const ws = ref(null)
const waitingForReboot = ref(false)
const rebootCheckTimer = ref(null)
const canClose = ref(false)
const lastMessage = ref('')
const expectedFirmware = ref(null) // Expected firmware version after upgrade
const previousFirmware = ref(null) // Firmware version before upgrade

const title = computed(() => {
  const routerName = props.router?.identity || props.router?.ip || 'Router'
  return props.upgradeType === 'firmware'
    ? `Firmware Upgrade - ${routerName}`
    : `RouterOS Upgrade - ${routerName}`
})

const isRunning = computed(() => status.value === 'running' || status.value === 'pending')
const isComplete = computed(() => status.value === 'complete')
const isFailed = computed(() => status.value === 'failed')

const headerClass = computed(() => {
  if (isFailed.value) return 'bg-danger text-white'
  if (isComplete.value) return 'bg-success text-white'
  return 'bg-primary text-white'
})

const iconClass = computed(() => {
  if (props.upgradeType === 'firmware') return 'bi bi-cpu'
  return 'bi bi-arrow-up-circle'
})

const progressBarClass = computed(() => {
  if (isFailed.value) return 'bg-danger'
  if (isComplete.value) return 'bg-success'
  return 'bg-primary'
})

const progressPercent = computed(() => {
  if (isComplete.value) return 100
  if (isFailed.value) return 100
  if (waitingForReboot.value) return 90
  return 50
})

const statusBannerClass = computed(() => {
  if (isFailed.value) return 'bg-danger-subtle'
  if (isComplete.value) return 'bg-success-subtle'
  if (waitingForReboot.value) return 'bg-warning-subtle'
  return 'bg-light'
})

const statusText = computed(() => {
  if (isFailed.value) return 'Upgrade Failed'
  if (isComplete.value) return 'Upgrade Complete'
  if (waitingForReboot.value) return 'Rebooting...'
  if (status.value === 'running') return 'Upgrading...'
  return 'Starting...'
})

const closeButtonText = computed(() => {
  if (isRunning.value && !canClose.value) return 'Running...'
  return 'Close'
})

const addConsoleLine = (text, type = 'normal') => {
  const now = new Date()
  const time = now.toLocaleTimeString('en-US', { hour12: false })
  consoleLines.value.push({ time, text, type })

  nextTick(() => {
    if (consoleRef.value) {
      consoleRef.value.scrollTop = consoleRef.value.scrollHeight
    }
  })
}

const updateElapsedTime = () => {
  if (!startTime.value) return
  const elapsed = Math.floor((Date.now() - startTime.value) / 1000)
  const mins = Math.floor(elapsed / 60)
  const secs = elapsed % 60
  elapsedTime.value = mins > 0 ? `${mins}m ${secs}s` : `${secs}s`
}

const connectWebSocket = (taskId) => {
  if (ws.value) {
    ws.value.close()
  }

  ws.value = createTaskWebSocket(
    taskId,
    (data) => {
      // Handle progress updates
      if (data.current_item) {
        currentStep.value = data.current_item
      }

      // Handle current message from backend
      if (data.current_message && data.current_message !== lastMessage.value) {
        lastMessage.value = data.current_message
        // Determine message type based on content
        let msgType = 'normal'
        if (data.current_message.includes('SUCCESS') || data.current_message.includes('Connected')) {
          msgType = 'success'
        } else if (data.current_message.includes('FAILED') || data.current_message.includes('Error')) {
          msgType = 'error'
        } else if (data.current_message.includes('Host:') || data.current_message.includes('backup')) {
          msgType = 'info'
        }
        addConsoleLine(data.current_message, msgType)
      }

      if (data.message) {
        addConsoleLine(data.message, data.level || 'normal')
      }

      // Handle completion
      if (data.complete || data.status === 'completed') {
        handleTaskComplete(data)
      } else if (data.status === 'failed') {
        handleTaskFailed(data)
      }

      // Handle individual results (just log, don't start reboot watch - handleTaskComplete does that)
      if (data.results?.results) {
        data.results.results.forEach(result => {
          if (result.success) {
            addConsoleLine(`${result.ip}: Success`, 'success')
          } else {
            addConsoleLine(`${result.ip}: ${result.error}`, 'error')
          }
        })
      }
    },
    (error) => {
      addConsoleLine('WebSocket connection error', 'error')
      status.value = 'failed'
      canClose.value = true
    }
  )
}

const handleTaskComplete = (data) => {
  // Prevent duplicate handling
  if (waitingForReboot.value || status.value === 'complete') return

  const results = data.results
  if (results && results.results?.length > 0) {
    addConsoleLine(`Completed: ${results.successful} successful, ${results.failed} failed`, 'info')

    // Check if reboot is needed
    const routerResult = results.results.find(r => r.router_id === props.router?.id || r.ip === props.router?.ip)
    if (routerResult?.firmware_upgraded || routerResult?.rebooted) {
      startRebootWatch()
      return
    }

    // No reboot needed, mark as complete
    status.value = 'complete'
    canClose.value = true
    addConsoleLine('Upgrade process completed', 'success')
  }
  // If no results yet, don't mark as complete - wait for message with results
}

const handleTaskFailed = (data) => {
  status.value = 'failed'
  canClose.value = true
  if (data.error) {
    addConsoleLine(`Error: ${data.error}`, 'error')
  }
}

const startRebootWatch = () => {
  if (waitingForReboot.value) {
    return  // Already watching for reboot
  }

  if (!props.router?.id) {
    addConsoleLine('Cannot watch for reboot: router data unavailable', 'error')
    status.value = 'failed'
    canClose.value = true
    return
  }

  // Store expected firmware from router's upgrade_firmware field
  if (props.upgradeType === 'firmware' && props.router?.upgrade_firmware) {
    expectedFirmware.value = props.router.upgrade_firmware
    previousFirmware.value = props.router?.firmware
    addConsoleLine(`Expected firmware after upgrade: ${expectedFirmware.value}`, 'info')
  }

  waitingForReboot.value = true
  addConsoleLine('Router is rebooting, waiting for it to come back online...', 'warning')

  let attempts = 0
  const maxAttempts = 60 // 5 minutes max
  const routerId = props.router.id  // Capture router ID to avoid stale props
  const isFirmwareUpgrade = props.upgradeType === 'firmware'

  const checkRouter = async () => {
    attempts++
    try {
      addConsoleLine(`Checking router status (attempt ${attempts})...`, 'muted')

      // For firmware upgrade, use checkFirmware to verify
      if (isFirmwareUpgrade) {
        const result = await scanApi.checkFirmware(routerId)

        if (!result.success) {
          throw new Error(result.error || 'Failed to connect')
        }

        // Router is back online
        addConsoleLine('Router is back online!', 'success')

        // Verify firmware upgrade
        const currentFw = result.current_firmware
        const upgradeFw = result.upgrade_firmware

        addConsoleLine(`Current firmware: ${currentFw}`, 'info')

        if (expectedFirmware.value && currentFw === expectedFirmware.value) {
          addConsoleLine(`Firmware upgrade VERIFIED: ${previousFirmware.value || 'unknown'} -> ${currentFw}`, 'success')
        } else if (currentFw === upgradeFw) {
          addConsoleLine('Firmware is up to date (no upgrade needed)', 'success')
        } else if (currentFw !== upgradeFw && upgradeFw) {
          addConsoleLine(`WARNING: Firmware still needs upgrade: ${currentFw} -> ${upgradeFw}`, 'warning')
        } else {
          addConsoleLine(`Firmware: ${currentFw}`, 'info')
        }
      } else {
        // For RouterOS upgrade, just check connectivity
        await scanApi.quickScanSingle(routerId)
        addConsoleLine('Router is back online!', 'success')
      }

      waitingForReboot.value = false
      status.value = 'complete'
      canClose.value = true

      // Refresh router data
      await store.fetchRouters()
      addConsoleLine('Router data refreshed', 'success')

      emit('complete', { success: true, router: props.router })

    } catch (error) {
      if (attempts >= maxAttempts) {
        addConsoleLine('Timeout waiting for router to come back online', 'error')
        waitingForReboot.value = false
        status.value = 'failed'
        canClose.value = true
      } else {
        // Schedule next check
        rebootCheckTimer.value = setTimeout(checkRouter, 5000)
      }
    }
  }

  // Start checking after 30 seconds (give router time to reboot)
  rebootCheckTimer.value = setTimeout(checkRouter, 30000)
}

const handleClose = () => {
  if (isRunning.value && !canClose.value) return
  cleanup()
  emit('close')
}

const refreshAndClose = async () => {
  await store.fetchRouters()
  cleanup()
  emit('close')
}

const cleanup = () => {
  if (ws.value) {
    ws.value.close()
    ws.value = null
  }
  if (elapsedTimer.value) {
    clearInterval(elapsedTimer.value)
    elapsedTimer.value = null
  }
  if (rebootCheckTimer.value) {
    clearTimeout(rebootCheckTimer.value)
    rebootCheckTimer.value = null
  }
}

// Watch for task start
watch(() => props.taskId, (newTaskId) => {
  if (newTaskId && props.visible) {
    consoleLines.value = []
    status.value = 'running'
    startTime.value = Date.now()
    waitingForReboot.value = false
    canClose.value = false
    lastMessage.value = ''
    expectedFirmware.value = null
    previousFirmware.value = null

    elapsedTimer.value = setInterval(updateElapsedTime, 1000)

    addConsoleLine(`Starting ${props.upgradeType} upgrade for ${props.router?.identity || props.router?.ip}`, 'info')
    addConsoleLine(`Task ID: ${newTaskId}`, 'muted')

    connectWebSocket(newTaskId)
  }
})

// Watch for modal visibility
watch(() => props.visible, (visible) => {
  if (!visible) {
    cleanup()
  }
})

onUnmounted(() => {
  cleanup()
})
</script>

<style scoped>
.console-output {
  height: 300px;
  overflow-y: auto;
  background-color: #1e1e1e;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 12px;
  padding: 12px;
}

.console-line {
  padding: 2px 0;
  white-space: pre-wrap;
  word-break: break-all;
}

.console-time {
  color: #6c757d;
  margin-right: 8px;
}

.console-text {
  color: #d4d4d4;
}

.console-normal .console-text {
  color: #d4d4d4;
}

.console-info .console-text {
  color: #3794ff;
}

.console-success .console-text {
  color: #4ec9b0;
}

.console-warning .console-text {
  color: #dcdcaa;
}

.console-error .console-text {
  color: #f14c4c;
}

.console-muted .console-text {
  color: #6c757d;
}

.status-banner {
  border-bottom: 1px solid var(--bs-border-color);
}

.spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.modal-content {
  border: none;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
}

.modal-header {
  border-bottom: none;
}

.modal-footer {
  border-top: 1px solid var(--bs-border-color);
}
</style>
