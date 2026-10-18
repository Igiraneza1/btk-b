from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone


# =====================================================================
# ORDER RULE: a class must be written ABOVE any class that links to it.
#   1. Boutique, BoutiqueUser   (no links to other shop classes)
#   2. Product                  (links to Boutique)
#   3. StockMovement            (links to Boutique and Product)
#   4. OtherTransaction         (links to Boutique)
#   5. AuditLog                 (links to Boutique)
# =====================================================================


# ---------------------------------------------------------------------
# 1. BOUTIQUES AND WHO WORKS IN THEM
# ---------------------------------------------------------------------
class Boutique(models.Model):
    name = models.CharField(max_length=150)
    pin_hash = models.CharField(max_length=128, blank=True)
    failed_pin_attempts = models.PositiveSmallIntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)
    block_below_cost = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class BoutiqueUser(models.Model):
    class Role(models.TextChoices):
        MANAGER = "manager", "Manager"
        STAFF = "staff", "Staff"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    boutique = models.ForeignKey(
        Boutique,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.STAFF)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "boutique"],
                name="unique_user_boutique",
            )
        ]

    def __str__(self):
        return f"{self.user} - {self.boutique} ({self.role})"


# ---------------------------------------------------------------------
# 2. PRODUCTS (belong to one boutique)
# ---------------------------------------------------------------------
class Product(models.Model):
    boutique = models.ForeignKey(
        Boutique,
        on_delete=models.PROTECT,
        related_name="products",
    )
    name = models.CharField(max_length=200)
    name_key = models.CharField(max_length=200, editable=False)
    photo = models.ImageField(upload_to="products/", null=True, blank=True)
    quantity = models.PositiveIntegerField(default=0)
    cost_price = models.BigIntegerField(default=0)
    last_bought_qty = models.PositiveIntegerField(default=0)
    last_sell_price = models.BigIntegerField(null=True, blank=True)
    min_quantity = models.PositiveIntegerField(default=5)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["boutique", "name_key"],
                name="unique_product_name_per_boutique",
            )
        ]

    def save(self, *args, **kwargs):
        # "  Red   Dress " -> name "Red Dress", name_key "red dress"
        self.name = " ".join(self.name.split())
        self.name_key = self.name.lower()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.boutique})"


# ---------------------------------------------------------------------
# 3. STOCK IN / STOCK OUT
# ---------------------------------------------------------------------
class StockMovement(models.Model):
    class Type(models.TextChoices):
        IN = "in", "Stock in"
        OUT = "out", "Stock out"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        CANCELLED = "cancelled", "Cancelled"

    boutique = models.ForeignKey(
        Boutique, on_delete=models.PROTECT, related_name="movements"
    )
    product = models.ForeignKey(
        Product, on_delete=models.PROTECT, related_name="movements"
    )
    type = models.CharField(max_length=3, choices=Type.choices)
    quantity = models.PositiveIntegerField()
    unit_price = models.BigIntegerField()
    total = models.BigIntegerField()
    cost_price_at_sale = models.BigIntegerField(null=True, blank=True)
    below_cost = models.BooleanField(default=False)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="stock_movements",
    )
    created_at = models.DateTimeField(default=timezone.now)
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.ACTIVE
    )
    cancelled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    cancel_reason = models.TextField(blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["boutique", "created_at"]),
            models.Index(fields=["recorded_by"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(quantity__gt=0),
                name="movement_quantity_positive",
            )
        ]

    def __str__(self):
        return f"{self.type} {self.quantity} x {self.product.name}"


# ---------------------------------------------------------------------
# 4. OTHER INCOME AND EXPENSES (rent, transport, cleaning...)
# ---------------------------------------------------------------------
class OtherTransaction(models.Model):
    class Type(models.TextChoices):
        INCOME = "income", "Income"
        EXPENSE = "expense", "Expense"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        CANCELLED = "cancelled", "Cancelled"

    boutique = models.ForeignKey(
        Boutique, on_delete=models.PROTECT, related_name="other_transactions"
    )
    type = models.CharField(max_length=7, choices=Type.choices)
    description = models.CharField(max_length=255)
    amount = models.BigIntegerField()
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="other_transactions",
    )
    created_at = models.DateTimeField(default=timezone.now)
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.ACTIVE
    )
    cancelled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    cancel_reason = models.TextField(blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["boutique", "created_at"])]

    def __str__(self):
        return f"{self.type}: {self.description} ({self.amount})"


# ---------------------------------------------------------------------
# 5. AUDIT LOG (who did what, and when)
# ---------------------------------------------------------------------
class AuditLog(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="audit_entries",
    )
    boutique = models.ForeignKey(
        Boutique,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="audit_entries",
    )
    action = models.CharField(max_length=100)
    details = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.action} by {self.user}"