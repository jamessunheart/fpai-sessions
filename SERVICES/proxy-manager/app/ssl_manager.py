"""SSL certificate management via certbot."""
import subprocess
import logging
from typing import Tuple, Optional
from pathlib import Path

from app.config import settings

logger = logging.getLogger(__name__)


class SSLManager:
    """Manages SSL certificates via certbot."""

    def __init__(self):
        self.certbot_bin = settings.certbot_bin
        self.default_email = settings.default_ssl_email
        self.last_operation_status: str = "unknown"

    def issue_certificate(
        self, domain: str, email: Optional[str] = None, force_renew: bool = False
    ) -> Tuple[bool, str, Optional[dict]]:
        """
        Issue or renew SSL certificate for a domain.

        Args:
            domain: Domain name for the certificate
            email: Email for Let's Encrypt notifications
            force_renew: Force renewal even if cert is valid

        Returns:
            Tuple of (success, message, certificate_info)
        """
        try:
            email_to_use = email or self.default_email

            # Build certbot command
            cmd = [
                self.certbot_bin,
                "certonly",
                "--nginx",
                "-d",
                domain,
                "--email",
                email_to_use,
                "--agree-tos",
                "--non-interactive",
            ]

            if force_renew:
                cmd.append("--force-renewal")

            logger.info(f"Running certbot for domain: {domain}")

            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=120  # 2 minute timeout
            )

            output = result.stderr + result.stdout
            success = result.returncode == 0

            if success:
                logger.info(f"SSL certificate obtained successfully for {domain}")
                self.last_operation_status = "success"

                # Get certificate info
                cert_info = self._get_certificate_info(domain)
                return True, "Certificate obtained successfully", cert_info

            else:
                logger.error(f"Certbot failed for {domain}: {output}")
                self.last_operation_status = "failed"
                return False, f"Certbot failed: {output}", None

        except subprocess.TimeoutExpired:
            error_msg = "Certbot operation timed out"
            logger.error(error_msg)
            self.last_operation_status = "timeout"
            return False, error_msg, None

        except Exception as e:
            error_msg = f"Failed to issue certificate: {str(e)}"
            logger.error(error_msg)
            self.last_operation_status = "error"
            return False, error_msg, None

    def _get_certificate_info(self, domain: str) -> Optional[dict]:
        """
        Get information about an existing certificate.

        Args:
            domain: Domain name

        Returns:
            Dictionary with certificate info or None
        """
        try:
            cert_path = Path(f"/etc/letsencrypt/live/{domain}/fullchain.pem")

            if not cert_path.exists():
                return None

            # Get certificate expiry using openssl
            result = subprocess.run(
                [
                    "openssl",
                    "x509",
                    "-in",
                    str(cert_path),
                    "-noout",
                    "-enddate",
                    "-issuer",
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.returncode == 0:
                output = result.stdout.strip()
                lines = output.split("\n")

                info = {"domain": domain, "path": str(cert_path)}

                for line in lines:
                    if line.startswith("notAfter="):
                        info["expiry"] = line.replace("notAfter=", "")
                    elif line.startswith("issuer="):
                        info["issuer"] = line.replace("issuer=", "")

                return info

            return None

        except Exception as e:
            logger.error(f"Failed to get certificate info: {str(e)}")
            return None

    def check_certificate_exists(self, domain: str) -> bool:
        """Check if a certificate exists for a domain."""
        cert_path = Path(f"/etc/letsencrypt/live/{domain}/fullchain.pem")
        return cert_path.exists()

    def is_certbot_available(self) -> bool:
        """Check if certbot is available."""
        return Path(self.certbot_bin).exists()

    def renew_all_certificates(self) -> Tuple[bool, str]:
        """
        Renew all certificates that are due for renewal.

        Returns:
            Tuple of (success, message)
        """
        try:
            cmd = [self.certbot_bin, "renew", "--non-interactive"]

            logger.info("Running certbot renew")

            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=300  # 5 minute timeout
            )

            output = result.stderr + result.stdout
            success = result.returncode == 0

            if success:
                logger.info("Certificate renewal completed")
                self.last_operation_status = "success"
                return True, "Renewal completed successfully"
            else:
                logger.error(f"Certificate renewal failed: {output}")
                self.last_operation_status = "failed"
                return False, f"Renewal failed: {output}"

        except subprocess.TimeoutExpired:
            error_msg = "Certificate renewal timed out"
            logger.error(error_msg)
            self.last_operation_status = "timeout"
            return False, error_msg

        except Exception as e:
            error_msg = f"Failed to renew certificates: {str(e)}"
            logger.error(error_msg)
            self.last_operation_status = "error"
            return False, error_msg
