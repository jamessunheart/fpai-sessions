#!/usr/bin/env python3
"""
Auto-Integration System
Automatically integrates credentials once received from VAs
Updates configurations and deploys services
"""

import json
import os
from pathlib import Path
from typing import Dict, List
from datetime import datetime
from credential_vault import CredentialVault
import subprocess


class AutoIntegrator:
    """Automatically integrates new credentials into system"""

    def __init__(self):
        self.vault = CredentialVault()
        self.base_dir = Path("/root/delegation-system")
        self.integration_log = self.base_dir / "integration_log.json"

        if not self.integration_log.exists():
            self.integration_log.write_text(json.dumps([], indent=2))

    def integrate_stripe(self, credentials: Dict) -> Dict:
        """Integrate Stripe credentials into system"""

        print("🔄 Integrating Stripe credentials...")

        # Update landing page with payment link
        landing_page = Path("/root/delegation-system/landing-page/index.html")

        if landing_page.exists():
            content = landing_page.read_text()

            # Replace placeholder with actual payment link
            if credentials.get('payment_link'):
                content = content.replace(
                    'https://buy.stripe.com/YOUR_PAYMENT_LINK',
                    credentials['payment_link']
                )

            landing_page.write_text(content)
            print("  ✅ Landing page updated with Stripe payment link")

        # Update environment variables
        env_file = self.base_dir / ".env"
        env_updates = [
            f"STRIPE_SECRET_KEY={credentials.get('secret_key', '')}",
            f"STRIPE_PUBLISHABLE_KEY={credentials.get('publishable_key', '')}",
        ]

        if env_file.exists():
            env_content = env_file.read_text()
        else:
            env_content = ""

        for update in env_updates:
            key = update.split('=')[0]
            # Remove old value if exists
            lines = [line for line in env_content.split('\n') if not line.startswith(f"{key}=")]
            lines.append(update)
            env_content = '\n'.join(lines)

        env_file.write_text(env_content)
        print("  ✅ Environment variables updated")

        return {
            "service": "stripe",
            "status": "integrated",
            "actions": ["updated_landing_page", "updated_env_vars"]
        }

    def integrate_calendly(self, credentials: Dict) -> Dict:
        """Integrate Calendly credentials into system"""

        print("🔄 Integrating Calendly credentials...")

        # Update landing page with booking link
        landing_page = Path("/root/delegation-system/landing-page/index.html")

        if landing_page.exists():
            content = landing_page.read_text()

            # Replace placeholder with actual booking link
            if credentials.get('booking_link'):
                content = content.replace(
                    'YOUR_CALENDLY_URL',
                    credentials['booking_link']
                )

            landing_page.write_text(content)
            print("  ✅ Landing page updated with Calendly booking link")

        return {
            "service": "calendly",
            "status": "integrated",
            "actions": ["updated_landing_page"]
        }

    def integrate_facebook_oauth(self, credentials: Dict) -> Dict:
        """Integrate Facebook Ads credentials into system"""

        print("🔄 Integrating Facebook Ads credentials...")

        # Update Facebook ad creation script
        fb_script = self.base_dir / "create_facebook_ad.py"

        if fb_script.exists():
            content = fb_script.read_text()

            # Update credentials in script
            replacements = {
                'YOUR_ACCESS_TOKEN': credentials.get('access_token', ''),
                'YOUR_AD_ACCOUNT_ID': credentials.get('ad_account_id', ''),
                'YOUR_PAGE_ID': credentials.get('page_id', '')
            }

            for placeholder, value in replacements.items():
                if value:
                    content = content.replace(placeholder, value)

            fb_script.write_text(content)
            print("  ✅ Facebook ad script updated")

        # Update environment variables
        env_file = self.base_dir / ".env"
        env_updates = [
            f"FACEBOOK_ACCESS_TOKEN={credentials.get('access_token', '')}",
            f"FACEBOOK_AD_ACCOUNT_ID={credentials.get('ad_account_id', '')}",
            f"FACEBOOK_PAGE_ID={credentials.get('page_id', '')}",
        ]

        if env_file.exists():
            env_content = env_file.read_text()
        else:
            env_content = ""

        for update in env_updates:
            key = update.split('=')[0]
            lines = [line for line in env_content.split('\n') if not line.startswith(f"{key}=")]
            lines.append(update)
            env_content = '\n'.join(lines)

        env_file.write_text(env_content)
        print("  ✅ Environment variables updated")

        return {
            "service": "facebook_ads",
            "status": "integrated",
            "actions": ["updated_fb_script", "updated_env_vars"]
        }

    def integrate_google_oauth(self, credentials: Dict) -> Dict:
        """Integrate Google Ads credentials into system"""

        print("🔄 Integrating Google Ads credentials...")

        # Update Google ad creation script
        google_script = self.base_dir / "create_google_ad.py"

        if google_script.exists():
            content = google_script.read_text()

            # Update credentials
            replacements = {
                'YOUR_DEVELOPER_TOKEN': credentials.get('developer_token', ''),
                'YOUR_CLIENT_ID': credentials.get('client_id', ''),
                'YOUR_CLIENT_SECRET': credentials.get('client_secret', ''),
                'YOUR_REFRESH_TOKEN': credentials.get('refresh_token', ''),
                'YOUR_CUSTOMER_ID': credentials.get('customer_id', '')
            }

            for placeholder, value in replacements.items():
                if value:
                    content = content.replace(placeholder, value)

            google_script.write_text(content)
            print("  ✅ Google ad script updated")

        # Update environment variables
        env_file = self.base_dir / ".env"
        env_updates = [
            f"GOOGLE_ADS_DEVELOPER_TOKEN={credentials.get('developer_token', '')}",
            f"GOOGLE_ADS_CLIENT_ID={credentials.get('client_id', '')}",
            f"GOOGLE_ADS_CLIENT_SECRET={credentials.get('client_secret', '')}",
            f"GOOGLE_ADS_REFRESH_TOKEN={credentials.get('refresh_token', '')}",
            f"GOOGLE_ADS_CUSTOMER_ID={credentials.get('customer_id', '')}",
        ]

        if env_file.exists():
            env_content = env_file.read_text()
        else:
            env_content = ""

        for update in env_updates:
            key = update.split('=')[0]
            lines = [line for line in env_content.split('\n') if not line.startswith(f"{key}=")]
            lines.append(update)
            env_content = '\n'.join(lines)

        env_file.write_text(env_content)
        print("  ✅ Environment variables updated")

        return {
            "service": "google_ads",
            "status": "integrated",
            "actions": ["updated_google_script", "updated_env_vars"]
        }

    def deploy_landing_page(self) -> Dict:
        """Deploy landing page to Vercel once credentials are integrated"""

        print("🚀 Deploying landing page to Vercel...")

        landing_dir = self.base_dir / "landing-page"

        try:
            # Check if vercel is installed
            subprocess.run(["which", "vercel"], check=True, capture_output=True)

            # Deploy to production
            result = subprocess.run(
                ["vercel", "--prod", "--yes"],
                cwd=landing_dir,
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                # Extract URL from output
                url = None
                for line in result.stdout.split('\n'):
                    if 'https://' in line:
                        url = line.strip()
                        break

                print(f"  ✅ Landing page deployed: {url}")

                return {
                    "service": "vercel",
                    "status": "deployed",
                    "url": url
                }
            else:
                print(f"  ⚠️ Deployment failed: {result.stderr}")
                return {
                    "service": "vercel",
                    "status": "failed",
                    "error": result.stderr
                }

        except subprocess.CalledProcessError:
            print("  ⚠️ Vercel CLI not found. Install with: npm install -g vercel")
            return {
                "service": "vercel",
                "status": "not_available",
                "error": "Vercel CLI not installed"
            }

    def auto_integrate_service(self, service_name: str, credentials: Dict) -> Dict:
        """Automatically integrate a service based on credentials received"""

        integration_map = {
            "stripe": self.integrate_stripe,
            "calendly": self.integrate_calendly,
            "facebook_oauth": self.integrate_facebook_oauth,
            "google_oauth": self.integrate_google_oauth
        }

        if service_name not in integration_map:
            print(f"⚠️ No auto-integration available for {service_name}")
            return {
                "service": service_name,
                "status": "manual_integration_required"
            }

        # Execute integration
        result = integration_map[service_name](credentials)

        # Log integration
        integration_record = {
            "service": service_name,
            "integrated_at": datetime.now().isoformat(),
            "result": result
        }

        integrations = json.loads(self.integration_log.read_text())
        integrations.append(integration_record)
        self.integration_log.write_text(json.dumps(integrations, indent=2))

        print(f"✅ {service_name} integrated successfully")

        return result

    def check_readiness_and_deploy(self):
        """Check if all required credentials are available and deploy"""

        print("\n🔍 Checking deployment readiness...")

        # Check which credentials are available
        required_services = ["stripe", "calendly"]
        optional_services = ["facebook_oauth", "google_oauth"]

        available = {}
        for service in required_services + optional_services:
            try:
                creds = self.vault.get_credential("tier2_monitored", service)
                available[service] = bool(creds)
            except:
                available[service] = False

        print("\nCredentials status:")
        for service, status in available.items():
            icon = "✅" if status else "❌"
            req = "(REQUIRED)" if service in required_services else "(optional)"
            print(f"  {icon} {service} {req}")

        # Check if ready to deploy
        ready = all(available[s] for s in required_services)

        if ready:
            print("\n✅ All required credentials available!")
            print("🚀 Deploying landing page...")

            deployment = self.deploy_landing_page()

            if deployment['status'] == 'deployed':
                print(f"\n🎉 LANDING PAGE LIVE: {deployment['url']}")
                print("\n📊 Next steps:")
                print("  1. Test payment flow (click Stripe button)")
                print("  2. Test booking flow (click Calendly button)")
                print("  3. Launch $100 Facebook ad campaign")
                print("  4. Monitor conversions!")

                return deployment
        else:
            missing = [s for s in required_services if not available[s]]
            print(f"\n⚠️ Missing required credentials: {', '.join(missing)}")
            print("Waiting for VAs to complete setup tasks...")

        return {"status": "waiting_for_credentials", "missing": missing if not ready else []}


def main():
    """Demo auto-integration"""

    integrator = AutoIntegrator()

    print("\n🤖 AUTO-INTEGRATION SYSTEM")
    print("=" * 70)
    print()
    print("Automatically integrates credentials once VAs submit them")
    print()

    # Check readiness and attempt deploy
    integrator.check_readiness_and_deploy()

    print()
    print("=" * 70)
    print()
    print("System will automatically:")
    print("  1. Monitor credential vault for new credentials")
    print("  2. Integrate credentials into services")
    print("  3. Deploy landing page when ready")
    print("  4. Notify when live")
    print()


if __name__ == "__main__":
    main()
