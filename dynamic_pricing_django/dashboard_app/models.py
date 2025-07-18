# dashboard_app/models.py

from django.db import models
from django.utils import timezone # Import timezone for default datetime

class Product(models.Model):
    # Unique identifier for the product
    id = models.CharField(max_length=50, primary_key=True)
    # Name of the product
    name = models.CharField(max_length=200)
    # Category of the product (e.g., Electronics, Groceries)
    category = models.CharField(max_length=100)
    # Current selling price of the product
    current_price = models.DecimalField(max_digits=10, decimal_places=2)
    # Suggested price from ML model (for dynamic pricing)
    suggested_price = models.DecimalField(max_digits=10, decimal_places=2)
    # Current inventory level
    inventory = models.IntegerField()
    # Forecasted demand for the next 7 days
    demand_forecast = models.IntegerField()
    # Number of units sold in the last 7 days (this will become a derived/summary field later)
    sales_last_7_days = models.IntegerField()
    # Profit margin (e.g., 0.35 for 35%)
    margin = models.DecimalField(max_digits=5, decimal_places=2)
    # Price of the product from a competitor
    competitor_price = models.DecimalField(max_digits=10, decimal_places=2)
    # Timestamp of the last update to this product record
    last_updated = models.DateTimeField(auto_now=True) # Automatically updates on each save

    def __str__(self):
        """String representation of the Product object."""
        return self.name

    class Meta:
        """Meta options for the Product model."""
        verbose_name_plural = "Products" # Makes the model name plural in Django Admin


class ProductDailyRecord(models.Model):
    """
    Stores daily historical data for each product.
    This will allow for detailed trend analysis and better ML model training.
    """
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='daily_records')
    date = models.DateField(default=timezone.now) # Date of the record
    sales_units = models.IntegerField(default=0) # Units sold on this specific day
    inventory_level = models.IntegerField(default=0) # Inventory level at end of day
    price_at_day_end = models.DecimalField(max_digits=10, decimal_places=2, default=0.00) # Price at end of day

    class Meta:
        """Meta options for the ProductDailyRecord model."""
        unique_together = ('product', 'date') # Ensure only one record per product per day
        ordering = ['date'] # Order records by date by default
        verbose_name_plural = "Product Daily Records"

    def __str__(self):
        return f"{self.product.name} on {self.date}: Sales={self.sales_units}, Inv={self.inventory_level}"
