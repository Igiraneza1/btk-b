from django.contrib import admin

from .models import Boutique, BoutiqueUser


@admin.register(Boutique)
class BoutiqueAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active", "created_at")


@admin.register(BoutiqueUser)
class BoutiqueUserAdmin(admin.ModelAdmin):
    list_display = ("user", "boutique", "role")