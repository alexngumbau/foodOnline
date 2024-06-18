from django.contrib import admin

from menu.models import Category, FoodItem

# Register your models here.

admin.site.register(Category)
admin.site.register(FoodItem)