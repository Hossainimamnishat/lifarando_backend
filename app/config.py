from pydantic_settings import BaseSettings, SettingsConfigDict
import os
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    # --- server ---
    APP_NAME: str = "FoodBackend"
    ENV: str = "dev"
    API_V1_PREFIX: str = "/api/v1"
    SECRET_KEY: str

    # --- database ---
    DATABASE_URL: str

    # --- uploads/static ---
    MEDIA_DIR: str = "app/media"
    MEDIA_BASE_URL: str = "http://localhost:8000/static"

    # --- pricing/fees ---
    SERVICE_FEE_RATE: float = 0.10
    DELIVERY_BASE_FEE: float = 2.00
    DELIVERY_PER_KM_FEE: float = 0.60
    BIKE_MAX_KM: int = 8
    CAR_MAX_KM: int = 15
    BIKE_PAY_PER_KM: float = 0.15
    BONUS_EVERY_N_ORDERS: int = 25
    BONUS_AMOUNT: float = 25.00
    COMMISSION_DEFAULT_RATE: float = 0.12

    # --- payments ---
    PAYMENT_ENABLED: bool = True
    PAYPAL_CLIENT_ID: str | None = None
    PAYPAL_SECRET: str | None = None
    STRIPE_API_KEY: str | None = None


settings = Settings(
    DATABASE_URL=os.getenv("DATABASE_URL"),
    SECRET_KEY=os.getenv("SECRET_KEY"),
)
