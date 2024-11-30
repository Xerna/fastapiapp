from pydantic import BaseModel

class Settings(BaseModel):
    # API Settings
    API_V1_STR: str = "/api"
    PROJECT_NAME: str = "ConcierTop API"
    
    # Keycloak settings
    KEYCLOAK_URL: str = "http://auth.159.223.175.204.nip.io"
    REALM: str = "conciertop"
    CLIENT_ID: str = "fastapi-client"
    CLIENT_SECRET: str = "TUmetBGUse7AQ2MdDRF29pF7w0erRHss"
    
    # Database settings
    DB_DRIVER: str = '{ODBC Driver 17 for SQL Server}'
    DB_SERVER: str = '159.223.175.204'
    DB_NAME: str = 'ConcierTop'
    DB_USER: str = 'remote_user'
    DB_PASSWORD: str = 'R3m0t3_SQL1'

    class Config:
        case_sensitive = True

settings = Settings()