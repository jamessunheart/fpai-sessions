@app.get("/api/config/swarm-secret")
async def get_swarm_secret(
    current_user: auth.CurrentUser = Depends(auth.require_admin),
):
    """Get the Swarm Secret for display (Admin only)."""
    return {"secret": "fpai-swarm-genesis-permanent-link-v1"}

@app.post("/api/genesis/keys")










