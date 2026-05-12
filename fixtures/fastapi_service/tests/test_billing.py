from app.services.billing import apply_discount, calculate_invoice_total


def test_calculate_invoice_total():
    items = [{"price": 10, "quantity": 2}, {"price": 5, "quantity": 1}]
    assert calculate_invoice_total(items) == 25


def test_apply_discount():
    assert apply_discount(100, 15) == 85
