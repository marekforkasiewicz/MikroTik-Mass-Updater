<template>
  <div class="container-fluid py-4">
    <div class="d-flex justify-content-between align-items-center mb-4">
      <h2><i class="bi bi-file-earmark-code me-2"></i>Configuration Templates</h2>
      <div>
        <button class="btn btn-outline-secondary me-2" @click="showProfilesModal = true">
          <i class="bi bi-diagram-3 me-1"></i> Device Profiles
        </button>
        <button class="btn btn-primary" @click="newTemplate">
          <i class="bi bi-plus-lg me-1"></i> New Template
        </button>
      </div>
    </div>

    <div class="row">
      <!-- Template List -->
      <div class="col-md-4">
        <div class="card">
          <div class="card-header">
            <div class="input-group input-group-sm">
              <input type="text" class="form-control" v-model="searchQuery"
                     placeholder="Search templates..." />
              <select class="form-select" v-model="filterCategory" style="max-width: 130px;">
                <option value="">All Categories</option>
                <option v-for="cat in categories" :key="cat" :value="cat">{{ cat }}</option>
              </select>
            </div>
          </div>
          <div class="list-group list-group-flush" style="max-height: 70vh; overflow-y: auto;">
            <a v-for="template in filteredTemplates" :key="template.id" href="#"
               class="list-group-item list-group-item-action"
               :class="{ active: selectedTemplate?.id === template.id }"
               @click.prevent="selectTemplate(template)">
              <div class="d-flex justify-content-between align-items-start">
                <div>
                  <strong>{{ template.name }}</strong>
                  <div class="small text-muted">
                    <span class="badge bg-secondary me-1">{{ template.category }}</span>
                    <span v-if="template.tags && template.tags.length" class="text-muted">
                      <i class="bi bi-tags"></i> {{ template.tags.join(', ') }}
                    </span>
                  </div>
                  <div class="small text-muted mt-1" v-if="template.description">
                    {{ truncate(template.description, 60) }}
                  </div>
                </div>
                <span :class="template.is_active ? 'text-success' : 'text-secondary'">
                  <i :class="template.is_active ? 'bi bi-check-circle-fill' : 'bi bi-circle'"></i>
                </span>
              </div>
            </a>
            <div v-if="filteredTemplates.length === 0" class="list-group-item text-center text-muted">
              <i class="bi bi-file-earmark-x fs-4"></i>
              <p class="mb-0 mt-2">No templates found</p>
            </div>
          </div>
        </div>
      </div>

      <!-- Template Editor -->
      <div class="col-md-8">
        <div class="card" v-if="editingTemplate">
          <div class="card-header d-flex justify-content-between align-items-center">
            <h5 class="mb-0">{{ editingTemplate.id ? 'Edit Template' : 'New Template' }}</h5>
            <div>
              <button class="btn btn-sm btn-outline-info me-2" @click="validateTemplate" title="Validate Syntax">
                <i class="bi bi-check2-circle me-1"></i> Validate
              </button>
              <button class="btn btn-sm btn-outline-secondary me-2" @click="previewTemplate"
                      :disabled="!editingTemplate.content" title="Preview">
                <i class="bi bi-eye me-1"></i> Preview
              </button>
              <button class="btn btn-sm btn-primary" @click="saveTemplate" :disabled="saving">
                <span v-if="saving" class="spinner-border spinner-border-sm me-1"></span>
                Save
              </button>
            </div>
          </div>
          <div class="card-body">
            <div class="row mb-3">
              <div class="col-md-6">
                <label class="form-label">Name <span class="text-danger">*</span></label>
                <input type="text" class="form-control" v-model="editingTemplate.name"
                       placeholder="e.g., DNS Configuration" />
              </div>
              <div class="col-md-3">
                <label class="form-label">Category</label>
                <select class="form-select" v-model="editingTemplate.category">
                  <option value="general">General</option>
                  <option value="network">Network</option>
                  <option value="security">Security</option>
                  <option value="wireless">Wireless</option>
                  <option value="system">System</option>
                  <option value="firewall">Firewall</option>
                  <option value="vpn">VPN</option>
                </select>
              </div>
              <div class="col-md-3">
                <label class="form-label">Status</label>
                <div class="form-check form-switch mt-2">
                  <input type="checkbox" class="form-check-input" v-model="editingTemplate.is_active" id="isActive" />
                  <label class="form-check-label" for="isActive">Active</label>
                </div>
              </div>
            </div>

            <div class="mb-3">
              <label class="form-label">Description</label>
              <textarea class="form-control" v-model="editingTemplate.description" rows="2"
                        placeholder="Brief description of what this template does"></textarea>
            </div>

            <div class="mb-3">
              <label class="form-label">
                Template Content (Jinja2) <span class="text-danger">*</span>
                <a href="#" class="ms-2 small" @click.prevent="showHelpModal = true">
                  <i class="bi bi-question-circle"></i> Help
                </a>
              </label>
              <textarea class="form-control font-monospace" v-model="editingTemplate.content"
                        rows="12" style="font-size: 13px; tab-size: 2;"
                        placeholder="# RouterOS commands with Jinja2 syntax&#10;/ip dns set servers={{ dns_primary }},{{ dns_secondary }}"></textarea>
            </div>

            <!-- Validation Result -->
            <div v-if="validationResult" class="mb-3">
              <div :class="validationResult.valid ? 'alert alert-success' : 'alert alert-danger'" class="py-2">
                <div v-if="validationResult.valid">
                  <i class="bi bi-check-circle-fill me-2"></i>Template syntax is valid
                </div>
                <div v-else>
                  <i class="bi bi-x-circle-fill me-2"></i>Syntax errors:
                  <ul class="mb-0 mt-2">
                    <li v-for="error in validationResult.errors" :key="error">{{ error }}</li>
                  </ul>
                </div>
                <div v-if="validationResult.warnings?.length" class="mt-2 text-warning">
                  <i class="bi bi-exclamation-triangle me-1"></i>Warnings:
                  <ul class="mb-0">
                    <li v-for="warning in validationResult.warnings" :key="warning">{{ warning }}</li>
                  </ul>
                </div>
              </div>
            </div>

            <!-- Variables -->
            <div class="mb-3">
              <div class="d-flex justify-content-between align-items-center mb-2">
                <label class="form-label mb-0">Template Variables</label>
                <button class="btn btn-sm btn-outline-primary" @click="addVariable">
                  <i class="bi bi-plus"></i> Add Variable
                </button>
              </div>
              <div v-if="editingTemplate.variables && editingTemplate.variables.length" class="table-responsive">
                <table class="table table-sm table-bordered">
                  <thead class="table-light">
                    <tr>
                      <th>Name</th>
                      <th>Type</th>
                      <th>Default</th>
                      <th>Required</th>
                      <th>Description</th>
                      <th style="width: 50px;"></th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="(variable, index) in editingTemplate.variables" :key="index">
                      <td>
                        <input type="text" class="form-control form-control-sm" v-model="variable.name"
                               placeholder="variable_name" />
                      </td>
                      <td>
                        <select class="form-select form-select-sm" v-model="variable.type">
                          <option value="string">String</option>
                          <option value="integer">Integer</option>
                          <option value="boolean">Boolean</option>
                          <option value="list">List</option>
                        </select>
                      </td>
                      <td>
                        <input type="text" class="form-control form-control-sm" v-model="variable.default"
                               placeholder="default value" />
                      </td>
                      <td class="text-center">
                        <input type="checkbox" class="form-check-input" v-model="variable.required" />
                      </td>
                      <td>
                        <input type="text" class="form-control form-control-sm" v-model="variable.description"
                               placeholder="Description" />
                      </td>
                      <td>
                        <button class="btn btn-sm btn-outline-danger" @click="removeVariable(index)">
                          <i class="bi bi-trash"></i>
                        </button>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <div v-else class="text-muted small">
                No variables defined. Variables allow customization when deploying.
              </div>
            </div>

            <!-- Tags -->
            <div class="mb-3">
              <label class="form-label">Tags</label>
              <input type="text" class="form-control" v-model="tagsInput"
                     placeholder="Enter tags separated by commas"
                     @blur="updateTags" />
              <small class="text-muted">Separate tags with commas</small>
            </div>
          </div>
          <div class="card-footer d-flex justify-content-between">
            <div>
              <button class="btn btn-danger" @click="confirmDelete" v-if="editingTemplate.id">
                <i class="bi bi-trash me-1"></i> Delete
              </button>
            </div>
            <div v-if="editingTemplate.id">
              <button class="btn btn-outline-secondary me-2" @click="showDeployments">
                <i class="bi bi-clock-history me-1"></i> History
              </button>
              <button class="btn btn-success" @click="showDeployModal = true">
                <i class="bi bi-rocket-takeoff me-1"></i> Deploy
              </button>
            </div>
          </div>
        </div>

        <div class="card" v-else>
          <div class="card-body text-center py-5 text-muted">
            <i class="bi bi-file-earmark-code fs-1"></i>
            <p class="mt-2">Select a template to edit or create a new one</p>
            <button class="btn btn-primary" @click="newTemplate">
              <i class="bi bi-plus-lg me-1"></i> Create Template
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Preview Modal -->
    <div class="modal fade" id="previewModal" tabindex="-1" ref="previewModalEl">
      <div class="modal-dialog modal-lg">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">Template Preview</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
          </div>
          <div class="modal-body">
            <div class="mb-3" v-if="routers.length">
              <label class="form-label">Preview with Router</label>
              <select class="form-select" v-model="previewRouterId" @change="previewTemplate">
                <option :value="null">Sample Router (default)</option>
                <option v-for="router in routers" :key="router.id" :value="router.id">
                  {{ router.identity || router.ip }} ({{ router.ip }})
                </option>
              </select>
            </div>
            <div class="mb-3" v-if="editingTemplate?.variables?.length">
              <label class="form-label">Variables</label>
              <div class="row g-2">
                <div class="col-md-6" v-for="variable in editingTemplate.variables" :key="variable.name">
                  <label class="form-label small">{{ variable.name }}</label>
                  <input type="text" class="form-control form-control-sm"
                         v-model="previewVariables[variable.name]"
                         :placeholder="variable.default || ''"
                         @change="previewTemplate" />
                </div>
              </div>
            </div>
            <div v-if="previewLoading" class="text-center py-3">
              <div class="spinner-border text-primary" role="status"></div>
            </div>
            <div v-else-if="previewResult">
              <label class="form-label">Rendered Output</label>
              <pre class="bg-dark text-light p-3 rounded" style="max-height: 400px; overflow-y: auto;">{{ previewResult }}</pre>
            </div>
            <div v-else-if="previewError" class="alert alert-danger">
              {{ previewError }}
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
          </div>
        </div>
      </div>
    </div>

    <!-- Deploy Modal -->
    <div class="modal fade" id="deployModal" tabindex="-1" ref="deployModalEl">
      <div class="modal-dialog modal-lg">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">Deploy Template: {{ editingTemplate?.name }}</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
          </div>
          <div class="modal-body">
            <!-- Router Selection -->
            <div class="mb-3">
              <label class="form-label">Select Routers <span class="text-danger">*</span></label>
              <div class="d-flex gap-2 mb-2">
                <button class="btn btn-sm btn-outline-secondary" @click="selectAllRouters">Select All</button>
                <button class="btn btn-sm btn-outline-secondary" @click="selectOnlineRouters">Online Only</button>
                <button class="btn btn-sm btn-outline-secondary" @click="deployForm.router_ids = []">Clear</button>
              </div>
              <select class="form-select" v-model="deployForm.router_ids" multiple size="6">
                <option v-for="router in routers" :key="router.id" :value="router.id"
                        :disabled="!router.is_online">
                  {{ router.identity || router.ip }} ({{ router.ip }})
                  {{ router.is_online ? '' : '- offline' }}
                </option>
              </select>
              <small class="text-muted">Selected: {{ deployForm.router_ids.length }} router(s)</small>
            </div>

            <!-- Variables -->
            <div class="mb-3" v-if="editingTemplate?.variables?.length">
              <label class="form-label">Variables</label>
              <div class="row g-2">
                <div class="col-md-6" v-for="variable in editingTemplate.variables" :key="variable.name">
                  <label class="form-label small">
                    {{ variable.name }}
                    <span v-if="variable.required" class="text-danger">*</span>
                  </label>
                  <input type="text" class="form-control form-control-sm"
                         v-model="deployForm.variables[variable.name]"
                         :placeholder="variable.default || ''" />
                  <small class="text-muted" v-if="variable.description">{{ variable.description }}</small>
                </div>
              </div>
            </div>

            <!-- Options -->
            <div class="row mb-3">
              <div class="col-md-6">
                <div class="form-check">
                  <input type="checkbox" class="form-check-input" v-model="deployForm.dry_run" id="dryRun" />
                  <label class="form-check-label" for="dryRun">Dry run (preview only)</label>
                </div>
              </div>
              <div class="col-md-6">
                <div class="form-check">
                  <input type="checkbox" class="form-check-input" v-model="deployForm.backup_before" id="backupBefore" />
                  <label class="form-check-label" for="backupBefore">Create backup before deploy</label>
                </div>
              </div>
            </div>

            <!-- Deployment Progress -->
            <div v-if="deployTaskId && deploying" class="mt-4">
              <h6>
                <span class="spinner-border spinner-border-sm me-2"></span>
                Deployment in Progress
              </h6>
              <div class="progress mb-2" style="height: 25px;">
                <div class="progress-bar progress-bar-striped progress-bar-animated"
                     :style="{ width: deployProgressPercent + '%' }">
                  {{ deployProgress.current }} / {{ deployProgress.total }}
                </div>
              </div>
              <div v-if="deployProgress.currentItem" class="text-muted small">
                <i class="bi bi-router me-1"></i>
                Current: {{ deployProgress.currentItem }}
              </div>
              <div v-if="deployProgress.message" class="text-muted small">
                {{ deployProgress.message }}
              </div>
            </div>

            <!-- Deployment Results -->
            <div v-if="deployResults.length && !deploying" class="mt-4">
              <h6>
                <i class="bi bi-check-circle me-1" v-if="deployTaskStatus === 'completed'"></i>
                <i class="bi bi-x-circle me-1" v-else-if="deployTaskStatus === 'failed'"></i>
                Deployment Results
              </h6>
              <div class="table-responsive">
                <table class="table table-sm">
                  <thead>
                    <tr>
                      <th>Router</th>
                      <th>Status</th>
                      <th>Details</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="result in deployResults" :key="result.router_id">
                      <td>{{ result.router_identity || result.router_ip }}</td>
                      <td>
                        <span :class="getStatusBadgeClass(result.status)">
                          {{ result.status }}
                        </span>
                      </td>
                      <td>
                        <button v-if="result.rendered_content" class="btn btn-sm btn-outline-info"
                                @click="showRenderedContent(result)">
                          <i class="bi bi-eye"></i> View
                        </button>
                        <span v-if="result.error" class="text-danger small">{{ result.error }}</span>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <div class="alert alert-secondary mt-2" v-if="selectedRendered">
                <div class="d-flex justify-content-between align-items-center mb-2">
                  <strong>{{ selectedRendered.router }}</strong>
                  <button class="btn btn-sm btn-outline-secondary" @click="selectedRendered = null">Close</button>
                </div>
                <pre class="mb-0" style="max-height: 200px; overflow-y: auto; white-space: pre-wrap;">{{ selectedRendered.content }}</pre>
              </div>
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal" @click="resetDeployModal"
                    :disabled="deploying">
              Close
            </button>
            <button type="button" class="btn btn-danger" @click="cancelDeployment"
                    v-if="deploying && deployTaskId">
              <i class="bi bi-x-circle me-1"></i> Cancel
            </button>
            <button type="button" class="btn btn-success" @click="deployTemplate"
                    :disabled="deploying || deployForm.router_ids.length === 0"
                    v-if="!deployResults.length && !deploying">
              {{ deployForm.dry_run ? 'Preview' : 'Deploy' }} to {{ deployForm.router_ids.length }} router(s)
            </button>
            <button type="button" class="btn btn-primary" @click="resetDeployModal"
                    v-if="deployResults.length && !deploying">
              Deploy Again
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Profiles Modal -->
    <div class="modal fade" id="profilesModal" tabindex="-1" ref="profilesModalEl">
      <div class="modal-dialog modal-xl">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">Device Profiles</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
          </div>
          <div class="modal-body">
            <div class="d-flex justify-content-between align-items-center mb-3">
              <p class="text-muted mb-0">
                Device profiles group templates and auto-assign them based on router model/architecture.
              </p>
              <button class="btn btn-primary btn-sm" @click="newProfile">
                <i class="bi bi-plus-lg me-1"></i> New Profile
              </button>
            </div>
            <div class="table-responsive">
              <table class="table table-sm table-hover">
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Description</th>
                    <th>Device Filter</th>
                    <th>Templates</th>
                    <th>Status</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="profile in profiles" :key="profile.id">
                    <td><strong>{{ profile.name }}</strong></td>
                    <td>{{ truncate(profile.description, 40) }}</td>
                    <td>
                      <small v-if="profile.device_filter?.model?.length">
                        Model: {{ profile.device_filter.model.join(', ') }}
                      </small>
                      <small v-if="profile.device_filter?.architecture?.length">
                        Arch: {{ profile.device_filter.architecture.join(', ') }}
                      </small>
                    </td>
                    <td>{{ profile.template_ids?.length || 0 }} template(s)</td>
                    <td>
                      <span :class="profile.is_active ? 'badge bg-success' : 'badge bg-secondary'">
                        {{ profile.is_active ? 'Active' : 'Inactive' }}
                      </span>
                    </td>
                    <td>
                      <button class="btn btn-sm btn-outline-primary me-1" @click="editProfile(profile)">
                        <i class="bi bi-pencil"></i>
                      </button>
                      <button class="btn btn-sm btn-outline-danger" @click="deleteProfile(profile)">
                        <i class="bi bi-trash"></i>
                      </button>
                    </td>
                  </tr>
                  <tr v-if="profiles.length === 0">
                    <td colspan="6" class="text-center text-muted">No profiles defined</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
          </div>
        </div>
      </div>
    </div>

    <!-- Help Modal -->
    <div class="modal fade" id="helpModal" tabindex="-1" ref="helpModalEl">
      <div class="modal-dialog modal-lg">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">Jinja2 Template Syntax</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
          </div>
          <div class="modal-body" v-pre>
            <h6>Built-in Router Variables</h6>
            <ul>
              <li><code>{{ router.ip }}</code> - Router IP address</li>
              <li><code>{{ router.identity }}</code> - Router identity name</li>
              <li><code>{{ router.model }}</code> - Router model</li>
              <li><code>{{ router.ros_version }}</code> - RouterOS version</li>
              <li><code>{{ router.architecture }}</code> - CPU architecture</li>
              <li><code>{{ router.location }}</code> - Location (if set)</li>
              <li><code>{{ router.tags }}</code> - Tags list</li>
            </ul>

            <h6>Custom Variables</h6>
            <p>Define variables in the Variables section, then use them:</p>
            <pre class="bg-light p-2">/ip dns set servers={{ dns_primary }},{{ dns_secondary }}</pre>

            <h6>Conditionals</h6>
            <pre class="bg-light p-2">{% if router.model.startswith("hAP") %}
