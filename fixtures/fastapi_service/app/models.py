from pydantic import BaseModel, EmailStr


class OrderItem(BaseModel):
    sku: str
    price: float
    quantity: int = 1


class OrderCreate(BaseModel):
    user_id: int
    items: list[OrderItem]


class Order(BaseModel):
    order_id: int
    user_id: int
    status: str
    total: float


class User(BaseModel):
    user_id: int
    email: EmailStr
    is_active: bool = True
