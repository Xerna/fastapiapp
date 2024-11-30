from pydantic import BaseModel, EmailStr, Field
from datetime import datetime, time,date
from typing import Optional, List
from decimal import *


# Modelos de Usuario
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    nombre: str
    apellido: Optional[str] = None

class UserResponse(BaseModel):
    id_usuario: str
    nombre: str
    email: str
    fecha_registro: Optional[datetime] = None
    apellido: Optional[str] = None
    roles: List[str] = []

class ConciertoBase(BaseModel):
    nombre_concierto: str = Field(..., max_length=100)
    fecha_concierto: date
    hora_inicio: time
    hora_apertura: time
    id_lugar: int
    precio_base: float = Field(..., gt=0)
    estado: str = Field(default="Programado", max_length=20)
    ruta_carrusel: Optional[str] = Field(default=None, max_length=235)
    ruta_concierto_carrusel: Optional[str] = Field(default=None, max_length=235)

class ConciertoCreate(ConciertoBase):
    pass

class ConciertoResponse(ConciertoBase):
    id_concierto: int

# Modelos de Localidad
class LocalidadCreate(BaseModel):
    id_concierto: int
    platinum_precio: Decimal
    vip_precio: Decimal
    general_precio: Decimal

class LocalidadResponse(BaseModel):
    id_localidad: int
    id_concierto: int
    platinum_precio: float
    vip_precio: float
    general_precio: float
    nombre_concierto: str
    nombre_lugar: str

#Transacciones
class TransaccionBase(BaseModel):
    id_boleto: int
    monto: Decimal = Field(..., ge=0)
    metodo_pago: str = Field(..., max_length=50)
    estado: str = Field(default="Pendiente", max_length=20)
    fecha_transaccion: date = Field(default_factory=date.today)
    hora_transaccion: time = Field(default_factory=time)
    fecha_creacion: date = Field(default_factory=date.today)

class TransaccionCreate(TransaccionBase):
    pass

class TransaccionResponse(TransaccionBase):
    id_transaccion: int
    id_usuario: str

class LoginData(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
    user_info: dict                

class LugarCreate(BaseModel):
    nombre_lugar: str = Field(..., max_length=100)
    direccion: str = Field(..., max_length=255)
    capacidad: int = Field(..., gt=0)
    ruta_escenario: str = Field(..., max_length=255)

class LugarUpdate(BaseModel):
    nombre_lugar: Optional[str] = Field(None, max_length=100)
    direccion: Optional[str] = Field(None, max_length=255)
    capacidad: Optional[int] = Field(None, gt=0)
    ruta_escenario: Optional[str] = Field(None, max_length=255)

class LugarResponse(BaseModel):
    id_lugar: int
    nombre_lugar: str
    direccion: str
    capacidad: int
    ruta_escenario: str

class BoletoBase(BaseModel):
    id_concierto: int
    id_usuario: Optional[str] = None
    id_localidad: int
    precio_final: Decimal = Field(..., ge=0)
    cantidad_boletos: int = Field(..., gt=0)
    status: str = "verifying"
    session_id: Optional[str] = None

class BoletoCreate(BaseModel):
    id_concierto: int
    id_localidad: int
    cantidad_boletos: int = Field(..., gt=0)
    precio_final: Decimal = Field(..., ge=0)
    session_id: Optional[str] = None

class BoletoResponse(BoletoBase):
    id_boleto: int
    fecha_compra: date
    hora_compra: time
    qr_imagen: str

