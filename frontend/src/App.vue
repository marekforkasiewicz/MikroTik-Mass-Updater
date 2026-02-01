<template>
  <ErrorBoundary>
    <!-- Login page when not authenticated -->
    <LoginPage v-if="!authStore.isAuthenticated" />

    <!-- Main app when authenticated -->
    <div v-else class="d-flex">
    <!-- Sidebar -->
    <nav class="sidebar d-flex flex-column" :class="{ 'show': store.sidebarOpen }">
      <div class="p-3 border-bottom border-secondary">
        <h5 class="text-white mb-0">
          <i class="bi bi-router me-2"></i>
          MikroTik Updater
        </h5>
      </div>

      <ul class="nav flex-column mt-3">
        <li class="nav-item">
          <router-link to="/" class="nav-link" :class="{ active: $route.path === '/' }">
            <i class="bi bi-speedometer2"></i>
            Dashboard
          </router-link>
        </li>
        <li class="nav-item">
          <router-link to="/routers" class="nav-link" :class="{ active: $route.path === '/routers' }">
            <i class="bi bi-hdd-network"></i>
            Routers
          </router-link>
        </li>
        <li class="nav-item">
          <router-link to="/groups" class="nav-link" :class="{ active: $route.path === '/groups' }">
            <i class="bi bi-collection"></i>
            Groups
          </router-link>
        </li>

        <!-- Separator -->
        <li class="nav-item mt-2 mb-2">
          <hr class="border-secondary mx-3 my-0">
        </li>

        <li class="nav-item" v-if="authStore.isOperator">
          <router-link to="/operations" class="nav-link" :class="{ active: $route.path === '/operations' }">
            <i class="bi bi-gear-wide-connected"></i>
            Operations
          </router-link>
        </li>
        <li class="nav-item" v-if="authStore.isOperator">
          <router-link to="/automation" class="nav-link" :class="{ active: $route.path === '/automation' }">
            <i class="bi bi-clock-history"></i>
            Automation
          </router-link>
        </li>
        <li class="nav-item">
          <router-link to="/monitoring" class="nav-link" :class="{ active: $route.path === '/monitoring' }">
            <i class="bi bi-heart-pulse"></i>
            Monitoring
          </router-link>
        </li>

        <!-- Separator -->
        <li class="nav-item mt-2 mb-2">
          <hr class="border-secondary mx-3 my-0">
        </li>

        <li class="nav-item">
          <router-link to="/reports" class="nav-link" :class="{ active: $route.path === '/reports' }">
            <i class="bi bi-file-earmark-bar-graph"></i>
            Reports & Logs
          </router-link>
        </li>

        <!-- Admin section -->
        <template v-if="authStore.isAdmin">
          <li class="nav-item">
            <router-link to="/settings" class="nav-link" :class="{ active: $route.path === '/settings' }">
              <i class="bi bi-sliders"></i>
              Settings
            </router-link>
          </li>
        </template>
      </ul>

      <div class="mt-auto p-3 border-top border-secondary">
        <small class="text-muted">
          <i class="bi bi-info-circle me-1"></i>
          v2.0.0
        </small>
      </div>
    </nav>

    <!-- Main content -->
    <div class="flex-grow-1">
      <!-- Top navbar -->
      <nav class="navbar navbar-expand navbar-light bg-white border-bottom px-4">
        <button class="btn btn-link d-md-none" @click="store.toggleSidebar()">
          <i class="bi bi-list fs-4"></i>
        </button>

        <div class="ms-auto d-flex align-items-center">
          <!-- Router stats -->
          <span class="badge bg-success me-2" v-if="store.routerStats.online > 0">
            {{ store.routerStats.online }} Online
          </span>
          <span class="badge bg-danger me-2" v-if="store.routerStats.offline > 0">
            {{ store.routerStats.offline }} Offline
          </span>
          <span class="badge bg-warning text-dark me-3" v-if="store.routerStats.needsUpdate > 0">
            {{ store.routerStats.needsUpdate }} Updates
          </span>

          <!-- Theme toggle -->
          <button class="theme-toggle me-3" @click="store.toggleTheme()" :title="store.theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'">
            <i class="bi" :class="store.theme === 'dark' ? 'bi-sun' : 'bi-moon-stars'"></i>
            <span>{{ store.theme === 'dark' ? 'Light' : 'Dark' }}</span>
          </button>

          <!-- User menu -->
          <div class="dropdown">
            <button class="btn btn-outline-secondary dropdown-toggle d-flex align-items-center" type="button" data-bs-toggle="dropdown">
              <i class="bi bi-person-circle me-2"></i>
              <span>{{ authStore.user?.username }}</span>
              <span class="badge ms-2" :class="roleBadgeClass">{{ authStore.user?.role }}</span>
            </button>
            <ul class="dropdown-menu dropdown-menu-end">
              <li><span class="dropdown-item-text text-muted small">{{ authStore.user?.email }}</span></li>
              <li><hr class="dropdown-divider"></li>
              <li>
                <a class="dropdown-item" href="#" @click.prevent="logout">
                  <i class="bi bi-box-arrow-right me-2"></i>Logout
                </a>
              </li>
            </ul>
          </div>
        </div>
      </nav>

      <!-- Page content -->
      <main class="p-4">
        <router-view></router-view>
      </main>
    </div>

    <!-- Notifications -->
    <div class="toast-container">
      <div
        v-for="notification in store.notifications"
        :key="notification.id"
        class="toast show"
        :class="{
          'bg-success text-white': notification.type === 'success',
          'bg-danger text-white': notification.type === 'error',
          'bg-warning': notification.type === 'warning',
          'bg-info text-white': notification.type === 'info'
        }"
      >
        <div class="toast-body d-flex justify-content-between align-items-center">
          <span>{{ notification.message }}</span>
          <button
            type="button"
            class="btn-close btn-close-white ms-2"
            @click="store.removeNotification(notification.id)"
          ></button>
        </div>
      </div>
    </div>
  </div>
  </ErrorBoundary>
</template>

<script setup>
import { computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useMainStore } from './stores/main'
import { useAuthStore } from './stores/auth'
import LoginPage from './components/LoginPage.vue'
import ErrorBoundary from './components/ErrorBoundary.vue'

const router = useRouter()
const store = useMainStore()
const authStore = useAuthStore()

const roleBadgeClass = computed(() => {
  const badges = {
    admin: 'bg-danger',
    operator: 'bg-primary',
    viewer: 'bg-secondary'
  }
  return badges[authStore.user?.role] || 'bg-secondary'
})

async function logout() {
  await authStore.logout()
  router.push('/login')
}

// Watch for authentication state changes
watch(() => authStore.isAuthenticated, async (isAuth) => {
  if (isAuth) {
    await store.fetchRouters()
  }
})

onMounted(async () => {
  store.initTheme()

  // Try to restore session from stored token
  await authStore.checkAuth()

  if (authStore.isAuthenticated) {
    await store.fetchRouters()
  }
})
</script>

<style scoped>
.sidebar {
  width: 250px;
  min-width: 250px;
}
</style>
