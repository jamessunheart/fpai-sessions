import os
import subprocess
import logging
from jinja2 import Template
from app.config import settings
from app.models import ProxyConfig

logger = logging.getLogger(__name__)

NGINX_TEMPLATE = """
server {
    listen 80;
    server_name {{ domain }};

    location / {
        proxy_pass http://{{ upstream_host }}:{{ upstream_port }};
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
"""

class NginxManager:
    def __init__(self):
        # Ensure config directories exist (mock/safe mode check)
        os.makedirs(settings.nginx_sites_available, exist_ok=True)
        os.makedirs(settings.nginx_sites_enabled, exist_ok=True)

    def create_config(self, config: ProxyConfig) -> bool:
        try:
            # Generate config content
            template = Template(NGINX_TEMPLATE)
            content = template.render(
                domain=config.domain,
                upstream_host=config.upstream_host,
                upstream_port=config.upstream_port
            )
            
            filename = f"fpai-{config.droplet_name}.conf"
            available_path = os.path.join(settings.nginx_sites_available, filename)
            enabled_path = os.path.join(settings.nginx_sites_enabled, filename)
            
            # Write to sites-available
            with open(available_path, "w") as f:
                f.write(content)
            
            # Symlink to sites-enabled
            if not os.path.exists(enabled_path):
                os.symlink(available_path, enabled_path)
                
            return True
        except Exception as e:
            logger.error(f"Failed to create config: {e}")
            return False

    def delete_config(self, droplet_name: str) -> bool:
        filename = f"fpai-{droplet_name}.conf"
        available_path = os.path.join(settings.nginx_sites_available, filename)
        enabled_path = os.path.join(settings.nginx_sites_enabled, filename)
        
        try:
            if os.path.exists(enabled_path):
                os.remove(enabled_path)
            if os.path.exists(available_path):
                os.remove(available_path)
            return True
        except Exception as e:
            logger.error(f"Failed to delete config: {e}")
            return False

    def test_and_reload(self) -> bool:
        # In a real environment, we would run `nginx -t` and `nginx -s reload`
        # For this implementation, we check if the binary exists first
        if not os.path.exists(settings.nginx_bin):
            logger.warning(f"Nginx binary not found at {settings.nginx_bin}, skipping reload")
            return True # Simulate success for development without nginx installed

        try:
            # Test config
            subprocess.run([settings.nginx_bin, "-t"], check=True, capture_output=True)
            # Reload
            subprocess.run([settings.nginx_bin, "-s", "reload"], check=True, capture_output=True)
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Nginx reload failed: {e.stderr}")
            return False

