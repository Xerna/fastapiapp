from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import requests
from jose import jwt
from .config import settings

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.KEYCLOAK_URL}/realms/{settings.REALM}/protocol/openid-connect/token"
)

async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        # Using token introspection instead of userinfo
        response = requests.post(
            f"{settings.KEYCLOAK_URL}/realms/{settings.REALM}/protocol/openid-connect/token/introspect",
            data={
                "token": token,
                "client_id": settings.CLIENT_ID,
                "client_secret": settings.CLIENT_SECRET
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
            
        token_info = response.json()
        
        # Check if token is active
        if not token_info.get("active", False):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token is inactive"
            )
            
        return token_info

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate credentials: {str(e)}"
        )

async def verify_admin(token_info: dict = Depends(get_current_user)):
    try:
        # Check for admin role in realm_access
        realm_access = token_info.get("realm_access", {})
        roles = realm_access.get("roles", [])
        
        if "admin" not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough privileges"
            )
        return token_info
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not verify admin role"
        )