import sqlite3
import os
import base64
import datetime
import sys
import json

# ------------------------------------------------------------------------------
# CONFIG & KEYS
# ------------------------------------------------------------------------------
MASTER_ENCRYPTION_KEY = "f8d9fb643b3f182f26cb268df3228e2d8548197d319c2bfef362f3657281739b"
JWT_SECRET_KEY = "bcce98e062783333f928a6f9b18ed09eb4205659d6af4943379b600333aa598b"
JWT_ALGORITHM = "HS256"

CREDENTIALS_DB = "/root/SERVICES/credentials-manager/credentials.db"
API_PORTAL_DB = "/root/SERVICES/api-portal/data/api_portal.db"
GLOBAL_ENV_FILE = "/root/FPAI_Cockpit/.env"
API_PORTAL_ENV = "/root/SERVICES/api-portal/.env"

# ------------------------------------------------------------------------------
# CRYPTO UTILS
# ------------------------------------------------------------------------------
try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.backends import default_backend
    from jose import jwt
    import bcrypt
except ImportError:
    print("❌ Error: Missing dependencies. Run with credentials-manager venv.")
    sys.exit(1)

class CryptoManager:
    def __init__(self):
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'fpai-credentials-salt',
            iterations=100000,
            backend=default_backend()
        )
        key = base64.urlsafe_b64encode(
            kdf.derive(MASTER_ENCRYPTION_KEY.encode())
        )
        self.fernet = Fernet(key)

    def encrypt(self, value: str) -> str:
        encrypted = self.fernet.encrypt(value.encode())
        return base64.b64encode(encrypted).decode()
    
    def hash_token(self, token: str) -> str:
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(token.encode('utf-8'), salt)
        return hashed.decode('utf-8')

crypto = CryptoManager()

# ------------------------------------------------------------------------------
# APIS DEFINITION
# ------------------------------------------------------------------------------
APIS = [
    {"name": "Claude", "provider": "anthropic", "env_var": "ANTHROPIC_API_KEY", "type": "api_key", "service": "llm", "tier": "paid"},
    {"name": "OpenAI", "provider": "openai", "env_var": "OPENAI_API_KEY", "type": "api_key", "service": "llm", "tier": "paid"},
    {"name": "Gemini", "provider": "google", "env_var": "GEMINI_API_KEY", "type": "api_key", "service": "llm", "tier": "paid"}
]

# ------------------------------------------------------------------------------
# HELPERS
# ------------------------------------------------------------------------------
def get_env_vars():
    vars = {}
    if os.path.exists(GLOBAL_ENV_FILE):
        with open(GLOBAL_ENV_FILE, 'r') as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    key, val = line.strip().split('=', 1)
                    vars[key] = val
    return vars

def get_db_connection(db_path):
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        print(f"❌ Failed to connect to {db_path}: {e}")
        sys.exit(1)

def update_portal_env(token):
    """Inject token into API Portal .env"""
    print(f"\n📝 Updating API Portal .env with token...")
    lines = []
    if os.path.exists(API_PORTAL_ENV):
        with open(API_PORTAL_ENV, 'r') as f:
            lines = f.readlines()
    
    new_lines = []
    found = False
    for line in lines:
        if line.startswith("APIPORTAL_CREDENTIALS_MANAGER_TOKEN="):
            new_lines.append(f"APIPORTAL_CREDENTIALS_MANAGER_TOKEN={token}\n")
            found = True
        else:
            new_lines.append(line)
            
    if not found:
        if new_lines and not new_lines[-1].endswith('\n'):
            new_lines.append('\n')
        new_lines.append(f"APIPORTAL_CREDENTIALS_MANAGER_TOKEN={token}\n")
        
    with open(API_PORTAL_ENV, 'w') as f:
        f.writelines(new_lines)
    print("   ✅ API Portal .env updated.")

