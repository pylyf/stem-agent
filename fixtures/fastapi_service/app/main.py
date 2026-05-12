from fastapi import FastAPI

from .routers import orders, users
from .services.billing import calculate_invoice_total
from .settings import Settings

app = FastAPI(title="Orders API")
settings = Settings()

app.include_router(orders.router)
app.include_router(users.router)


@app.get("/health")
def health():
    return {"status": "ok", "env": settings.environment}


@app.get("/invoice-preview")
def invoice_preview():
    return {"total": calculate_invoice_total([{"price": 10, "quantity": 2}])}
