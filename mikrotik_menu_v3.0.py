#!/usr/bin/env python3

####################################################
# MikroTik Mass Updater - ncurses Menu Interface
# Version 3.1 (Fixed - No Flickering)
# Interactive Terminal UI + Live Router Status
####################################################

import curses
import subprocess
import os
import sys
import threading
import queue
import logging
import librouteros
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field

# Setup logging for debugging
LOG_FILE = "menu_debug.log"
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class UpdateTree(str, Enum):
    """Router update channels"""
    STABLE = "stable"
    DEVELOPMENT = "development"
    TESTING = "testing"


class Color:
    """Color definitions for ncurses"""
    DEFAULT = 0
    HEADER = 1
    SELECTED = 2
    NORMAL = 3
    INFO = 4
    WARNING = 5
    SUCCESS = 6
    ERROR = 7


@dataclass
class RouterStatus:
    """Router status information"""
    ip: str
    identity: str = "N/A"
    model: str = "N/A"
    os_version: str = "N/A"
    firmware: str = "N/A"
    update_tree: str = "N/A"
    uptime: str = "N/A"
    status: str = "Checking..."
    success: bool = False


class SafeScreen:
    """Thread-safe screen wrapper with bounds checking"""

    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.lock = threading.Lock()
        self._height = 0
        self._width = 0
        self._update_size()

    def _update_size(self):
        """Update cached screen dimensions"""
        try:
            self._height, self._width = self.stdscr.getmaxyx()
        except curses.error:
            self._height, self._width = 24, 80

    @property
    def height(self):
        return self._height

    @property
    def width(self):
        return self._width

    def refresh_size(self):
        """Call after terminal resize"""
        with self.lock:
            self._update_size()

    def safe_addstr(self, y: int, x: int, text: str, attr: int = 0) -> bool:
        """Safely add string with bounds checking"""
        with self.lock:
            try:
                if y < 0 or y >= self._height - 1:
                    return False
                if x < 0 or x >= self._width:
                    return False

                # Truncate text to fit
                max_len = self._width - x - 1
                if max_len <= 0:
                    return False

                display_text = text[:max_len]
                self.stdscr.addstr(y, x, display_text, attr)
                return True
            except curses.error as e:
                logger.debug(f"addstr error at ({y},{x}): {e}")
                return False

    def safe_hline(self, y: int, x: int, char: str, length: int) -> bool:
        """Safely draw horizontal line"""
        with self.lock:
            try:
                if y < 0 or y >= self._height - 1:
                    return False
                if x < 0:
                    return False

                max_len = min(length, self._width - x - 1)
                if max_len <= 0:
                    return False

                self.stdscr.hline(y, x, char, max_len)
                return True
            except curses.error as e:
                logger.debug(f"hline error at ({y},{x}): {e}")
                return False

    def erase(self):
        """Erase screen (better than clear - no flicker)"""
        with self.lock:
            try:
                self.stdscr.erase()
            except curses.error:
                pass

    def noutrefresh(self):
        """Mark for refresh without actual update"""
        with self.lock:
            try:
                self.stdscr.noutrefresh()
            except curses.error:
                pass

    def refresh(self):
        """Perform actual screen update"""
        with self.lock:
            try:
                self.stdscr.refresh()
            except curses.error:
                pass

    def getch(self) -> int:
        """Get character input"""
        try:
            return self.stdscr.getch()
        except curses.error:
            return -1


