# dashboard_app/views.py

from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponse # Import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
import json
from .models import Product, ProductDailyRecord
from decimal import Decimal
from datetime import date, timedelta, datetime
import random
import os

from django.core.management import call_command
from io import StringIO

# For Matplotlib plotting
import matplotlib
matplotlib.use('Agg') # Use 'Agg' backend for non-interactive plotting (important for server-side)
import matplotlib.pyplot as plt
import io # To save plot to a buffer


# Define the path where charts were previously saved (no longer directly saving here for dynamic charts)
# CHART_SAVE_DIR = os.path.join('static', 'charts')
# os.makedirs(os.path.join('dynamic_pricing_django', CHART_SAVE_DIR), exist_ok=True)


@login_required
def dashboard_view(request):
    """
    Renders the main dashboard page, fetching all product data and historical records.
    Requires user to be logged in.
    """
    products = Product.objects.all().order_by('name')

    products_for_template = []
    for product in products:
        low_stock_threshold = product.demand_forecast * Decimal('0.5')
        is_low_stock = product.inventory < low_stock_threshold and product.inventory > 0
        is_out_of_stock = product.inventory == 0

        today = date.today()
        seven_days_ago = today - timedelta(days=6)
        historical_records = product.daily_records.filter(date__range=[seven_days_ago, today]).order_by('date')

        historical_sales_map = {record.date.isoformat(): record.sales_units for record in historical_records}

        sales_data_for_chart = []
        for i in range(7):
            current_date = seven_days_ago + timedelta(days=i)
            sales_data_for_chart.append(historical_sales_map.get(current_date.isoformat(), 0))


        products_for_template.append({
            'id': product.id,
            'name': product.name,
            'category': product.category,
            'current_price': float(product.current_price),
            'suggested_price': float(product.suggested_price),
            'inventory': product.inventory,
            'demand_forecast': product.demand_forecast,
            'sales_last_7_days': product.sales_last_7_days,
            'margin': float(product.margin),
            'competitor_price': float(product.competitor_price),
            'last_updated': product.last_updated.isoformat(),
            'is_low_stock': is_low_stock,
            'is_out_of_stock': is_out_of_stock,
            'historical_sales_data': sales_data_for_chart,
        })

    return render(request, 'dashboard.html', {'products': products_for_template, 'user': request.user})

@login_required
def product_detail_view(request, product_id):
    """
    Renders the detail page for a single product.
    Fetches the product and its full historical data.
    Does NOT generate charts here; charts are generated via a separate API.
    Requires user to be logged in.
    """
    product = get_object_or_404(Product, id=product_id)

    # Prepare product data for template (no chart_urls needed here anymore)
    product_data = {
        'id': product.id,
        'name': product.name,
        'category': product.category,
        'current_price': float(product.current_price),
        'suggested_price': float(product.suggested_price),
        'inventory': product.inventory,
        'demand_forecast': product.demand_forecast,
        'sales_last_7_days': product.sales_last_7_days,
        'margin': float(product.margin),
        'competitor_price': float(product.competitor_price),
        'last_updated': product.last_updated.isoformat(),
        # 'history' data is not strictly needed by the template anymore if charts are API-driven,
        # but keeping it here for potential future client-side use or debugging.
        # The chart API will re-fetch history as needed.
    }

    return render(request, 'product_detail.html', {'product': product_data, 'user': request.user})


@login_required
def api_get_chart(request, product_id, chart_type):
    """
    API endpoint to generate and return a specific Matplotlib chart image.
    Requires user to be logged in.
    """
    product = get_object_or_404(Product, id=product_id)
    historical_records = product.daily_records.all().order_by('date')

    dates = [record.date for record in historical_records]
    sales_units = [record.sales_units for record in historical_records]
    inventory_levels = [record.inventory_level for record in historical_records]
    prices_at_day_end = [float(record.price_at_day_end) for record in historical_records]

    # Ensure there's enough data to plot
    if len(dates) < 2: # Need at least two points to draw a line
        # Return a placeholder or empty image if not enough data
        # For simplicity, we'll return a blank image or 404
        # In a real app, you might serve a "no data" image.
        return HttpResponse(status=204) # 204 No Content

    plt.figure(figsize=(10, 5)) # Consistent figure size
    plt.xticks(rotation=45, ha='right') # Rotate date labels for readability
    plt.tight_layout() # Adjust layout to prevent labels overlapping

    if chart_type == 'sales':
        plt.plot(dates, sales_units, marker='o', linestyle='-', color='#4BC0C0') # Teal
        plt.title(f'{product.name} - Daily Sales History')
        plt.xlabel('Date')
        plt.ylabel('Units Sold')
        plt.grid(True)
    elif chart_type == 'price':
        plt.plot(dates, prices_at_day_end, marker='o', linestyle='-', color='#9966FF') # Purple
        plt.title(f'{product.name} - Daily Price History')
        plt.xlabel('Date')
        plt.ylabel('Price ($)')
        plt.grid(True)
    elif chart_type == 'inventory':
        plt.plot(dates, inventory_levels, marker='o', linestyle='-', color='#FF6384') # Red
        plt.title(f'{product.name} - Daily Inventory History')
        plt.xlabel('Date')
        plt.ylabel('Units')
        plt.grid(True)
    else:
        return HttpResponse(status=404, content="Chart type not found.")

    # Save plot to a BytesIO object (in-memory buffer)
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0) # Rewind the buffer to the beginning
    plt.close() # Close the plot to free memory

    return HttpResponse(buffer.getvalue(), content_type='image/png')


