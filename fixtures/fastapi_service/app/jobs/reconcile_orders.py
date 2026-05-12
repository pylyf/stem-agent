from app.repositories.orders import OrderRepository


def reconcile_open_orders() -> int:
    repository = OrderRepository()
    sample = repository.get_order(1)
    return 1 if sample["status"] == "created" else 0
