from django.contrib import admin

from .models import (
    AuditLog,
    Boutique,
    BoutiqueUser,
    OtherTransaction,
    Product,
    StockMovement,
)

@admin.register(Boutique)
class BoutiqueAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active", "created_at")

@admin.register(BoutiqueUser)
class BoutiqueUserAdmin(admin.ModelAdmin):
    list_display = ("user", "boutique", "role")

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "boutique", "quantity", "cost_price")
    search_fields = ("name",)
    ordering = ("quantity",)

@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ("created_at", "product", "type", "quantity", "total", "status")
    list_filter = ("type", "status", "boutique")

@admin.register(OtherTransaction)
class OtherTransactionAdmin(admin.ModelAdmin):
    list_display = ("created_at", "type", "description", "amount", "status")
    list_filter = ("type", "status", "boutique")

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "user", "action", "boutique")