/interface wireless set wlan1 ssid="{{ ssid }}"
{% endif %}</pre>

            <h6>Loops</h6>
            <pre class="bg-light p-2">{% for server in ntp_servers %}
/system ntp client servers add address={{ server }}
{% endfor %}</pre>

            <h6>Filters</h6>
            <ul>
              <li><code>{{ variable | lower }}</code> - Lowercase</li>
              <li><code>{{ variable | upper }}</code> - Uppercase</li>
              <li><code>{{ variable | yesno }}</code> - Convert boolean to yes/no</li>
              <li><code>{{ variable | quote }}</code> - Wrap in quotes</li>
              <li><code>{{ variable | default("value") }}</code> - Default value</li>
            </ul>

            <h6>Functions</h6>
            <ul>
              <li><code>{{ now() }}</code> - Current timestamp</li>
            </ul>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
          </div>
        </div>
      </div>
    </div>

    <!-- Profile Edit Modal -->
    <div class="modal fade" id="profileEditModal" tabindex="-1" ref="profileEditModalEl">
      <div class="modal-dialog modal-lg">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">{{ editingProfile?.id ? 'Edit Profile' : 'New Profile' }}</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
          </div>
          <div class="modal-body" v-if="editingProfile">
            <div class="row mb-3">
              <div class="col-md-8">
                <label class="form-label">Name <span class="text-danger">*</span></label>
                <input type="text" class="form-control" v-model="editingProfile.name"
                       placeholder="e.g., hAP Standard Config" />
              </div>
              <div class="col-md-4">
                <label class="form-label">Status</label>
                <div class="form-check form-switch mt-2">
                  <input type="checkbox" class="form-check-input" v-model="editingProfile.is_active" />
                  <label class="form-check-label">Active</label>
                </div>
              </div>
            </div>

            <div class="mb-3">
              <label class="form-label">Description</label>
              <textarea class="form-control" v-model="editingProfile.description" rows="2"></textarea>
            </div>

            <div class="row mb-3">
              <div class="col-md-6">
                <label class="form-label">Model Filter (glob patterns)</label>
                <input type="text" class="form-control" v-model="profileModelFilter"
                       placeholder="e.g., hAP*, RB4011*" />
                <small class="text-muted">Comma-separated patterns. Use * for wildcard.</small>
              </div>
              <div class="col-md-6">
                <label class="form-label">Architecture Filter</label>
                <input type="text" class="form-control" v-model="profileArchFilter"
                       placeholder="e.g., arm, arm64, tile" />
                <small class="text-muted">Comma-separated architectures.</small>
              </div>
            </div>

            <div class="mb-3">
              <label class="form-label">Templates</label>
              <select class="form-select" v-model="editingProfile.template_ids" multiple size="5">
                <option v-for="template in templates" :key="template.id" :value="template.id">
                  {{ template.name }} ({{ template.category }})
                </option>
              </select>
              <small class="text-muted">Select templates to include in this profile.</small>
            </div>

            <div class="mb-3">
              <label class="form-label">Profile Variables (JSON)</label>
              <textarea class="form-control font-monospace" v-model="profileVariablesJson" rows="3"
                        placeholder='{"dns_primary": "8.8.8.8"}'></textarea>
              <small class="text-muted">Default variable values for this profile.</small>
            </div>

            <!-- Matching Routers Preview -->
            <div v-if="editingProfile.id && matchingRouters.length > 0" class="mb-3">
              <label class="form-label">Matching Routers ({{ matchingRouters.length }})</label>
              <div class="border rounded p-2" style="max-height: 120px; overflow-y: auto;">
                <span v-for="router in matchingRouters" :key="router.id" class="badge bg-secondary me-1 mb-1">
                  {{ router.identity || router.ip }}
                </span>
              </div>
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
            <button type="button" class="btn btn-primary" @click="saveProfile" :disabled="savingProfile">
              <span v-if="savingProfile" class="spinner-border spinner-border-sm me-1"></span>
              Save Profile
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Deployment History Modal -->
    <div class="modal fade" id="historyModal" tabindex="-1" ref="historyModalEl">
      <div class="modal-dialog modal-xl">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">Deployment History: {{ editingTemplate?.name }}</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
          </div>
          <div class="modal-body">
            <div v-if="loadingHistory" class="text-center py-4">
              <div class="spinner-border text-primary"></div>
            </div>
            <div v-else-if="deploymentHistory.length === 0" class="text-center text-muted py-4">
              <i class="bi bi-clock-history fs-1"></i>
              <p class="mt-2">No deployment history found</p>
            </div>
            <div v-else class="table-responsive">
              <table class="table table-sm table-hover">
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Router</th>
                    <th>Status</th>
                    <th>Details</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="deploy in deploymentHistory" :key="deploy.id">
                    <td>{{ formatDate(deploy.deployed_at) }}</td>
                    <td>Router #{{ deploy.router_id }}</td>
                    <td>
                      <span :class="getDeployStatusBadge(deploy.status)">
                        {{ deploy.status }}
                      </span>
                    </td>
                    <td>
                      <button class="btn btn-sm btn-outline-info" @click="showDeployDetails(deploy)"
                              v-if="deploy.rendered_content">
                        <i class="bi bi-eye"></i>
                      </button>
                      <span v-if="deploy.error_message" class="text-danger small ms-2">
                        {{ truncate(deploy.error_message, 30) }}
                      </span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div v-if="selectedDeployDetail" class="mt-3">
              <div class="d-flex justify-content-between align-items-center mb-2">
                <strong>Rendered Content</strong>
                <button class="btn btn-sm btn-outline-secondary" @click="selectedDeployDetail = null">
                  Close
                </button>
              </div>
              <pre class="bg-dark text-light p-3 rounded" style="max-height: 300px; overflow-y: auto;">{{ selectedDeployDetail }}</pre>
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
          </div>
        </div>
      </div>
    </div>

    <!-- Delete Confirmation -->
    <ConfirmModal
      :visible="showDeleteModal"
      title="Delete Template"
      :message="deleteModalMessage"
      variant="danger"
      confirmText="Delete"
      :loading="deleting"
      @confirm="handleDeleteConfirm"
      @cancel="showDeleteModal = false"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick, watch } from 'vue'
