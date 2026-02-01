"""Role-based access control permissions"""

from enum import Enum
from typing import List


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
    ],
}


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