@csrf_exempt
@login_required
def api_update_product(request):
    """
    API endpoint to update a product's price or inventory.
    Requires user to be logged in.
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            product_id = data.get('id')
            product = Product.objects.get(id=product_id)

            if 'currentPrice' in data:
                product.current_price = Decimal(str(data['currentPrice']))
            if 'inventory' in data:
                product.inventory = int(data['inventory'])

            product.save()

            today = date.today()
            simulated_daily_sales = max(0, int(round(product.sales_last_7_days / 7 * random.uniform(0.8, 1.2))))
            ProductDailyRecord.objects.update_or_create(
                product=product,
                date=today,
                defaults={
                    'sales_units': simulated_daily_sales,
                    'inventory_level': product.inventory, # Update inventory level in daily record
                    'price_at_day_end': product.current_price # Update price in daily record
                }
            )

            updated_product_data = {
                'id': product.id,
                'name': product.name,
                'category': product.category,
                'currentPrice': float(product.current_price),
                'suggestedPrice': float(product.suggested_price),
                'inventory': product.inventory,
                'demandForecast': product.demand_forecast,
                'salesLast7Days': product.sales_last_7_days,
                'margin': float(product.margin),
                'competitorPrice': float(product.competitor_price),
                'lastUpdated': product.last_updated.isoformat(),
            }
            return JsonResponse({'status': 'success', 'message': f'Product {product_id} updated successfully.', 'product': updated_product_data})
        except Product.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Product not found.'}, status=404)
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON in request body.'}, status=400)
        except ValueError as ve:
            return JsonResponse({'status': 'error', 'message': f'Invalid data type: {str(ve)}'}, status=400)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'An unexpected error occurred: {str(e)}'}, status=500)
    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=405)


@login_required
@csrf_exempt
def api_run_ml_predictions(request):
    """
    API endpoint to trigger the ML prediction management command.
    Requires user to be logged in.
    """
    if request.method == 'POST':
        try:
            out = StringIO()
            call_command('run_ml_predictions', stdout=out)
            command_output = out.getvalue()

            return JsonResponse({'status': 'success', 'message': 'ML predictions triggered successfully.', 'output': command_output})
        except CommandError as ce:
            return JsonResponse({'status': 'error', 'message': f'Error running ML command: {ce}', 'output': str(ce)}, status=500)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'An unexpected error occurred: {e}', 'output': str(e)}, status=500)
    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=405)

@login_required
@csrf_exempt
def api_add_historical_record(request):
    """
    API endpoint to add or update a historical daily record for a product.
    Expects POST request with product_id, date (YYYY-MM-DD), and sales_units.
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            product_id = data.get('product_id')
            record_date_str = data.get('date')
            sales_units = data.get('sales_units')

            if not all([product_id, record_date_str, sales_units is not None]):
                return JsonResponse({'status': 'error', 'message': 'Missing data (product_id, date, or sales_units).'}, status=400)

            product = get_object_or_404(Product, id=product_id)
            record_date = datetime.strptime(record_date_str, '%Y-%m-%d').date()
            sales_units = int(sales_units)

            if sales_units < 0:
                return JsonResponse({'status': 'error', 'message': 'Sales units cannot be negative.'}, status=400)

            # When manually adding historical sales, we might not have inventory/price for that specific historical day.
            # We'll use the current inventory and price of the product as a fallback if not provided,
            # or you could add fields to the form to capture them.
            # For now, we'll use current values if the record is being created for today.
            # If for a past date, these might be 0 or default values unless explicitly provided.
            current_inventory_for_record = product.inventory
            current_price_for_record = product.current_price

            daily_record, created = ProductDailyRecord.objects.update_or_create(
                product=product,
                date=record_date,
                defaults={
                    'sales_units': sales_units,
                    'inventory_level': current_inventory_for_record, # Log current inventory with historical sales
                    'price_at_day_end': current_price_for_record # Log current price with historical sales
                }
            )
            action = "created" if created else "updated"
            return JsonResponse({'status': 'success', 'message': f'Historical record for {product.name} on {record_date} {action} successfully.'})

        except Product.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Product not found.'}, status=404)
        except ValueError as ve:
            return JsonResponse({'status': 'error', 'message': f'Invalid data format: {str(ve)}. Date must be YYYY-MM-DD, sales_units must be integer.'}, status=400)
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON in request body.'}, status=400)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'An unexpected error occurred: {str(e)}'}, status=500)
    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=405)
