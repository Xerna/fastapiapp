from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from ..models import ConciertoCreate, ConciertoResponse,ConciertoBase
from ..database import get_db_connection
from ..auth import verify_admin, get_current_user
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder

router = APIRouter()

@router.get("/", response_model=List[ConciertoResponse])
async def get_conciertos():
    try:
        connection = get_db_connection()
        if connection is None:
            raise HTTPException(status_code=500, detail="Database connection failed")
        
        cursor = connection.cursor()
        
        query = """
            SELECT 
                c.id_concierto,
                c.nombre_concierto,
                c.fecha_concierto,
                c.hora_inicio,
                c.hora_apertura,
                c.id_lugar,
                c.precio_base,
                c.estado,
                c.ruta_carrusel,
                c.ruta_concierto_carrusel
            FROM conciertos c
        """
        cursor.execute(query)
        
        conciertos = []
        for row in cursor.fetchall():
            conciertos.append({
                "id_concierto": row.id_concierto,
                "nombre_concierto": row.nombre_concierto,
                "fecha_concierto": row.fecha_concierto,
                "hora_inicio": row.hora_inicio,
                "hora_apertura": row.hora_apertura,
                "id_lugar": row.id_lugar,
                "precio_base": float(row.precio_base),
                "estado": row.estado,
                "ruta_carrusel": row.ruta_carrusel,
                "ruta_concierto_carrusel": row.ruta_concierto_carrusel
            })
        
        return JSONResponse(
            content=jsonable_encoder(conciertos),
            headers={"Access-Control-Allow-Origin": "*"}
        )
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'connection' in locals(): connection.close()

@router.post("/", response_model=ConciertoResponse)
async def create_concierto(
    concierto: ConciertoCreate,
    current_user: dict = Depends(verify_admin)
):
    try:
        connection = get_db_connection()
        if not connection:
            raise HTTPException(status_code=500, detail="Database connection failed")
        
        cursor = connection.cursor()
        
        sql_query = """
            INSERT INTO conciertos (
                nombre_concierto,
                fecha_concierto,
                hora_inicio,
                hora_apertura,
                id_lugar,
                precio_base,
                estado
            )
            OUTPUT 
                INSERTED.id_concierto,
                INSERTED.nombre_concierto,
                INSERTED.fecha_concierto,
                INSERTED.hora_inicio,
                INSERTED.hora_apertura,
                INSERTED.id_lugar,
                INSERTED.precio_base,
                INSERTED.estado
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        
        params = (
            concierto.nombre_concierto,
            concierto.fecha_concierto,
            concierto.hora_inicio,
            concierto.hora_apertura,
            concierto.id_lugar,
            concierto.precio_base,
            concierto.estado
        )
        
        try:
            cursor.execute(sql_query, params)
            result = cursor.fetchone()
            connection.commit()
            
            response_data = {
                "id_concierto": result.id_concierto,
                "nombre_concierto": result.nombre_concierto,
                "fecha_concierto": result.fecha_concierto,
                "hora_inicio": result.hora_inicio,
                "hora_apertura": result.hora_apertura,
                "id_lugar": result.id_lugar,
                "precio_base": float(result.precio_base),
                "estado": result.estado,
                "ruta_carrusel": None,
                "ruta_concierto_carrusel": None
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
                detail=f"Error al insertar en la base de datos: {str(e)}"
            )

    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'connection' in locals() and connection:
            connection.close()

# Get concierto by ID (usuario normal)
@router.get("/{id_concierto}", response_model=ConciertoResponse)
async def get_concierto_by_id(
    id_concierto: int,
    current_user: dict = Depends(get_current_user)
):
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        
        query = """
            SELECT id_concierto, nombre_concierto, fecha_concierto, 
                   hora_inicio, hora_apertura, id_lugar, precio_base, 
                   estado, ruta_carrusel, ruta_concierto_carrusel
            FROM conciertos 
            WHERE id_concierto = ?
        """
        
        cursor.execute(query, (id_concierto,))
        result = cursor.fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="Concierto no encontrado")
            
        return ConciertoResponse(
            id_concierto=result.id_concierto,
            nombre_concierto=result.nombre_concierto,
            fecha_concierto=result.fecha_concierto,
            hora_inicio=result.hora_inicio,
            hora_apertura=result.hora_apertura,
            id_lugar=result.id_lugar,
            precio_base=float(result.precio_base),
            estado=result.estado,
            ruta_carrusel=result.ruta_carrusel,
            ruta_concierto_carrusel=result.ruta_concierto_carrusel
        )
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'connection' in locals(): connection.close()

# Delete concierto (admin)
@router.delete("/{id_concierto}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_concierto(
    id_concierto: int,
    current_user: dict = Depends(verify_admin)
):
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        
        cursor.execute("DELETE FROM conciertos WHERE id_concierto = ?", (id_concierto,))
        
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Concierto no encontrado")
            
        connection.commit()
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'connection' in locals(): connection.close()

# Update concierto (admin)
@router.put("/{id_concierto}", response_model=ConciertoResponse)
async def update_concierto(
    id_concierto: int,
    concierto: ConciertoBase,
    current_user: dict = Depends(verify_admin)
):
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        
        update_query = """
            UPDATE conciertos 
            SET nombre_concierto = ?,
                fecha_concierto = ?,
                hora_inicio = ?,
                hora_apertura = ?,
                id_lugar = ?,
                precio_base = ?,
                estado = ?,
                ruta_carrusel = ?,
                ruta_concierto_carrusel = ?
            OUTPUT 
                INSERTED.id_concierto,
                INSERTED.nombre_concierto,
                INSERTED.fecha_concierto,
                INSERTED.hora_inicio,
                INSERTED.hora_apertura,
                INSERTED.id_lugar,
                INSERTED.precio_base,
                INSERTED.estado,
                INSERTED.ruta_carrusel,
                INSERTED.ruta_concierto_carrusel
            WHERE id_concierto = ?
        """
        
        params = (
            concierto.nombre_concierto,
            concierto.fecha_concierto,
            concierto.hora_inicio,
            concierto.hora_apertura,
            concierto.id_lugar,
            concierto.precio_base,
            concierto.estado,
            concierto.ruta_carrusel,
            concierto.ruta_concierto_carrusel,
            id_concierto
        )
        
        cursor.execute(update_query, params)
        result = cursor.fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="Concierto no encontrado")
            
        connection.commit()
        
        return ConciertoResponse(
            id_concierto=result.id_concierto,
            nombre_concierto=result.nombre_concierto,
            fecha_concierto=result.fecha_concierto,
            hora_inicio=result.hora_inicio,
            hora_apertura=result.hora_apertura,
            id_lugar=result.id_lugar,
            precio_base=float(result.precio_base),
            estado=result.estado,
            ruta_carrusel=result.ruta_carrusel,
            ruta_concierto_carrusel=result.ruta_concierto_carrusel
        )
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'connection' in locals(): connection.close()