# ------------------------------------------------------------------------------
# MAIN
# ------------------------------------------------------------------------------
def main():
    print("🚀 Bootstrapping API Portal & Credentials Manager...")
    
    env_vars = get_env_vars()
    cred_conn = get_db_connection(CREDENTIALS_DB)
    portal_conn = get_db_connection(API_PORTAL_DB)
    cred_cursor = cred_conn.cursor()
    portal_cursor = portal_conn.cursor()
    now = datetime.datetime.utcnow()

    credential_ids = []

    # --- 1. PROCESS APIS ---
    for api in APIS:
        print(f"\nProcessing {api['name']}...")
        
        key_value = env_vars.get(api['env_var'])
        if not key_value:
            print(f"   ⚠️ {api['env_var']} not found. Skipping.")
            continue
            
        # Credential
        cred_cursor.execute("SELECT id FROM credentials WHERE name = ?", (f"{api['name']} API Key",))
        existing_cred = cred_cursor.fetchone()
        encrypted_val = crypto.encrypt(key_value)
        
        if existing_cred:
            cred_id = existing_cred['id']
            cred_cursor.execute(
                "UPDATE credentials SET encrypted_value = ?, updated_at = ? WHERE id = ?",
                (encrypted_val, now, cred_id)
            )
        else:
            cred_cursor.execute(
                "INSERT INTO credentials (name, type, encrypted_value, service, meta, is_active, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (f"{api['name']} API Key", api['type'], encrypted_val, api['service'], "{}", True, now, now)
            )
            cred_id = cred_cursor.lastrowid
        
        credential_ids.append(cred_id)
        cred_conn.commit()

        # ActiveAPI
        portal_cursor.execute("SELECT id FROM active_apis WHERE api_name = ?", (api['name'],))
        existing_api = portal_cursor.fetchone()
        
        if not existing_api:
            portal_cursor.execute(
                """
                INSERT INTO active_apis (
                    api_name, provider, credential_ids, status, tier, rate_limit, 
                    monthly_cost, credits_per_call, internal_cost_credits, 
                    alert_threshold_percent, auto_pause_enabled, capabilities, 
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (api['name'], api['provider'], f"[{cred_id}]", "active", api['tier'], 60, 0.0, 1.0, 0.5, 80, False, '["llm"]', now, now)
            )
            api_id = portal_cursor.lastrowid
        else:
            api_id = existing_api['id']

        # API Key Pool
        portal_cursor.execute("SELECT id FROM api_keys WHERE api_id = ? AND credential_id = ?", (api_id, cred_id))
        if not portal_cursor.fetchone():
            portal_cursor.execute(
                "INSERT INTO api_keys (api_id, credential_id, label, priority, status, usage_count, error_count, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (api_id, cred_id, "Primary Key", 10, "active", 0, 0, now, now)
            )
        portal_conn.commit()

    # --- 2. CREATE ACCESS TOKEN FOR PORTAL ---
    print("\n🔑 Creating Access Token for API Portal...")
    helper_name = "api-portal"
    
    # Generate token
    import secrets
    token_value = secrets.token_urlsafe(20) # ~27 chars, well within bcrypt 72 byte limit
    token_hash = crypto.hash_token(token_value)
    expires_at = now + datetime.timedelta(days=3650) # 10 years

    # Insert into access_tokens
    cred_cursor.execute("SELECT id FROM access_tokens WHERE helper_name = ?", (helper_name,))
    existing_token = cred_cursor.fetchone()
    
    if existing_token:
        print(f"   ✅ Token record exists. Creating NEW token value anyway.")
        # We must update it to match the new JWT we will generate
        cred_cursor.execute(
            "UPDATE access_tokens SET token_hash = ?, credential_ids = ?, expires_at = ? WHERE id = ?",
            (token_hash, json.dumps(credential_ids), expires_at, existing_token['id'])
        )
        token_id = existing_token['id']
    else:
        cred_cursor.execute(
            "INSERT INTO access_tokens (token_hash, helper_name, credential_ids, scope, expires_at, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (token_hash, helper_name, json.dumps(credential_ids), "read", expires_at, now)
        )
        token_id = cred_cursor.lastrowid
        print(f"   ✅ Created Access Token ID: {token_id}")
    
    cred_conn.commit()

    # Generate JWT
    jwt_payload = {
        "type": "helper",
        "token_id": token_id,
        "helper_name": helper_name,
        "credential_ids": credential_ids,
        "scope": "read",
        "exp": expires_at
    }
    jwt_token = jwt.encode(jwt_payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    
    # --- 3. UPDATE PORTAL CONFIG ---
    update_portal_env(jwt_token)

    print("\n✅ Bootstrap complete.")

if __name__ == "__main__":
    main()