import { Modal } from 'bootstrap'
import { templatesApi, routerApi, taskApi, createTaskWebSocket } from '../services/api'
import ConfirmModal from './ConfirmModal.vue'
import { useMainStore } from '../stores/main'
import { useTemplateDeployment } from '../composables/useTemplateDeployment'

const mainStore = useMainStore()

// Data
const templates = ref([])
const profiles = ref([])
const routers = ref([])
const categories = ref([])
const selectedTemplate = ref(null)
const editingTemplate = ref(null)
const searchQuery = ref('')
const filterCategory = ref('')
const saving = ref(false)
const tagsInput = ref('')

// Validation
const validationResult = ref(null)

// Preview
const previewRouterId = ref(null)
const previewVariables = ref({})
const previewResult = ref('')
const previewError = ref('')
const previewLoading = ref(false)

// Deploy
const showDeployModal = ref(false)

// Profiles
const showProfilesModal = ref(false)
const showProfileEditModal = ref(false)
const editingProfile = ref(null)
const savingProfile = ref(false)
const profileModelFilter = ref('')
const profileArchFilter = ref('')
const profileVariablesJson = ref('{}')
const matchingRouters = ref([])

// Deployment History
const showHistoryModal = ref(false)
const deploymentHistory = ref([])
const loadingHistory = ref(false)
const selectedDeployDetail = ref(null)

