"""SSH connection and file transfer management"""

import paramiko
from pathlib import Path
from typing import Optional, Tuple
import os

from .config import settings


class SSHManager:
    """Manages SSH connections to deployment server"""

    def __init__(self):
        """Initialize SSH manager"""
        self.client: Optional[paramiko.SSHClient] = None

    def connect(self) -> bool:
        """
        Connect to server via SSH.

        Returns True if successful, False otherwise.
        """
        try:
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            # Expand ~ in SSH key path
            key_path = settings.ssh_key_path_expanded

            if not key_path.exists():
                print(f"❌ SSH key not found: {key_path}")
                return False

            # Load private key
            private_key = paramiko.Ed25519Key.from_private_key_file(str(key_path))

            # Connect
            self.client.connect(
                hostname=settings.server_host,
                username=settings.server_user,
                pkey=private_key,
                timeout=10
            )

            return True

        except Exception as e:
            print(f"❌ SSH connection failed: {e}")
            return False

    def disconnect(self):
        """Close SSH connection"""
        if self.client:
            self.client.close()
            self.client = None

    def execute_command(self, command: str) -> Tuple[bool, str, str]:
        """
        Execute command on remote server.

        Returns (success, stdout, stderr)
        """
        if not self.client:
            return False, "", "Not connected"

        try:
            stdin, stdout, stderr = self.client.exec_command(command)
            stdout_text = stdout.read().decode('utf-8')
            stderr_text = stderr.read().decode('utf-8')
            exit_code = stdout.channel.recv_exit_status()

            return exit_code == 0, stdout_text, stderr_text

        except Exception as e:
            return False, "", str(e)

    def transfer_directory(self, local_path: str, remote_path: str) -> bool:
        """
        Transfer directory to remote server using SFTP.

        Returns True if successful.
        """
        if not self.client:
            print("❌ Not connected")
            return False

        try:
            sftp = self.client.open_sftp()

            # Create remote directory
            try:
                sftp.mkdir(remote_path)
            except:
                pass  # Directory might already exist

            # Transfer files recursively
            local_dir = Path(local_path)

            def transfer_recursive(local_base: Path, remote_base: str):
                for item in local_base.iterdir():
                    remote_item = f"{remote_base}/{item.name}"

                    if item.is_file():
                        print(f"   Transferring: {item.name}")
                        sftp.put(str(item), remote_item)
                    elif item.is_dir():
                        # Skip common directories
                        if item.name in ['.git', '__pycache__', '.venv', 'venv', 'node_modules']:
                            continue

                        try:
                            sftp.mkdir(remote_item)
                        except:
                            pass

                        transfer_recursive(item, remote_item)

            transfer_recursive(local_dir, remote_path)

            sftp.close()
            return True

        except Exception as e:
            print(f"❌ Transfer failed: {e}")
            return False

    def file_exists(self, remote_path: str) -> bool:
        """Check if file/directory exists on remote server"""
        success, stdout, _ = self.execute_command(f"test -e {remote_path} && echo 'exists'")
        return 'exists' in stdout

    def ensure_directory(self, remote_path: str) -> bool:
        """Ensure directory exists on remote server"""
        success, _, _ = self.execute_command(f"mkdir -p {remote_path}")
        return success

    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()
