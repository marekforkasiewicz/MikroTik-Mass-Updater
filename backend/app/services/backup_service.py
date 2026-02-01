"""Backup service for MikroTik cloud backups"""

import logging
import time
from typing import Optional, Tuple, Any
from dataclasses import dataclass

from ..core.enums import RouterOSCommand
from .router_service import RouterService

logger = logging.getLogger(__name__)


@dataclass
class BackupResult:
    """Result of a backup operation"""
    success: bool = False
    secret_key: Optional[str] = None
    error: Optional[str] = None
    message: str = ""


class BackupService:
    """Service for cloud backup operations"""

    @staticmethod
    def perform_cloud_backup(api: Any, cloud_password: str) -> BackupResult:
        """
        Perform cloud backup on router.

        Args:
            api: Connected API instance
            cloud_password: Password for the backup

        Returns:
            BackupResult with operation status
        """
        result = BackupResult()

        try:
            # Get existing backups
            existing_backups = list(api.path('/system/backup/cloud'))

            # Remove existing backups
            if existing_backups:
                for backup in existing_backups:
                    backup_id = backup.get('.id')
                    if backup_id:
                        try:
                            api.path('/system/backup/cloud').remove(backup_id)
                        except Exception as e:
                            logger.debug(f"Failed to remove backup {backup_id}: {e}")

            # Create and upload new backup
            try:
                api.path('/system/backup/cloud')(
                    'upload-file',
                    action='create-and-upload',
                    password=cloud_password
                )
            except Exception as e:
                result.error = f"Failed to create backup: {type(e).__name__}: {e}"
                return result

            result.message = "Cloud backup created successfully"

            # Wait for backup to complete
            time.sleep(2)

            # Get backup details
            try:
                latest_backups = list(api.path('/system/backup/cloud'))
                if latest_backups:
                    latest = latest_backups[0]
                    result.secret_key = latest.get('secret-download-key')
                    if result.secret_key:
                        result.message += f" (Key: {result.secret_key})"
            except Exception as e:
                logger.debug(f"Failed to get backup details: {e}")

            result.success = True

        except Exception as e:
            result.error = f"Cloud backup failed: {type(e).__name__}: {e}"
            logger.error(result.error)

        return result

    @staticmethod
    def list_cloud_backups(api: Any) -> Tuple[bool, list]:
        """
        List existing cloud backups.

        Returns:
            Tuple of (success, list of backups)
        """
        try:
            backups = list(api.path('/system/backup/cloud'))
            return True, backups
        except Exception as e:
            logger.error(f"Failed to list backups: {e}")
            return False, []

    @staticmethod
    def remove_cloud_backup(api: Any, backup_id: str) -> Tuple[bool, str]:
        """
        Remove a cloud backup.

        Returns:
            Tuple of (success, message)
        """
        try:
            api.path('/system/backup/cloud').remove(backup_id)
            return True, "Backup removed successfully"
        except Exception as e:
            return False, f"Failed to remove backup: {type(e).__name__}: {e}"
