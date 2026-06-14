# 🛡️ Admin Access Setup

To protect the `/dashboards` route, you need to create a password file on the server.

Run this command on your server:

```bash
# Install utils if needed
apt-get install apache2-utils -y

# Create user 'admin' (it will prompt for password)
htpasswd -c /etc/nginx/.htpasswd admin
```

Enter a strong password when prompted. This will be the login for `fullpotential.ai/dashboards`.