class UpdateTreeMenu:
    """Main menu handler for MikroTik Mass Updater"""

    def __init__(self):
        self.script_path = "./mikrotik_mass_updater_v5.3.0_REPORT.py"
        self.selected_tree = UpdateTree.STABLE
        self.username = ""
        self.password = ""
        self.selected_options = {
            'auto_change': True,
            'upgrade_firmware': True,
            'report': True,
            'dry_run': True,
            'cloud_backup': False,
            'cloud_password': '',
            'threads': 5,
            'timeout': 5,
        }
        self.log_file = None
        self.current_menu = 'main'

        # Thread-safe router status storage
        self._router_statuses: List[RouterStatus] = []
        self._status_lock = threading.Lock()
        self._discovery_in_progress = False
        self._discovery_thread = None

        # Screen wrapper
        self.screen: Optional[SafeScreen] = None

        # Dirty flag for efficient redrawing
        self._needs_redraw = True

    @property
    def router_statuses(self) -> List[RouterStatus]:
        with self._status_lock:
            return list(self._router_statuses)

    @router_statuses.setter
    def router_statuses(self, value: List[RouterStatus]):
        with self._status_lock:
            self._router_statuses = value
            self._needs_redraw = True

    @property
    def discovery_in_progress(self) -> bool:
        with self._status_lock:
            return self._discovery_in_progress

    @discovery_in_progress.setter
    def discovery_in_progress(self, value: bool):
        with self._status_lock:
            self._discovery_in_progress = value
            self._needs_redraw = True

    def init_colors(self):
        """Initialize color pairs"""
        try:
            if curses.has_colors():
                curses.start_color()
                curses.use_default_colors()
                curses.init_pair(Color.HEADER, curses.COLOR_WHITE, curses.COLOR_BLUE)
                curses.init_pair(Color.SELECTED, curses.COLOR_BLACK, curses.COLOR_YELLOW)
                curses.init_pair(Color.NORMAL, curses.COLOR_WHITE, -1)
                curses.init_pair(Color.INFO, curses.COLOR_CYAN, -1)
                curses.init_pair(Color.WARNING, curses.COLOR_YELLOW, -1)
                curses.init_pair(Color.SUCCESS, curses.COLOR_GREEN, -1)
                curses.init_pair(Color.ERROR, curses.COLOR_RED, -1)
                logger.debug("Colors initialized successfully")
        except curses.error as e:
            logger.warning(f"Color initialization failed: {e}")

    def draw_header(self):
        """Draw header bar"""
        if not self.screen:
            return

        header = " MikroTik Mass Updater v3.1 - Network Status Monitor "
        width = self.screen.width

        # Center and pad header
        padded = header.center(width)
        self.screen.safe_addstr(0, 0, padded,
                                curses.color_pair(Color.HEADER) | curses.A_BOLD)

    def draw_footer(self, message: str):
        """Draw footer bar with message"""
        if not self.screen:
            return

        height = self.screen.height
        width = self.screen.width

        footer = f" [q]Quit | [↑↓]Navigate | [Enter]Select | {message} "
        padded = footer.ljust(width)

        self.screen.safe_addstr(height - 1, 0, padded,
                                curses.color_pair(Color.INFO) | curses.A_REVERSE)

    def parse_host_file(self, filepath: str) -> List[Dict[str, Any]]:
        """Parse host list from file"""
        hosts = []
        try:
            with open(filepath, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue

                    try:
                        parts = line.split('|')
                        ip_port = parts[0]

                        if ':' in ip_port:
                            ip, port_str = ip_port.rsplit(':', 1)
                            port = int(port_str)
                        else:
                            ip = ip_port
                            port = 8728

                        username = parts[1] if len(parts) > 1 else self.username
                        password = parts[2] if len(parts) > 2 else self.password

                        hosts.append({
                            'ip': ip,
                            'port': port,
                            'username': username,
                            'password': password
                        })
                    except (ValueError, IndexError) as e:
                        logger.warning(f"Parse error on line {line_num}: {e}")
                        continue

        except FileNotFoundError:
            logger.error(f"Host file not found: {filepath}")
        except Exception as e:
            logger.error(f"Error reading host file: {e}")

        return hosts

    def discover_router(self, host_info: Dict[str, Any], result_queue: queue.Queue):
        """Discover single router info"""
        status = RouterStatus(ip=host_info['ip'])
        api = None

        try:
            api = librouteros.connect(
                host=host_info['ip'],
                username=host_info['username'],
                password=host_info['password'],
                port=host_info['port'],
                timeout=host_info.get('timeout', 5)
            )

            # Get identity
            try:
                identity_data = list(api.path('/system/identity').select('name'))
                if identity_data:
                    status.identity = identity_data[0].get('name', 'N/A')
            except Exception as e:
                logger.debug(f"Identity query failed for {host_info['ip']}: {e}")

            # Get routerboard info
            try:
                rb_data = list(api.path('/system/routerboard').select('board-name', 'current-firmware'))
                if rb_data:
                    status.model = rb_data[0].get('board-name', 'N/A')
                    status.firmware = rb_data[0].get('current-firmware', 'N/A')
            except Exception as e:
                logger.debug(f"Routerboard query failed for {host_info['ip']}: {e}")

            # Get system resource
            try:
                res_data = list(api.path('/system/resource').select('version', 'uptime'))
                if res_data:
                    status.os_version = res_data[0].get('version', 'N/A')
                    status.uptime = res_data[0].get('uptime', 'N/A')
            except Exception as e:
                logger.debug(f"Resource query failed for {host_info['ip']}: {e}")

            # Get update channel
            try:
                update_data = list(api.path('/system/package/update').select('channel'))
                if update_data:
                    status.update_tree = update_data[0].get('channel', 'N/A')
            except Exception as e:
                logger.debug(f"Update channel query failed for {host_info['ip']}: {e}")

            status.success = True
            status.status = "OK"

        except Exception as e:
            error_msg = str(e)[:35]
            status.status = f"ERR: {error_msg}"
            status.success = False
            logger.debug(f"Discovery failed for {host_info['ip']}: {e}")
        finally:
            if api:
                try:
                    api.close()
                except Exception:
                    pass

        result_queue.put(status)

    def start_network_discovery(self):
        """Start discovering routers in background"""
        if self.discovery_in_progress:
            return

        hosts = self.parse_host_file('list.txt')
        if not hosts:
            logger.warning("No hosts found in list.txt")
            return

        self.discovery_in_progress = True

        # Initialize with "Checking..." status
        with self._status_lock:
            self._router_statuses = [
                RouterStatus(ip=host['ip'], status="Checking...")
                for host in hosts
            ]

        def discovery_worker():
            result_queue = queue.Queue()
            threads = []

            for host in hosts:
                t = threading.Thread(
                    target=self.discover_router,
                    args=(host, result_queue),
                    daemon=True
                )
                threads.append(t)
                t.start()

            # Wait for all threads
            for t in threads:
                t.join(timeout=10)

            # Collect results
            results = []
            while not result_queue.empty():
                try:
                    results.append(result_queue.get_nowait())
                except queue.Empty:
                    break

            # Sort by IP to maintain order
            results.sort(key=lambda x: x.ip)

            self.router_statuses = results
            self.discovery_in_progress = False
            logger.info(f"Discovery complete: {len(results)} routers found")

        self._discovery_thread = threading.Thread(target=discovery_worker, daemon=True)
        self._discovery_thread.start()

    def draw_status_table(self):
        """Draw router status table"""
        if not self.screen:
            return

        height = self.screen.height
        width = self.screen.width

        self.screen.erase()
        self.draw_header()

        # Title
        title = "LIVE NETWORK STATUS"
        self.screen.safe_addstr(2, 2, title,
                                curses.color_pair(Color.INFO) | curses.A_BOLD)

        # Discovery status indicator
        if self.discovery_in_progress:
            spinner_chars = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
            import time
            spinner = spinner_chars[int(time.time() * 10) % len(spinner_chars)]
            self.screen.safe_addstr(2, width - 20, f"{spinner} Discovering...",
                                    curses.color_pair(Color.WARNING))

        # Table separator
        self.screen.safe_hline(3, 2, curses.ACS_HLINE, width - 4)

        # Column widths (adjusted for screen width)
        if width >= 140:
            cols = {
                'ip': 15, 'identity': 16, 'model': 14,
                'os': 12, 'fw': 10, 'tree': 12, 'uptime': 15, 'status': 15
            }
        elif width >= 100:
            cols = {
                'ip': 15, 'identity': 12, 'model': 12,
                'os': 10, 'fw': 8, 'tree': 10, 'uptime': 0, 'status': 12
            }
        else:
            cols = {
                'ip': 15, 'identity': 10, 'model': 0,
                'os': 10, 'fw': 0, 'tree': 8, 'uptime': 0, 'status': 10
            }

        # Build header
        header_parts = []
        if cols['ip']: header_parts.append(f"{'IP':<{cols['ip']}}")
        if cols['identity']: header_parts.append(f"{'Identity':<{cols['identity']}}")
        if cols['model']: header_parts.append(f"{'Model':<{cols['model']}}")
        if cols['os']: header_parts.append(f"{'RouterOS':<{cols['os']}}")
        if cols['fw']: header_parts.append(f"{'FW':<{cols['fw']}}")
        if cols['tree']: header_parts.append(f"{'Tree':<{cols['tree']}}")
        if cols['uptime']: header_parts.append(f"{'Uptime':<{cols['uptime']}}")
        if cols['status']: header_parts.append(f"{'Status':<{cols['status']}}")

        header = " | ".join(header_parts)
        self.screen.safe_addstr(4, 2, header,
                                curses.color_pair(Color.HEADER) | curses.A_BOLD)

        self.screen.safe_hline(5, 2, curses.ACS_HLINE, width - 4)

        # Data rows
        statuses = self.router_statuses
        row = 6
        max_rows = height - 5

        for status in statuses:
            if row >= max_rows:
                # Show "more..." indicator
                remaining = len(statuses) - (row - 6)
                self.screen.safe_addstr(row, 2, f"... and {remaining} more",
                                        curses.color_pair(Color.WARNING))
                break

            # Choose color based on status
            if status.success:
                color = curses.color_pair(Color.SUCCESS)
                status_icon = "✓"
            elif "ERR" in status.status:
                color = curses.color_pair(Color.ERROR)
                status_icon = "✗"
            else:
                color = curses.color_pair(Color.WARNING)
                status_icon = "○"

            # Build data row
            def truncate(s: str, length: int) -> str:
                if length == 0:
                    return ""
                s = s or "N/A"
                return s[:length-1].ljust(length) if len(s) >= length else s.ljust(length)

            row_parts = []
            if cols['ip']: row_parts.append(truncate(status.ip, cols['ip']))
            if cols['identity']: row_parts.append(truncate(status.identity, cols['identity']))
            if cols['model']: row_parts.append(truncate(status.model, cols['model']))
            if cols['os']: row_parts.append(truncate(status.os_version, cols['os']))
            if cols['fw']: row_parts.append(truncate(status.firmware, cols['fw']))
            if cols['tree']: row_parts.append(truncate(status.update_tree, cols['tree']))
            if cols['uptime']: row_parts.append(truncate(status.uptime, cols['uptime']))
            if cols['status']: row_parts.append(f"{status_icon} {truncate(status.status, cols['status']-2)}")

            data_row = " | ".join(row_parts)
            self.screen.safe_addstr(row, 2, data_row, color)
            row += 1

        # Summary line
        total = len(statuses)
        ok_count = sum(1 for s in statuses if s.success)

        self.screen.safe_hline(height - 4, 2, curses.ACS_HLINE, width - 4)

        summary = f"Total: {total} | Online: {ok_count} | Offline: {total - ok_count}"
        self.screen.safe_addstr(height - 3, 2, summary,
                                curses.color_pair(Color.INFO) | curses.A_BOLD)

        self.draw_footer("[r]Refresh | [m]Menu | [q]Quit")
        self.screen.noutrefresh()
        curses.doupdate()

    def draw_main_menu(self, selected: int) -> int:
        """Draw main menu"""
        if not self.screen:
            return 7

        self.screen.erase()
        self.draw_header()

        menu_items = [
            ("1. Network Status", 'status'),
            ("2. Credentials", 'creds'),
            ("3. Choose Update Tree", 'tree'),
            ("4. Configure Options", 'options'),
            ("5. Run Update Script", 'run'),
            ("6. View Last Report", 'report'),
            ("7. Exit", 'exit'),
        ]

        y = 3
        for i, (label, _) in enumerate(menu_items):
            if i == selected:
                attr = curses.color_pair(Color.SELECTED) | curses.A_BOLD
                prefix = "► "
            else:
                attr = curses.color_pair(Color.NORMAL)
                prefix = "  "

            self.screen.safe_addstr(y + i, 2, f"{prefix}{label}", attr)

        # Current configuration display
        state_y = y + len(menu_items) + 2
        self.screen.safe_hline(state_y, 2, curses.ACS_HLINE, 50)

        info_attr = curses.color_pair(Color.INFO)
        self.screen.safe_addstr(state_y + 1, 2, "Current Configuration:", info_attr | curses.A_BOLD)

        username_display = self.username if self.username else "(not set)"
        self.screen.safe_addstr(state_y + 2, 4, f"Username: {username_display}", info_attr)

        if self.password:
            pwd_display = "●" * min(len(self.password), 12)
        else:
            pwd_display = "(not set)"
        self.screen.safe_addstr(state_y + 3, 4, f"Password: {pwd_display}", info_attr)

        self.screen.safe_addstr(state_y + 4, 4,
                                f"Update Tree: {self.selected_tree.value.upper()}", info_attr)

        auto_status = "YES" if self.selected_options['auto_change'] else "NO"
        auto_color = Color.SUCCESS if self.selected_options['auto_change'] else Color.WARNING
        self.screen.safe_addstr(state_y + 5, 4, f"Auto-Change Tree: ", info_attr)
        self.screen.safe_addstr(state_y + 5, 22, auto_status,
                                curses.color_pair(auto_color) | curses.A_BOLD)

        self.screen.safe_addstr(state_y + 6, 4,
                                f"Threads: {self.selected_options['threads']}", info_attr)

        self.draw_footer("[↑↓]Navigate | [Enter]Select")
        self.screen.noutrefresh()
        curses.doupdate()

        return len(menu_items)

    def get_input(self, prompt: str, is_password: bool = False, max_len: int = 100) -> str:
        """Get user input with proper handling"""
        if not self.screen:
            return ""

        input_str = ""
        cursor_visible = False

        try:
            curses.curs_set(1)
            cursor_visible = True
        except curses.error:
            pass

        while True:
            self.screen.erase()
            self.draw_header()

            self.screen.safe_addstr(3, 2, prompt,
                                    curses.color_pair(Color.INFO) | curses.A_BOLD)

            display_str = "●" * len(input_str) if is_password else input_str
            self.screen.safe_addstr(5, 4, ">>> " + display_str,
                                    curses.color_pair(Color.NORMAL))

            self.screen.safe_addstr(7, 2, "[Enter] Confirm | [Esc] Cancel | [Backspace] Delete",
                                    curses.color_pair(Color.WARNING))

            self.screen.noutrefresh()
            curses.doupdate()

            key = self.screen.getch()

            if key == 27:  # Escape
                input_str = ""
                break
            elif key in (curses.KEY_BACKSPACE, ord('\b'), 127):
                input_str = input_str[:-1]
            elif key in (ord('\n'), curses.KEY_ENTER):
                break
            elif 32 <= key <= 126 and len(input_str) < max_len:
                input_str += chr(key)

        try:
            if cursor_visible:
                curses.curs_set(0)
        except curses.error:
            pass

        return input_str

    def draw_creds_menu(self):
        """Draw credentials menu"""
        if not self.screen:
            return

        while True:
            self.screen.erase()
            self.draw_header()

            self.screen.safe_addstr(2, 2, "Configure API Credentials:",
                                    curses.color_pair(Color.INFO) | curses.A_BOLD)

            self.screen.safe_addstr(4, 4, "[u] Set username",
                                    curses.color_pair(Color.WARNING))
            self.screen.safe_addstr(5, 4, "[p] Set password",
                                    curses.color_pair(Color.WARNING))
            self.screen.safe_addstr(6, 4, "[b] Back to menu",
                                    curses.color_pair(Color.WARNING))

            self.screen.safe_hline(8, 4, curses.ACS_HLINE, 40)

            username_display = self.username if self.username else "(not set)"
            self.screen.safe_addstr(9, 4, f"Current Username: {username_display}",
                                    curses.color_pair(Color.NORMAL))

            if self.password:
                pwd_display = "●" * min(len(self.password), 12)
            else:
                pwd_display = "(not set)"
            self.screen.safe_addstr(10, 4, f"Current Password: {pwd_display}",
                                    curses.color_pair(Color.NORMAL))

            self.draw_footer("Credentials Setup")
            self.screen.noutrefresh()
            curses.doupdate()

            key = self.screen.getch()

            if key in (ord('u'), ord('U')):
                username = self.get_input("Enter API username:")
                if username:
                    self.username = username
            elif key in (ord('p'), ord('P')):
                password = self.get_input("Enter API password:", is_password=True)
                if password:
                    self.password = password
            elif key in (ord('b'), ord('B'), ord('q'), 27):
                break

    def draw_tree_menu(self, selected: int) -> int:
        """Draw update tree selection menu"""
        if not self.screen:
            return 3

        self.screen.erase()
        self.draw_header()

        self.screen.safe_addstr(2, 2, "Select Update Tree Channel:",
                                curses.color_pair(Color.INFO) | curses.A_BOLD)

        trees = [
            ("STABLE", UpdateTree.STABLE, "Production-ready stable releases"),
            ("DEVELOPMENT", UpdateTree.DEVELOPMENT, "Beta development releases"),
            ("TESTING", UpdateTree.TESTING, "Alpha testing releases"),
        ]

        y = 4
        for i, (label, tree_enum, desc) in enumerate(trees):
            is_current = (tree_enum == self.selected_tree)

            if i == selected:
                attr = curses.color_pair(Color.SELECTED) | curses.A_BOLD
                prefix = "► "
            else:
                attr = curses.color_pair(Color.NORMAL)
                prefix = "  "

            # Show current selection marker
            current_marker = " ◄ current" if is_current else ""
            self.screen.safe_addstr(y + i * 2, 4, f"{prefix}{label}{current_marker}", attr)
            self.screen.safe_addstr(y + i * 2 + 1, 8, f"└─ {desc}",
                                    curses.color_pair(Color.INFO))

        self.draw_footer("[↑↓]Navigate | [Enter]Select | [b]Back")
        self.screen.noutrefresh()
        curses.doupdate()

        return len(trees)

    def draw_options_menu(self, selected: int) -> int:
        """Draw options configuration menu"""
        if not self.screen:
            return 8

        self.screen.erase()
        self.draw_header()

        self.screen.safe_addstr(2, 2, "Configure Options:",
                                curses.color_pair(Color.INFO) | curses.A_BOLD)

        options = [
            ("Auto-Change Update Tree (SSH)", 'auto_change', 'toggle'),
            ("Upgrade Firmware", 'upgrade_firmware', 'toggle'),
            ("Enable Cloud Backup", 'cloud_backup', 'toggle'),
            ("Generate Report", 'report', 'toggle'),
            ("Dry-Run Mode (no changes)", 'dry_run', 'toggle'),
            ("Threads", 'threads', 'number'),
            ("Timeout (seconds)", 'timeout', 'number'),
            ("← Back to Main Menu", 'back', 'action'),
        ]

        y = 4
        for i, (label, key, opt_type) in enumerate(options):
            if i == selected:
                attr = curses.color_pair(Color.SELECTED) | curses.A_BOLD
                prefix = "► "
            else:
                prefix = "  "
                if opt_type == 'toggle':
                    if self.selected_options.get(key, False):
                        attr = curses.color_pair(Color.SUCCESS)
                    else:
                        attr = curses.color_pair(Color.WARNING)
                else:
                    attr = curses.color_pair(Color.NORMAL)

            if opt_type == 'toggle':
                value = "ON " if self.selected_options.get(key, False) else "OFF"
                value_indicator = "[✓]" if self.selected_options.get(key, False) else "[✗]"
            elif opt_type == 'number':
                value = str(self.selected_options[key])
                value_indicator = f"[{value}]"
            else:
                value_indicator = ""

            line = f"{prefix}{label:<40} {value_indicator}"
            self.screen.safe_addstr(y + i, 4, line, attr)

        self.draw_footer("[Space]Toggle | [+/-]Adjust | [b]Back")
        self.screen.noutrefresh()
        curses.doupdate()

        return len(options)

    def build_command(self) -> List[str]:
        """Build command to run as list (safer than string)"""
        cmd = [
            "python3", self.script_path,
            "-u", self.username,
            "-p", self.password,
            "--update-tree", self.selected_tree.value,
        ]

        if self.selected_options['auto_change']:
            cmd.append("--auto-change-tree")
        if self.selected_options['upgrade_firmware']:
            cmd.append("--upgrade-firmware")
        if self.selected_options['report']:
            cmd.append("--report")
            report_file = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            cmd.extend(["--report-file", report_file])
            self.log_file = report_file
        if self.selected_options['dry_run']:
            cmd.append("--dry-run")
        if self.selected_options['cloud_backup'] and self.selected_options['cloud_password']:
            cmd.extend(["--cloud-password", self.selected_options['cloud_password']])

        cmd.extend(["-t", str(self.selected_options['threads'])])
        cmd.extend(["--timeout", str(self.selected_options['timeout'])])

        return cmd

    def run_script_direct(self, stdscr):
        """Run script directly"""
        if not self.username or not self.password:
            self.screen.erase()
            self.draw_header()

            self.screen.safe_addstr(3, 2, "ERROR: Credentials not set!",
                                    curses.color_pair(Color.ERROR) | curses.A_BOLD)
            self.screen.safe_addstr(5, 2, "Please set username and password in menu option 2.",
                                    curses.color_pair(Color.WARNING))
            self.screen.safe_addstr(7, 2, "Press any key to continue...",
                                    curses.color_pair(Color.INFO))

            self.screen.noutrefresh()
            curses.doupdate()
            self.screen.getch()
            return

        cmd = self.build_command()

        # Properly exit curses
        curses.nocbreak()
        stdscr.keypad(False)
        curses.echo()
        curses.endwin()

        os.system('clear')
        print("\n" + "=" * 80)
        print("Running MikroTik Mass Updater")
        print("=" * 80)
        print(f"Command: {' '.join(cmd)}\n")

        try:
            # Use list form - safer than shell=True
            result = subprocess.run(cmd)
            print("\n" + "=" * 80)
            print(f"Process completed with exit code: {result.returncode}")
            print("=" * 80 + "\n")
        except FileNotFoundError:
            print(f"Error: Script not found: {self.script_path}")
        except Exception as e:
            print(f"Error running script: {e}")
            logger.error(f"Script execution error: {e}")

        input("Press Enter to return to menu...")

    def view_report(self, stdscr):
        """View last report file"""
        if not self.log_file or not os.path.exists(self.log_file):
            self.screen.erase()
            self.draw_header()

            self.screen.safe_addstr(3, 2, "No report file available.",
                                    curses.color_pair(Color.WARNING))
            self.screen.safe_addstr(5, 2, "Run the update script first to generate a report.",
                                    curses.color_pair(Color.INFO))
            self.screen.safe_addstr(7, 2, "Press any key to continue...",
                                    curses.color_pair(Color.INFO))

            self.screen.noutrefresh()
            curses.doupdate()
            self.screen.getch()
            return

        # Exit curses to show report
        curses.nocbreak()
        stdscr.keypad(False)
        curses.echo()
        curses.endwin()

        os.system(f"less '{self.log_file}'")

    def handle_resize(self):
        """Handle terminal resize"""
        if self.screen:
            self.screen.refresh_size()
            self._needs_redraw = True

    def run(self, stdscr):
        """Main menu loop"""
        # Initialize curses properly
        curses.curs_set(0)
        curses.noecho()
        curses.cbreak()
        stdscr.keypad(True)
        stdscr.timeout(200)  # 200ms for smooth updates without busy loop

        self.screen = SafeScreen(stdscr)
        self.init_colors()

        selected_main = 0
        selected_tree = 0
        selected_options = 0

        # Start initial discovery
        self.start_network_discovery()

        logger.info("Menu started")

        while True:
            try:
                # Handle terminal resize
                if curses.is_term_resized(self.screen.height, self.screen.width):
                    self.handle_resize()
                    stdscr.clear()

                if self.current_menu == 'main':
                    num_items = self.draw_main_menu(selected_main)
                    key = self.screen.getch()

                    if key == -1:  # Timeout - no input
                        continue
                    elif key == ord('q'):
                        break
                    elif key == curses.KEY_RESIZE:
                        self.handle_resize()
                    elif key == curses.KEY_UP:
                        selected_main = (selected_main - 1) % num_items
                    elif key == curses.KEY_DOWN:
                        selected_main = (selected_main + 1) % num_items
                    elif key in (ord('\n'), curses.KEY_ENTER):
                        if selected_main == 0:  # Network Status
                            self.current_menu = 'status'
                        elif selected_main == 1:  # Credentials
                            self.draw_creds_menu()
                        elif selected_main == 2:  # Update Tree
                            self.current_menu = 'tree'
                            # Pre-select current tree
                            trees = [UpdateTree.STABLE, UpdateTree.DEVELOPMENT, UpdateTree.TESTING]
                            selected_tree = trees.index(self.selected_tree)
                        elif selected_main == 3:  # Options
                            self.current_menu = 'options'
                            selected_options = 0
                        elif selected_main == 4:  # Run Script
                            self.run_script_direct(stdscr)
                            # Reinitialize curses
                            curses.cbreak()
                            stdscr.keypad(True)
                            curses.noecho()
                            curses.curs_set(0)
                            stdscr.clear()
                            self.screen = SafeScreen(stdscr)
                            self.init_colors()
                        elif selected_main == 5:  # View Report
                            self.view_report(stdscr)
                            curses.cbreak()
                            stdscr.keypad(True)
                            curses.noecho()
                            curses.curs_set(0)
                            stdscr.clear()
                            self.screen = SafeScreen(stdscr)
                            self.init_colors()
                        elif selected_main == 6:  # Exit
                            break

                elif self.current_menu == 'status':
                    self.draw_status_table()
                    key = self.screen.getch()

                    if key == -1:
                        continue
                    elif key in (ord('q'), ord('m'), 27):
                        self.current_menu = 'main'
                    elif key == ord('r'):
                        self.start_network_discovery()
                    elif key == curses.KEY_RESIZE:
                        self.handle_resize()

                elif self.current_menu == 'tree':
                    num_items = self.draw_tree_menu(selected_tree)
                    key = self.screen.getch()

                    if key == -1:
                        continue
                    elif key in (ord('q'), ord('b'), 27):
                        self.current_menu = 'main'
                    elif key == curses.KEY_UP:
                        selected_tree = (selected_tree - 1) % num_items
                    elif key == curses.KEY_DOWN:
                        selected_tree = (selected_tree + 1) % num_items
                    elif key in (ord('\n'), curses.KEY_ENTER):
                        trees = [UpdateTree.STABLE, UpdateTree.DEVELOPMENT, UpdateTree.TESTING]
                        self.selected_tree = trees[selected_tree]
                        self.current_menu = 'main'
                    elif key == curses.KEY_RESIZE:
                        self.handle_resize()

                elif self.current_menu == 'options':
                    num_items = self.draw_options_menu(selected_options)
                    key = self.screen.getch()

                    if key == -1:
                        continue
                    elif key in (ord('q'), ord('b'), 27):
                        self.current_menu = 'main'
                    elif key == curses.KEY_UP:
                        selected_options = (selected_options - 1) % num_items
                    elif key == curses.KEY_DOWN:
                        selected_options = (selected_options + 1) % num_items
                    elif key == ord(' '):
                        # Toggle options
                        toggle_keys = ['auto_change', 'upgrade_firmware', 'cloud_backup',
                                       'report', 'dry_run']
                        if selected_options < len(toggle_keys):
                            key_name = toggle_keys[selected_options]
                            self.selected_options[key_name] = not self.selected_options[key_name]
                    elif key in (ord('+'), ord('=')):
                        if selected_options == 5:  # Threads
                            self.selected_options['threads'] = min(20, self.selected_options['threads'] + 1)
                        elif selected_options == 6:  # Timeout
                            self.selected_options['timeout'] = min(60, self.selected_options['timeout'] + 1)
                    elif key == ord('-'):
                        if selected_options == 5:  # Threads
                            self.selected_options['threads'] = max(1, self.selected_options['threads'] - 1)
                        elif selected_options == 6:  # Timeout
                            self.selected_options['timeout'] = max(1, self.selected_options['timeout'] - 1)
                    elif key in (ord('\n'), curses.KEY_ENTER):
                        if selected_options == num_items - 1:  # Back
                            self.current_menu = 'main'
                    elif key == curses.KEY_RESIZE:
                        self.handle_resize()

            except KeyboardInterrupt:
                logger.info("Menu interrupted by user")
                break
            except curses.error as e:
                logger.error(f"Curses error: {e}")
                continue
            except Exception as e:
                logger.error(f"Unexpected error in menu loop: {e}")
                continue

        logger.info("Menu exited")


def main():
    """Entry point"""
    script_path = "./mikrotik_mass_updater_v5.3.0_REPORT.py"

    if not os.path.exists(script_path):
        print(f"Error: {script_path} not found!")
        print("Make sure the script is in the current directory.")
        sys.exit(1)

    menu = UpdateTreeMenu()

    try:
        curses.wrapper(menu.run)
    except KeyboardInterrupt:
        print("\nMenu terminated by user.")
        sys.exit(0)
    except Exception as e:
        print(f"Fatal error: {e}")
        logger.exception("Fatal error in main")
        sys.exit(1)

    print("Goodbye!")


if __name__ == '__main__':
    main()
