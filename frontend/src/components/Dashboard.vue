<template>
  <div>
    <h2 class="mb-4">Dashboard</h2>

    <!-- Stats Cards -->
    <div class="row g-4 mb-4">
      <div class="col-md-3">
        <div class="card stat-card h-100">
          <div class="card-body d-flex justify-content-between align-items-center">
            <div>
              <h6 class="text-muted mb-1">Total Routers</h6>
              <div class="stat-value">{{ store.routerStats.total }}</div>
            </div>
            <i class="bi bi-hdd-network stat-icon text-primary"></i>
          </div>
        </div>
      </div>

      <div class="col-md-3">
        <div class="card stat-card h-100 border-start border-success border-4">
          <div class="card-body d-flex justify-content-between align-items-center">
            <div>
              <h6 class="text-muted mb-1">Online</h6>
              <div class="stat-value text-success">{{ store.routerStats.online }}</div>
            </div>
            <i class="bi bi-check-circle stat-icon text-success"></i>
          </div>
        </div>
      </div>

      <div class="col-md-3">
        <div class="card stat-card h-100 border-start border-danger border-4">
          <div class="card-body d-flex justify-content-between align-items-center">
            <div>
              <h6 class="text-muted mb-1">Offline</h6>
              <div class="stat-value text-danger">{{ store.routerStats.offline }}</div>
            </div>
            <i class="bi bi-x-circle stat-icon text-danger"></i>
          </div>
        </div>
      </div>

      <div class="col-md-3">
        <div class="card stat-card h-100 border-start border-warning border-4">
          <div class="card-body d-flex justify-content-between align-items-center">
            <div>
              <h6 class="text-muted mb-1">Needs Update</h6>
              <div class="stat-value text-warning">{{ store.routerStats.needsUpdate }}</div>
            </div>
            <i class="bi bi-arrow-repeat stat-icon text-warning"></i>
          </div>
        </div>
      </div>
    </div>

    <!-- Quick Actions -->
    <div class="row g-4 mb-4">
      <div class="col-md-6">
        <div class="card h-100">
          <div class="card-header">
            <h5 class="mb-0">Quick Actions</h5>
          </div>
          <div class="card-body">
            <div class="d-grid gap-2">
              <button class="btn btn-outline-primary" @click="importRouters" :disabled="loading">
                <i class="bi bi-upload me-2"></i>
                Import from list.txt
              </button>
              <button class="btn btn-outline-success" @click="startQuickScan" :disabled="loading">
                <i class="bi bi-lightning me-2"></i>
                Quick Scan All
              </button>
              <button class="btn btn-outline-info" @click="startFullScan" :disabled="loading">
                <i class="bi bi-search me-2"></i>
                Full Scan All
              </button>
              <router-link to="/update" class="btn btn-primary">
                <i class="bi bi-cloud-download me-2"></i>
                Start Update
              </router-link>
            </div>
          </div>
        </div>
      </div>

      <div class="col-md-6">
        <div class="card h-100">
          <div class="card-header d-flex justify-content-between align-items-center">
            <h5 class="mb-0">Recent Routers</h5>
            <router-link to="/routers" class="btn btn-sm btn-outline-primary">
              View All
            </router-link>
          </div>
          <div class="card-body p-0">
            <div class="table-responsive">
              <table class="table table-hover mb-0 router-table">
                <thead>
                  <tr>
                    <th>IP</th>
                    <th>Identity</th>
                    <th>Status</th>
                    <th>Version</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="router in recentRouters" :key="router.id">
                    <td>{{ router.ip }}</td>
                    <td>{{ router.identity || '-' }}</td>
                    <td>
                      <i
                        class="bi status-icon"
                        :class="{
                          'bi-check-circle-fill status-online': router.is_online,
                          'bi-x-circle-fill status-offline': !router.is_online
                        }"
                      ></i>
                    </td>
                    <td>{{ router.ros_version || '-' }}</td>
                  </tr>
                  <tr v-if="recentRouters.length === 0">
                    <td colspan="4" class="text-center text-muted py-3">
                      No routers found. Import from list.txt to get started.
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Running Tasks -->
    <div class="card" v-if="store.runningTasks.length > 0">
      <div class="card-header">
        <h5 class="mb-0">
          <i class="bi bi-gear spin me-2"></i>
          Running Tasks
        </h5>
      </div>
      <div class="card-body">
        <div v-for="task in store.runningTasks" :key="task.id" class="mb-3">
          <div class="d-flex justify-content-between mb-1">
            <span>{{ task.type }} - {{ task.current_item || 'Starting...' }}</span>
            <span>{{ task.progress }}/{{ task.total }}</span>
          </div>
          <div class="progress task-progress">
            <div
              class="progress-bar progress-bar-striped progress-bar-animated"
              :style="{ width: `${(task.progress / task.total) * 100}%` }"
            ></div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useMainStore } from '../stores/main'

const store = useMainStore()
const loading = ref(false)

const recentRouters = computed(() => {
  return store.routers.slice(0, 5)
})

const importRouters = async () => {
  loading.value = true
  try {
    await store.importRoutersFromFile()
  } finally {
    loading.value = false
  }
}

const startQuickScan = async () => {
  loading.value = true
  try {
    await store.startQuickScan()
  } finally {
    loading.value = false
  }
}

const startFullScan = async () => {
  loading.value = true
  try {
    await store.startFullScan()
  } finally {
    loading.value = false
  }
}
</script>
