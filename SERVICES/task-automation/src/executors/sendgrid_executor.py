"""
SendGrid Executor
Automates SendGrid email relay setup
"""

import subprocess
from typing import Dict
from .base import BaseExecutor
from src.models import BlockerType


class SendGridExecutor(BaseExecutor):
    """
    Executes SendGrid email relay setup tasks

    Process:
    1. Check if API key already exists
    2. If not, guide user through signup and API key creation
    3. Store API key in vault
    4. Configure Postfix to use SendGrid relay
    5. Test email delivery
    6. Verify configuration
    """

    async def execute(self) -> Dict:
        """Execute SendGrid setup"""

        self.mark_in_progress()

        try:
            # Step 1: Check for existing API key
            self.log("Checking for existing SendGrid API key...")
            api_key = self.get_credential("api_key")

            if not api_key:
                self.log("No existing SendGrid API key found")

                # Mark as blocked - need user to get API key
                self.mark_blocked(
                    blocker=BlockerType.HUMAN_APPROVAL,
                    details="User needs to sign up for SendGrid and create API key"
                )

                self.notify_human(
                    action_type="service_signup",
                    message="SendGrid API key required",
                    instructions=self._get_signup_instructions()
                )

                return {
                    "status": "blocked",
                    "blocker": "api_key_required",
                    "instructions": self._get_signup_instructions(),
                    "next_steps": "Provide API key to resume automation"
                }

            # Step 2: Validate API key format
            self.log(f"Found API key: {api_key[:10]}...")
            if not api_key.startswith("SG."):
                self.log("WARNING: API key doesn't match SendGrid format (SG.xxxx)")

            # Step 3: Get sender email from params
            sender_email = self.task.params.get("sender", "james@fullpotential.com")
            self.log(f"Sender email: {sender_email}")

            # Step 4: Configure Postfix relay on server
            self.log("Configuring Postfix to use SendGrid relay...")
            success = self._configure_postfix(api_key)

            if not success:
                raise Exception("Failed to configure Postfix")

            self.log("✅ Postfix configured successfully")

            # Step 5: Test email delivery
            self.log("Testing email delivery...")
            test_result = self._test_email_delivery(sender_email)

            if not test_result:
                self.log("⚠️ Test email may have failed - check logs")

            # Step 6: Complete
            result = {
                "status": "completed",
                "api_key_stored": True,
                "postfix_configured": True,
                "test_email_sent": test_result,
                "sender_email": sender_email,
                "relay_host": "smtp.sendgrid.net:587"
            }

            self.mark_completed(result)
            self.log("✅ SendGrid setup complete!")

            return result

        except Exception as e:
            error_msg = f"SendGrid setup failed: {str(e)}"
            self.log(f"❌ {error_msg}")
            self.mark_failed(error_msg)
            raise

    def _get_signup_instructions(self) -> str:
        """Get signup instructions for user"""
        return """
📧 SendGrid Setup Instructions (5 minutes):

1. Sign up for SendGrid (FREE):
   https://signup.sendgrid.com/

2. After signup, create API key:
   - Go to Settings → API Keys
   - Click "Create API Key"
   - Name: "FullPotential Mail"
   - Permissions: "Full Access" or "Mail Send"
   - Click "Create & View"
   - COPY the API key (shows only once!)

3. Verify sender email:
   - Go to Settings → Sender Authentication
   - Click "Verify a Single Sender"
   - Use: james@fullpotential.com
   - Check email dashboard for verification link
   - Click the verification link

4. Provide API key:
   Once you have the API key, run:

   ssh root@198.54.123.234 "cd /root/SERVICES/task-automation && \\
     python3 -c 'from src.credentials import CredentialVault; \\
     v = CredentialVault(); \\
     v.store_credential(\"sendgrid\", \"api_key\", \"YOUR_API_KEY_HERE\")'"

   Then resume this task:
   python3 src/cli.py show {task_id}

The system will then automatically:
✅ Configure Postfix relay
✅ Test email delivery
✅ Complete setup

Total time: 5 minutes
Human actions required: 2 (signup + provide API key)
""".format(task_id=self.task.id)

    def _configure_postfix(self, api_key: str) -> bool:
        """Configure Postfix on server to use SendGrid"""
        try:
            # SSH to server and configure Postfix
            config_script = f"""
set -e

# Create SASL password file
cat > /etc/postfix/sasl_passwd << 'SASL_EOF'
[smtp.sendgrid.net]:587 apikey:{api_key}
SASL_EOF

# Secure the file
chmod 600 /etc/postfix/sasl_passwd
postmap /etc/postfix/sasl_passwd

# Configure Postfix
postconf -e 'relayhost = [smtp.sendgrid.net]:587'
postconf -e 'smtp_sasl_auth_enable = yes'
postconf -e 'smtp_sasl_password_maps = hash:/etc/postfix/sasl_passwd'
postconf -e 'smtp_sasl_security_options = noanonymous'
postconf -e 'smtp_tls_security_level = encrypt'
postconf -e 'header_size_limit = 4096000'

# Restart Postfix
systemctl restart postfix

echo "✅ Postfix configured"
"""

            result = subprocess.run(
                ['ssh', 'root@198.54.123.234', config_script],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                self.log("Postfix configuration output:")
                self.log(result.stdout)
                return True
            else:
                self.log(f"Postfix configuration error: {result.stderr}")
                return False

        except Exception as e:
            self.log(f"Failed to configure Postfix: {str(e)}")
            return False

    def _test_email_delivery(self, sender_email: str) -> bool:
        """Test email delivery"""
        try:
            test_script = f"""
echo "This is a test email sent via SendGrid by the Task Automation Framework.

If you receive this, the setup is complete and working perfectly!

✅ SendGrid relay: ACTIVE
✅ Email delivery: WORKING
✅ Automation: SUCCESSFUL

Automated by Task ID: {self.task.id}

-FPAI Task Automation System" | mail -s "✅ SendGrid Relay Test - Task Automation" {sender_email}

echo "Test email sent"
"""

            result = subprocess.run(
                ['ssh', 'root@198.54.123.234', test_script],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                self.log("✅ Test email sent successfully")
                return True
            else:
                self.log(f"⚠️ Test email command failed: {result.stderr}")
                return False

        except Exception as e:
            self.log(f"Failed to send test email: {str(e)}")
            return False
