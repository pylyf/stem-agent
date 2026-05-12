def calculate_invoice_total(items: list[dict]) -> float:
    return sum(float(item["price"]) * int(item.get("quantity", 1)) for item in items)


def apply_discount(total: float, percent: float) -> float:
    return round(total * (1 - percent / 100), 2)
