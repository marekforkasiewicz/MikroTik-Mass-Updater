<template>
  <div>
    <h2 class="mb-4">
      <i class="bi bi-diagram-3 me-2"></i>
      Network Topology
    </h2>

    <!-- Controls -->
    <div class="card mb-4">
      <div class="card-body">
        <div class="row align-items-center">
          <div class="col-auto">
            <button class="btn btn-primary me-2" @click="loadTopology" :disabled="loading">
              <span v-if="loading" class="spinner-border spinner-border-sm me-1"></span>
              <i v-else class="bi bi-arrow-clockwise me-1"></i>
              Refresh
            </button>
            <button class="btn btn-outline-secondary me-2" @click="refreshNeighbors" :disabled="refreshingNeighbors">
              <span v-if="refreshingNeighbors" class="spinner-border spinner-border-sm me-1"></span>
              <i v-else class="bi bi-broadcast me-1"></i>
              Scan Neighbors
            </button>
            <button class="btn btn-outline-secondary me-2" @click="fitNetwork">
              <i class="bi bi-arrows-fullscreen me-1"></i>
              Fit View
            </button>
            <button class="btn btn-outline-secondary" @click="togglePhysics">
              <i class="bi me-1" :class="physicsEnabled ? 'bi-pause-circle' : 'bi-play-circle'"></i>
              {{ physicsEnabled ? 'Freeze' : 'Unfreeze' }}
            </button>
          </div>
          <div class="col">
            <div class="d-flex justify-content-end gap-3 flex-wrap align-items-center">
              <!-- Device types -->
              <div class="d-flex align-items-center" title="Edge/Gateway Router">
                <img src="/icons/router-edge.svg" class="legend-icon me-1" alt="Edge Router">
                <small>Gateway</small>
              </div>
              <div class="d-flex align-items-center" title="Standard Router">
                <img src="/icons/router.svg" class="legend-icon me-1" alt="Router">
                <small>Router</small>
              </div>
              <div class="d-flex align-items-center" title="Access Point">
                <img src="/icons/access-point.svg" class="legend-icon me-1" alt="AP">
                <small>AP</small>
              </div>
              <div class="d-flex align-items-center" title="Wireless Bridge">
                <img src="/icons/wireless-bridge.svg" class="legend-icon me-1" alt="Wireless">
                <small>Wireless</small>
              </div>
              <span class="text-muted">|</span>
              <!-- Status colors -->
              <div class="d-flex align-items-center">
                <span class="status-dot bg-success me-1"></span>
                <small>OK</small>
              </div>
              <div class="d-flex align-items-center">
                <span class="status-dot bg-warning me-1"></span>
                <small>Warning</small>
              </div>
              <div class="d-flex align-items-center">
                <span class="status-dot bg-danger me-1"></span>
                <small>Offline</small>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Stats -->
    <div class="row g-3 mb-4" v-if="stats">
      <div class="col-md-3">
        <div class="card text-center">
          <div class="card-body py-2">
            <h4 class="mb-0">{{ stats.total_nodes }}</h4>
            <small class="text-muted">Total Devices</small>
          </div>
        </div>
      </div>
      <div class="col-md-3">
        <div class="card text-center border-success">
          <div class="card-body py-2">
            <h4 class="mb-0 text-success">{{ stats.online }}</h4>
            <small class="text-muted">Online</small>
          </div>
        </div>
      </div>
      <div class="col-md-3">
        <div class="card text-center border-danger">
          <div class="card-body py-2">
            <h4 class="mb-0 text-danger">{{ stats.offline }}</h4>
            <small class="text-muted">Offline</small>
          </div>
        </div>
      </div>
      <div class="col-md-3">
        <div class="card text-center">
          <div class="card-body py-2">
            <h4 class="mb-0">{{ stats.total_edges }}</h4>
            <small class="text-muted">Connections</small>
          </div>
        </div>
      </div>
    </div>

    <!-- Network Graph -->
    <div class="card">
      <div class="card-body p-0">
        <div ref="networkContainer" class="network-container" @contextmenu.prevent></div>
      </div>
    </div>

    <!-- Router Details Modal -->
    <div class="modal fade" id="routerDetailModal" tabindex="-1">
      <div class="modal-dialog">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">
              <i class="bi bi-router me-2"></i>
              {{ selectedRouter?.label || 'Router Details' }}
            </h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
          </div>
          <div class="modal-body" v-if="selectedRouter">
            <table class="table table-sm">
              <tbody>
                <tr>
                  <th>IP Address</th>
                  <td><code>{{ selectedRouter.ip }}</code></td>
                </tr>
                <tr>
                  <th>Model</th>
                  <td>{{ selectedRouter.model || '-' }}</td>
                </tr>
                <tr>
                  <th>Version</th>
                  <td>{{ selectedRouter.version || '-' }}</td>
                </tr>
                <tr>
                  <th>Status</th>
                  <td>
                    <span class="badge" :class="{
                      'bg-success': selectedRouter.status === 'healthy',
                      'bg-warning': selectedRouter.status === 'warning',
                      'bg-danger': selectedRouter.status === 'critical' || selectedRouter.status === 'offline',
                      'bg-primary': selectedRouter.status === 'online'
                    }">
                      {{ selectedRouter.status }}
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>

            <!-- Neighbors -->
            <h6 class="mt-3">Neighbors</h6>
            <div v-if="routerNeighbors.length > 0">
              <ul class="list-group list-group-flush">
                <li v-for="neighbor in routerNeighbors" :key="neighbor.mac" class="list-group-item d-flex justify-content-between">
                  <span>{{ neighbor.identity || neighbor.address }}</span>
                  <small class="text-muted">{{ neighbor.interface }}</small>
                </li>
              </ul>
            </div>
            <div v-else class="text-muted">
              <small>No neighbors discovered. Click "Refresh Neighbors" to scan.</small>
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-outline-secondary" @click="refreshSelectedNeighbors" :disabled="refreshingNeighbors">
              <span v-if="refreshingNeighbors" class="spinner-border spinner-border-sm me-1"></span>
              Refresh Neighbors
            </button>
            <router-link v-if="selectedRouter" :to="`/routers?id=${selectedRouter.id}`" class="btn btn-primary">
              View Router
            </router-link>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { Network } from 'vis-network'
