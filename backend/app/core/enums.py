"""Enumerations for MikroTik Mass Updater"""

from enum import Enum


class UpdateTree(str, Enum):
    """RouterOS update channels"""
    STABLE = "stable"
    DEVELOPMENT = "development"
    TESTING = "testing"
    LONG_TERM = "long-term"


class RouterOSCommand(str, Enum):
    """RouterOS API commands"""
    IDENTITY = "/system/identity/print"
    ROUTERBOARD = "/system/routerboard/print"
    RESOURCE = "/system/resource/print"
    PACKAGE_UPDATE = "/system/package/update/print"
    PACKAGE_CHECK = "/system/package/update/check-for-updates"
    PACKAGE_INSTALL = "/system/package/update/install"
    CLOUD_BACKUP_PRINT = "/system/backup/cloud/print"
    CLOUD_BACKUP_REMOVE = "/system/backup/cloud/remove-file"
    CLOUD_BACKUP_UPLOAD = "/system/backup/cloud/upload-file"
    ROUTERBOARD_PRINT = "/system/routerboard/print"
    ROUTERBOARD_UPGRADE = "/system/routerboard/upgrade"
    SCRIPT_PRINT = "/system/script/print"
    SCRIPT_ADD = "/system/script/add"
    SCRIPT_RUN = "/system/script/run"
    SCRIPT_REMOVE = "/system/script/remove"
    BACKUP_SAVE = "/system/backup/save"
    BACKUP_LOAD = "/system/backup/load"
    EXPORT = "/export"


class TaskStatus(str, Enum):
    """Task execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskType(str, Enum):
    """Types of tasks"""
    SCAN = "scan"
    QUICK_SCAN = "quick_scan"
    UPDATE = "update"
    BACKUP = "backup"
    FIRMWARE_UPGRADE = "firmware_upgrade"
    SCRIPT = "script"
    RESTORE = "restore"
    HEALTH_CHECK = "health_check"


class UserRole(str, Enum):
    """User roles"""
    ADMIN = "admin"
    OPERATOR = "operator"
    VIEWER = "viewer"


class NotificationChannelType(str, Enum):
    """Notification channel types"""
    EMAIL = "email"
    SLACK = "slack"
    TELEGRAM = "telegram"
    WEBHOOK = "webhook"
    DISCORD = "discord"


class AlertSeverity(str, Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertStatus(str, Enum):
    """Alert status"""
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


class HealthStatus(str, Enum):
    """Health check status"""
    OK = "ok"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class BackupType(str, Enum):
    """Backup types"""
    CONFIG = "config"
    FULL = "full"
    EXPORT = "export"
    CLOUD = "cloud"


class ScheduleTriggerType(str, Enum):
    """Schedule trigger types"""
    SCHEDULED = "scheduled"
    MANUAL = "manual"
    STARTUP = "startup"


class ScriptType(str, Enum):
    """Script types"""
    ROUTEROS = "routeros"
    SSH = "ssh"


class WebhookEvent(str, Enum):
    """Webhook event types"""
    ROUTER_ADDED = "router_added"
    ROUTER_REMOVED = "router_removed"
    ROUTER_UPDATED = "router_updated"
    ROUTER_OFFLINE = "router_offline"
    ROUTER_ONLINE = "router_online"
    SCAN_COMPLETED = "scan_completed"
    UPDATE_STARTED = "update_started"
    UPDATE_COMPLETED = "update_completed"
    UPDATE_FAILED = "update_failed"
    BACKUP_CREATED = "backup_created"
    BACKUP_FAILED = "backup_failed"
    SCRIPT_EXECUTED = "script_executed"
    ALERT_CREATED = "alert_created"
