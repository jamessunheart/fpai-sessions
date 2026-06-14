import subprocess
from app.core.config import settings

class SSLManager:
    def obtain_cert(self, domain: str, email: str = None, force_renew: bool = False) -> bool:
        email = email or settings.DEFAULT_SSL_EMAIL
        cmd = [
            settings.CERTBOT_BIN,
            "--nginx",
            "-d", domain,
            "--non-interactive",
            "--agree-tos",
            "-m", email
        ]
        
        if force_renew:
            cmd.append("--force-renewal")
            
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            return True
        except subprocess.CalledProcessError:
            return False






