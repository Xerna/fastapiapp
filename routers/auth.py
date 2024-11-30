from fastapi import APIRouter, Depends
from ..auth import get_current_user, verify_admin

router = APIRouter(
    prefix="/auth",
    tags=["authentication"]
)

@router.get("/test-auth/")
async def test_auth(current_user: dict = Depends(get_current_user)):
    return {
        "message": "Successfully authenticated",
        "token_info": current_user
    }

@router.get("/test-admin/")
async def test_admin(current_user: dict = Depends(verify_admin)):
    return {
        "message": "Successfully authenticated as admin",
        "token_info": current_user
    }