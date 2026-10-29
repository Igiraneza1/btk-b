from django.db import transaction

from .models import Product, StockMovement
from .services import StockError, check_numbers

class BelowCostWarning(StockError):
    """Sell price is lower than the buy price. Ask the user to confirm."""

def search_products(boutique, text):
    text = " ".join(text.split()).lower()
    return Product.objects.filter(
        boutique=boutique,
        name_key__contains=text,
        quantity__gt=0,
    ).order_by("name")[:10]

@transaction.atomic
def stock_out(boutique, user, product_id, quantity, unit_price,
              confirm_below_cost=False):
    check_numbers(quantity, unit_price)
    try:
        product = Product.objects.select_for_update().get(
            pk=product_id, boutique=boutique
        )
    except Product.DoesNotExist:
        raise StockError("Product not found.")

    if quantity > product.quantity:
        raise StockError(f"Only {product.quantity} in stock.")

    below_cost = unit_price < product.cost_price
    if below_cost:
        if boutique.block_below_cost:
            raise StockError("Selling below the buy price is not allowed.")
        if not confirm_below_cost:
            raise BelowCostWarning(
                "Sell price should be greater than buy price."
            )

    movement = StockMovement.objects.create(
        boutique=boutique,
        product=product,
        type=StockMovement.Type.OUT,
        quantity=quantity,
        unit_price=unit_price,
        total=quantity * unit_price,
        cost_price_at_sale=product.cost_price,
        below_cost=below_cost,
        recorded_by=user,
    )
    product.quantity -= quantity
    product.last_sell_price = unit_price
    product.save()
    return movement