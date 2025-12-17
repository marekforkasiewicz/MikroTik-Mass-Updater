#!/usr/bin/env python3

####################################################
# MikroTik Mass Updater - ncurses Menu Interface
# Version 3.0 (With Network Discovery)
# Interactive Terminal UI + Live Router Status
####################################################

import curses
import subprocess
import os
import sys
import threading
import queue
import librouteros
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

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

class UpdateTreeMenu:
    """Main menu handler for MikroTik Mass Updater"""

    def __init__(self):
        self.script_path = "./mikrotik_mass_updater_v5.3.0_REPORT.py"
        self.selected_tree = UpdateTree.STABLE
        self.username = "admin"
        self.password = "password"
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
        self.router_statuses: List[RouterStatus] = []
        self.discovery_in_progress = False
        self.discovery_thread = None

    def init_colors(self, stdscr):
        """Initialize color pairs"""
        try:
            curses.init_pair(Color.HEADER, curses.COLOR_WHITE, curses.COLOR_BLUE)
            curses.init_pair(Color.SELECTED, curses.COLOR_BLACK, curses.COLOR_YELLOW)
            curses.init_pair(Color.NORMAL, curses.COLOR_WHITE, curses.COLOR_BLACK)
            curses.init_pair(Color.INFO, curses.COLOR_CYAN, curses.COLOR_BLACK)
            curses.init_pair(Color.WARNING, curses.COLOR_YELLOW, curses.COLOR_BLACK)
            curses.init_pair(Color.SUCCESS, curses.COLOR_GREEN, curses.COLOR_BLACK)
            curses.init_pair(Color.ERROR, curses.COLOR_RED, curses.COLOR_BLACK)
        except Exception as e:
            pass

    def draw_header(self, stdscr):
        """Draw header bar"""
        try:
            height, width = stdscr.getmaxyx()
            header = "MikroTik Mass Updater v3.0 - Network Status Monitor"
            stdscr.attron(curses.color_pair(Color.HEADER))
            stdscr.addstr(0, 0, header.center(width))
            stdscr.attroff(curses.color_pair(Color.HEADER))
        except Exception:
            pass

    def draw_footer(self, stdscr, message: str):
        """Draw footer bar with message"""
        try:
            height, width = stdscr.getmaxyx()
            footer = f"[q]uit | [↑↓]Navigate | [Enter]Select | [Space]Toggle | {message}"
            stdscr.attron(curses.color_pair(Color.INFO))
            stdscr.addstr(height - 1, 0, footer[:width])
            stdscr.attroff(curses.color_pair(Color.INFO))
        except Exception:
            pass

    def parse_host_file(self, filepath: str) -> List[Dict[str, Any]]:
        """Parse host list from file"""
        hosts = []
        try:
            with open(filepath, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    parts = line.split('|')
                    ip_port = parts[0]
                    
                    if ':' in ip_port:
                        ip, port = ip_port.rsplit(':', 1)
                        port = int(port)
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
        except FileNotFoundError:
            pass
        except Exception as e:
            pass
        
        return hosts

    def discover_router(self, host_info: Dict[str, Any], result_queue: queue.Queue):
        """Discover single router info"""
        status = RouterStatus(ip=host_info['ip'])
        
        try:
            # Connect to router
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
            except:
                pass
            
            # Get routerboard info
            try:
                rb_data = list(api.path('/system/routerboard').select('board-name', 'current-firmware'))
                if rb_data:
                    status.model = rb_data[0].get('board-name', 'N/A')
                    status.firmware = rb_data[0].get('current-firmware', 'N/A')
            except:
                pass
            
            # Get system resource
            try:
                res_data = list(api.path('/system/resource').select('version', 'uptime'))
                if res_data:
                    status.os_version = res_data[0].get('version', 'N/A')
                    status.uptime = res_data[0].get('uptime', 'N/A')
            except:
                pass
            
            # Get update channel
            try:
                update_data = list(api.path('/system/package/update').select('channel'))
                if update_data:
                    status.update_tree = update_data[0].get('channel', 'N/A')
            except:
                pass
            
            status.success = True
            status.status = "✓ OK"
            
            api.close()
            
        except Exception as e:
            status.status = f"✗ ERROR: {str(e)[:40]}"
            status.success = False
        
        result_queue.put(status)

    def start_network_discovery(self, stdscr):
        """Start discovering routers in background"""
        if self.discovery_in_progress:
            return
        
        hosts = self.parse_host_file('list.txt')
        if not hosts:
            return
        
        self.discovery_in_progress = True
        self.router_statuses = [RouterStatus(ip=host['ip'], status="Initializing...") for host in hosts]
        
        def discovery_worker():
            result_queue = queue.Queue()
            threads = []
            
            for host in hosts:
                t = threading.Thread(target=self.discover_router, args=(host, result_queue))
                threads.append(t)
                t.start()
            
            for t in threads:
                t.join()
            
            # Collect results
            results = []
            while not result_queue.empty():
                results.append(result_queue.get())
            
            self.router_statuses = results
            self.discovery_in_progress = False
        
        self.discovery_thread = threading.Thread(target=discovery_worker, daemon=True)
        self.discovery_thread.start()

    def draw_status_table(self, stdscr):
        """Draw router status table"""
        height, width = stdscr.getmaxyx()
        
        try:
            stdscr.clear()
            self.draw_header(stdscr)
            
            # Title and status
            stdscr.attron(curses.color_pair(Color.INFO))
            status_text = "LIVE NETWORK STATUS" if self.router_statuses else "No routers configured"
            stdscr.addstr(2, 2, status_text)
            
            if self.discovery_in_progress:
                stdscr.attron(curses.color_pair(Color.WARNING))
                stdscr.addstr(2, width - 30, "⟳ Discovering...")
                stdscr.attroff(curses.color_pair(Color.WARNING))
            
            stdscr.attroff(curses.color_pair(Color.INFO))
            
            # Table headers
            stdscr.addstr(3, 2, "─" * (width - 4))
            
            header = f"{'IP':<15} │ {'Identity':<16} │ {'Model':<12} │ {'RouterOS':<10} │ {'FW':<8} │ {'Tree':<12} │ {'Uptime':<15} │ {'Status':<12}"
            stdscr.attron(curses.color_pair(Color.HEADER))
            stdscr.addstr(4, 2, header[:width-4])
            stdscr.attroff(curses.color_pair(Color.HEADER))
            
            stdscr.addstr(5, 2, "─" * (width - 4))
            
            # Data rows
            row = 6
            for status in self.router_statuses:
                if row >= height - 3:
                    break
                
                # Choose color based on status
                if status.status == "✓ OK":
                    color = curses.color_pair(Color.SUCCESS)
                elif "ERROR" in status.status:
                    color = curses.color_pair(Color.ERROR)
                else:
                    color = curses.color_pair(Color.WARNING)
                
                # Truncate long values
                identity = status.identity[:16] if status.identity else "N/A"
                model = status.model[:12] if status.model else "N/A"
                os_ver = status.os_version[:10] if status.os_version else "N/A"
                fw = status.firmware[:8] if status.firmware else "N/A"
                tree = status.update_tree[:12] if status.update_tree else "N/A"
                uptime = status.uptime[:15] if status.uptime else "N/A"
                
                data = f"{status.ip:<15} │ {identity:<16} │ {model:<12} │ {os_ver:<10} │ {fw:<8} │ {tree:<12} │ {uptime:<15} │ "
                
                stdscr.attron(color)
                stdscr.addstr(row, 2, data[:width-4], curses.A_BOLD)
                stdscr.addstr(row, 2 + len(data), status.status[:12])
                stdscr.attroff(color)
                
                row += 1
            
            # Summary
            total = len(self.router_statuses)
            ok_count = sum(1 for s in self.router_statuses if s.status == "✓ OK")
            
            stdscr.addstr(height - 3, 2, "─" * (width - 4))
            stdscr.attron(curses.color_pair(Color.INFO))
            summary = f"Routers: {total} │ Online: {ok_count} │ Offline: {total - ok_count}"
            stdscr.addstr(height - 2, 2, summary)
            stdscr.attroff(curses.color_pair(Color.INFO))
            
            self.draw_footer(stdscr, "Press [r] to refresh | [m] for menu")
            
            stdscr.refresh()
            
        except Exception as e:
            pass

    def draw_main_menu(self, stdscr, selected: int) -> int:
        """Draw main menu"""
        height, width = stdscr.getmaxyx()
        
        try:
            stdscr.clear()
            self.draw_header(stdscr)
            
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
                    stdscr.attron(curses.color_pair(Color.SELECTED))
                    stdscr.addstr(y + i, 2, f"► {label}")
                    stdscr.attroff(curses.color_pair(Color.SELECTED))
                else:
                    stdscr.attron(curses.color_pair(Color.NORMAL))
                    stdscr.addstr(y + i, 2, f" {label}")
                    stdscr.attroff(curses.color_pair(Color.NORMAL))
            
            # Draw current state
            state_y = y + len(menu_items) + 2
            stdscr.attron(curses.color_pair(Color.INFO))
            stdscr.addstr(state_y, 2, "═" * (width - 4))
            stdscr.addstr(state_y + 1, 2, f"Username: {self.username}")
            pwd_display = "●" * len(self.password) if self.password else "NOT SET"
            stdscr.addstr(state_y + 2, 2, f"Password: {pwd_display}")
            stdscr.addstr(state_y + 3, 2, f"Update Tree: {self.selected_tree.value.upper()}")
            stdscr.addstr(state_y + 4, 2, f"Auto-Change: {'✓ YES' if self.selected_options['auto_change'] else '✗ NO'}")
            stdscr.addstr(state_y + 5, 2, f"Threads: {self.selected_options['threads']}")
            stdscr.attroff(curses.color_pair(Color.INFO))
            
            self.draw_footer(stdscr, "Main Menu")
            
            stdscr.refresh()
            
        except Exception:
            pass
        
        return 7

    def get_input(self, stdscr, prompt: str, is_password: bool = False, max_len: int = 100) -> str:
        """Get user input"""
        height, width = stdscr.getmaxyx()
        input_str = ""
        
        while True:
            try:
                stdscr.clear()
                self.draw_header(stdscr)
                stdscr.attron(curses.color_pair(Color.INFO))
                stdscr.addstr(3, 2, prompt)
                stdscr.attroff(curses.color_pair(Color.INFO))
                stdscr.attron(curses.color_pair(Color.NORMAL))
                display_str = "*" * len(input_str) if is_password else input_str
                stdscr.addstr(5, 4, ">>> " + display_str[:width - 8])
                stdscr.attroff(curses.color_pair(Color.NORMAL))
                stdscr.attron(curses.color_pair(Color.WARNING))
                stdscr.addstr(7, 2, "[Enter] confirm | [Esc] cancel | [Backspace] delete")
                stdscr.attroff(curses.color_pair(Color.WARNING))
                stdscr.refresh()
            except Exception:
                pass
            
            key = stdscr.getch()
            
            if key == 27:  # Escape
                return ""
            elif key == curses.KEY_BACKSPACE or key == ord('\b') or key == 127:
                input_str = input_str[:-1]
            elif key == ord('\n'):
                return input_str
            elif 32 <= key <= 126 and len(input_str) < max_len:
                input_str += chr(key)

    def draw_creds_menu(self, stdscr):
        """Draw credentials menu"""
        height, width = stdscr.getmaxyx()
        
        try:
            stdscr.clear()
            self.draw_header(stdscr)
            stdscr.attron(curses.color_pair(Color.INFO))
            stdscr.addstr(2, 2, "Configure API Credentials:")
            stdscr.attroff(curses.color_pair(Color.INFO))
            stdscr.attron(curses.color_pair(Color.WARNING))
            stdscr.addstr(4, 4, "Press [u] to set username")
            stdscr.addstr(5, 4, "Press [p] to set password")
            stdscr.addstr(6, 4, "Press [b] to go back")
            stdscr.attroff(curses.color_pair(Color.WARNING))
            stdscr.attron(curses.color_pair(Color.NORMAL))
            stdscr.addstr(8, 4, f"Current Username: {self.username}")
            pwd_display = "●" * len(self.password) if self.password else "NOT SET"
            stdscr.addstr(9, 4, f"Current Password: {pwd_display}")
            stdscr.attroff(curses.color_pair(Color.NORMAL))
            self.draw_footer(stdscr, "Credentials Setup")
            stdscr.refresh()
        except Exception:
            pass
        
        while True:
            key = stdscr.getch()
            if key == ord('u') or key == ord('U'):
                username = self.get_input(stdscr, "Enter API username:")
                if username:
                    self.username = username
                break
            elif key == ord('p') or key == ord('P'):
                password = self.get_input(stdscr, "Enter API password:", is_password=True)
                if password:
                    self.password = password
                break
            elif key == ord('b') or key == ord('B') or key == ord('q'):
                break

    def draw_tree_menu(self, stdscr, selected: int) -> int:
        """Draw update tree selection menu"""
        height, width = stdscr.getmaxyx()
        
        try:
            stdscr.clear()
            self.draw_header(stdscr)
            stdscr.attron(curses.color_pair(Color.INFO))
            stdscr.addstr(2, 2, "Select Update Tree Channel:")
            stdscr.attroff(curses.color_pair(Color.INFO))
            
            trees = [
                ("STABLE", UpdateTree.STABLE, "Production-ready stable releases"),
                ("DEVELOPMENT", UpdateTree.DEVELOPMENT, "Beta development releases"),
                ("TESTING", UpdateTree.TESTING, "Alpha testing releases"),
            ]
            
            y = 4
            for i, (label, tree_enum, desc) in enumerate(trees):
                if i == selected:
                    stdscr.attron(curses.color_pair(Color.SELECTED))
                    stdscr.addstr(y + i * 2, 4, f"► {label}")
                    stdscr.attroff(curses.color_pair(Color.SELECTED))
                else:
                    stdscr.attron(curses.color_pair(Color.NORMAL))
                    stdscr.addstr(y + i * 2, 4, f" {label}")
                    stdscr.attroff(curses.color_pair(Color.NORMAL))
                
                stdscr.attron(curses.color_pair(Color.INFO))
                stdscr.addstr(y + i * 2 + 1, 6, f"└─ {desc}")
                stdscr.attroff(curses.color_pair(Color.INFO))
            
            self.draw_footer(stdscr, "Select Tree | [Enter]Confirm")
            stdscr.refresh()
        except Exception:
            pass
        
        return 3

    def draw_options_menu(self, stdscr, selected: int) -> int:
        """Draw options configuration menu"""
        height, width = stdscr.getmaxyx()
        
        try:
            stdscr.clear()
            self.draw_header(stdscr)
            stdscr.attron(curses.color_pair(Color.INFO))
            stdscr.addstr(2, 2, "Configure Options:")
            stdscr.attroff(curses.color_pair(Color.INFO))
            
            options = [
                ("Auto-Change Update Tree (SSH)", 'auto_change'),
                ("Upgrade Firmware", 'upgrade_firmware'),
                ("Enable Cloud Backup", 'cloud_backup'),
                ("Generate Report", 'report'),
                ("Dry-Run Mode", 'dry_run'),
                ("Threads:", 'threads'),
                ("Timeout (seconds):", 'timeout'),
                ("Back to Main Menu", 'back'),
            ]
            
            y = 4
            for i, (label, key) in enumerate(options):
                if key in ['threads', 'timeout']:
                    value = self.selected_options[key]
                    if i == selected:
                        stdscr.attron(curses.color_pair(Color.SELECTED))
                        stdscr.addstr(y + i, 4, f"► {label:40} [{value}]")
                        stdscr.attroff(curses.color_pair(Color.SELECTED))
                    else:
                        stdscr.attron(curses.color_pair(Color.NORMAL))
                        stdscr.addstr(y + i, 4, f" {label:40} [{value}]")
                        stdscr.attroff(curses.color_pair(Color.NORMAL))
                else:
                    value = "✓ ON" if self.selected_options.get(key, False) else "✗ OFF"
                    color = curses.color_pair(Color.SUCCESS) if self.selected_options.get(key, False) else curses.color_pair(Color.WARNING)
                    
                    if i == selected:
                        stdscr.attron(curses.color_pair(Color.SELECTED))
                        stdscr.addstr(y + i, 4, f"► {label:40} [{value}]")
                        stdscr.attroff(curses.color_pair(Color.SELECTED))
                    else:
                        stdscr.attron(color)
                        stdscr.addstr(y + i, 4, f" {label:40} [{value}]")
                        stdscr.attroff(color)
            
            self.draw_footer(stdscr, "Toggle [Space] | Adjust [+/-] | Back [b]")
            stdscr.refresh()
        except Exception:
            pass
        
        return 8

    def build_command(self) -> str:
        """Build command to run"""
        cmd = [self.script_path, "-u", self.username, "-p", self.password]
        cmd.extend(["--update-tree", self.selected_tree.value])
        
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
        
        return " ".join(cmd)

    def run_script_direct(self, stdscr):
        """Run script directly"""
        if not self.password:
            try:
                height, width = stdscr.getmaxyx()
                stdscr.clear()
                self.draw_header(stdscr)
                stdscr.attron(curses.color_pair(Color.ERROR))
                stdscr.addstr(3, 2, "ERROR: Password not set!")
                stdscr.addstr(4, 2, "Please set credentials in menu 2 first.")
                stdscr.attroff(curses.color_pair(Color.ERROR))
                stdscr.attron(curses.color_pair(Color.INFO))
                stdscr.addstr(height - 2, 2, "Press any key to continue...")
                stdscr.attroff(curses.color_pair(Color.INFO))
                stdscr.refresh()
                stdscr.getch()
            except Exception:
                pass
            return
        
        cmd = self.build_command()
        
        # Exit ncurses
        curses.nocbreak()
        stdscr.keypad(False)
        curses.echo()
        curses.endwin()
        
        os.system('clear')
        print("\n" + "="*80)
        print("Running MikroTik Mass Updater")
        print("="*80)
        print(f"Command: {cmd}\n")
        
        try:
            result = subprocess.run(cmd, shell=True)
            print("\n" + "="*80)
            print(f"Process completed with exit code: {result.returncode}")
            print("="*80 + "\n")
        except Exception as e:
            print(f"Error: {e}\n")
        
        input("Press Enter to return to menu...")

    def run(self, stdscr):
        """Main menu loop"""
        curses.curs_set(0)
        stdscr.nodelay(False)
        stdscr.timeout(100)  # 100ms timeout for responsiveness
        self.init_colors(stdscr)
        
        selected_main = 0
        selected_tree = 0
        selected_options = 0
        
        # Start initial discovery
        self.start_network_discovery(stdscr)
        
        while True:
            try:
                if self.current_menu == 'main':
                    num_items = self.draw_main_menu(stdscr, selected_main)
                    key = stdscr.getch()
                    
                    if key == ord('q'):
                        break
                    elif key == curses.KEY_UP:
                        selected_main = (selected_main - 1) % num_items
                    elif key == curses.KEY_DOWN:
                        selected_main = (selected_main + 1) % num_items
                    elif key == ord('\n'):
                        if selected_main == 0:
                            # Show network status
                            self.current_menu = 'status'
                        elif selected_main == 1:
                            self.draw_creds_menu(stdscr)
                        elif selected_main == 2:
                            self.current_menu = 'tree'
                            selected_tree = 0
                        elif selected_main == 3:
                            self.current_menu = 'options'
                            selected_options = 0
                        elif selected_main == 4:
                            self.run_script_direct(stdscr)
                            curses.cbreak()
                            stdscr.keypad(True)
                            curses.noecho()
                            curses.curs_set(0)
                            stdscr.clear()
                            self.init_colors(stdscr)
                        elif selected_main == 5:
                            if self.log_file and os.path.exists(self.log_file):
                                curses.endwin()
                                os.system(f"less {self.log_file}")
                                curses.cbreak()
                                stdscr.keypad(True)
                                curses.noecho()
                                curses.curs_set(0)
                                stdscr.clear()
                                self.init_colors(stdscr)
                        elif selected_main == 6:
                            break

                elif self.current_menu == 'status':
                    self.draw_status_table(stdscr)
                    key = stdscr.getch()
                    
                    if key == ord('q') or key == ord('m'):
                        self.current_menu = 'main'
                    elif key == ord('r'):
                        self.start_network_discovery(stdscr)

                elif self.current_menu == 'tree':
                    num_items = self.draw_tree_menu(stdscr, selected_tree)
                    key = stdscr.getch()
                    
                    if key == ord('q') or key == ord('b'):
                        self.current_menu = 'main'
                    elif key == curses.KEY_UP:
                        selected_tree = (selected_tree - 1) % num_items
                    elif key == curses.KEY_DOWN:
                        selected_tree = (selected_tree + 1) % num_items
                    elif key == ord('\n'):
                        trees = [UpdateTree.STABLE, UpdateTree.DEVELOPMENT, UpdateTree.TESTING]
                        self.selected_tree = trees[selected_tree]
                        self.current_menu = 'main'

                elif self.current_menu == 'options':
                    num_items = self.draw_options_menu(stdscr, selected_options)
                    key = stdscr.getch()
                    
                    if key == ord('q') or key == ord('b'):
                        self.current_menu = 'main'
                    elif key == curses.KEY_UP:
                        selected_options = (selected_options - 1) % num_items
                    elif key == curses.KEY_DOWN:
                        selected_options = (selected_options + 1) % num_items
                    elif key == ord(' '):
                        options = ['auto_change', 'upgrade_firmware', 'cloud_backup', 'report', 'dry_run', None, None, None]
                        if selected_options < len(options) and options[selected_options]:
                            key_name = options[selected_options]
                            self.selected_options[key_name] = not self.selected_options[key_name]
                    elif key == ord('+') or key == ord('='):
                        if selected_options == 5:
                            self.selected_options['threads'] = min(20, self.selected_options['threads'] + 1)
                        elif selected_options == 6:
                            self.selected_options['timeout'] = min(30, self.selected_options['timeout'] + 1)
                    elif key == ord('-'):
                        if selected_options == 5:
                            self.selected_options['threads'] = max(1, self.selected_options['threads'] - 1)
                        elif selected_options == 6:
                            self.selected_options['timeout'] = max(1, self.selected_options['timeout'] - 1)

            except KeyboardInterrupt:
                break
            except Exception as e:
                pass

def main():
    """Entry point"""
    if not os.path.exists("./mikrotik_mass_updater_v5.3.0_REPORT.py"):
        print("Error: mikrotik_mass_updater_v5.3.0_REPORT.py not found!")
        print("Make sure the script is in the current directory.")
        sys.exit(1)
    
    menu = UpdateTreeMenu()
    
    try:
        curses.wrapper(menu.run)
    except KeyboardInterrupt:
        print("\nMenu terminated by user.")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
