#!/usr/bin/env python3

####################################################
#  MikroTik Mass Updater v5.3.0 (Enhanced Reporting)
#  Original Written by: Phillip Hutchison
#  Revamped version by: Kevin Byrd
#  Ported to Python and API by: Gabriel Rolland
#  Enhanced with Advanced Reporting System
####################################################

import threading
import queue
import time
import argparse
import librouteros
import socket
import logging
import os
import getpass
import yaml
import paramiko
import subprocess
from datetime import datetime
from tqdm import tqdm
from librouteros.query import Key
from enum import Enum
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass


# --- Configuration Constants ---
MIN_CONNECTION_TIMEOUT = 30
MAX_RETRY_ATTEMPTS = 3
RETRY_DELAY_SECONDS = 5
DEFAULT_UPDATE_CHECK_ATTEMPTS = 15
UPDATE_CHECK_DELAY = 2.0
REBOOT_SCRIPT_NAME = "mkmassupdate_reboot"
SSH_PORT = 22


# --- Enums for Update Trees ---
class UpdateTree(str, Enum):
    """RouterOS update channels"""
    STABLE = "stable"
    DEVELOPMENT = "development"
    TESTING = "testing"


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


@dataclass
class HostInfo:
    """Host connection information"""
    ip: str
    port: int = 8728
    username: Optional[str] = None
    password: Optional[str] = None

    def __repr__(self) -> str:
        return f"HostInfo(ip={self.ip}, port={self.port})"


@dataclass
class RouterInfo:
    """Collected information about a router"""
    ip: str
    identity: str = "N/A"
    model: str = "N/A"
    os_version: str = "N/A"
    current_firmware: str = "N/A"
    upgrade_firmware: str = "N/A"
    update_channel: str = "N/A"
    installed_version: str = "N/A"
    latest_version: str = "N/A"
    update_status: str = "N/A"
    success: bool = False
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# --- Logger setup definitions ---
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


class ColoredFormatter(logging.Formatter):
    LOG_COLORS = {
        logging.DEBUG: Colors.OKBLUE,
        logging.INFO: Colors.OKGREEN,
        logging.WARNING: Colors.WARNING,
        logging.ERROR: Colors.FAIL,
        logging.CRITICAL: Colors.FAIL + Colors.BOLD,
    }

    CONSOLE_FORMAT = "%(message)s"
    CONSOLE_FORMAT_WITH_LEVEL = "%(levelname)s: %(message)s"

    def __init__(self, use_colors=True):
        super().__init__()
        self.use_colors = use_colors
        self.LOG_COLORS = {
            logging.DEBUG: Colors.OKBLUE,
            logging.INFO: Colors.OKGREEN,
            logging.WARNING: Colors.WARNING,
            logging.ERROR: Colors.FAIL,
            logging.CRITICAL: Colors.FAIL + Colors.BOLD,
        }

        if self.use_colors:
            self.formatters = {
                level: logging.Formatter(
                    f"{color_val}{self.CONSOLE_FORMAT if level == logging.INFO else self.CONSOLE_FORMAT_WITH_LEVEL}{Colors.ENDC}"
                )
                for level, color_val in self.LOG_COLORS.items()
            }
        else:
            self.formatters = {
                level: logging.Formatter(
                    self.CONSOLE_FORMAT if level == logging.INFO else self.CONSOLE_FORMAT_WITH_LEVEL
                )
                for level in self.LOG_COLORS.keys()
            }

        self.default_formatter = logging.Formatter(self.CONSOLE_FORMAT_WITH_LEVEL)
        if not self.use_colors:
            self.formatters[logging.INFO] = logging.Formatter(self.CONSOLE_FORMAT)

    def format(self, record):
        message_content = record.getMessage()

        if not message_content.strip():
            return ""

        formatter = self.formatters.get(record.levelno, self.default_formatter)
        return formatter.format(record)


class NoEmptyMessagesFilter(logging.Filter):
    def filter(self, record):
        return bool(record.getMessage().strip())


def setup_logger(use_colors_arg, debug_level=False):
    logger_instance = logging.getLogger("MKMikroTikUpdater")
    logger_instance.setLevel(logging.DEBUG if debug_level else logging.INFO)
    logger_instance.propagate = False

    log_dir = 'log'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    log_filename = f"mkmassupdate-{time.strftime('%Y-%m-%d-%H-%M-%S')}.log"
    log_path = os.path.join(log_dir, log_filename)

    fh = logging.FileHandler(log_path, mode='w', encoding='utf-8')
    fh_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(threadName)s - %(message)s')
    fh.setFormatter(fh_formatter)
    fh.addFilter(NoEmptyMessagesFilter())
    logger_instance.addHandler(fh)

    ch = logging.StreamHandler()
    ch_formatter = ColoredFormatter(use_colors=use_colors_arg)
    ch.setFormatter(ch_formatter)
    logger_instance.addHandler(ch)

    return logger_instance


