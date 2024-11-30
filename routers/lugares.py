from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional
from ..auth import verify_admin
from ..database import get_db_connection
from ..models import LugarCreate, LugarResponse,LugarUpdate
from typing import List

router = APIRouter()

@router.post("/", response_model=LugarResponse, status_code=status.HTTP_201_CREATED)
async def create_lugar(
    lugar: LugarCreate,
    current_user: dict = Depends(verify_admin)
):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Insertar el nuevo lugar
        query = """
        INSERT INTO lugar (nombre_lugar, direccion, capacidad, ruta_escenario)
        VALUES (?, ?, ?, ?);
        SELECT SCOPE_IDENTITY() AS id;
        """
        
        cursor.execute(
            query,
            (lugar.nombre_lugar, lugar.direccion, lugar.capacidad, lugar.ruta_escenario)
        )
        
        # Obtener el ID generado
        id_lugar = cursor.fetchone()[0]
        
        conn.commit()
        cursor.close()
        conn.close()
        
        # Crear respuesta con el ID generado
        return LugarResponse(
            id_lugar=id_lugar,
            nombre_lugar=lugar.nombre_lugar,
            direccion=lugar.direccion,
            capacidad=lugar.capacidad,
            ruta_escenario=lugar.ruta_escenario
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al crear el lugar: {str(e)}"
        )


@router.get("/", response_model=List[LugarResponse])
async def get_lugares(current_user: dict = Depends(verify_admin)):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT id_lugar, nombre_lugar, direccion, capacidad, ruta_escenario FROM lugar")
        lugares = []
        for row in cursor.fetchall():
            lugares.append(LugarResponse(
                id_lugar=row[0],
                nombre_lugar=row[1],
                direccion=row[2],
                capacidad=row[3],
                ruta_escenario=row[4]
            ))
        return lugares
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

@router.delete("/{lugar_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_lugar(lugar_id: int, current_user: dict = Depends(verify_admin)):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM lugar WHERE id_lugar = ?", (lugar_id,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Lugar no encontrado")
        
        conn.commit()
        return None
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

@router.put("/{lugar_id}", response_model=LugarResponse)
async def update_lugar(
    lugar_id: int,
    lugar: LugarUpdate,
    current_user: dict = Depends(verify_admin)
):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get current values
        cursor.execute(
            "SELECT nombre_lugar, direccion, capacidad, ruta_escenario FROM lugar WHERE id_lugar = ?",
            (lugar_id,)
        )
        current = cursor.fetchone()
        if not current:
            raise HTTPException(status_code=404, detail="Lugar no encontrado")
        
        # Update with new values or keep current ones
        update_query = """
        UPDATE lugar 
        SET nombre_lugar = ?, direccion = ?, capacidad = ?, ruta_escenario = ?
        OUTPUT INSERTED.id_lugar, INSERTED.nombre_lugar, INSERTED.direccion, 
               INSERTED.capacidad, INSERTED.ruta_escenario
        WHERE id_lugar = ?
        """
        
        values = (
            lugar.nombre_lugar or current[0],
            lugar.direccion or current[1],
            lugar.capacidad or current[2],
            lugar.ruta_escenario or current[3],
            lugar_id
        )
        
        cursor.execute(update_query, values)
        updated = cursor.fetchone()
        conn.commit()
        
        return LugarResponse(
            id_lugar=updated[0],
            nombre_lugar=updated[1],
            direccion=updated[2],
            capacidad=updated[3],
            ruta_escenario=updated[4]
        )
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()
