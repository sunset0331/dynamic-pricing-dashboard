# dashboard_app/admin.py

from django.contrib import admin
from .models import Product, ProductDailyRecord # Import both models

# Register your Product model
admin.site.register(Product)

# Register your ProductDailyRecord model
admin.site.register(ProductDailyRecord)
