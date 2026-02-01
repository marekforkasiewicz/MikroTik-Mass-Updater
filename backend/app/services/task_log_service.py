"""Task logging service for file-based operation logging"""

import os
import re
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

from ..config import settings

logger = logging.getLogger(__name__)


@dataclass
class LogEntry:
    """Parsed log entry for a single router"""
    ip: str
    identity: Optional[str] = None
    model: Optional[str] = None
    ros_version: Optional[str] = None
    current_firmware: Optional[str] = None
    upgrade_firmware: Optional[str] = None
    installed_version: Optional[str] = None
    latest_version: Optional[str] = None
    update_channel: Optional[str] = None
    success: bool = False
    error: Optional[str] = None
    messages: List[str] = None

    def __post_init__(self):
        if self.messages is None:
            self.messages = []


class TaskLogService:
    """Service for managing task log files"""

    LOG_DIR = Path(settings.BASE_DIR) / "log"

    @classmethod
    def ensure_log_dir(cls):
        """Ensure log directory exists"""
        cls.LOG_DIR.mkdir(exist_ok=True)

    @classmethod
    def get_log_filename(cls, task_id: str) -> str:
        """Generate log filename for a task"""
        timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        return f"task-{task_id[:8]}-{timestamp}.log"

    @classmethod
    def get_log_filepath(cls, task_id: str, filename: str = None) -> Path:
        """Get full path to log file"""
        cls.ensure_log_dir()
        if not filename:
            filename = cls.get_log_filename(task_id)
        return cls.LOG_DIR / filename

    @classmethod
    def list_log_files(cls) -> List[Dict[str, Any]]:
        """List all log files with metadata"""
        cls.ensure_log_dir()
        files = []
        for f in cls.LOG_DIR.glob("*.log"):
            stat = f.stat()

            # Try to extract summary from file
            summary = cls._extract_summary(f)

            files.append({
                "filename": f.name,
                "size": stat.st_size,
                "size_human": cls._human_size(stat.st_size),
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "path": str(f),
                "summary": summary
            })
        return sorted(files, key=lambda x: x['modified'], reverse=True)

    @classmethod
    def _human_size(cls, size: int) -> str:
        """Convert bytes to human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

    @classmethod
    def _extract_summary(cls, filepath: Path) -> Dict[str, Any]:
        """Extract summary info from log file"""
        summary = {
            "total": 0,
            "successful": 0,
            "failed": 0,
            "task_type": None
        }
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()

            # Look for summary section
            if "Total hosts processed:" in content:
                match = re.search(r'Total hosts processed:\s*(\d+)', content)
                if match:
                    summary["total"] = int(match.group(1))

            if "Successful operations:" in content:
                match = re.search(r'Successful operations:\s*(\d+)', content)
                if match:
                    summary["successful"] = int(match.group(1))

            if "Failed operations:" in content:
                match = re.search(r'Failed operations:\s*(\d+)', content)
                if match:
                    summary["failed"] = int(match.group(1))

            # Try to get task type
            if "Type:" in content:
                match = re.search(r'Type:\s*(\w+)', content)
                if match:
                    summary["task_type"] = match.group(1)

        except Exception as e:
            logger.debug(f"Error extracting summary from {filepath}: {e}")

        return summary

    @classmethod
    def read_log_file(cls, filename: str) -> str:
        """Read content of a log file"""
        filepath = cls.LOG_DIR / filename
        if not filepath.exists():
            raise FileNotFoundError(f"Log file not found: {filename}")
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()

    @classmethod
    def delete_log_file(cls, filename: str) -> bool:
        """Delete a log file"""
        filepath = cls.LOG_DIR / filename
        if not filepath.exists():
            raise FileNotFoundError(f"Log file not found: {filename}")
        filepath.unlink()
        return True

    @classmethod
    def delete_old_logs(cls, days: int = 30) -> int:
        """Delete log files older than specified days"""
        cls.ensure_log_dir()
        cutoff = datetime.now().timestamp() - (days * 24 * 60 * 60)
        deleted = 0
        for f in cls.LOG_DIR.glob("*.log"):
            if f.stat().st_mtime < cutoff:
                f.unlink()
                deleted += 1
        return deleted

    @classmethod
    def parse_log_file(cls, filename: str) -> Dict[str, Any]:
        """Parse log file and extract structured data (supports both old CLI and new web formats)"""
        content = cls.read_log_file(filename)

        result = {
            "filename": filename,
            "task_id": None,
            "task_type": None,
            "started": None,
            "config": {},
            "routers": [],
            "summary": {
                "total": 0,
                "successful": 0,
                "failed": 0,
                "failed_hosts": []
            }
        }

        lines = content.split('\n')
        current_router = None
        in_config = False
        in_failed_hosts = False
        in_router_block = False

        for line in lines:
            # Task ID (new format)
            if "TASK STARTED:" in line:
                match = re.search(r'TASK STARTED:\s*(\S+)', line)
                if match:
                    result["task_id"] = match.group(1)

            # Starting job (old format)
            if "-- Starting job --" in line:
                result["task_type"] = "update"

            # Task Type
            if line.strip().startswith("Type:"):
                result["task_type"] = line.split(":", 1)[1].strip()

            # Target update tree (old format config)
            if "Target update tree:" in line:
                result["config"]["update_tree"] = line.split(":", 1)[1].strip()
            if "SSH auto-change enabled" in line:
                result["config"]["auto_change_tree"] = "true"

            # Configuration section (new format)
            if "Configuration:" in line:
                in_config = True
                continue
            if in_config and line.strip().startswith("-"):
                in_config = False
            if in_config and ":" in line and line.strip():
                parts = line.strip().split(":", 1)
                if len(parts) == 2:
                    result["config"][parts[0].strip()] = parts[1].strip()

            # Router entry - detect by "Host:" pattern
            host_match = re.search(r'Host:\s*(\d+\.\d+\.\d+\.\d+)', line)
            if host_match:
                # Save previous router
                if current_router:
                    # Determine success based on messages if not explicitly set
                    if not current_router.success and not current_router.error:
                        if any("SUCCESS" in m or "installed" in m.lower() or "rebooting" in m.lower()
                               for m in current_router.messages):
                            current_router.success = True
                    result["routers"].append(current_router)

                ip = host_match.group(1)
                current_router = LogEntry(ip=ip)
                in_router_block = True
                continue

            # Router details (when in router block)
            if current_router and in_router_block:
                line_stripped = line.strip()

                # End of router block
                if line_stripped.startswith("---") or line_stripped.startswith("==="):
                    in_router_block = False
                    continue

                # Parse router properties
                if line_stripped.startswith("Identity:"):
                    current_router.identity = line_stripped.split(":", 1)[1].strip()
                elif line_stripped.startswith("Model:"):
                    current_router.model = line_stripped.split(":", 1)[1].strip()
                elif "OS Version:" in line_stripped or "RouterOS Version:" in line_stripped:
                    current_router.ros_version = line_stripped.split(":", 1)[1].strip()
                elif line_stripped.startswith("Current Firmware:"):
                    current_router.current_firmware = line_stripped.split(":", 1)[1].strip()
                elif "Upgrade Firmware" in line_stripped:
                    current_router.upgrade_firmware = line_stripped.split(":", 1)[1].strip()
                elif line_stripped.startswith("Update Channel:"):
                    current_router.update_channel = line_stripped.split(":", 1)[1].strip()
                elif "Installed" in line_stripped and "Version:" in line_stripped:
                    current_router.installed_version = line_stripped.split(":", 1)[1].strip()
                elif "Latest" in line_stripped and "Version:" in line_stripped:
                    current_router.latest_version = line_stripped.split(":", 1)[1].strip()
                elif line_stripped.startswith("Status: SUCCESS") or line_stripped == "SUCCESS":
                    current_router.success = True
                elif line_stripped.startswith("Status: FAILED") or "FAILED" in line_stripped:
                    current_router.success = False
                    if " - " in line_stripped:
                        current_router.error = line_stripped.split(" - ", 1)[1]
                elif "Error" in line_stripped:
                    current_router.error = line_stripped
                    current_router.success = False
                elif line_stripped and not line_stripped.startswith("-"):
                    # Add as message
                    current_router.messages.append(line_stripped)

            # Summary section
            if "Total hosts processed:" in line or "Total Routers:" in line:
                match = re.search(r'(\d+)', line)
                if match:
                    result["summary"]["total"] = int(match.group(1))
            if "Successful operations:" in line or "Successfully Scanned:" in line:
                match = re.search(r'(\d+)', line)
                if match:
                    result["summary"]["successful"] = int(match.group(1))
            if "Failed operations:" in line:
                match = re.search(r'(\d+)', line)
                if match:
                    result["summary"]["failed"] = int(match.group(1))

            # Failed hosts section
            if "Failed hosts:" in line or "Failed IPs:" in line:
                in_failed_hosts = True
                continue
            if in_failed_hosts:
                if line.strip().startswith("- "):
                    result["summary"]["failed_hosts"].append(line.strip()[2:])
                elif line.strip().startswith("=") or line.strip().startswith("--"):
                    in_failed_hosts = False

        # Add last router
        if current_router:
            if not current_router.success and not current_router.error:
                if any("SUCCESS" in m or "installed" in m.lower() or "rebooting" in m.lower()
                       for m in current_router.messages):
                    current_router.success = True
            result["routers"].append(current_router)

        # If no summary was found, calculate from routers
        if result["summary"]["total"] == 0 and result["routers"]:
            result["summary"]["total"] = len(result["routers"])
            result["summary"]["successful"] = sum(1 for r in result["routers"] if r.success)
            result["summary"]["failed"] = result["summary"]["total"] - result["summary"]["successful"]

        # Convert LogEntry objects to dicts
        result["routers"] = [
            {
                "ip": r.ip,
                "identity": r.identity,
                "model": r.model,
                "ros_version": r.ros_version,
                "current_firmware": r.current_firmware,
                "upgrade_firmware": r.upgrade_firmware,
                "installed_version": r.installed_version,
                "latest_version": r.latest_version,
                "update_channel": r.update_channel,
                "success": r.success,
                "error": r.error,
                "messages": [m for m in r.messages if m]  # Filter empty messages
            }
            for r in result["routers"]
        ]

        return result

    @classmethod
    def get_statistics(cls) -> Dict[str, Any]:
        """Get overall statistics from all log files"""
        files = cls.list_log_files()

        total_tasks = len(files)
        total_routers = 0
        total_successful = 0
        total_failed = 0
        total_size = 0

        for f in files:
            total_size += f["size"]
            summary = f.get("summary", {})
            total_routers += summary.get("total", 0)
            total_successful += summary.get("successful", 0)
            total_failed += summary.get("failed", 0)

        return {
            "total_log_files": total_tasks,
            "total_routers_processed": total_routers,
            "total_successful": total_successful,
            "total_failed": total_failed,
            "total_size": total_size,
            "total_size_human": cls._human_size(total_size),
            "log_directory": str(cls.LOG_DIR)
        }
