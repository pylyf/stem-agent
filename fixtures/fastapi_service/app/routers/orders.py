from fastapi import APIRouter

from ..models import Order, OrderCreate
from ..repositories.orders import OrderRepository
from ..services.billing import calculate_invoice_total

router = APIRouter(prefix="/orders", tags=["orders"])
repository = OrderRepository()


@router.get("/{order_id}", response_model=Order)
def read_order(order_id: int):
    return repository.get_order(order_id)


@router.post("", response_model=Order)
def create_order(order: OrderCreate):
    total = calculate_invoice_total([item.model_dump() for item in order.items])
    return repository.create_order(order.user_id, total)


@router.post("/{order_id}/cancel")
def cancel_order(order_id: int):
    return repository.cancel_order(order_id)
