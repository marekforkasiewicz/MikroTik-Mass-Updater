"""Rollback and backup service"""

import logging
import os
import hashlib
from datetime import datetime, timedelta
from typing import Optional, List, Tuple
from pathlib import Path

from sqlalchemy.orm import Session

from ..models.backup import RouterBackup, RollbackLog
from ..models.router import Router
from ..schemas.backup import BackupCreate, RollbackCreate
from ..config import settings
from .router_service import RouterService

logger = logging.getLogger(__name__)


class RollbackService:
    """Service for backup and rollback operations"""

    def __init__(self, db: Session):
        self.db = db
        self.backup_dir = settings.DATA_DIR / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def create_backup(
        self,
        backup_data: BackupCreate,
        user_id: Optional[int] = None
    ) -> RouterBackup:
        """Create a backup for a router"""
        router = self.db.query(Router).filter(Router.id == backup_data.router_id).first()
        if not router:
            raise ValueError("Router not found")

        backup = RouterBackup(
            router_id=router.id,
            name=backup_data.name,
            backup_type=backup_data.backup_type,
            includes_passwords=backup_data.includes_passwords,
            encryption_type=backup_data.encryption_type,
            keep_forever=backup_data.keep_forever,
            router_version=router.ros_version,
            router_model=router.model,
            router_identity=router.identity,
            status="in_progress",
            created_by=user_id
        )

        self.db.add(backup)
        self.db.commit()
        self.db.refresh(backup)

        try:
            if backup_data.backup_type == "cloud":
                self._create_cloud_backup(backup, router)
            elif backup_data.backup_type == "export":
                self._create_export_backup(backup, router)
            else:
                self._create_config_backup(backup, router)

            backup.status = "completed"
        except Exception as e:
            backup.status = "failed"
            backup.error_message = str(e)
            logger.error(f"Backup failed for router {router.ip}: {e}")

        self.db.commit()
        self.db.refresh(backup)
        return backup

    def _create_cloud_backup(self, backup: RouterBackup, router: Router):
        """Create cloud backup on MikroTik cloud"""
        router_service = RouterService(self.db)
        api = router_service.connect(router)

        if not api:
            raise Exception("Failed to connect to router")

        try:
            # Create cloud backup
            backup_name = f"backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
            password = backup.encryption_type == "aes256"

            # Upload to cloud
            api.path("/system/backup/cloud").call(
                "upload-file",
                {"action": "create-and-upload", "password": "" if not password else "backup123"}
            )

            # Get cloud backup info
            cloud_backups = list(api.path("/system/backup/cloud").select())
            if cloud_backups:
                latest = cloud_backups[-1]
                backup.cloud_name = latest.get("name", backup_name)
                backup.secret_download_key = latest.get("secret-download-key", "")

        finally:
            api.close()

    def _create_export_backup(self, backup: RouterBackup, router: Router):
        """Create export backup (text configuration)"""
        router_service = RouterService(self.db)
        api = router_service.connect(router)

        if not api:
            raise Exception("Failed to connect to router")

        try:
            # Get export
            result = list(api.path("/export").select())
            export_content = "\n".join(str(line) for line in result)

            # Save to file
            filename = f"export_{router.ip.replace('.', '_')}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.rsc"
            file_path = self.backup_dir / str(router.id) / filename
            file_path.parent.mkdir(parents=True, exist_ok=True)

            with open(file_path, 'w') as f:
                f.write(export_content)

            backup.file_path = str(file_path)
            backup.file_size = file_path.stat().st_size
            backup.checksum = self._calculate_checksum(file_path)

        finally:
            api.close()

    def _create_config_backup(self, backup: RouterBackup, router: Router):
        """Create binary config backup"""
        router_service = RouterService(self.db)
        api = router_service.connect(router)

        if not api:
            raise Exception("Failed to connect to router")

        try:
            # Create backup on router
            backup_name = f"backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

            cmd_args = {"name": backup_name}
            if not backup.includes_passwords:
                cmd_args["dont-encrypt"] = "yes"

            api.path("/system/backup").call("save", cmd_args)

            # Note: In a real implementation, you would download the backup file
            # This would require SFTP or FTP access to the router

            backup.file_path = f"/flash/{backup_name}.backup"  # Path on router

        finally:
            api.close()

    def get_backup(self, backup_id: int) -> Optional[RouterBackup]:
        """Get backup by ID"""
        return self.db.query(RouterBackup).filter(RouterBackup.id == backup_id).first()

    def list_backups(
        self,
        router_id: Optional[int] = None,
        backup_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[RouterBackup], int]:
        """List backups"""
        query = self.db.query(RouterBackup)

        if router_id:
            query = query.filter(RouterBackup.router_id == router_id)
        if backup_type:
            query = query.filter(RouterBackup.backup_type == backup_type)

        total = query.count()
        backups = query.order_by(RouterBackup.created_at.desc()).offset(skip).limit(limit).all()
        return backups, total

    def delete_backup(self, backup_id: int) -> bool:
        """Delete a backup"""
        backup = self.db.query(RouterBackup).filter(RouterBackup.id == backup_id).first()
        if not backup:
            return False

        # Delete file if exists
        if backup.file_path and os.path.exists(backup.file_path):
            try:
                os.remove(backup.file_path)
            except Exception as e:
                logger.warning(f"Failed to delete backup file: {e}")

        self.db.delete(backup)
        self.db.commit()
        return True

    def restore_backup(
        self,
        rollback_data: RollbackCreate,
        user_id: Optional[int] = None
    ) -> RollbackLog:
        """Restore a router from backup"""
        router = self.db.query(Router).filter(Router.id == rollback_data.router_id).first()
        if not router:
            raise ValueError("Router not found")

        backup = None
        if rollback_data.backup_id:
            backup = self.get_backup(rollback_data.backup_id)
            if not backup:
                raise ValueError("Backup not found")

        rollback = RollbackLog(
            router_id=router.id,
            backup_id=rollback_data.backup_id,
            rollback_type=rollback_data.rollback_type,
            reason=rollback_data.reason,
            previous_version=router.ros_version,
            target_version=rollback_data.target_version,
            status="in_progress",
            initiated_by=user_id
        )

        self.db.add(rollback)
        self.db.commit()
        self.db.refresh(rollback)

        try:
            if rollback_data.rollback_type == "restore" and backup:
                self._restore_from_backup(rollback, router, backup)
            elif rollback_data.rollback_type == "downgrade":
                self._downgrade_version(rollback, router, rollback_data.target_version)
            elif rollback_data.rollback_type == "config_restore" and backup:
                self._restore_config(rollback, router, backup)

            rollback.status = "completed"
            rollback.completed_at = datetime.utcnow()
        except Exception as e:
            rollback.status = "failed"
            rollback.error_message = str(e)
            rollback.completed_at = datetime.utcnow()
            logger.error(f"Rollback failed for router {router.ip}: {e}")

        self.db.commit()
        self.db.refresh(rollback)
        return rollback

    def _restore_from_backup(self, rollback: RollbackLog, router: Router, backup: RouterBackup):
        """Restore router from backup file"""
        router_service = RouterService(self.db)
        api = router_service.connect(router)

        if not api:
            raise Exception("Failed to connect to router")

        try:
            if backup.backup_type == "cloud":
                # Restore from cloud
                api.path("/system/backup/cloud").call(
                    "download-file",
                    {"action": "restore", "number": "0"}
                )
            else:
                # Restore from local backup file
                backup_name = os.path.basename(backup.file_path) if backup.file_path else ""
                api.path("/system/backup").call(
                    "load",
                    {"name": backup_name.replace(".backup", "")}
                )

            rollback.reboot_required = True
            rollback.result = {"action": "restore_initiated"}

        finally:
            api.close()

    def _downgrade_version(self, rollback: RollbackLog, router: Router, target_version: str):
        """Downgrade RouterOS version"""
        # This is a complex operation that typically requires:
        # 1. Downloading the target version package
        # 2. Uploading to router
        # 3. Rebooting
        # For now, we'll just log the intent

        rollback.result = {
            "action": "downgrade_requested",
            "target_version": target_version,
            "note": "Manual intervention may be required"
        }
        logger.warning(f"Downgrade requested for {router.ip} to version {target_version}")

    def _restore_config(self, rollback: RollbackLog, router: Router, backup: RouterBackup):
        """Restore configuration from export file"""
        if backup.backup_type != "export":
            raise ValueError("Config restore requires an export backup")

        if not backup.file_path or not os.path.exists(backup.file_path):
            raise ValueError("Backup file not found")

        router_service = RouterService(self.db)
        api = router_service.connect(router)

        if not api:
            raise Exception("Failed to connect to router")

        try:
            # Read export file
            with open(backup.file_path, 'r') as f:
                config_content = f.read()

            # This would need to be executed as a script
            # In practice, you'd need to upload and import the .rsc file

            rollback.result = {
                "action": "config_restore",
                "lines": len(config_content.split('\n'))
            }

        finally:
            api.close()

    def get_rollback_logs(
        self,
        router_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 50
    ) -> Tuple[List[RollbackLog], int]:
        """Get rollback history"""
        query = self.db.query(RollbackLog)

        if router_id:
            query = query.filter(RollbackLog.router_id == router_id)

        total = query.count()
        logs = query.order_by(RollbackLog.started_at.desc()).offset(skip).limit(limit).all()
        return logs, total

    def cleanup_old_backups(self, days: int = 30):
        """Clean up expired backups"""
        cutoff = datetime.utcnow() - timedelta(days=days)

        expired = self.db.query(RouterBackup).filter(
            RouterBackup.keep_forever == False,
            RouterBackup.expires_at != None,
            RouterBackup.expires_at < cutoff
        ).all()

        for backup in expired:
            self.delete_backup(backup.id)

        logger.info(f"Cleaned up {len(expired)} expired backups")

    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA256 checksum of a file"""
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)
        return sha256.hexdigest()
