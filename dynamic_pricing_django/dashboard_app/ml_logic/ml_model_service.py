# dashboard_app/ml_logic/ml_model_service.py

import random
from decimal import Decimal
import os
import joblib # For saving and loading scikit-learn models
import numpy as np
from sklearn.linear_model import LinearRegression # Our simple ML model

# Define a path to save/load the trained model
MODEL_PATH = os.path.join(os.path.dirname(__file__), 'demand_forecast_model.joblib')

def train_demand_forecast_model(historical_data):
    """
    Trains a simple Linear Regression model for demand forecasting.
    In a real scenario, this would use more features and a more complex model.

    Args:
        historical_data (list of dict): List of historical records.
                                        Each dict should have 'sales_units' and 'demand_forecast'
                                        (or a target variable).
                                        For this simple model, we'll use sales_units as feature
                                        and a slightly adjusted version as target.
    Returns:
        sklearn.linear_model.LinearRegression: The trained model.
    """
    if not historical_data:
        print("No historical data available for training. Skipping model training.")
        return None

    # Prepare data for training: X (features), y (target)
    # For simplicity, let's assume we're predicting 'next day demand' based on 'today's sales'
    # In a real scenario, you'd have features like promotions, seasonality, etc.
    # Here, we'll just use sales_units to predict a slightly adjusted version of itself
    # to simulate a learning process.
    X = np.array([d['sales_units'] for d in historical_data]).reshape(-1, 1)
    # Simulate a target: next day demand is roughly current sales + some noise
    y = np.array([d['sales_units'] * random.uniform(0.95, 1.05) for d in historical_data])

    if X.shape[0] < 2: # Need at least 2 samples for LinearRegression
        print("Not enough historical data points to train the model. Skipping training.")
        return None

    model = LinearRegression()
    model.fit(X, y)
    print(f"Demand forecast model trained. Coefficients: {model.coef_}, Intercept: {model.intercept_}")
    return model

def load_or_train_model(historical_data=None, force_retrain=False):
    """
    Loads a pre-trained model or trains a new one if not found/forced.
    """
    model = None
    if os.path.exists(MODEL_PATH) and not force_retrain:
        try:
            model = joblib.load(MODEL_PATH)
            print(f"Loaded demand forecast model from {MODEL_PATH}")
        except Exception as e:
            print(f"Error loading model: {e}. Retraining model.")
            model = None # Force retraining if load fails

    if model is None and historical_data:
        print("Model not found or loading failed. Training new model...")
        model = train_demand_forecast_model(historical_data)
        if model:
            joblib.dump(model, MODEL_PATH)
            print(f"Trained and saved new model to {MODEL_PATH}")
    elif model is None and not historical_data:
        print("No historical data provided and no model found. Cannot train.")

    return model

def get_ml_predictions(product_data_list, historical_records_map):
    """
    Generates demand forecasts and suggested prices using a trained ML model.

    Args:
        product_data_list (list of dict): Current product data.
        historical_records_map (dict): A map of product_id to its list of historical daily records.

    Returns:
        list of dict: Predictions for each product.
    """
    predictions = []
    # Load or train the model using all available historical data
    all_historical_data = []
    for product_id in historical_records_map:
        all_historical_data.extend(historical_records_map[product_id])

    demand_model = load_or_train_model(all_historical_data)

    for product in product_data_list:
        product_id = product['id']
        sales_7_days = product['sales_last_7_days']
        current_price = product['current_price']
        competitor_price = product['competitor_price']
        margin = product['margin']

        # --- Demand Forecasting Logic (using ML model if available) ---
        new_demand_forecast = int(round(sales_7_days * random.uniform(0.9, 1.1))) # Fallback to old simulation
        if demand_model and sales_7_days is not None:
            try:
                # Predict demand based on sales_last_7_days as a feature
                # In a real model, you'd use more sophisticated features
                predicted_demand = demand_model.predict(np.array([[sales_7_days]]))
                new_demand_forecast = int(round(max(0, predicted_demand[0])))
                # Add some noise to the ML prediction for simulation realism
                new_demand_forecast = int(round(new_demand_forecast * random.uniform(0.95, 1.05)))
            except Exception as e:
                print(f"Error predicting demand for {product_id} with ML model: {e}. Using fallback simulation.")
                new_demand_forecast = int(round(sales_7_days * random.uniform(0.9, 1.1)))


        # --- Dynamic Pricing Logic (still simulated for now) ---
        min_acceptable_price = current_price / (Decimal('1') - margin)
        target_margin = Decimal('0.30')
        base_suggested_price = current_price

        if new_demand_forecast > sales_7_days * 1.1:
            base_suggested_price *= Decimal(str(random.uniform(1.01, 1.05)))
        elif new_demand_forecast < sales_7_days * 0.9:
            base_suggested_price *= Decimal(str(random.uniform(0.95, 0.99)))

        if competitor_price > 0 and abs(current_price - competitor_price) / current_price < Decimal('0.10'):
            base_suggested_price = (base_suggested_price + competitor_price) / Decimal('2')

        cost_of_goods = current_price * (Decimal('1') - margin)
        min_price_for_target_margin = cost_of_goods / (Decimal('1') - target_margin)

        new_suggested_price = max(base_suggested_price, min_price_for_target_margin)
        new_suggested_price = round(new_suggested_price, 2)

        predictions.append({
            'id': product_id,
            'new_demand_forecast': new_demand_forecast,
            'new_suggested_price': new_suggested_price
        })

    return predictions

if __name__ == '__main__':
    # Example usage for testing the service directly
    # To test, you'd need to simulate historical data
    sample_historical_data = [
        {'sales_units': 10}, {'sales_units': 12}, {'sales_units': 11},
        {'sales_units': 15}, {'sales_units': 13}, {'sales_units': 14},
    ]
    # Train and save a model
    model = train_demand_forecast_model(sample_historical_data)
    if model:
        joblib.dump(model, MODEL_PATH)

    # Now load and use it for predictions
    sample_products = [
        {'id': 'prod001', 'sales_last_7_days': 80, 'current_price': Decimal('129.99'), 'competitor_price': Decimal('135.00'), 'margin': Decimal('0.35')},
        {'id': 'prod002', 'sales_last_7_days': 30, 'current_price': Decimal('15.50'), 'competitor_price': Decimal('15.99'), 'margin': Decimal('0.20')},
    ]
    # Create a dummy historical_records_map for the get_ml_predictions function signature
    dummy_historical_map = {
        'prod001': [{'sales_units': 75}, {'sales_units': 82}],
        'prod002': [{'sales_units': 28}, {'sales_units': 31}],
    }
    simulated_predictions = get_ml_predictions(sample_products, dummy_historical_map)
    print("\nSimulated ML Predictions (using trained model if available):")
    for p in simulated_predictions:
        print(f"  Product ID: {p['id']}, Demand Forecast: {p['new_demand_forecast']}, Suggested Price: {p['new_suggested_price']}")