// Help
const showHelpModal = ref(false)

// Delete
const showDeleteModal = ref(false)
const deleteModalMessage = ref('')
const deleting = ref(false)

// Modal refs
const previewModalEl = ref(null)
const deployModalEl = ref(null)
const profilesModalEl = ref(null)
const profileEditModalEl = ref(null)
const historyModalEl = ref(null)
const helpModalEl = ref(null)
let previewModal = null
let deployModal = null
let profilesModal = null
let profileEditModal = null
let historyModal = null
let helpModal = null

// Computed
const filteredTemplates = computed(() => {
  let result = templates.value

  if (filterCategory.value) {
    result = result.filter(t => t.category === filterCategory.value)
  }

  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    result = result.filter(t =>
      t.name.toLowerCase().includes(query) ||
      (t.description && t.description.toLowerCase().includes(query)) ||
      (t.tags && t.tags.some(tag => tag.toLowerCase().includes(query)))
    )
  }

  return result
})

const deployment = useTemplateDeployment({
  templatesApi,
  taskApi,
  createTaskWebSocket,
  notify: (type, message) => mainStore.addNotification(type, message)
})

const {
  deploying,
  deployForm,
  deployResults,
  selectedRendered,
  deployTaskId,
  deployTaskStatus,
  deployProgress,
  deployProgressPercent,
  selectAllRouters,
  selectOnlineRouters,
  resetDeployModal,
  deployTemplate: runDeployment,
  cancelDeployment,
  showRenderedContent,
  getStatusBadgeClass
} = deployment

