from fastapi import APIRouter, Depends, HTTPException, status,Response
from typing import List
from ..models import LocalidadResponse,LocalidadCreate
from ..database import get_db_connection
from ..auth import verify_admin, get_current_user
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from decimal import Decimal

router = APIRouter()
@router.options("/", include_in_schema=False)
@router.options("/{id_localidad}", include_in_schema=False)
async def options_handler():
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization, Accept",
            "Access-Control-Allow-Credentials": "false"
        }
    )

@router.get("/", response_model=List[LocalidadResponse])
async def get_localidades():
    try:
        connection = get_db_connection()
        if connection is None:
            raise HTTPException(status_code=500, detail="Database connection failed")
        
        cursor = connection.cursor()
        
        query = """
            SELECT 
                l.id_localidad,
                l.id_concierto,
                l.platinum_precio,
                l.vip_precio,
                l.general_precio,
                c.nombre_concierto,
                lug.nombre_lugar
            FROM localidades l
            INNER JOIN conciertos c ON l.id_concierto = c.id_concierto
            INNER JOIN lugar lug ON c.id_lugar = lug.id_lugar
        """
        
        cursor.execute(query)
        
        localidades = []
        for row in cursor.fetchall():
            localidad = {
                "id_localidad": row.id_localidad,
                "id_concierto": row.id_concierto,
                "platinum_precio": float(row.platinum_precio),
                "vip_precio": float(row.vip_precio),
                "general_precio": float(row.general_precio),
                "nombre_concierto": row.nombre_concierto,
                "nombre_lugar": row.nombre_lugar
            }
            localidades.append(localidad)
        
        return JSONResponse(
            status_code=200,
            content=jsonable_encoder(localidades),
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, Authorization",
                "Access-Control-Allow-Credentials": "false"
            }
        )
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'connection' in locals():
            connection.close()

@router.post("/", response_model=LocalidadResponse)
async def create_localidad(
    localidad: LocalidadCreate,
    current_user: dict = Depends(verify_admin)
):
    try:
        connection = get_db_connection()
        if not connection:
            raise HTTPException(status_code=500, detail="Database connection failed")
        
        cursor = connection.cursor()
        
        # Verificar si el concierto existe
        cursor.execute(
            "SELECT id_concierto FROM conciertos WHERE id_concierto = ?", 
            (localidad.id_concierto,)
        )
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Concierto no encontrado")

        # Primero insertamos y obtenemos el ID
        insert_query = """
        INSERT INTO localidades (
            id_concierto,
            platinum_precio,
            vip_precio,
            general_precio
        )
        OUTPUT INSERTED.id_localidad
        VALUES (?, ?, ?, ?);
        """
        
        params = (
            localidad.id_concierto,
            Decimal(str(localidad.platinum_precio)),
            Decimal(str(localidad.vip_precio)),
            Decimal(str(localidad.general_precio))
        )
        
        cursor.execute(insert_query, params)
        inserted_id = cursor.fetchone()[0]
        
        # Luego obtenemos todos los datos
        select_query = """
        SELECT 
            l.id_localidad,
            l.id_concierto,
            l.platinum_precio,
            l.vip_precio,
            l.general_precio,
            c.nombre_concierto,
            lug.nombre_lugar
        FROM localidades l
        INNER JOIN conciertos c ON l.id_concierto = c.id_concierto
        INNER JOIN lugar lug ON c.id_lugar = lug.id_lugar
        WHERE l.id_localidad = ?
        """
        
        cursor.execute(select_query, (inserted_id,))
        result = cursor.fetchone()
        
        if not result:
            connection.rollback()
            raise HTTPException(
                status_code=500,
                detail="Error al recuperar la localidad creada"
            )
            
        connection.commit()
        
        response_data = {
            "id_localidad": result.id_localidad,
            "id_concierto": result.id_concierto,
            "platinum_precio": float(result.platinum_precio),
            "vip_precio": float(result.vip_precio),
            "general_precio": float(result.general_precio),
            "nombre_concierto": result.nombre_concierto,
            "nombre_lugar": result.nombre_lugar
        }

        return JSONResponse(
            status_code=201,
            content=jsonable_encoder(response_data),
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, Authorization, Accept",
                "Access-Control-Allow-Credentials": "false"
            }
        )

    except HTTPException as he:
        if 'connection' in locals() and connection:
            connection.rollback()
        raise he
    except Exception as e:
        if 'connection' in locals() and connection:
            connection.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error al crear la localidad: {str(e)}"
        )
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'connection' in locals() and connection:
            connection.close()

@router.put("/{id_localidad}", response_model=LocalidadResponse)
async def update_localidad(
    id_localidad: int,
    localidad: LocalidadCreate,
    current_user: dict = Depends(verify_admin)
):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        query = """
            UPDATE localidades
            SET id_concierto = ?, platinum_precio = ?, vip_precio = ?, general_precio = ?
            OUTPUT 
                INSERTED.id_localidad,
                INSERTED.id_concierto,
                INSERTED.platinum_precio,
                INSERTED.vip_precio,
                INSERTED.general_precio,
                c.nombre_concierto,
                l.nombre_lugar
            FROM conciertos c
            JOIN lugar l ON c.id_lugar = l.id_lugar
            WHERE id_localidad = ?
        """
        
        cursor.execute(query, (
            localidad.id_concierto,
            localidad.platinum_precio,
            localidad.vip_precio,
            localidad.general_precio,
            id_localidad
        ))
        
        result = cursor.fetchone()
        if not result:
            raise HTTPException(status_code=404, detail="Localidad no encontrada")
            
        conn.commit()
        
        return JSONResponse(
            content=jsonable_encoder({
                "id_localidad": result.id_localidad,
                "id_concierto": result.id_concierto,
                "platinum_precio": float(result.platinum_precio),
                "vip_precio": float(result.vip_precio),
                "general_precio": float(result.general_precio),
                "nombre_concierto": result.nombre_concierto,
                "nombre_lugar": result.nombre_lugar
            })
        )
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

@router.delete("/{id_localidad}")
async def delete_localidad(
    id_localidad: int,
    current_user: dict = Depends(verify_admin)
):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("DELETE FROM localidades WHERE id_localidad = ?", (id_localidad,))
        
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Localidad no encontrada")
            
        conn.commit()
        
        return JSONResponse(
            content={"message": "Localidad eliminada exitosamente"}
        )
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()


@router.get("/concierto/{id_concierto}", response_model=List[LocalidadResponse])
async def get_localidades_by_concierto(id_concierto: int):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = """
            SELECT 
                l.id_localidad,
                l.id_concierto,
                l.platinum_precio,
                l.vip_precio,
                l.general_precio,
                c.nombre_concierto,
                lug.nombre_lugar
            FROM localidades l
            INNER JOIN conciertos c ON l.id_concierto = c.id_concierto
            INNER JOIN lugar lug ON c.id_lugar = lug.id_lugar
            WHERE l.id_concierto = ?
        """
        
        cursor.execute(query, (id_concierto,))
        
        localidades = [{
            "id_localidad": row.id_localidad,
            "id_concierto": row.id_concierto,
            "platinum_precio": float(row.platinum_precio),
            "vip_precio": float(row.vip_precio),
            "general_precio": float(row.general_precio),
            "nombre_concierto": row.nombre_concierto,
            "nombre_lugar": row.nombre_lugar
        } for row in cursor.fetchall()]
        
        return JSONResponse(
            content=jsonable_encoder(localidades),
            headers={"Access-Control-Allow-Origin": "*"}
        )
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()