logger = logging.getLogger("MKMikroTikUpdater")


# --- SSH Helper Functions ---
def ssh_change_update_tree(
    ip: str,
    username: str,
    password: str,
    new_tree: UpdateTree,
    ssh_port: int = SSH_PORT,
    timeout: int = 10
) -> Tuple[bool, str]:
    """Change RouterOS update tree via SSH using CLI command."""
    try:
        try:
            import paramiko
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            ssh.connect(
                ip,
                port=ssh_port,
                username=username,
                password=password,
                timeout=timeout,
                look_for_keys=False,
                allow_agent=False
            )

            command = f"/system package update set channel={new_tree.value}"
            stdin, stdout, stderr = ssh.exec_command(command)

            error = stderr.read().decode().strip()
            output = stdout.read().decode().strip()

            ssh.close()

            if error:
                return (False, f"SSH error: {error}")
            else:
                return (True, f"Update tree changed to '{new_tree.value}' via SSH")

        except ImportError:
            try:
                command = f"/system package update set channel={new_tree.value}"
                sshpass_cmd = [
                    'sshpass', '-p', password,
                    'ssh',
                    '-o', 'StrictHostKeyChecking=no',
                    '-o', 'ConnectTimeout=10',
                    f'{username}@{ip}',
                    command
                ]

                result = subprocess.run(
                    sshpass_cmd,
                    capture_output=True,
                    timeout=timeout,
                    text=True
                )

                if result.returncode == 0:
                    return (True, f"Update tree changed to '{new_tree.value}' via SSH")
                else:
                    return (False, f"SSH error: {result.stderr}")

            except FileNotFoundError:
                return (False, "SSH tool not available (install paramiko or sshpass)")
            except subprocess.TimeoutExpired:
                return (False, "SSH connection timeout")

    except Exception as e:
        return (False, f"SSH connection failed: {type(e).__name__}: {e}")