// Lifecycle
onMounted(async () => {
  await Promise.all([
    loadTemplates(),
    loadRouters(),
    loadProfiles(),
    loadCategories()
  ])

  nextTick(() => {
    if (previewModalEl.value) previewModal = new Modal(previewModalEl.value)
    if (deployModalEl.value) deployModal = new Modal(deployModalEl.value)
    if (profilesModalEl.value) profilesModal = new Modal(profilesModalEl.value)
    if (profileEditModalEl.value) profileEditModal = new Modal(profileEditModalEl.value)
    if (historyModalEl.value) historyModal = new Modal(historyModalEl.value)
    if (helpModalEl.value) helpModal = new Modal(helpModalEl.value)
  })
})

watch(showDeployModal, (val) => {
  if (val) deployModal?.show()
})

watch(showProfilesModal, (val) => {
  if (val) profilesModal?.show()
})

watch(showProfileEditModal, (val) => {
  if (val) profileEditModal?.show()
})

watch(showHistoryModal, (val) => {
  if (val) historyModal?.show()
})

watch(showHelpModal, (val) => {
  if (val) helpModal?.show()
})

// Methods
async function loadTemplates() {
  try {
    const response = await templatesApi.list()
    templates.value = response.items || []
  } catch (error) {
    console.error('Failed to load templates:', error)
    mainStore.addNotification('error', 'Failed to load templates')
  }
}

