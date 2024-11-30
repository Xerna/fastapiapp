from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from datetime import datetime
from ..database import get_db_connection
from ..auth import verify_admin, get_current_user
from ..models import TransaccionCreate, TransaccionResponse
from typing import List

router = APIRouter()

@router.post("/", response_model=TransaccionResponse)
async def create_transaccion(
    transaccion: TransaccionCreate,
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
        if not connection:
            raise HTTPException(
                status_code=500,
                detail="Error de conexión con la base de datos"
            )

        cursor = connection.cursor()

        # Verificar si el boleto existe y está disponible
        cursor.execute(
            "SELECT id_boleto FROM boletos_prueba WHERE id_boleto = ?",
            (transaccion.id_boleto,)
        )
        boleto = cursor.fetchone()
        if not boleto:
            raise HTTPException(
                status_code=404,
                detail="Boleto no encontrado"
            )

        # Crear la transacción
        now = datetime.now()
        sql_query = """
            INSERT INTO transacciones (
                id_boleto,
                monto,
                fecha_transaccion,
                hora_transaccion,
                metodo_pago,
                estado,
                fecha_creacion    -- Removida la coma extra
            )
            OUTPUT
                INSERTED.id_transaccion,
                INSERTED.id_boleto,
                INSERTED.monto,
                INSERTED.fecha_transaccion,
                INSERTED.hora_transaccion,
                INSERTED.metodo_pago,
                INSERTED.estado,
                INSERTED.fecha_creacion
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """

        params = (
            transaccion.id_boleto,
            transaccion.monto,
            now.date(),
            now.time(),
            transaccion.metodo_pago,
            transaccion.estado,
            now.date()
        )

        try:
            cursor.execute(sql_query, params)
            result = cursor.fetchone()
            connection.commit()
            response_data = {
                "id_transaccion": result.id_transaccion,
                "id_boleto": result.id_boleto,
                "monto": float(result.monto),
                "fecha_transaccion": result.fecha_transaccion,
                "hora_transaccion": result.hora_transaccion,
                "metodo_pago": result.metodo_pago,
                "estado": result.estado,
                "fecha_creacion": result.fecha_creacion
            }

            return JSONResponse(
                status_code=201,
                content=jsonable_encoder(response_data),
                headers={"Access-Control-Allow-Origin": "*"}
            )

        except Exception as e:
            connection.rollback()
            raise HTTPException(
                status_code=500,
                detail=f"Error al crear la transacción: {str(e)}"
            )

    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'connection' in locals() and connection:
            connection.close()

# Get todas las transacciones (admin)
@router.get("/", response_model=List[TransaccionResponse])
async def get_transacciones(current_user: dict = Depends(verify_admin)):
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        
        query = """
            SELECT id_transaccion, id_boleto, monto, fecha_transaccion,
                   hora_transaccion, metodo_pago, estado, fecha_creacion
            FROM transacciones
        """
        cursor.execute(query)
        
        transacciones = []
        for row in cursor.fetchall():
            transaccion = {
                "id_transaccion": row.id_transaccion,
                "id_boleto": row.id_boleto,
                "monto": float(row.monto),
                "fecha_transaccion": row.fecha_transaccion,
                "hora_transaccion": row.hora_transaccion,
                "metodo_pago": row.metodo_pago,
                "estado": row.estado,
                "fecha_creacion": row.fecha_creacion,
                "id_usuario": current_user.get('sub', '')
            }
            transacciones.append(transaccion)
        
        return JSONResponse(content=jsonable_encoder(transacciones))
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'connection' in locals(): connection.close()

# # Get transacciones por id usuario (usuario normal)
# @router.get("/usuario", response_model=List[TransaccionResponse])
# async def get_transacciones_by_usuario(current_user: dict = Depends(get_current_user)):
#     try:
#         user_id = current_user.get('sub')
#         if not user_id:
#             raise HTTPException(status_code=400, detail="ID de usuario no encontrado")

#         connection = get_db_connection()
#         cursor = connection.cursor()
        
#         query = """
#             SELECT id_transaccion, id_boleto, monto, fecha_transaccion,
#                    hora_transaccion, metodo_pago, estado, fecha_creacion
#             FROM transacciones
#             WHERE id_usuario = ?
#         """
#         cursor.execute(query, (user_id,))
        
#         transacciones = []
#         for row in cursor.fetchall():
#             transaccion = {
#                 "id_transaccion": row.id_transaccion,
#                 "id_boleto": row.id_boleto,
#                 "monto": float(row.monto),
#                 "fecha_transaccion": row.fecha_transaccion,
#                 "hora_transaccion": row.hora_transaccion,
#                 "metodo_pago": row.metodo_pago,
#                 "estado": row.estado,
#                 "fecha_creacion": row.fecha_creacion,
#                 "id_usuario": user_id
#             }
#             transacciones.append(transaccion)
        
#         return JSONResponse(content=jsonable_encoder(transacciones))
#     finally:
#         if 'cursor' in locals(): cursor.close()
#         if 'connection' in locals(): connection.close()