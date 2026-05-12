class OrderRepository:
    def get_order(self, order_id: int) -> dict:
        return {"order_id": order_id, "user_id": 1, "status": "created", "total": 42.0}

    def create_order(self, user_id: int, total: float) -> dict:
        return {"order_id": 100, "user_id": user_id, "status": "created", "total": total}

    def cancel_order(self, order_id: int) -> dict:
        return {"order_id": order_id, "status": "cancelled"}
