from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    environment: str = "local"
    database_url: str = "sqlite:///orders.db"
    billing_provider: str = "stripe"
    order_reconcile_interval_minutes: int = 15
