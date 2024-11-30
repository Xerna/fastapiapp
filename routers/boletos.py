from fastapi import APIRouter, Depends, HTTPException, status,Request
from typing import List
import qrcode
import io
import base64
from ..models import BoletoCreate, BoletoResponse
from ..database import get_db_connection
from ..auth import get_current_user
from datetime import datetime,date
from fastapi.responses import HTMLResponse,JSONResponse
from fastapi.templating import Jinja2Templates
import os
from pathlib import Path

router = APIRouter()
# Obtener la ruta absoluta al directorio de templates
BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"

# Inicializar templates con la ruta absoluta
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
def serialize_datetime(obj):
    """Helper function to serialize date/datetime objects"""
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    
@router.post("/", response_model=BoletoResponse)
async def create_boleto(
    boleto: BoletoCreate,
    current_user: dict = Depends(get_current_user)
):
    try:
        user_id = current_user.get('sub')
        if not user_id:
            raise HTTPException(
                status_code=400,
                detail="No se pudo obtener el ID del usuario"
            )

        connection = get_db_connection()
        cursor = connection.cursor()

        # Actualizamos la query para incluir session_id
        sql_query_insert = """
            INSERT INTO boletos (
                id_concierto, id_usuario, id_localidad,
                fecha_compra, hora_compra, precio_final,
                cantidad_boletos, status, session_id
            )
            OUTPUT 
                INSERTED.id_boleto
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        now = datetime.now()
        params = (
            boleto.id_concierto,
            user_id,
            boleto.id_localidad,
            now.date(),
            now.time(),
            boleto.precio_final,
            boleto.cantidad_boletos,
            "verifying",
            boleto.session_id
        )

        cursor.execute(sql_query_insert, params)
        result = cursor.fetchone()
        boleto_id = result.id_boleto

        # Generación del QR y actualización siguen igual...
        validation_url = f"http://api.159.223.175.204.nip.io/api/boletos/validate/{boleto_id}"
        
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(validation_url)
        qr.make(fit=True)

        img_buffer = io.BytesIO()
        qr_image = qr.make_image(fill_color="black", back_color="white")
        qr_image.save(img_buffer, format='PNG')
        qr_base64 = base64.b64encode(img_buffer.getvalue()).decode()
        img_data = f"data:image/png;base64,{qr_base64}"

        cursor.execute("""
            UPDATE boletos 
            SET qr_imagen = ? 
            WHERE id_boleto = ?
        """, (img_data, boleto_id))

        # Actualizamos la query de selección para incluir session_id
        cursor.execute("""
            SELECT 
                id_boleto, id_concierto, id_usuario, id_localidad,
                fecha_compra, hora_compra, precio_final,
                cantidad_boletos, qr_imagen, status, session_id
            FROM boletos
            WHERE id_boleto = ?
        """, (boleto_id,))

        result = cursor.fetchone()
        connection.commit()

        return {
            "id_boleto": result.id_boleto,
            "id_concierto": result.id_concierto,
            "id_usuario": result.id_usuario,
            "id_localidad": result.id_localidad,
            "fecha_compra": result.fecha_compra,
            "hora_compra": result.hora_compra,
            "precio_final": float(result.precio_final),
            "cantidad_boletos": result.cantidad_boletos,
            "qr_imagen": result.qr_imagen,
            "status": result.status,
            "session_id": result.session_id
        }

    except Exception as e:
        print(f"Error creating ticket: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al crear el boleto: {str(e)}"
        )
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'connection' in locals():
            connection.close()


@router.get("/by_current_user_id", response_model=List[BoletoResponse])
async def get_boletos_by_user(current_user: dict = Depends(get_current_user)):
    try:
        user_id = current_user.get('sub')
        if not user_id:
            raise HTTPException(
                status_code=400,
                detail="No se pudo obtener el ID del usuario"
            )

        connection = get_db_connection()
        cursor = connection.cursor()
        
        # Actualizamos la query para incluir session_id
        query = """
            SELECT 
                id_boleto, id_concierto, id_usuario, id_localidad,
                fecha_compra, hora_compra, precio_final,
                cantidad_boletos, qr_imagen, status, session_id
            FROM boletos
            WHERE id_usuario = ? AND status IN ('aprobado', 'Canjeado')
        """
        
        cursor.execute(query, (user_id,))
        
        boletos = []
        for row in cursor.fetchall():
            boleto = {
                "id_boleto": row.id_boleto,
                "id_concierto": row.id_concierto,
                "id_usuario": row.id_usuario,
                "id_localidad": row.id_localidad,
                "fecha_compra": row.fecha_compra,
                "hora_compra": row.hora_compra,
                "precio_final": float(row.precio_final),
                "cantidad_boletos": row.cantidad_boletos,
                "qr_imagen": row.qr_imagen,
                "status": row.status,
                "session_id": row.session_id
            }
            boletos.append(boleto)

        return boletos

    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'connection' in locals():
            connection.close()



@router.get("/validate/{boleto_id}", response_class=HTMLResponse)
async def validate_boleto_page(request: Request, boleto_id: int):
    """Endpoint que devuelve la página HTML de validación"""
    return templates.TemplateResponse("validation.html", {
        "request": request,
        "boleto_id": boleto_id
    })

@router.get("/api/validate/{boleto_id}")
async def validate_boleto_api(boleto_id: int):
    """Endpoint API que realiza la validación y retorna JSON"""
    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        # Verificar el estado actual del boleto
        cursor.execute("""
            SELECT status, id_concierto, fecha_compra 
            FROM boletos 
            WHERE id_boleto = ?
        """, (boleto_id,))

        result = cursor.fetchone()
        if not result:
            return JSONResponse({
                "valid": False,
                "message": "Boleto no encontrado",
                "status": "error"
            })

        # Si el boleto ya está canjeado
        if result.status == "Canjeado":
            return JSONResponse({
                "valid": False,
                "message": "Este boleto ya ha sido canjeado",
                "status": "Canjeado"
            })

        # Si el boleto no está aprobado
        if result.status != "aprobado":
            return JSONResponse({
                "valid": False,
                "message": f"Este boleto no está aprobado para su uso (Estado actual: {result.status})",
                "status": result.status
            })

        # Actualizar el estado del boleto a "Canjeado"
        cursor.execute("""
            UPDATE boletos 
            SET status = 'Canjeado' 
            WHERE id_boleto = ?
        """, (boleto_id,))

        connection.commit()

        # Serializamos los datos antes de enviarlos
        response_data = {
            "valid": True,
            "message": "Boleto validado exitosamente",
            "status": "Canjeado",
            "id_concierto": result.id_concierto,
            "fecha_compra": serialize_datetime(result.fecha_compra)  # Aquí convertimos la fecha
        }

        return JSONResponse(content=response_data)

    except Exception as e:
        print(f"Error en validate_boleto_api: {str(e)}")
        return JSONResponse({
            "valid": False,
            "message": f"Error al validar el boleto: {str(e)}",
            "status": "error"
        })
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'connection' in locals():
            connection.close()