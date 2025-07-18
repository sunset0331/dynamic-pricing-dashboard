# dashboard_app/management/commands/run_ml_predictions.py

from django.core.management.base import BaseCommand, CommandError
from dashboard_app.models import Product, ProductDailyRecord
from dashboard_app.ml_logic.ml_model_service import get_ml_predictions, load_or_train_model # Import new functions
from decimal import Decimal
import random
from datetime import date, timedelta

class Command(BaseCommand):
    help = 'Runs the ML prediction models and logs daily product data.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--retrain',
            action='store_true',
            help='Force retraining of the ML model before making predictions.',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting ML prediction and daily data logging...'))

        # 1. Fetch all product data needed by the ML model
        products_for_ml = []
        for product in Product.objects.all():
            products_for_ml.append({
                'id': product.id,
                'sales_last_7_days': product.sales_last_7_days,
                'current_price': product.current_price,
                'competitor_price': product.competitor_price,
                'margin': product.margin,
            })

        if not products_for_ml:
            self.stdout.write(self.style.WARNING('No products found in the database to run predictions on.'))
            return

        # 2. Fetch all historical data for model training/prediction
        # Group historical records by product ID
        historical_records_map = {}
        for product in Product.objects.all():
            # Fetch all historical records for each product for training
            # You might want to limit this to a certain period (e.g., last year) for large datasets
            records = product.daily_records.all().order_by('date').values('sales_units', 'inventory_level', 'price_at_day_end')
            historical_records_map[product.id] = list(records)

        # 3. Call the ML service to get predictions
        try:
            # Pass historical_records_map to the prediction function
            predictions = get_ml_predictions(products_for_ml, historical_records_map)
            self.stdout.write(self.style.SUCCESS(f'Generated predictions for {len(predictions)} products.'))
        except Exception as e:
            raise CommandError(f'Error during ML prediction: {e}')

        # 4. Update Product objects in the database with new predictions
        updated_count = 0
        logged_count = 0
        today = date.today()

        for prediction in predictions:
            try:
                product = Product.objects.get(id=prediction['id'])

                # Update Product object with new ML predictions
                product.demand_forecast = prediction['new_demand_forecast']
                product.suggested_price = prediction['new_suggested_price']
                product.save()
                updated_count += 1

                # Log Daily Record (simulate daily sales for today's record)
                # This sales_units value could also come from a real data source or another ML model
                simulated_daily_sales = max(0, int(round(product.sales_last_7_days / 7 * random.uniform(0.8, 1.2))))

                daily_record, created = ProductDailyRecord.objects.update_or_create(
                    product=product,
                    date=today,
                    defaults={
                        'sales_units': simulated_daily_sales,
                        'inventory_level': product.inventory,
                        'price_at_day_end': product.current_price
                    }
                )
                if created:
                    self.stdout.write(self.style.SUCCESS(f'  Created new daily record for {product.name} on {today}.'))
                else:
                    self.stdout.write(self.style.SUCCESS(f'  Updated daily record for {product.name} on {today}.'))
                logged_count += 1

            except Product.DoesNotExist:
                self.stdout.write(self.style.WARNING(f'Product with ID {prediction["id"]} not found in DB. Skipping update and logging.'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Failed to update product or log daily record for {prediction["id"]}: {e}'))

        self.stdout.write(self.style.SUCCESS(f'Successfully updated {updated_count} products with new ML predictions.'))
        self.stdout.write(self.style.SUCCESS(f'Successfully logged {logged_count} daily records.'))

        # --- Optional: Populate historical data for the last few days for better charts ---
        # This part ensures some initial historical data for training and charts
        self.stdout.write(self.style.HTTP_INFO('Populating simulated historical data for the last 7 days (if not present)...'))
        for product in Product.objects.all():
            for i in range(1, 8): # For last 7 days (Day -1 to Day -7)
                past_date = today - timedelta(days=i)
                if not ProductDailyRecord.objects.filter(product=product, date=past_date).exists():
                    simulated_past_sales = max(0, int(round(product.sales_last_7_days / 7 * random.uniform(0.7, 1.3))))
                    simulated_past_inventory = max(0, product.inventory + random.randint(-20, 20))
                    simulated_past_price = product.current_price * Decimal(str(random.uniform(0.98, 1.02)))
                    ProductDailyRecord.objects.create(
                        product=product,
                        date=past_date,
                        sales_units=simulated_past_sales,
                        inventory_level=simulated_past_inventory,
                        price_at_day_end=round(simulated_past_price, 2)
                    )
                    self.stdout.write(self.style.HTTP_INFO(f'  Added historical record for {product.name} on {past_date}.'))
        self.stdout.write(self.style.SUCCESS('Finished populating historical data.'))