import { DataSet } from 'vis-data'
import { topologyApi } from '../services/api'
import { Modal } from 'bootstrap'

const networkContainer = ref(null)
const loading = ref(false)
const refreshingNeighbors = ref(false)
const physicsEnabled = ref(true)
const stats = ref(null)
const selectedRouter = ref(null)
const routerNeighbors = ref([])

let network = null
let nodes = null
let edges = null
let detailModal = null

const networkOptions = {
  nodes: {
    shape: 'circularImage',
    size: 35,
    font: {
      size: 12,
      color: '#333',
      vadjust: 30
    },
    borderWidth: 3,
    shadow: {
      enabled: true,
      color: 'rgba(0,0,0,0.25)',
      size: 8,
      x: 2,
      y: 2
    },
    shapeProperties: {
      useBorderWithImage: true,
      interpolation: false
    }
  },
  edges: {
    width: 2,
    color: { color: '#6c757d', opacity: 0.8 },
    smooth: {
      type: 'continuous',
      roundness: 0.5
    }
  },
  physics: {
    enabled: true,
    barnesHut: {
      gravitationalConstant: -2000,
      centralGravity: 0.3,
      springLength: 150,
      springConstant: 0.04,
      damping: 0.09
    },
    stabilization: {
      iterations: 150,
      fit: true
    }
  },
  interaction: {
    hover: true,
    tooltipDelay: 200,
    hideEdgesOnDrag: true,
    navigationButtons: true,
    keyboard: true
  },
  layout: {
    improvedLayout: true
  }
}

const loadTopology = async () => {
  loading.value = true
  try {
    const data = await topologyApi.getMap()

    stats.value = data.stats

    // Update or create network
    if (network) {
      nodes.clear()
      edges.clear()
      nodes.add(data.nodes)
      edges.add(data.edges)
    } else {
      await initNetwork(data)
    }
  } catch (error) {
    console.error('Failed to load topology:', error)
  } finally {
    loading.value = false
  }
}

const initNetwork = async (data) => {
  await nextTick()

  nodes = new DataSet(data.nodes)
  edges = new DataSet(data.edges)

  network = new Network(
    networkContainer.value,
    { nodes, edges },
    networkOptions
  )

  // Click event - show router details
  network.on('click', (params) => {
    if (params.nodes.length > 0) {
      const nodeId = params.nodes[0]
      const node = nodes.get(nodeId)
      showRouterDetails(node)
    }
  })

  // Double click - open router page
  network.on('doubleClick', (params) => {
    if (params.nodes.length > 0) {
      const nodeId = params.nodes[0]
      window.location.href = `/routers?id=${nodeId}`
    }
  })
}

const showRouterDetails = async (node) => {
  selectedRouter.value = node
  routerNeighbors.value = []

  // Load neighbors
  try {
    const data = await topologyApi.getNeighbors(node.id)
    routerNeighbors.value = data.neighbors || []
  } catch (error) {
    console.error('Failed to load neighbors:', error)
  }

  // Show modal
  if (!detailModal) {
    detailModal = new Modal(document.getElementById('routerDetailModal'))
  }
  detailModal.show()
}

const refreshNeighbors = async () => {
  refreshingNeighbors.value = true
  try {
    await topologyApi.refreshAllNeighbors()
    await loadTopology()
  } catch (error) {
    console.error('Failed to refresh neighbors:', error)
  } finally {
    refreshingNeighbors.value = false
  }
}

const refreshSelectedNeighbors = async () => {
  if (!selectedRouter.value) return

  refreshingNeighbors.value = true
  try {
    await topologyApi.refreshNeighbors(selectedRouter.value.id)
    const data = await topologyApi.getNeighbors(selectedRouter.value.id)
    routerNeighbors.value = data.neighbors || []
  } catch (error) {
    console.error('Failed to refresh neighbors:', error)
  } finally {
    refreshingNeighbors.value = false
  }
}

const fitNetwork = () => {
  if (network) {
    network.fit({
      animation: {
        duration: 500,
        easingFunction: 'easeInOutQuad'
      }
    })
  }
}

const togglePhysics = () => {
  physicsEnabled.value = !physicsEnabled.value
  if (network) {
    network.setOptions({
      physics: { enabled: physicsEnabled.value }
    })
  }
}

onMounted(() => {
  loadTopology()
})

onUnmounted(() => {
  if (network) {
    network.destroy()
    network = null
  }
})
</script>

<style scoped>
.network-container {
  width: 100%;
  height: 600px;
  border: 1px solid #dee2e6;
  border-radius: 0.375rem;
  background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
}

.legend-icon {
  width: 28px;
  height: 28px;
  object-fit: contain;
}

.status-dot {
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 50%;
}
</style>