async function loadRouters() {
  try {
    const response = await routerApi.list()
    routers.value = response.routers || response.items || []
  } catch (error) {
    console.error('Failed to load routers:', error)
  }
}

async function loadProfiles() {
  try {
    const response = await templatesApi.listProfiles()
    profiles.value = response.items || []
  } catch (error) {
    console.error('Failed to load profiles:', error)
  }
}

async function loadCategories() {
  try {
    const cats = await templatesApi.getCategories()
    categories.value = cats || []
  } catch (error) {
    // Categories endpoint might return empty array for new installations
    categories.value = []
  }
}

function selectTemplate(template) {
  selectedTemplate.value = template
  editingTemplate.value = { ...template }
  tagsInput.value = (template.tags || []).join(', ')
  validationResult.value = null
}

function newTemplate() {
  selectedTemplate.value = null
  editingTemplate.value = {
    name: '',
    description: '',
    category: 'general',
    content: '',
    variables: [],
    tags: [],
    is_active: true
  }
  tagsInput.value = ''
  validationResult.value = null
}

function addVariable() {
  if (!editingTemplate.value.variables) {
    editingTemplate.value.variables = []
  }
  editingTemplate.value.variables.push({
    name: '',
    type: 'string',
    default: '',
    required: false,
    description: ''
  })
}

