"""Update service for MikroTik RouterOS updates"""

import logging
import time
import socket
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass

import librouteros
from librouteros.query import Key

from ..core.constants import (
    MAX_RETRY_ATTEMPTS, RETRY_DELAY_SECONDS,
    DEFAULT_UPDATE_CHECK_ATTEMPTS, UPDATE_CHECK_DELAY,
    REBOOT_SCRIPT_NAME
)
from ..core.enums import UpdateTree, RouterOSCommand
from .router_service import RouterService, HostInfo
from .ssh_service import SSHService

logger = logging.getLogger(__name__)


@dataclass
class UpdateResult:
    """Result of an update operation"""
    ip: str
    identity: Optional[str] = None
    success: bool = False
    previous_version: Optional[str] = None
    new_version: Optional[str] = None
    firmware_upgraded: bool = False
    backup_created: bool = False
    tree_changed: bool = False
    rebooted: bool = False
    error: Optional[str] = None
    messages: List[str] = None
    # Additional router info collected during update
    update_channel: Optional[str] = None
    ros_version: Optional[str] = None
    firmware: Optional[str] = None
    upgrade_firmware: Optional[str] = None
    model: Optional[str] = None

    def __post_init__(self):
        if self.messages is None:
            self.messages = []


class UpdateService:
    """Service for RouterOS update operations"""

    @staticmethod
    def _parse_version(version_str: str) -> tuple:
        """
        Parse MikroTik version string into comparable tuple.
        Examples: 7.21.2, 7.22beta6, 7.21rc6
        Returns tuple: (major, minor, patch, prerelease_type, prerelease_num)
        prerelease_type: 0=stable, -1=rc, -2=beta, -3=alpha
        """
        import re
        if not version_str:
            return (0, 0, 0, 0, 0)

        # Remove any extra text after version (like "(testing) 2026-01-09...")
        version_str = version_str.split()[0] if ' ' in version_str else version_str

        # Match version pattern: 7.21.2 or 7.22beta6 or 7.21rc6
        match = re.match(r'^(\d+)\.(\d+)(?:\.(\d+))?(?:(alpha|beta|rc)(\d+))?', version_str, re.IGNORECASE)
        if not match:
            return (0, 0, 0, 0, 0)

        major = int(match.group(1))
        minor = int(match.group(2))
        patch = int(match.group(3) or 0)

        prerelease_type = 0  # stable
        prerelease_num = 0

        if match.group(4):
            pr_type = match.group(4).lower()
            prerelease_num = int(match.group(5))
            if pr_type == 'alpha':
                prerelease_type = -3
            elif pr_type == 'beta':
                prerelease_type = -2
            elif pr_type == 'rc':
                prerelease_type = -1

        return (major, minor, patch, prerelease_type, prerelease_num)

    @staticmethod
    def _is_newer_version(latest: str, installed: str) -> bool:
        """
        Check if latest version is newer than installed version.
        Returns True if update is available.
        """
        if not latest or not installed:
            return False

        latest_parsed = UpdateService._parse_version(latest)
        installed_parsed = UpdateService._parse_version(installed)

        return latest_parsed > installed_parsed

    @staticmethod
    def check_update_tree_status(api: Any, desired_tree: UpdateTree) -> Tuple[str, bool]:
        """
        Check current update tree status.

        Returns:
            Tuple of (current_channel, matches_desired)
        """
        try:
            response = list(api.path('/system/package/update').select('channel', 'status'))
            if response:
                status_info = response[0]
                current_channel = status_info.get('channel', status_info.get('status', 'unknown'))
                matches = desired_tree.value.lower() in current_channel.lower()
                return current_channel, matches
        except Exception as e:
            logger.debug(f"Error checking update tree: {e}")

        return "unknown", False

    @staticmethod
    def auto_change_update_tree(
        ip: str,
        username: str,
        password: str,
        current_tree: str,
        desired_tree: UpdateTree
    ) -> Tuple[bool, str]:
        """
        Automatically change update tree via SSH if needed.

        Returns:
            Tuple of (success, message)
        """
        if desired_tree.value.lower() in current_tree.lower():
            return True, f"Update tree already set to '{desired_tree.value}'"

        success, message = SSHService.change_update_tree(
            ip, username, password, desired_tree
        )

        if success:
            time.sleep(1)  # Wait for change to take effect

        return success, message

    @staticmethod
    def check_for_updates(
        api: Any,
        check_attempts: int = DEFAULT_UPDATE_CHECK_ATTEMPTS,
        check_delay: float = UPDATE_CHECK_DELAY
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Check for available updates.

        Returns:
            Tuple of (updates_available, installed_version, latest_version)
        """
        try:
            # Trigger update check
            api.path('/system/package/update')('check-for-updates')
        except Exception as e:
            logger.debug(f"Error triggering update check: {e}")
            return False, None, None

        # Wait for check to complete
        for attempt in range(check_attempts):
            time.sleep(check_delay)
            try:
                status_response = list(api.path('/system/package/update').select(
                    'status', 'installed-version', 'latest-version'
                ))
                if status_response:
                    status = status_response[0].get('status', '').lower()
                    if 'checking' not in status:
                        installed = status_response[0].get('installed-version')
                        latest = status_response[0].get('latest-version')

                        if latest and latest != installed:
                            return True, installed, latest
                        return False, installed, latest
            except Exception as e:
                logger.debug(f"Error checking update status: {e}")

        return False, None, None

    @staticmethod
    def install_updates(api: Any, max_retries: int = 2) -> Tuple[bool, str]:
        """
        Install available updates with retry support.

        Returns:
            Tuple of (success, message)
        """
        import time as time_module

        last_error = None
        for attempt in range(max_retries):
            try:
                update_path = api.path('system', 'package', 'update')
                # Use tuple() to force execution like original script
                tuple(update_path('install'))
                return True, "Update installation initiated, router will reboot"
            except (socket.error, TimeoutError, ConnectionResetError):
                # Expected - router is rebooting
                return True, "Update initiated, router is rebooting"
            except librouteros.exceptions.TrapError as e:
                last_error = e
                error_msg = e.message if hasattr(e, 'message') else str(e)
                logger.warning(f"Install attempt {attempt + 1} failed: {error_msg}")
                if attempt < max_retries - 1:
                    time_module.sleep(RETRY_DELAY_SECONDS)
                    continue
            except Exception as e:
                last_error = e
                logger.warning(f"Install attempt {attempt + 1} failed: {type(e).__name__}: {e}")
                if attempt < max_retries - 1:
                    time_module.sleep(RETRY_DELAY_SECONDS)
                    continue

        return False, f"Failed to install updates after {max_retries} attempts: {type(last_error).__name__}: {last_error}"

    @staticmethod
    def check_firmware_upgrade(api: Any) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Check if firmware upgrade is available.

        Returns:
            Tuple of (upgrade_available, current_firmware, upgrade_firmware)
        """
        try:
            rb_response = list(api.path('/system/routerboard').select(
                'current-firmware', 'upgrade-firmware'
            ))
            if rb_response:
                info = rb_response[0]
                current = info.get('current-firmware')
                upgrade = info.get('upgrade-firmware')

                if current and upgrade and current != upgrade:
                    return True, current, upgrade
                return False, current, upgrade
        except Exception as e:
            logger.debug(f"Error checking firmware: {e}")

        return False, None, None

    @staticmethod
    def upgrade_firmware(api: Any) -> Tuple[bool, str]:
        """
        Upgrade routerboard firmware.

        Returns:
            Tuple of (success, message)
        """
        try:
            # Use tuple() to force execution, matching original script behavior
            routerboard_path = api.path('/system', 'routerboard')
            tuple(routerboard_path('upgrade'))
            return True, "Firmware upgrade command sent"
        except Exception as e:
            return False, f"Firmware upgrade failed: {type(e).__name__}: {e}"

    @staticmethod
    def reboot_router(api: Any) -> Tuple[bool, str]:
        """
        Reboot router using script method.

        Returns:
            Tuple of (success, message)
        """
        try:
            # Check if reboot script exists
            name_key = Key('name')
            scripts = list(
                api.path('/system', 'script')
                .select(name_key)
                .where(name_key == REBOOT_SCRIPT_NAME)
            )

            if not scripts:
                # Create reboot script
                api.path('/system/script').add(
                    name=REBOOT_SCRIPT_NAME,
                    source='/system reboot',
                    policy='reboot'
                )

            # Run reboot script
            script_path = api.path('/system', 'script')
            tuple(script_path('run', **{'number': REBOOT_SCRIPT_NAME}))
            time.sleep(1)

            return True, "Reboot initiated"

        except (socket.error, TimeoutError, ConnectionResetError):
            return True, "Router is rebooting as expected"
        except librouteros.exceptions.ConnectionClosed:
            return True, "Router is rebooting (connection closed)"
        except Exception as e:
            # Check if it's a connection-related error (router rebooting)
            error_str = str(e).lower()
            if 'closed' in error_str or 'reset' in error_str or 'connection' in error_str:
                return True, "Router is rebooting"
            return False, f"Reboot failed: {type(e).__name__}: {e}"

    @staticmethod
    def process_router_update(
        host: HostInfo,
        default_username: str,
        default_password: str,
        desired_tree: UpdateTree = UpdateTree.STABLE,
        auto_change_tree: bool = False,
        upgrade_firmware: bool = False,
        dry_run: bool = False,
        timeout: int = 30,
        cached_latest_version: Optional[str] = None
    ) -> UpdateResult:
        """
        Process complete update for a single router.

        Args:
            host: Router host information
            default_username: Default API username
            default_password: Default API password
            desired_tree: Target update tree
            auto_change_tree: Whether to auto-change tree via SSH
            upgrade_firmware: Whether to upgrade firmware
            dry_run: If True, don't perform actual updates
            timeout: Connection timeout
            cached_latest_version: Fallback latest version from database if router can't fetch it

        Returns:
            UpdateResult with operation results
        """
        result = UpdateResult(ip=host.ip)
        username = host.username or default_username
        password = host.password or default_password
        api = None

        try:
            # Connect to router
            api = RouterService.connect(host, default_username, default_password, timeout)
            result.messages.append(f"Connected to {host.ip}")

            # Get router identity
            try:
                identity_data = list(api.path('/system/identity').select('name'))
                if identity_data:
                    result.identity = identity_data[0].get('name')
            except Exception:
                pass

            # Check and change update tree if needed
            current_tree, matches = UpdateService.check_update_tree_status(api, desired_tree)
            result.messages.append(f"Current update tree: {current_tree}")

            if auto_change_tree and not matches:
                success, msg = UpdateService.auto_change_update_tree(
                    host.ip, username, password, current_tree, desired_tree
                )
                result.messages.append(msg)
                result.tree_changed = success

                if not success:
                    result.error = "Failed to change update tree"
                    return result

            # Check firmware upgrade FIRST (before RouterOS updates)
            # This matches the original script behavior
            firmware_upgraded = False
            if upgrade_firmware:
                fw_available, current_fw, upgrade_fw = UpdateService.check_firmware_upgrade(api)

                if fw_available:
                    result.messages.append(f"Firmware upgrade available: {current_fw} -> {upgrade_fw}")

                    if not dry_run:
                        success, msg = UpdateService.upgrade_firmware(api)
                        result.messages.append(msg)

                        if success:
                            result.firmware_upgraded = True
                            firmware_upgraded = True
                            # Wait for firmware upgrade command to be fully processed
                            # MikroTik needs time to prepare firmware for flashing
                            result.messages.append("Waiting for firmware to be prepared (10s)...")
                            time.sleep(10)
                    else:
                        result.messages.append("Dry-run: Skipping firmware upgrade")
                else:
                    result.messages.append(f"Firmware is up to date: {current_fw}")

            # Check for RouterOS updates
            updates_available, installed, latest = UpdateService.check_for_updates(api)
            result.previous_version = installed

            # If router couldn't fetch latest version, use cached version from database
            if not latest and cached_latest_version:
                latest = cached_latest_version
                result.messages.append(f"Using cached latest version: {latest}")
                # Re-evaluate if update is available using version comparison
                if installed and latest:
                    updates_available = UpdateService._is_newer_version(latest, installed)

            result.new_version = latest

            reboot_triggered = False
            if updates_available:
                result.messages.append(f"RouterOS update available: {installed} -> {latest}")

                if not dry_run:
                    # Wait before installing (as per original script)
                    time.sleep(2)
                    success, msg = UpdateService.install_updates(api)
                    result.messages.append(msg)
                    if success:
                        result.rebooted = True
                        reboot_triggered = True
                    else:
                        result.error = msg
                else:
                    result.messages.append("Dry-run: Skipping update installation")
            else:
                result.messages.append(f"RouterOS is up to date: {installed}")

            # If firmware was upgraded but no RouterOS update triggered reboot, reboot now
            if firmware_upgraded and not reboot_triggered:
                success, msg = UpdateService.reboot_router(api)
                result.messages.append(msg)
                result.rebooted = success

            # Collect full router info for database update (if not rebooting)
            if not result.rebooted:
                try:
                    # Get RouterOS version
                    resource = list(api.path('/system/resource').select('version', 'board-name'))
                    if resource:
                        result.ros_version = resource[0].get('version')
                        result.model = resource[0].get('board-name')

                    # Get firmware info
                    rb_info = list(api.path('/system/routerboard').select(
                        'current-firmware', 'upgrade-firmware'
                    ))
                    if rb_info:
                        result.firmware = rb_info[0].get('current-firmware')
                        result.upgrade_firmware = rb_info[0].get('upgrade-firmware')

                    # Get update channel
                    update_info = list(api.path('/system/package/update').select('channel'))
                    if update_info:
                        result.update_channel = update_info[0].get('channel')
                except Exception:
                    pass  # Non-critical, continue

            result.success = True

        except librouteros.exceptions.TrapError as e:
            error_msg = e.message if hasattr(e, 'message') else str(e)
            result.error = f"API Error: {error_msg}"
            result.messages.append(result.error)
        except (TimeoutError, socket.error) as e:
            result.error = f"Connection failed: {type(e).__name__}"
            result.messages.append(result.error)
        except Exception as e:
            result.error = f"Unexpected error: {type(e).__name__}: {str(e)[:50]}"
            result.messages.append(result.error)
        finally:
            if api:
                try:
                    api.close()
                except Exception:
                    pass

        return result
