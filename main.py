from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
import requests
from .config import settings
from .database import get_db_connection
from .routers.conciertos import router as conciertos_router
from .routers.localidades import router as localidades_router
from .routers.transacciones import router as transacciones_router
from .routers.usuarios import router as usuarios_router
from .routers.lugares import router as lugares_router
from .routers.boletos import router as boletos_router
from .routers import auth 

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(usuarios_router, prefix=f"{settings.API_V1_STR}/usuarios", tags=["usuarios"])
app.include_router(conciertos_router, prefix=f"{settings.API_V1_STR}/conciertos", tags=["conciertos"])
app.include_router(localidades_router, prefix=f"{settings.API_V1_STR}/localidades", tags=["localidades"])
app.include_router(transacciones_router, prefix=f"{settings.API_V1_STR}/transacciones", tags=["transacciones"])
app.include_router(lugares_router, prefix=f"{settings.API_V1_STR}/lugares", tags=["lugares"])
app.include_router(boletos_router, prefix=f"{settings.API_V1_STR}/boletos", tags=["boletos"])
app.include_router(auth.router, prefix=f"{settings.API_V1_STR}")
                   
@app.get("/api/health")
async def health_check():
    try:
        # Probar conexión a la base de datos
        conn = get_db_connection()
        if conn:
            conn.close()
            db_status = "connected"
        else:
            db_status = "disconnected"
            
        # Probar conexión a Keycloak
        keycloak_status = "unknown"
        try:
            response = requests.get(f"{settings.KEYCLOAK_URL}/realms/{settings.REALM}/.well-known/openid-configuration")
            keycloak_status = "connected" if response.status_code == 200 else "error"
        except Exception:
            keycloak_status = "disconnected"
            
        return {
            "status": "healthy",
            "database": db_status,
            "keycloak": keycloak_status,
            "keycloak_url": settings.KEYCLOAK_URL,
            "realm": settings.REALM,
            "client_id": settings.CLIENT_ID
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)