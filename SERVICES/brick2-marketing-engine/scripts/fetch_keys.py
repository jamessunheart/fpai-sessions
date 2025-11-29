import json
import urllib.request
import urllib.error
import os
import sys

# Configuration
API_PORTAL_URL = "http://localhost:8060"
PROVIDERS = [
    {"name": "Claude", "env_var": "ANTHROPIC_API_KEY"},
    {"name": "OpenAI", "env_var": "OPENAI_API_KEY"},
    {"name": "Gemini", "env_var": "GEMINI_API_KEY"}
]
ENV_FILE = "/root/FPAI_Cockpit/SERVICES/brick2-marketing-engine/.env"
GLOBAL_ENV_FILE = "/root/FPAI_Cockpit/.env"

def fetch_key(api_name):
    """Fetch API key from API Portal"""
    url = f"{API_PORTAL_URL}/internal/request-key"
    payload = {
        "api_name": api_name,
        "calling_service": "brick2-marketing-engine"
    }
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
    
    try:
        with urllib.request.urlopen(req) as response:
            if response.status == 200:
                result = json.loads(response.read().decode('utf-8'))
                return result.get("api_key")
    except urllib.error.HTTPError as e:
        print(f"❌ Failed to fetch key for {api_name}: HTTP {e.code} - {e.read().decode('utf-8')}")
    except Exception as e:
        print(f"❌ Error fetching key for {api_name}: {str(e)}")
    return None

def update_env_file(file_path, updates):
    """Update .env file with new keys"""
    try:
        lines = []
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                lines = f.readlines()
        
        # Create a dictionary of existing lines to preserve comments/structure
        env_dict = {}
        new_lines = []
        processed_keys = set()

        for line in lines:
            if line.strip() and not line.startswith('#') and '=' in line:
                key, val = line.strip().split('=', 1)
                if key in updates:
                    new_lines.append(f"{key}={updates[key]}\n")
                    processed_keys.add(key)
                else:
                    new_lines.append(line)
            else:
                new_lines.append(line)
        
        # Add missing keys
        for key, val in updates.items():
            if key not in processed_keys:
                # Add a newline if the last line doesn't have one
                if new_lines and not new_lines[-1].endswith('\n'):
                    new_lines.append('\n')
                new_lines.append(f"{key}={val}\n")
        
        with open(file_path, 'w') as f:
            f.writelines(new_lines)
        print(f"✅ Updated {file_path}")
        
    except Exception as e:
        print(f"❌ Error updating {file_path}: {str(e)}")

def main():
    print("🔑 Fetching API Keys from API Portal...")
    
    updates = {}
    
    for provider in PROVIDERS:
        print(f"   Requesting key for {provider['name']}...")
        key = fetch_key(provider['name'])
        if key:
            print(f"   ✅ Got key for {provider['name']}")
            updates[provider['env_var']] = key
        else:
            print(f"   ⚠️ Could not retrieve key for {provider['name']}")
    
    if updates:
        print("\n💾 Saving keys to environment files...")
        update_env_file(ENV_FILE, updates)
        update_env_file(GLOBAL_ENV_FILE, updates)
        
        print("\n🔄 Please restart the service to apply changes.")
    else:
        print("\n⚠️ No keys retrieved. Check if API Portal has active APIs configured.")

if __name__ == "__main__":
    main()

