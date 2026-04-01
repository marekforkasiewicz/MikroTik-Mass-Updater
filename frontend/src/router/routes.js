import Dashboard from '../components/Dashboard.vue'
import RouterList from '../components/RouterList.vue'
import LoginPage from '../components/LoginPage.vue'

const GroupList = () => import('../components/GroupList.vue')
const MonitoringDashboard = () => import('../components/MonitoringDashboard.vue')
const BatchOperations = () => import('../components/BatchOperations.vue')
const Automation = () => import('../components/Automation.vue')
const Settings = () => import('../components/Settings.vue')
const ReportsAndLogs = () => import('../components/ReportsAndLogs.vue')
const TemplateList = () => import('../components/TemplateList.vue')
const ComplianceCheck = () => import('../components/ComplianceCheck.vue')
const NetworkTopology = () => import('../components/NetworkTopology.vue')

export const appRoutes = [
  {
    path: '/login',
    name: 'login',
    component: LoginPage,
    meta: { public: true }
  },
  {
    path: '/',
    name: 'dashboard',
    component: Dashboard
  },
  {
    path: '/routers',
    name: 'routers',
    component: RouterList
  },
  {
    path: '/groups',
    name: 'groups',
    component: GroupList
  },
  {
    path: '/operations',
    name: 'operations',
    component: BatchOperations,
    meta: { requiresOperator: true }
  },
  {
    path: '/automation',
    name: 'automation',
    component: Automation,
    meta: { requiresOperator: true }
  },
  {
    path: '/monitoring',
    name: 'monitoring',
    component: MonitoringDashboard
  },
  {
    path: '/reports',
    name: 'reports',
    component: ReportsAndLogs
  },
  {
    path: '/settings',
    name: 'settings',
    component: Settings,
    meta: { requiresAdmin: true }
  },
  {
    path: '/templates',
    name: 'templates',
    component: TemplateList,
    meta: { requiresOperator: true }
  },
  {
    path: '/compliance',
    name: 'compliance',
    component: ComplianceCheck,
    meta: { requiresOperator: true }
  },
  {
    path: '/topology',
    name: 'topology',
    component: NetworkTopology
  },
  { path: '/scan', redirect: '/operations' },
  { path: '/update', redirect: '/operations' },
  { path: '/scripts', redirect: '/operations' },
  { path: '/schedules', redirect: '/automation' },
  { path: '/backups', redirect: '/automation' },
  { path: '/tasks', redirect: '/automation' },
  { path: '/logs', redirect: '/reports' },
  { path: '/notifications', redirect: '/settings' },
  { path: '/webhooks', redirect: '/settings' },
  { path: '/users', redirect: '/settings' }
]
