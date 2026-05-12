class UserRepository:
    def get_user(self, user_id: int) -> dict:
        return {"user_id": user_id, "email": "user@example.com", "is_active": True}

    def list_users(self) -> list[dict]:
        return [
            {"user_id": 1, "email": "admin@example.com", "is_active": True},
            {"user_id": 2, "email": "buyer@example.com", "is_active": True},
        ]
