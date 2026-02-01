"""SSH service for MikroTik operations"""

import logging
import subprocess
from typing import Tuple
from ..core.enums import UpdateTree
from ..core.constants import SSH_PORT

logger = logging.getLogger(__name__)


class SSHService:
    """Service for SSH operations on MikroTik routers"""

    @staticmethod
    def change_update_tree(
        ip: str,
        username: str,
        password: str,
        new_tree: UpdateTree,
        ssh_port: int = SSH_PORT,
        timeout: int = 10
    ) -> Tuple[bool, str]:
        """
        Change RouterOS update tree via SSH using CLI command.

        Args:
            ip: Router IP address
            username: SSH username
            password: SSH password
            new_tree: Target update tree
            ssh_port: SSH port (default 22)
            timeout: Connection timeout

        Returns:
            Tuple of (success, message)
        """
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
            # Fallback to sshpass if paramiko is not available
            return SSHService._change_tree_sshpass(
                ip, username, password, new_tree, ssh_port, timeout
            )
        except Exception as e:
            return (False, f"SSH connection failed: {type(e).__name__}: {e}")

    @staticmethod
    def _change_tree_sshpass(
        ip: str,
        username: str,
        password: str,
        new_tree: UpdateTree,
        ssh_port: int,
        timeout: int
    ) -> Tuple[bool, str]:
        """Fallback method using sshpass command"""
        try:
            command = f"/system package update set channel={new_tree.value}"
            sshpass_cmd = [
                'sshpass', '-p', password,
                'ssh',
                '-o', 'StrictHostKeyChecking=no',
                '-o', f'ConnectTimeout={timeout}',
                '-p', str(ssh_port),
                f'{username}@{ip}',
                command
            ]

            result = subprocess.run(
                sshpass_cmd,
                capture_output=True,
                timeout=timeout + 5,
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
            return (False, f"SSH error: {type(e).__name__}: {e}")

    @staticmethod
    def execute_command(
        ip: str,
        username: str,
        password: str,
        command: str,
        ssh_port: int = SSH_PORT,
        timeout: int = 10
    ) -> Tuple[bool, str, str]:
        """
        Execute arbitrary command via SSH.

        Returns:
            Tuple of (success, stdout, stderr)
        """
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

            stdin, stdout, stderr = ssh.exec_command(command)

            output = stdout.read().decode().strip()
            error = stderr.read().decode().strip()

            ssh.close()

            return (not bool(error), output, error)

        except Exception as e:
            return (False, "", str(e))
