# Import Libraries
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from lightgbm import LGBMRegressor
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error
from sklearn.model_selection import train_test_split, GridSearchCV, cross_val_score
from sklearn.preprocessing import MinMaxScaler

# ===============================
# 1. DATA LOADING AND PREPARATION
# ===============================
# File Loading
df_weather = pd.read_csv("../resources/df_weather_cleaned.csv")
df_sales = pd.read_csv("../resources/fact_sales.csv")
df_dates = pd.read_csv("../resources/dim_date.csv")

# Merge sales with dates to add temporal variables
df_sales = df_sales.merge(df_dates, left_on="created_date_key", right_on="surrogate_key", how="left")

# Average weather per day (national average)
df_weather_avg = df_weather.groupby('date')[['TMAX_C', 'TMIN_C', 'PRCP_MM']].mean().reset_index()

# Ensure date formats
df_sales['date'] = pd.to_datetime(df_sales['date'])
df_weather_avg['date'] = pd.to_datetime(df_weather_avg['date'])

# Merge sales with weather
df = df_sales.merge(df_weather_avg, on='date', how='left')

# ===============================
# 2. VARIABLE CLEANING AND SELECTION
# ===============================

# Remove unnecessary columns
columns_to_drop = [
    'fact_sales_id', 'product_key', 'business_partner_key', 'created_date_key',
    'modified_date_key', 'employee_key', 'order_id', 'item_id',
    'sls_order_product_id', 'order_created_by', 'order_created_at',
    'order_changed_by', 'order_changed_at', 'order_fiscal_variant',
    'order_fiscal_year_period', 'order_partner_id', 'order_org', 'currency',
    'order_gross_amount', 'order_net_amount', 'order_tax_amount',
    'lifecycle_status', 'billing_status', 'delivery_status', 'dwh_create_date',
    'surrogate_key', 'date_type', 'date_id', 'month_name', 'weekday_name',
    'quarter', 'date'
]
df.drop(columns=[col for col in columns_to_drop if col in df.columns], inplace=True)

# ===============================
# 3. FEATURES & TARGET
# ===============================

# Define the predictor variables (X) and the target variable (y)
X = df[['TMAX_C', 'TMIN_C', 'PRCP_MM', 'year', 'month', 'day', 'day_of_week', 'is_weekend']]
y = df['total_price']

# ===============================
# 4. NORMALIZATION
# ===============================

# Scale the features between 0 and 1 to improve model performance
scaler = MinMaxScaler()
X_scaled = scaler.fit_transform(X)

# ===============================
# 5. BASIC TRAINING AND EVALUATION
# ===============================

# Split the dataset into training and testing sets (80/20)
X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.2, random_state=18)

# Baseline LGBMRegressor model
model = LGBMRegressor(random_state=18)
model.fit(X_train, y_train)

# Predictions and evaluation
y_pred = model.predict(X_test)

rmse = np.sqrt(mean_squared_error(y_test, y_pred))
r2 = r2_score(y_test, y_pred)
mae = mean_absolute_error(y_test, y_pred)

print(f"LightGBM Base RMSE: {rmse:.2f}")
print(f"LightGBM Base R2 Score: {r2:.4f}")
print(f"LightGBM Base MAE: {mae:.2f}")

# ===============================
# 6. GRID SEARCH OPTIMIZATION
# ===============================

# Define the hyperparameter grid to optimize the model
param_grid = {
    'n_estimators': [100, 200, 300],
    'max_depth': [3, 5, 7, -1],
    'learning_rate': [0.05, 0.1, 0.2],
    'subsample': [0.8, 1.0],
    'colsample_bytree': [0.8, 1.0]
}

# Configure GridSearchCV with cross-validation
grid_search = GridSearchCV(
    estimator=LGBMRegressor(random_state=18),
    param_grid=param_grid,
    cv=5,
    scoring='neg_root_mean_squared_error',
    n_jobs=-1, # Use all CPU
    verbose=1
)

grid_search.fit(X_train, y_train)# Training with all parameter combinations

# Retrieve the best model found
best_model = grid_search.best_estimator_
print("✅ Best LightGBM parameters:", grid_search.best_params_)

# Final evaluation
y_pred = best_model.predict(X_test)

rmse = np.sqrt(mean_squared_error(y_test, y_pred))
r2 = r2_score(y_test, y_pred)
mae = mean_absolute_error(y_test, y_pred)

print(f"Optimized LightGBM RMSE: {rmse:.2f}")
print(f"Optimized LightGBM R2 Score: {r2:.4f}")
print(f"Optimized LightGBM MAE: {mae:.2f}")

# ===============================
# 7. CROSS-VALIDATION
# ===============================

# Cross-validation RMSE
cv_rmse_scores = cross_val_score(best_model, X_scaled, y, cv=5, scoring='neg_root_mean_squared_error')
cv_rmse = -cv_rmse_scores
print(f"LightGBM Cross-Validation RMSE scores: {cv_rmse}")
print(f"LightGBM Mean CV RMSE: {cv_rmse.mean():.2f}")
print(f"LightGBM Std CV RMSE: {cv_rmse.std():.2f}")

# Cross-validation MAE
cv_mae_scores = cross_val_score(best_model, X_scaled, y, cv=5, scoring='neg_mean_absolute_error')
cv_mae = -cv_mae_scores
print(f"LightGBM Cross-Validation MAE scores: {cv_mae}")
print(f"LightGBM Mean CV MAE: {cv_mae.mean():.2f}")
print(f"LightGBM Std CV MAE: {cv_mae.std():.2f}")

# ===============================
# 8. VISUALIZATIONS
# ===============================

# Feature importance
importances = pd.Series(best_model.feature_importances_, index=X.columns).sort_values(ascending=True)
plt.figure(figsize=(8, 5))
importances.plot(kind='barh')
plt.title("LightGBM - Feature Importance")
plt.tight_layout()
plt.show()

# Real vs Predicted
plt.figure(figsize=(6, 6))
sns.scatterplot(x=y_test, y=y_pred, alpha=0.6)
plt.plot([y_test.min(), y_test.max()], [y_test.min(), y_test.max()], 'r--')
plt.xlabel("Actual Orders")
plt.ylabel("Predicted Orders")
plt.title("LightGBM - Actual vs Predicted")
plt.grid(True)
plt.tight_layout()
plt.show()

# Residuals
residuals = y_test - y_pred
plt.figure(figsize=(8, 5))
sns.histplot(residuals, kde=True, bins=30, color="skyblue")
plt.axvline(0, color='black', linestyle='--')
plt.title("LightGBM - Residual Distribution")
plt.xlabel("Residual Error = Actual - Predicted")
plt.grid(True)
plt.tight_layout()
plt.show()

# Create results summary DataFrame
results = pd.DataFrame({
    'Model': ['Base', 'Optimized'],
    'RMSE': [np.sqrt(mean_squared_error(y_test, model.predict(X_test))), rmse],
    'R2': [r2_score(y_test, model.predict(X_test)), r2],
    'MAE': [mean_absolute_error(y_test, model.predict(X_test)), mae]
})

print(results)
