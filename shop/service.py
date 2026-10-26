from django.db import transaction

from .models import Product, StockMovement


class StockError(Exception):
    """A rule was broken (bad quantity, duplicate name...)."""


def check_numbers(quantity, unit_price):
    if quantity <= 0:
        raise StockError("Quantity must be greater than 0.")
    if unit_price <= 0:
        raise StockError("Price must be greater than 0.")


def record_movement(product, user, quantity, unit_price):
    return StockMovement.objects.create(
        boutique=product.boutique,
        product=product,
        type=StockMovement.Type.IN,
        quantity=quantity,
        unit_price=unit_price,
        total=quantity * unit_price,
        recorded_by=user,
    )


@transaction.atomic
def stock_in_new(boutique, user, name, quantity, unit_price,
                 photo=None, min_quantity=5):
    check_numbers(quantity, unit_price)
    name = " ".join(name.split())
    exists = Product.objects.filter(
        boutique=boutique, name_key=name.lower()
    ).exists()
    if exists:
        raise StockError("This product already exists, choose Existing product.")
    product = Product.objects.create(
        boutique=boutique,
        name=name,
        photo=photo,
        quantity=quantity,
        cost_price=unit_price,
        last_bought_qty=quantity,
        min_quantity=min_quantity,
    )
    return record_movement(product, user, quantity, unit_price)


@transaction.atomic
def stock_in_existing(boutique, user, product_id, quantity, unit_price):
    check_numbers(quantity, unit_price)
    product = Product.objects.select_for_update().get(
        pk=product_id, boutique=boutique
    )
    product.quantity += quantity
    product.cost_price = unit_price
    product.last_bought_qty = quantity
    product.save()
    return record_movement(product, user, quantity, unit_price)