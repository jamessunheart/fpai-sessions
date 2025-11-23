import subprocess
import os
from pathlib import Path
from jinja2 import Template
from app.config import settings
import logging

logger = logging.getLogger(__name__)

NGINX_TEMPLATE = """
server {
    listen 80;
    server_name {{ domain }};

    location / {
        proxy_pass {{ upstream_url }};
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
"""

class NginxController:
    @staticmethod
    def test_config() -> bool:
        if settings.TEST_MODE:
            return True
        try:
            subprocess.check_call(["nginx", "-t"])
            return True
        except subprocess.CalledProcessError:
            return False

    @staticmethod
    def reload() -> bool:
        if settings.TEST_MODE:
            logger.info("TEST MODE: NGINX reload simulated")
            return True
        try:
            subprocess.check_call(["nginx", "-s", "reload"])
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to reload NGINX: {e}")
            return False

    @staticmethod
    def write_config(domain: str, upstream_url: str) -> str:
        config_content = Template(NGINX_TEMPLATE).render(
            domain=domain,
            upstream_url=upstream_url
        )
        filename = f"{domain}.conf"
        path = Path(settings.NGINX_CONFIG_PATH) / filename
        
        # Ensure directory exists
        Path(settings.NGINX_CONFIG_PATH).mkdir(parents=True, exist_ok=True)

        if settings.TEST_MODE:
            logger.info(f"TEST MODE: Writing to {path}")
            
        try:
            with open(path, "w") as f:
                f.write(config_content)
            return str(path)
        except Exception as e:
            logger.error(f"Failed to write config: {e}")
            raise

    @staticmethod
    def delete_config(domain: str) -> bool:
        filename = f"{domain}.conf"
        path = Path(settings.NGINX_CONFIG_PATH) / filename
        if path.exists():
            os.remove(path)
            return True
        return False

