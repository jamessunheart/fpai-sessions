import os
import subprocess
from jinja2 import Template
from app.core.config import settings
from app.models.schemas import ProxyConfig

NGINX_TEMPLATE = """
server {
    listen 80;
    server_name {{ domain }};

    {% if ssl_enabled %}
    # Redirect HTTP to HTTPS
    return 301 https://$host$request_uri;
    {% else %}
    location / {
        proxy_pass http://{{ upstream_host }}:{{ upstream_port }};
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    {% endif %}
}

{% if ssl_enabled %}
server {
    listen 443 ssl;
    server_name {{ domain }};

    ssl_certificate /etc/letsencrypt/live/{{ domain }}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/{{ domain }}/privkey.pem;

    location / {
        proxy_pass http://{{ upstream_host }}:{{ upstream_port }};
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
{% endif %}
"""

class NginxManager:
    def __init__(self):
        self.available_path = settings.NGINX_SITES_AVAILABLE
        self.enabled_path = settings.NGINX_SITES_ENABLED
        os.makedirs(self.available_path, exist_ok=True)
        os.makedirs(self.enabled_path, exist_ok=True)

    def create_config(self, config: ProxyConfig) -> str:
        template = Template(NGINX_TEMPLATE)
        nginx_conf = template.render(
            domain=config.domain,
            upstream_host=config.upstream_host,
            upstream_port=config.upstream_port,
            ssl_enabled=config.enable_ssl
        )
        
        file_path = os.path.join(self.available_path, f"{config.droplet_name}.conf")
        with open(file_path, "w") as f:
            f.write(nginx_conf)
            
        return file_path

    def enable_site(self, droplet_name: str):
        source = os.path.join(self.available_path, f"{droplet_name}.conf")
        link = os.path.join(self.enabled_path, f"{droplet_name}.conf")
        
        if os.path.exists(link):
            os.remove(link)
            
        os.symlink(source, link)

    def delete_site(self, droplet_name: str):
        available = os.path.join(self.available_path, f"{droplet_name}.conf")
        enabled = os.path.join(self.enabled_path, f"{droplet_name}.conf")
        
        if os.path.exists(enabled):
            os.remove(enabled)
        if os.path.exists(available):
            os.remove(available)

    def test_config(self) -> bool:
        try:
            subprocess.run([settings.NGINX_BIN, "-t"], check=True, capture_output=True)
            return True
        except subprocess.CalledProcessError:
            return False

    def reload(self) -> bool:
        if not self.test_config():
            return False
        try:
            subprocess.run([settings.NGINX_BIN, "-s", "reload"], check=True, capture_output=True)
            return True
        except subprocess.CalledProcessError:
            return False






