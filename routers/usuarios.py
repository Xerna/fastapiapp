from fastapi import APIRouter, HTTPException, status,Depends
from fastapi.responses import JSONResponse
import requests
from ..models import LoginData, LoginResponse
from ..config import settings
from ..models import UserCreate, UserResponse
from datetime import datetime
from ..auth import verify_admin, get_current_user
router = APIRouter()

@router.post("/login", response_model=LoginResponse)
async def login(login_data: LoginData):
    try:
        # Determinar si es email o username
        is_email = '@' in login_data.username
        
        token_payload = {
            'client_id': settings.CLIENT_ID,
            'client_secret': settings.CLIENT_SECRET,
            'grant_type': 'password',
            'password': login_data.password
        }
        
        if is_email:
            # Buscar username por email
            service_token_response = requests.post(
                f"{settings.KEYCLOAK_URL}/realms/{settings.REALM}/protocol/openid-connect/token",
                data={
                    'client_id': settings.CLIENT_ID,
                    'client_secret': settings.CLIENT_SECRET,
                    'grant_type': 'client_credentials'
                }
            )
            
            if service_token_response.status_code != 200:
                raise HTTPException(status_code=401, detail="Error de autenticación")
            
            # Buscar usuario por email
            users_response = requests.get(
                f"{settings.KEYCLOAK_URL}/admin/realms/{settings.REALM}/users",
                headers={'Authorization': f'Bearer {service_token_response.json()["access_token"]}'},
                params={'email': login_data.username}
            )
            
            if users_response.status_code != 200 or not users_response.json():
                raise HTTPException(status_code=404, detail="Usuario no encontrado")
                
            token_payload['username'] = users_response.json()[0]['username']
        else:
            token_payload['username'] = login_data.username

        # Autenticar usuario
        response = requests.post(
            f"{settings.KEYCLOAK_URL}/realms/{settings.REALM}/protocol/openid-connect/token",
            data=token_payload
        )
        
        if response.status_code != 200:
            raise HTTPException(status_code=401, detail="Credenciales inválidas")
            
        token_data = response.json()
        user_info = get_user_info(token_data['access_token'])
        
        return {
            "access_token": token_data["access_token"],
            "refresh_token": token_data.get("refresh_token", ""),
            "token_type": token_data.get("token_type", "Bearer"),
            "expires_in": token_data.get("expires_in", 300),
            "user_info": user_info
        }

    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def get_user_info(token):
    user_info_response = requests.get(
        f"{settings.KEYCLOAK_URL}/realms/{settings.REALM}/protocol/openid-connect/userinfo",
        headers={'Authorization': f'Bearer {token}'}
    )
    
    if user_info_response.status_code == 200:
        user_info = user_info_response.json()
    else:
        user_info = {
            "sub": "unknown",
            "email": "",
            "given_name": "",
            "family_name": "",
            "realm_access": {"roles": ["user"]}
        }
    
    return {
        "id": user_info.get("sub", "unknown"),
        "email": user_info.get("email", ""),
        "nombre": user_info.get("given_name", ""),
        "apellido": user_info.get("family_name", ""),
        "roles": user_info.get("realm_access", {}).get("roles", ["user"])
    }

@router.post("", response_model=UserResponse)
async def register_user(user: UserCreate):
    try:
        # 1. Obtener token de servicio
        token_response = requests.post(
            f"{settings.KEYCLOAK_URL}/realms/{settings.REALM}/protocol/openid-connect/token",
            data={
                'client_id': settings.CLIENT_ID,
                'client_secret': settings.CLIENT_SECRET,
                'grant_type': 'client_credentials'
            }
        )
        
        if token_response.status_code != 200:
            print(f"Error getting token: {token_response.text}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Authentication failed: {token_response.text}"
            )

        access_token = token_response.json()['access_token']
        
        # 2. Verificar si existe el rol 'user'
        get_role_response = requests.get(
            f"{settings.KEYCLOAK_URL}/admin/realms/{settings.REALM}/roles",
            headers={'Authorization': f'Bearer {access_token}'}
        )

        if get_role_response.status_code != 200:
            print(f"Error getting roles: {get_role_response.text}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to get roles"
            )

        roles = get_role_response.json()
        user_role = next((role for role in roles if role['name'] == 'user'), None)

        if not user_role:
            # El rol no existe, vamos a crearlo
            create_role_response = requests.post(
                f"{settings.KEYCLOAK_URL}/admin/realms/{settings.REALM}/roles",
                headers={
                    'Authorization': f'Bearer {access_token}',
                    'Content-Type': 'application/json'
                },
                json={
                    "name": "user",
                    "description": "Comprador de tickets - acceso básico"
                }
            )
            
            if create_role_response.status_code != 201:
                print(f"Error creating role: {create_role_response.text}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to create user role"
                )
            
            # Obtener el rol recién creado
            user_role = create_role_response.json()

        # 3. Crear usuario
        user_data = {
            "username": user.email,
            "email": user.email,
            "enabled": True,
            "firstName": user.nombre,
            "lastName": user.apellido or "",
            "emailVerified": True,
            "credentials": [{
                "type": "password",
                "value": user.password,
                "temporary": False
            }]
        }

        create_user_response = requests.post(
            f"{settings.KEYCLOAK_URL}/admin/realms/{settings.REALM}/users",
            headers={
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            },
            json=user_data
        )

        if create_user_response.status_code not in [201, 204]:
            print(f"Error creating user: {create_user_response.text}")
            raise HTTPException(
                status_code=create_user_response.status_code,
                detail=f"Failed to create user: {create_user_response.text}"
            )

        # 4. Buscar el usuario creado para obtener su ID
        get_users_response = requests.get(
            f"{settings.KEYCLOAK_URL}/admin/realms/{settings.REALM}/users",
            headers={'Authorization': f'Bearer {access_token}'},
            params={'email': user.email}
        )

        if get_users_response.status_code != 200:
            print(f"Error getting user: {get_users_response.text}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve user after creation"
            )

        users = get_users_response.json()
        if not users:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="User not found after creation"
            )

        user_id = users[0]['id']

        # 5. Asignar rol
        role_to_assign = {
            "id": user_role['id'],
            "name": user_role['name']
        }

        assign_role_response = requests.post(
            f"{settings.KEYCLOAK_URL}/admin/realms/{settings.REALM}/users/{user_id}/role-mappings/realm",
            headers={
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            },
            json=[role_to_assign]
        )

        if assign_role_response.status_code != 204:
            print(f"Error assigning role: {assign_role_response.text}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to assign role to user"
            )

        # 6. Devolver la respuesta
        return UserResponse(
            id_usuario=user_id,
            email=user.email,
            nombre=user.nombre,
            apellido=user.apellido,
            fecha_registro=datetime.now()
        )
        
    except Exception as e:
        print(f"Error en register_user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    try:
        user_id = current_user.get('sub')
        if not user_id:
            raise HTTPException(
                status_code=400,
                detail="No se pudo obtener el ID del usuario"
            )
            
        realm_access = current_user.get('realm_access', {})
        roles = realm_access.get('roles', [])
            
        return {
            "id_usuario": user_id,
            "email": current_user.get('email'),
            "nombre": current_user.get('given_name', ''),
            "apellido": current_user.get('family_name'),
            "fecha_registro": None,
            "roles": roles
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )   
         