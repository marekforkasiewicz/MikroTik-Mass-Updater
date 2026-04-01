"""Role-based access control permissions"""

from enum import Enum
from typing import Iterable, List, Sequence


class Role(str, Enum):
    """User roles"""
    ADMIN = "admin"
    OPERATOR = "operator"
    VIEWER = "viewer"


class Permission(str, Enum):
    """Available permissions"""
    # Router permissions
    VIEW_ROUTERS = "view_routers"
    ADD_ROUTERS = "add_routers"
    EDIT_ROUTERS = "edit_routers"
    DELETE_ROUTERS = "delete_routers"

    # Scan permissions
    RUN_SCAN = "run_scan"

    # Update permissions
    RUN_UPDATES = "run_updates"

    # User management
    VIEW_USERS = "view_users"
    MANAGE_USERS = "manage_users"

    # Settings
    VIEW_SETTINGS = "view_settings"
    MANAGE_SETTINGS = "manage_settings"

    # Scripts
    VIEW_SCRIPTS = "view_scripts"
    EXECUTE_SCRIPTS = "execute_scripts"
    MANAGE_SCRIPTS = "manage_scripts"

    # Schedules
    VIEW_SCHEDULES = "view_schedules"
    MANAGE_SCHEDULES = "manage_schedules"

    # Backups
    VIEW_BACKUPS = "view_backups"
    CREATE_BACKUPS = "create_backups"
    RESTORE_BACKUPS = "restore_backups"
    DELETE_BACKUPS = "delete_backups"

    # Groups
    VIEW_GROUPS = "view_groups"
    MANAGE_GROUPS = "manage_groups"

    # Notifications
    VIEW_NOTIFICATIONS = "view_notifications"
    MANAGE_NOTIFICATIONS = "manage_notifications"

    # Monitoring
    VIEW_MONITORING = "view_monitoring"
    MANAGE_MONITORING = "manage_monitoring"

    # Reports
    VIEW_REPORTS = "view_reports"
    EXPORT_REPORTS = "export_reports"

    # Webhooks
    VIEW_WEBHOOKS = "view_webhooks"
    MANAGE_WEBHOOKS = "manage_webhooks"

    # API Keys
    VIEW_API_KEYS = "view_api_keys"
    MANAGE_API_KEYS = "manage_api_keys"

    # Templates (ZTP)
    VIEW_TEMPLATES = "view_templates"
    MANAGE_TEMPLATES = "manage_templates"
    DEPLOY_TEMPLATES = "deploy_templates"


# Role-permission mapping
ROLE_PERMISSIONS: dict[Role, List[Permission]] = {
    Role.ADMIN: list(Permission),  # Admin has all permissions

    Role.OPERATOR: [
        # Router operations
        Permission.VIEW_ROUTERS,
        Permission.ADD_ROUTERS,
        Permission.EDIT_ROUTERS,
        Permission.RUN_SCAN,
        Permission.RUN_UPDATES,

        # Scripts
        Permission.VIEW_SCRIPTS,
        Permission.EXECUTE_SCRIPTS,

        # Schedules
        Permission.VIEW_SCHEDULES,
        Permission.MANAGE_SCHEDULES,

        # Backups
        Permission.VIEW_BACKUPS,
        Permission.CREATE_BACKUPS,
        Permission.RESTORE_BACKUPS,

        # Groups
        Permission.VIEW_GROUPS,
        Permission.MANAGE_GROUPS,

        # Notifications (view only)
        Permission.VIEW_NOTIFICATIONS,

        # Monitoring
        Permission.VIEW_MONITORING,

        # Reports
        Permission.VIEW_REPORTS,
        Permission.EXPORT_REPORTS,

        # Webhooks (view only)
        Permission.VIEW_WEBHOOKS,

        # API Keys (own keys)
        Permission.VIEW_API_KEYS,
        Permission.MANAGE_API_KEYS,

        # Templates (ZTP)
        Permission.VIEW_TEMPLATES,
        Permission.MANAGE_TEMPLATES,
        Permission.DEPLOY_TEMPLATES,
    ],

    Role.VIEWER: [
        Permission.VIEW_ROUTERS,
        Permission.VIEW_SCRIPTS,
        Permission.VIEW_SCHEDULES,
        Permission.VIEW_BACKUPS,
        Permission.VIEW_GROUPS,
        Permission.VIEW_NOTIFICATIONS,
        Permission.VIEW_MONITORING,
        Permission.VIEW_REPORTS,
        Permission.VIEW_WEBHOOKS,
        Permission.VIEW_TEMPLATES,
    ],
}

ROLE_LEVELS: dict[Role, int] = {
    Role.VIEWER: 1,
    Role.OPERATOR: 2,
    Role.ADMIN: 3,
}

API_KEY_WILDCARD_SCOPE = "*"


def get_permissions_for_role(role: Role) -> List[Permission]:
    """Get list of permissions for a role"""
    return ROLE_PERMISSIONS.get(role, [])


def has_permission(role: Role, permission: Permission) -> bool:
    """Check if a role has a specific permission"""
    return permission in get_permissions_for_role(role)


def has_any_permission(role: Role, permissions: List[Permission]) -> bool:
    """Check if a role has any of the specified permissions"""
    role_permissions = get_permissions_for_role(role)
    return any(p in role_permissions for p in permissions)


def has_all_permissions(role: Role, permissions: List[Permission]) -> bool:
    """Check if a role has all of the specified permissions"""
    role_permissions = get_permissions_for_role(role)
    return all(p in role_permissions for p in permissions)


def role_scope_name(role: Role) -> str:
    """Return the API-key scope name for a role gate."""
    return f"role:{role.value}"


def parse_api_key_scopes(scopes: str | Sequence[str] | None) -> set[str]:
    """Parse stored API key scopes into a normalized set."""
    if not scopes:
        return set()
    if isinstance(scopes, str):
        values = scopes.split(",")
    else:
        values = scopes
    return {value.strip() for value in values if value and value.strip()}


def serialize_api_key_scopes(scopes: Iterable[str]) -> str:
    """Serialize API key scopes for database storage."""
    return ",".join(sorted(parse_api_key_scopes(list(scopes))))


def get_valid_api_key_scopes() -> set[str]:
    """Return the set of accepted API key scopes."""
    permission_scopes = {permission.value for permission in Permission}
    role_scopes = {role_scope_name(role) for role in Role}
    return permission_scopes | role_scopes | {API_KEY_WILDCARD_SCOPE}


def get_default_api_key_scopes_for_role(role: Role) -> set[str]:
    """Return the default scopes for a new API key created by the given role."""
    scopes = {permission.value for permission in get_permissions_for_role(role)}
    scopes.add(role_scope_name(role))
    return scopes


def role_scope_allows(allowed_roles: Sequence[Role], scope_roles: Sequence[Role]) -> bool:
    """Check whether a scoped API key can satisfy a role-gated endpoint."""
    for scoped_role in scope_roles:
        scoped_level = ROLE_LEVELS[scoped_role]
        for allowed_role in allowed_roles:
            if scoped_level >= ROLE_LEVELS[allowed_role]:
                return True
    return False
