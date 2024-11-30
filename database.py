import pyodbc
from .config import settings

def get_db_connection():
    try:
        conn_str = (
            f"DRIVER={settings.DB_DRIVER};"
            f"SERVER={settings.DB_SERVER};"
            f"DATABASE={settings.DB_NAME};"
            f"UID={settings.DB_USER};"
            f"PWD={settings.DB_PASSWORD}"
        )
        connection = pyodbc.connect(conn_str)
        return connection
    except pyodbc.Error as e:
        print(f"Error connecting to SQL Server: {e}")
        return None

def test_connection():
    conn = get_db_connection()
    if conn:
        conn.close()
        return True
    return False