function removeVariable(index) {
  editingTemplate.value.variables.splice(index, 1)
}

function updateTags() {
  if (tagsInput.value) {
    editingTemplate.value.tags = tagsInput.value.split(',').map(t => t.trim()).filter(t => t)
  } else {
    editingTemplate.value.tags = []
  }
}

async function validateTemplate() {
  if (!editingTemplate.value.content) {
    mainStore.addNotification('warning', 'Please enter template content first')
    return
  }

  try {
    validationResult.value = await templatesApi.validate(editingTemplate.value.content)
  } catch (error) {
    validationResult.value = {
      valid: false,
      errors: [error.message],
      warnings: []
    }
  }
}

async function previewTemplate() {
  if (!editingTemplate.value?.id) {
    mainStore.addNotification('warning', 'Save the template first to preview')
    return
  }

  previewLoading.value = true
  previewError.value = ''
  previewResult.value = ''

  try {
    const response = await templatesApi.preview(editingTemplate.value.id, {
      router_id: previewRouterId.value,
      variables: previewVariables.value
    })
    previewResult.value = response.rendered
    previewModal?.show()
  } catch (error) {
    previewError.value = error.message
    previewModal?.show()
  } finally {
    previewLoading.value = false
  }
}

async function saveTemplate() {
  if (!editingTemplate.value.name || !editingTemplate.value.content) {
    mainStore.addNotification('warning', 'Name and content are required')
    return
  }

  updateTags()
  saving.value = true

  try {
    if (editingTemplate.value.id) {
      const updated = await templatesApi.update(editingTemplate.value.id, editingTemplate.value)
      editingTemplate.value = updated
    } else {
      const created = await templatesApi.create(editingTemplate.value)
      editingTemplate.value = created
    }
    await loadTemplates()
    await loadCategories()
    mainStore.addNotification('success', 'Template saved successfully')
    selectTemplate(editingTemplate.value)
  } catch (error) {
    console.error('Failed to save template:', error)
    mainStore.addNotification('error', 'Failed to save template: ' + error.message)
  } finally {
    saving.value = false
  }
}

function confirmDelete() {
  if (!editingTemplate.value?.id) return
  deleteModalMessage.value = `Are you sure you want to delete template "${editingTemplate.value.name}"? This action cannot be undone.`
  showDeleteModal.value = true
}

