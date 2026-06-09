async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> CurrentUser:
    """Get current user, raise 401 if not authenticated."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    payload = decode_token(token)
    
    if payload:
        return CurrentUser(
            member_id=payload.get("sub"),
            email=payload.get("email"),
            role=payload.get("role", "member"),
        )
        
    # If NOT a valid local JWT, check if it's a Genesis Agent Key
    if token.startswith("agent-"):
        from .integrations import genesis_client
        result = await genesis_client.verify_key(token)
        if result and result.get("status") == "valid":
            return CurrentUser(
                member_id=result.get("agent_name", "unknown_agent"),
                email=f"{result.get('agent_name', 'agent')}@genesis.local",
                role=result.get("role", "agent"),
            )
            
    # If we got here, it's invalid
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )











