"""Tests for NGINX manager."""
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from app.nginx_manager import NGINXManager
from app.models import ProxyConfig


@pytest.fixture
def nginx_manager(tmp_path):
    """Create an NGINX manager with temporary directories."""
    with patch("app.nginx_manager.settings") as mock_settings:
        mock_settings.nginx_sites_available = str(tmp_path / "sites-available")
        mock_settings.nginx_sites_enabled = str(tmp_path / "sites-enabled")
        mock_settings.nginx_bin = "/usr/sbin/nginx"

        manager = NGINXManager()
        manager.sites_available.mkdir(parents=True, exist_ok=True)
        manager.sites_enabled.mkdir(parents=True, exist_ok=True)

        yield manager


@pytest.fixture
def sample_config():
    """Create a sample proxy configuration."""
    return ProxyConfig(
        droplet_name="test-service",
        domain="test.example.com",
        upstream_host="localhost",
        upstream_port=8001,
        ssl_enabled=False,
    )


def test_generate_config_http_only(nginx_manager, sample_config):
    """Test NGINX config generation for HTTP-only."""
    config_content = nginx_manager.generate_config(sample_config)

    assert "server {" in config_content
    assert "listen 80;" in config_content
    assert "server_name test.example.com;" in config_content
    assert "proxy_pass http://localhost:8001;" in config_content
    assert "ssl" not in config_content.lower()


def test_generate_config_with_ssl(nginx_manager, sample_config):
    """Test NGINX config generation with SSL."""
    sample_config.ssl_enabled = True
    config_content = nginx_manager.generate_config(sample_config)

    assert "listen 443 ssl" in config_content
    assert "ssl_certificate" in config_content
    assert "return 301 https://" in config_content  # HTTP redirect


def test_write_config(nginx_manager, sample_config):
    """Test writing NGINX configuration to file."""
    success, error = nginx_manager.write_config(sample_config)

    assert success is True
    assert error is None

    # Check file exists
    config_path = nginx_manager.get_config_path("test-service")
    assert config_path.exists()

    # Check symlink exists
    enabled_path = nginx_manager.get_enabled_path("test-service")
    assert enabled_path.is_symlink()


def test_delete_config(nginx_manager, sample_config):
    """Test deleting NGINX configuration."""
    # First create a config
    nginx_manager.write_config(sample_config)

    # Then delete it
    success, error = nginx_manager.delete_config("test-service")

    assert success is True
    assert error is None

    # Check files are gone
    config_path = nginx_manager.get_config_path("test-service")
    enabled_path = nginx_manager.get_enabled_path("test-service")

    assert not config_path.exists()
    assert not enabled_path.exists()


def test_list_configs(nginx_manager):
    """Test listing proxy configurations."""
    # Create multiple configs
    for i in range(3):
        config = ProxyConfig(
            droplet_name=f"service-{i}",
            domain=f"service{i}.example.com",
            upstream_host="localhost",
            upstream_port=8000 + i,
            ssl_enabled=False,
        )
        nginx_manager.write_config(config)

    configs = nginx_manager.list_configs()
    assert len(configs) == 3
    assert "service-0" in configs
    assert "service-1" in configs
    assert "service-2" in configs


@patch("subprocess.run")
def test_test_config_success(mock_run, nginx_manager):
    """Test NGINX config test with success."""
    mock_run.return_value = Mock(returncode=0, stderr="", stdout="test successful")

    success, output = nginx_manager.test_config()

    assert success is True
    assert "test successful" in output
    mock_run.assert_called_once()


@patch("subprocess.run")
def test_test_config_failure(mock_run, nginx_manager):
    """Test NGINX config test with failure."""
    mock_run.return_value = Mock(
        returncode=1, stderr="config test failed", stdout=""
    )

    success, output = nginx_manager.test_config()

    assert success is False
    assert "config test failed" in output


@patch("subprocess.run")
def test_reload_success(mock_run, nginx_manager):
    """Test NGINX reload with success."""
    mock_run.return_value = Mock(returncode=0, stderr="", stdout="reload successful")

    success, output = nginx_manager.reload()

    assert success is True
    assert nginx_manager.last_reload_status is True
    assert nginx_manager.last_reload_timestamp is not None


@patch("subprocess.run")
def test_reload_failure(mock_run, nginx_manager):
    """Test NGINX reload with failure."""
    mock_run.return_value = Mock(returncode=1, stderr="reload failed", stdout="")

    success, output = nginx_manager.reload()

    assert success is False
    assert nginx_manager.last_reload_status is False