async function handleDeleteConfirm() {
  if (!editingTemplate.value?.id) return
  deleting.value = true

  try {
    await templatesApi.delete(editingTemplate.value.id)
    editingTemplate.value = null
    selectedTemplate.value = null
    await loadTemplates()
    mainStore.addNotification('success', 'Template deleted')
  } catch (error) {
    console.error('Failed to delete template:', error)
    mainStore.addNotification('error', 'Failed to delete template')
  } finally {
    deleting.value = false
    showDeleteModal.value = false
  }
}

async function deployTemplate() {
  if (!editingTemplate.value?.id) {
    mainStore.addNotification('warning', 'Select a template first')
    return
  }
  await runDeployment(editingTemplate.value.id)
}

async function showDeployments() {
  if (!editingTemplate.value?.id) return

  loadingHistory.value = true
  deploymentHistory.value = []
  selectedDeployDetail.value = null

  try {
    const response = await templatesApi.listDeployments({ template_id: editingTemplate.value.id })
    deploymentHistory.value = response.items || []
  } catch (error) {
    console.error('Failed to load deployment history:', error)
    mainStore.addNotification('error', 'Failed to load history')
  } finally {
    loadingHistory.value = false
  }

  showHistoryModal.value = true
}

function showDeployDetails(deploy) {
  selectedDeployDetail.value = deploy.rendered_content
}

function getDeployStatusBadge(status) {
  switch (status) {
    case 'completed': return 'badge bg-success'
    case 'failed': return 'badge bg-danger'
    case 'running': return 'badge bg-primary'
    case 'pending': return 'badge bg-warning'
    default: return 'badge bg-secondary'
  }
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return date.toLocaleString()
}

// Profile methods
function newProfile() {
  editingProfile.value = {
    name: '',
    description: '',
    device_filter: { model: [], architecture: [] },
    template_ids: [],
    variables: {},
    is_active: true
  }
  profileModelFilter.value = ''
  profileArchFilter.value = ''
  profileVariablesJson.value = '{}'
  matchingRouters.value = []
  showProfileEditModal.value = true
}

function editProfile(profile) {
  editingProfile.value = {
    ...profile,
    template_ids: profile.template_ids || []
  }
  profileModelFilter.value = (profile.device_filter?.model || []).join(', ')
  profileArchFilter.value = (profile.device_filter?.architecture || []).join(', ')
  profileVariablesJson.value = JSON.stringify(profile.variables || {}, null, 2)
  loadMatchingRouters(profile.id)
  showProfileEditModal.value = true
}

async function loadMatchingRouters(profileId) {
  try {
    const response = await templatesApi.getProfileRouters(profileId)
    matchingRouters.value = response.routers || []
  } catch (error) {
    matchingRouters.value = []
  }
}

async function saveProfile() {
  if (!editingProfile.value.name) {
    mainStore.addNotification('warning', 'Name is required')
    return
  }

  // Parse filters
  const modelPatterns = profileModelFilter.value
    ? profileModelFilter.value.split(',').map(s => s.trim()).filter(s => s)
    : []
  const archPatterns = profileArchFilter.value
    ? profileArchFilter.value.split(',').map(s => s.trim()).filter(s => s)
    : []

  // Parse variables JSON
  let variables = {}
  try {
    if (profileVariablesJson.value.trim()) {
      variables = JSON.parse(profileVariablesJson.value)
    }
  } catch (e) {
    mainStore.addNotification('error', 'Invalid JSON in variables')
    return
  }

  const profileData = {
    name: editingProfile.value.name,
    description: editingProfile.value.description,
    device_filter: { model: modelPatterns, architecture: archPatterns },
    template_ids: editingProfile.value.template_ids,
    variables: variables,
    is_active: editingProfile.value.is_active
  }

  savingProfile.value = true
  try {
    if (editingProfile.value.id) {
      await templatesApi.updateProfile(editingProfile.value.id, profileData)
    } else {
      await templatesApi.createProfile(profileData)
    }
    await loadProfiles()
    profileEditModal?.hide()
    showProfileEditModal.value = false
    mainStore.addNotification('success', 'Profile saved')
  } catch (error) {
    console.error('Failed to save profile:', error)
    mainStore.addNotification('error', 'Failed to save profile: ' + error.message)
  } finally {
    savingProfile.value = false
  }
}

async function deleteProfile(profile) {
  if (!confirm(`Delete profile "${profile.name}"?`)) return

  try {
    await templatesApi.deleteProfile(profile.id)
    await loadProfiles()
    mainStore.addNotification('success', 'Profile deleted')
  } catch (error) {
    console.error('Failed to delete profile:', error)
    mainStore.addNotification('error', 'Failed to delete profile')
  }
}

// Utilities
function truncate(text, maxLen) {
  if (!text) return ''
  return text.length > maxLen ? text.substring(0, maxLen) + '...' : text
}
</script>

<style scoped>
.list-group-item.active .text-muted {
  color: rgba(255, 255, 255, 0.7) !important;
}
.list-group-item.active .badge.bg-secondary {
  background-color: rgba(255, 255, 255, 0.2) !important;
}
</style>
