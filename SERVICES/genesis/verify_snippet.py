@app.get("/auth/verify-key/{api_key}")
async def verify_api_key(api_key: str):
    """Verify an API key and identify the agent (Internal/Service use)."""
    keys = load_json(KEYS_FILE)
    
    # Reverse lookup (inefficient for huge lists, fine for <1000 agents)
    for name, key in keys.items():
        if key == api_key:
            return {"status": "valid", "agent_name": name, "role": "agent"}
            
    raise HTTPException(401, "Invalid Key")