# --- API Helper Functions ---
def execute_with_retry(
    api: Any,
    command: str,
    params: Optional[Dict[str, Any]] = None,
    max_retries: int = MAX_RETRY_ATTEMPTS,
    retry_delay: float = RETRY_DELAY_SECONDS
) -> List[Dict[str, Any]]:
    """Execute RouterOS API command with automatic retry on failure."""
    last_exception = None
    for attempt in range(max_retries):
        try:
            if params is not None:
                return list(api(command, **params))
            return list(api(command))
        except (TimeoutError, socket.error) as e:
            last_exception = e
            logger.warning(f"Attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                continue
            raise last_exception


def parse_host_line(line: str, default_api_port: int) -> Optional[HostInfo]:
    """Parse a single line from IP list file."""
    stripped_line = line.strip()
    try:
        parts = stripped_line.split('|')

        ip_port_str = parts[0]
        if not ip_port_str:
            raise ValueError("IP/Port part is empty")

        ip_port_parts = ip_port_str.split(':')
        ip = ip_port_parts[0]
        if not ip:
            raise ValueError("IP address cannot be empty")

        port_str = ip_port_parts[1] if len(ip_port_parts) > 1 else str(default_api_port)
        port = int(port_str)
        if not (1 <= port <= 65535):
            raise ValueError(f"Port number {port} out of range (1-65535)")

        username = parts[1] if len(parts) > 1 else None
        password = parts[2] if len(parts) > 2 else None

        return HostInfo(ip=ip, port=port, username=username, password=password)
    except ValueError as e:
        logger.warning(f"Skipping malformed line: '{stripped_line}'. Error: {e}")
        return None
    except IndexError:
        logger.warning(f"Skipping malformed line due to incorrect format: '{stripped_line}'")
        return None


def _connect_to_router(
    host_info: HostInfo,
    default_username: str,
    default_password: str,
    timeout: int
) -> Any:
    """Establish connection to MikroTik router using librouteros."""
    username = host_info.username or default_username
    password = host_info.password or default_password

    effective_timeout = max(MIN_CONNECTION_TIMEOUT, timeout)
    api = librouteros.connect(
        host=host_info.ip,
        username=username,
        password=password,
        port=int(host_info.port),
        timeout=effective_timeout
    )
    return api


def _execute_router_command(
    api: Any,
    command_item: Any,
    entry_lines: List[str]
) -> Optional[List[Dict[str, Any]]]:
    """Execute a single router command using the provided API connection."""
    try:
        if isinstance(command_item, tuple):
            cmd, params = command_item
            response = execute_with_retry(api, cmd, params)
        else:
            cmd = command_item
            response = execute_with_retry(api, cmd)
        return response
    except (TimeoutError, socket.error) as e:
        entry_lines.append(f"  Error executing command {command_item}: TimeoutError after retries\n")
    except Exception as e:
        entry_lines.append(f"  Error executing command {command_item}: {type(e).__name__}: {e}\n")
    return None


def _gather_router_info(
    api: Any,
    host_ip: str,
    entry_lines: List[str]
) -> RouterInfo:
    """
    Gather comprehensive router information.

    Returns:
        RouterInfo dataclass with all collected information
    """
    router_info = RouterInfo(ip=host_ip)

    # Get Identity
    try:
        identity_response = _execute_router_command(
            api,
            RouterOSCommand.IDENTITY.value,
            entry_lines
        )
        if identity_response:
            router_info.identity = identity_response[0].get('name', 'N/A')
            entry_lines.append(f"  Identity: {router_info.identity}\n")
    except Exception as e:
        entry_lines.append(f"  Error getting identity: {e}\n")

    # Get Routerboard (Model & Firmware)
    try:
        routerboard_response = _execute_router_command(
            api,
            RouterOSCommand.ROUTERBOARD_PRINT.value,
            entry_lines
        )
        if routerboard_response:
            info = routerboard_response[0]
            router_info.model = info.get('board-name', info.get('model', 'N/A'))
            router_info.current_firmware = info.get('current-firmware', 'N/A')
            router_info.upgrade_firmware = info.get('upgrade-firmware', 'N/A')
            entry_lines.append(f"  Model: {router_info.model}\n")
            entry_lines.append(f"  Current Firmware: {router_info.current_firmware}\n")
            if router_info.upgrade_firmware and router_info.upgrade_firmware != router_info.current_firmware:
                entry_lines.append(f"  Upgrade Firmware Available: {router_info.upgrade_firmware}\n")
    except Exception as e:
        entry_lines.append(f"  Error getting routerboard: {e}\n")

    # Get System Resource (OS Version)
    try:
        resource_response = _execute_router_command(
            api,
            RouterOSCommand.RESOURCE.value,
            entry_lines
        )
        if resource_response:
            info = resource_response[0]
            router_info.os_version = info.get('version', 'N/A')
            entry_lines.append(f"  OS Version: {router_info.os_version}\n")
    except Exception as e:
        entry_lines.append(f"  Error getting system resource: {e}\n")

    # Get Package Update Info (Channel & Versions)
    try:
        update_response = _execute_router_command(
            api,
            RouterOSCommand.PACKAGE_UPDATE.value,
            entry_lines
        )
        if update_response:
            info = update_response[0]
            router_info.update_channel = info.get('channel', info.get('status', 'N/A'))
            router_info.installed_version = info.get('installed-version', 'N/A')
            router_info.latest_version = info.get('latest-version', 'N/A')
            router_info.update_status = info.get('status', 'N/A')
            entry_lines.append(f"  Update Channel: {router_info.update_channel}\n")
            entry_lines.append(f"  Installed Package Version: {router_info.installed_version}\n")
            if router_info.latest_version:
                entry_lines.append(f"  Latest Package Version: {router_info.latest_version}\n")
            entry_lines.append(f"  Update Status: {router_info.update_status}\n")
    except Exception as e:
        entry_lines.append(f"  Error getting package update info: {e}\n")

    router_info.success = True
    return router_info


def _check_update_tree_status(
    api: Any,
    desired_tree: UpdateTree,
    entry_lines: List[str]
) -> str:
    """Check the current update tree status from router."""
    try:
        response = _execute_router_command(
            api,
            RouterOSCommand.PACKAGE_UPDATE.value,
            entry_lines
        )

        if response:
            status_info = response[0]
            current_channel = status_info.get('channel', 
                           status_info.get('status', 'unknown'))

            if desired_tree.value not in current_channel.lower():
                entry_lines.append(
                    f"  ⚠️  WARNING: Router is on '{current_channel}' but you requested '{desired_tree.value}'\n"
                )

            return current_channel
        else:
            entry_lines.append("  Could not determine current update tree\n")
            return "unknown"

    except Exception as e:
        entry_lines.append(f"  Error checking update tree: {type(e).__name__}\n")
        return "unknown"


def _auto_change_update_tree_ssh(
    ip: str,
    username: str,
    password: str,
    current_tree: str,
    desired_tree: UpdateTree,
    entry_lines: List[str]
) -> bool:
    """Automatically change update tree via SSH if needed."""
    if desired_tree.value in current_tree.lower():
        entry_lines.append(f"  Update tree already set to '{desired_tree.value}'\n")
        return True

    entry_lines.append(f"  Attempting to change update tree from '{current_tree}' to '{desired_tree.value}' via SSH...\n")

    success, message = ssh_change_update_tree(ip, username, password, desired_tree)
    entry_lines.append(f"  SSH: {message}\n")

    if success:
        entry_lines.append(f"  ✅ Update tree successfully changed to '{desired_tree.value}'\n")
        time.sleep(1)
        return True
    else:
        entry_lines.append(f"  ❌ Failed to change update tree via SSH\n")
        return False


def _check_and_process_updates(
    api: Any,
    entry_lines: List[str],
    dry_run: bool,
    check_attempts: int,
    check_delay: float,
    desired_tree: UpdateTree
) -> bool:
    """Check for updates and process them if available."""
    current_tree = _check_update_tree_status(api, desired_tree, entry_lines)

    entry_lines.append("  Checking for updates...\n")
    response = _execute_router_command(
        api,
        RouterOSCommand.PACKAGE_CHECK.value,
        entry_lines
    )

    if response is None:
        return False

    check_complete = False
    for attempt in range(check_attempts):
        time.sleep(check_delay)
        status_response = _execute_router_command(
            api,
            RouterOSCommand.PACKAGE_UPDATE.value,
            entry_lines
        )

        if status_response:
            status = status_response[0].get('status', '').lower()
            if 'checking' not in status:
                entry_lines.append(f"  Status: {status}\n")
                check_complete = True
                break
        else:
            return False

    if not check_complete:
        entry_lines.append("  Timeout waiting for update check to complete.\n")
        return False

    status_response = _execute_router_command(
        api,
        RouterOSCommand.PACKAGE_UPDATE.value,
        entry_lines
    )

    if not status_response:
        return False

    for res in status_response:
        installed_version = res.get('installed-version', '')
        latest_version = res.get('latest-version', '')

        if latest_version and latest_version != installed_version:
            entry_lines.append(f"  Updates available: {installed_version} -> {latest_version}\n")
            entry_lines.append(f"  Active update tree: {current_tree}\n")
            entry_lines.append(f"  Requested tree: {desired_tree.value}\n")

            if not dry_run:
                time.sleep(2)
                try:
                    update_package_path = api.path('system', 'package', 'update')
                    execute_with_retry(update_package_path, 'install', max_retries=2)
                    entry_lines.append(f"  Updates installed. Rebooting...\n")
                    return True
                except Exception as e:
                    entry_lines.append(f"  Error installing updates: {type(e).__name__}: {e}\n")
                    return False
            else:
                entry_lines.append(f"  Dry-run: Skipping installation of updates.\n")

    return False


def _perform_cloud_backup(api: Any, cloud_password: str, entry_lines: List[str]) -> bool:
    """Perform cloud backup on router."""
    existing_backups = _execute_router_command(
        api,
        RouterOSCommand.CLOUD_BACKUP_PRINT.value,
        entry_lines
    )

    if existing_backups is None:
        entry_lines.append("  Cloud backup: Failed to retrieve list of existing backups. Aborting.\n")
        return False

    if existing_backups:
        backup_ids = [backup['.id'] for backup in existing_backups if '.id' in backup]

        if backup_ids:
            all_removed_successfully = True
            for backup_id in backup_ids:
                remove_params = {'number': backup_id}
                response_remove = _execute_router_command(
                    api,
                    (RouterOSCommand.CLOUD_BACKUP_REMOVE.value, remove_params),
                    entry_lines
                )
                if response_remove is None:
                    all_removed_successfully = False

            if not all_removed_successfully:
                return False

    upload_params = {
        'action': 'create-and-upload',
        'password': cloud_password
    }
    response_upload = _execute_router_command(
        api,
        (RouterOSCommand.CLOUD_BACKUP_UPLOAD.value, upload_params),
        entry_lines
    )

    if response_upload is None:
        entry_lines.append("  Cloud backup: Failed to create and upload new backup.\n")
        return False

    entry_lines.append("  Cloud backup: Successfully created and uploaded new backup.\n")

    time.sleep(2)
    latest_backups = _execute_router_command(
        api,
        RouterOSCommand.CLOUD_BACKUP_PRINT.value,
        entry_lines
    )

    if latest_backups:
        latest_backup = latest_backups[0]
        secret_key = latest_backup.get('secret-download-key')
        if secret_key:
            entry_lines.append(f"  Cloud backup: Secret Download Key: {secret_key}\n")
        else:
            entry_lines.append("  Cloud backup: Could not find secret-download-key.\n")
    else:
        entry_lines.append("  Cloud backup: Failed to retrieve backup details.\n")

    return True


def _reboot_router(api: Any, entry_lines: List[str]) -> None:
    """Reboot router via script."""
    try:
        name_key = Key('name')
        scripts = list(
            api.path('/system', 'script')
            .select(name_key)
            .where(name_key == REBOOT_SCRIPT_NAME)
        )

        if not scripts:
            add_script_params = {
                'name': REBOOT_SCRIPT_NAME,
                'source': '/system reboot',
                'policy': 'reboot'
            }
            add_response = _execute_router_command(
                api,
                (RouterOSCommand.SCRIPT_ADD.value, add_script_params),
                entry_lines
            )
            if add_response is None:
                entry_lines.append("  Failed to create reboot script. Aborting reboot.\n")
                return
            entry_lines.append("  Reboot script created successfully.\n")

        entry_lines.append("  Executing reboot script...\n")
        script_path = api.path('/system', 'script')
        tuple(script_path('run', **{'number': REBOOT_SCRIPT_NAME}))
        time.sleep(1)

    except (socket.error, TimeoutError, ConnectionResetError):
        entry_lines.append("  Router is rebooting as expected. Disconnected.\n")
    except Exception as e:
        entry_lines.append(f"  Unexpected error during reboot: {type(e).__name__}: {e}\n")


def _perform_firmware_upgrade(api: Any, entry_lines: List[str]) -> Optional[bool]:
    """Perform firmware upgrade if available."""
    routerboard_info = _execute_router_command(
        api,
        RouterOSCommand.ROUTERBOARD_PRINT.value,
        entry_lines
    )

    if not routerboard_info:
        entry_lines.append("  Firmware upgrade: Failed to retrieve routerboard information.\n")
        return False

    info = routerboard_info[0]
    current_firmware = info.get('current-firmware')
    upgrade_firmware = info.get('upgrade-firmware')

    if not current_firmware or not upgrade_firmware:
        entry_lines.append("  Firmware upgrade: Could not determine firmware versions.\n")
        return False

    if current_firmware == upgrade_firmware:
        entry_lines.append(f"  Firmware is up to date (current: {current_firmware}).\n")
        return None
    else:
        entry_lines.append(
            f"  Firmware upgrade available: {current_firmware} -> {upgrade_firmware}\n"
        )
        entry_lines.append("  Firmware upgrade: Attempting to upgrade...\n")

        upgrade_response = _execute_router_command(
            api,
            RouterOSCommand.ROUTERBOARD_UPGRADE.value,
            entry_lines
        )

        if upgrade_response is None:
            entry_lines.append("  Firmware upgrade: Failed.\n")
            return False

        entry_lines.append("  Firmware upgrade: Upgrade command sent.\n")
        return True


def worker(
    q: queue.Queue,
    default_username: str,
    default_password: str,
    cloud_password: Optional[str],
    stop_event: threading.Event,
    timeout: int,
    dry_run: bool,
    aggregated_results_list: List[Dict[str, Any]],
    router_info_list: List[RouterInfo],
    update_check_attempts: int,
    update_check_delay: float,
    upgrade_firmware: bool,
    pbar: Any,
    custom_commands: List[Any],
    desired_tree: UpdateTree,
    auto_change_tree: bool
) -> None:
    """Worker thread function to process router updates."""
    api = None

    while not stop_event.is_set():
        entry_lines = []
        success = False
        IP = None
        router_info = None

        try:
            host_info = q.get(timeout=1)
            IP = host_info.ip

            entry_lines.append(f"\nHost: {IP}\n")

            api = _connect_to_router(
                host_info,
                default_username,
                default_password,
                timeout
            )

            # Gather comprehensive router information
            router_info = _gather_router_info(api, IP, entry_lines)

            if not router_info.success:
                success = False
            else:
                success = True

                # Auto-change update tree if requested
                if auto_change_tree:
                    current_tree = _check_update_tree_status(api, desired_tree, entry_lines)
                    if not _auto_change_update_tree_ssh(
                        IP,
                        host_info.username or default_username,
                        host_info.password or default_password,
                        current_tree,
                        desired_tree,
                        entry_lines
                    ):
                        success = False

                if cloud_password:
                    backup_success = _perform_cloud_backup(api, cloud_password, entry_lines)
                    if not backup_success:
                        entry_lines.append("  Warning: Cloud backup failed. Proceeding.\n")

                firmware_upgraded = False
                if success and upgrade_firmware:
                    firmware_upgrade_status = _perform_firmware_upgrade(api, entry_lines)
                    if firmware_upgrade_status is False:
                        success = False
                    elif firmware_upgrade_status is True:
                        firmware_upgraded = True

                if success:
                    reboot_triggered = _check_and_process_updates(
                        api,
                        entry_lines,
                        dry_run,
                        update_check_attempts,
                        update_check_delay,
                        desired_tree
                    )
                    if not reboot_triggered and firmware_upgraded:
                        _reboot_router(api, entry_lines)

        except librouteros.exceptions.TrapError as e:
            error_message = f"  Error: {type(e).__name__}: {e.message if hasattr(e, 'message') else str(e)}\n"
            entry_lines.append(error_message)
            success = False
        except (TimeoutError, socket.error) as e:
            entry_lines.append(f"  Error: Connection failed - {type(e).__name__}: {e}\n")
            success = False
        except queue.Empty:
            if stop_event.is_set():
                logger.debug(f"Worker {threading.current_thread().name} exiting.")
            return
        except Exception as e:
            if IP:
                entry_lines.append(f"  Unexpected error: {type(e).__name__}: {e}\n")
            else:
                entry_lines.append(f"  Unexpected error: {type(e).__name__}: {e}\n")
            success = False
        finally:
            if api:
                try:
                    api.close()
                except Exception:
                    pass

            final_entry_text = "".join(entry_lines).strip()

            with log_lock:
                if final_entry_text:
                    logger.info("-" * 70)

                if success:
                    logger.info(final_entry_text)
                else:
                    logger.error(final_entry_text)

                if IP is not None:
                    aggregated_results_list.append({"IP": IP, "success": success})

                if router_info:
                    router_info_list.append(router_info)

            if not stop_event.is_set():
                try:
                    q.task_done()
                except ValueError:
                    logger.debug("ValueError on q.task_done()")
                    pass

            if IP is not None:
                pbar.update(1)


def generate_report(router_info_list: List[RouterInfo]) -> str:
    """
    Generate a comprehensive report from collected router information.

    Returns:
        Formatted report as string
    """
    report_lines = []
    report_lines.append("\n\n" + "=" * 100)
    report_lines.append("DETAILED ROUTER INVENTORY REPORT")
    report_lines.append("=" * 100 + "\n")

    report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    report_lines.append(f"Total Routers: {len(router_info_list)}\n")
    report_lines.append(f"Successfully Scanned: {sum(1 for r in router_info_list if r.success)}\n\n")

    # Header
    header = f"{'IP Address':<15} | {'Identity':<20} | {'Model':<20} | {'RouterOS':<12} | {'Firmware':<12} | {'Update Channel':<15} | {'System Ver':<12}"
    report_lines.append(header)
    report_lines.append("-" * 150 + "\n")

    # Data rows
    for router in router_info_list:
        if router.success:
            row = f"{router.ip:<15} | {router.identity:<20} | {router.model:<20} | {router.os_version:<12} | {router.current_firmware:<12} | {router.update_channel:<15} | {router.installed_version:<12}"
            report_lines.append(row + "\n")

    report_lines.append("\n" + "-" * 150 + "\n")

    # Detailed section
    report_lines.append("\nDETAILED INFORMATION:\n")
    report_lines.append("=" * 100 + "\n\n")

    for i, router in enumerate(router_info_list, 1):
        if router.success:
            report_lines.append(f"{i}. Router: {router.ip}\n")
            report_lines.append(f"   ├─ Identity: {router.identity}\n")
            report_lines.append(f"   ├─ Model: {router.model}\n")
            report_lines.append(f"   ├─ RouterOS Version: {router.os_version}\n")
            report_lines.append(f"   ├─ Current Firmware: {router.current_firmware}\n")
            if router.upgrade_firmware and router.upgrade_firmware != router.current_firmware:
                report_lines.append(f"   ├─ Upgrade Firmware Available: {router.upgrade_firmware} ⚠️\n")
            report_lines.append(f"   ├─ Update Channel: {router.update_channel}\n")
            report_lines.append(f"   ├─ Installed Package Version: {router.installed_version}\n")
            if router.latest_version and router.latest_version != router.installed_version:
                report_lines.append(f"   ├─ Latest Package Version: {router.latest_version} ⚠️\n")
            report_lines.append(f"   ├─ Update Status: {router.update_status}\n")
            report_lines.append(f"   └─ Timestamp: {router.timestamp}\n\n")

    # Summary statistics
    report_lines.append("\nSUMMARY STATISTICS:\n")
    report_lines.append("=" * 100 + "\n")

    channels = {}
    for router in router_info_list:
        if router.success:
            ch = router.update_channel
            channels[ch] = channels.get(ch, 0) + 1

    report_lines.append("\nUpdate Channels Distribution:\n")
    for channel, count in sorted(channels.items()):
        report_lines.append(f"  {channel}: {count} router(s)\n")

    # Firmware versions
    firmware_versions = {}
    for router in router_info_list:
        if router.success:
            fw = router.current_firmware
            firmware_versions[fw] = firmware_versions.get(fw, 0) + 1

    report_lines.append("\nFirmware Versions Distribution:\n")
    for fw, count in sorted(firmware_versions.items()):
        report_lines.append(f"  {fw}: {count} router(s)\n")

    # OS versions
    os_versions = {}
    for router in router_info_list:
        if router.success:
            os = router.os_version
            os_versions[os] = os_versions.get(os, 0) + 1

    report_lines.append("\nRouterOS Versions Distribution:\n")
    for os_ver, count in sorted(os_versions.items()):
        report_lines.append(f"  {os_ver}: {count} router(s)\n")

    # Routers needing updates
    report_lines.append("\nRouters Needing Updates:\n")
    updates_needed = [r for r in router_info_list if r.success and r.latest_version and r.latest_version != r.installed_version]
    if updates_needed:
        for router in updates_needed:
            report_lines.append(f"  {router.ip} ({router.identity}): {router.installed_version} → {router.latest_version}\n")
    else:
        report_lines.append("  None - All systems are up to date!\n")

    # Firmware upgrades available
    report_lines.append("\nRouters with Firmware Upgrades Available:\n")
    fw_updates = [r for r in router_info_list if r.success and r.upgrade_firmware and r.upgrade_firmware != r.current_firmware]
    if fw_updates:
        for router in fw_updates:
            report_lines.append(f"  {router.ip} ({router.identity}): {router.current_firmware} → {router.upgrade_firmware}\n")
    else:
        report_lines.append("  None - All firmware is up to date!\n")

    report_lines.append("\n" + "=" * 100 + "\n")

    return "".join(report_lines)


log_lock = threading.Lock()
q = queue.Queue()
threads = []
stop_event = threading.Event()
aggregated_results = []
router_info_list = []


def main():
    parser = argparse.ArgumentParser(
        description="MikroTik Mass Updater v5.3.0 - With Advanced Reporting"
    )
    parser.add_argument("-u", "--username", required=True, help="API username")
    parser.add_argument("-p", "--password", help="API password (prompted if not provided)")
    parser.add_argument("-t", "--threads", type=int, default=5, help="Number of concurrent threads")
    parser.add_argument("--timeout", type=int, default=5, help="Connection timeout in seconds")
    parser.add_argument("--ip-list", default='list.txt', help="Path to IP list file")
    parser.add_argument(
        "--port",
        type=int,
        default=8728,
        help="Default API port"
    )
    parser.add_argument(
        "--update-tree",
        type=str,
        choices=['stable', 'development', 'testing'],
        default='stable',
        help="Update tree channel"
    )
    parser.add_argument(
        "--auto-change-tree",
        action="store_true",
        help="Automatically change update tree via SSH if different"
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Generate detailed report (default: enabled)"
    )
    parser.add_argument(
        "--report-file",
        help="Save report to file (optional)"
    )
    parser.add_argument(
        "--update-check-attempts",
        type=int,
        default=15,
        help="Number of update check attempts"
    )
    parser.add_argument(
        "--update-check-delay",
        type=float,
        default=2.0,
        help="Delay between update checks in seconds"
    )
    parser.add_argument("--no-colors", action="store_true", help="Disable colored console output")
    parser.add_argument("--dry-run", action="store_true", help="Dry run mode - skip actual installation")
    parser.add_argument("--start-line", type=int, default=1, help="Start from line number in list")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--cloud-password", help="Password for cloud backup")
    parser.add_argument("--upgrade-firmware", action="store_true", help="Enable firmware upgrade")
    parser.add_argument("--custom-commands", help="Path to YAML file with custom commands")
    args = parser.parse_args()

    if not args.password:
        args.password = getpass.getpass(f"Enter password for user '{args.username}': ")

    setup_logger(not args.no_colors, args.debug)
    pbar = None

    custom_commands = []
    if args.custom_commands:
        try:
            with open(args.custom_commands, 'r') as f:
                loaded_commands = yaml.safe_load(f)
                if loaded_commands:
                    for item in loaded_commands:
                        if 'params' in item:
                            custom_commands.append((item['command'], item['params']))
                        else:
                            custom_commands.append(item['command'])
            logger.info(f"Loaded {len(custom_commands)} custom commands")
        except FileNotFoundError:
            logger.error(f"Custom commands file not found: {args.custom_commands}")
        except Exception as e:
            logger.error(f"Error parsing custom commands: {e}")

    try:
        desired_tree = UpdateTree(args.update_tree)
    except ValueError:
        logger.error(f"Invalid update tree: {args.update_tree}")
        return

    try:
        logger.info("-- Starting job --")
        logger.info(f"Target update tree: {desired_tree.value}")
        if args.auto_change_tree:
            logger.info("SSH auto-change enabled")

        try:
            with open(args.ip_list, 'r') as f:
                lines = [
                    line for i, line in enumerate(f, 1)
                    if i >= args.start_line and line.strip() and not line.strip().startswith('#')
                ]
            total_hosts = len(lines)
            pbar = tqdm(total=total_hosts, desc="Processing hosts", unit="host")
        except FileNotFoundError:
            logger.error(f"IP list file not found: {args.ip_list}")
            return

        # Start worker threads
        for i in range(args.threads):
            t = threading.Thread(
                target=worker,
                args=(
                    q, args.username, args.password, args.cloud_password, stop_event,
                    args.timeout, args.dry_run, aggregated_results, router_info_list,
                    args.update_check_attempts, args.update_check_delay,
                    args.upgrade_firmware, pbar, custom_commands, desired_tree,
                    args.auto_change_tree
                ),
                name=f"Worker-{i+1}"
            )
            threads.append(t)
            t.start()

        # Populate queue
        for line_content in lines:
            if stop_event.is_set():
                logger.warning("Interruption detected, stopping queue population.")
                break
            host_info = parse_host_line(line_content, args.port)
            if host_info:
                q.put(host_info)

        # Wait for completion
        while not q.empty() and not stop_event.is_set():
            time.sleep(0.1)

        if not stop_event.is_set():
            q.join()

    except KeyboardInterrupt:
        logger.warning("\nInterrupted by user. Shutting down gracefully...")
        stop_event.set()

    finally:
        if pbar:
            pbar.close()

        if stop_event.is_set():
            logger.warning("Clearing queue due to interruption...")
            while not q.empty():
                try:
                    q.get_nowait()
                    q.task_done()
                except queue.Empty:
                    break
                except ValueError:
                    break

        for t in threads:
            t.join()

        # Generate report
        if args.report or args.report_file:
            report = generate_report(router_info_list)
            logger.info(report)

            if args.report_file:
                try:
                    with open(args.report_file, 'w', encoding='utf-8') as f:
                        f.write(report)
                    logger.info(f"\nReport saved to: {args.report_file}")
                except Exception as e:
                    logger.error(f"Failed to save report: {e}")

        # Summary
        total_hosts_processed = len(aggregated_results)
        successful_ops = sum(1 for res in aggregated_results if res["success"])
        failed_ops = total_hosts_processed - successful_ops
        failed_ips = [res["IP"] for res in aggregated_results if not res["success"]]

        summary_lines = []
        summary_lines.append("\n\n-- Job Summary --\n")
        summary_lines.append(f"Total hosts processed: {total_hosts_processed}\n")
        summary_lines.append(f"Successful operations: {successful_ops}\n")
        summary_lines.append(f"Failed operations: {failed_ops}\n")

        if failed_ops > 0:
            summary_lines.append("Failed IPs:\n")
            for ip in failed_ips:
                summary_lines.append(f"  - {ip}\n")

        summary_output = "".join(summary_lines)
        logger.info(summary_output.strip())
        logger.info("-- Job finished --")

        logging.shutdown()


if __name__ == '__main__':
    main()
