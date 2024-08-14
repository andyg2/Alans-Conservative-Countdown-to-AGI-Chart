import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from sklearn.preprocessing import PolynomialFeatures
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score
from bs4 import BeautifulSoup
import requests
import json
import re

def scrape_agi_data(url):
    # Fetch the webpage content
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')

    # Find all tables with the specified class
    tables = soup.find_all('table', class_='table table-striped table-hover table-sm')

    data = []

    for table in tables:
        # Check if this table contains <kbd> tags
        if table.find('kbd'):
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all('td')
                if len(cells) >= 2:
                    date_cell = cells[0].text.strip()
                    percentage_cell = cells[1]
                    
                    # Extract date
                    date_match = re.search(r'(\w+)/(\d{4})', date_cell)
                    if date_match:
                        month, year = date_match.groups()
                        date_obj = datetime.strptime(f"{month} {year}", "%b %Y")
                        formatted_date = date_obj.strftime("%Y-%m")
                    else:
                        continue  # Skip this row if date format doesn't match

                    # Extract percentage
                    kbd_tag = percentage_cell.find('kbd')
                    if kbd_tag:
                        percentage = kbd_tag.text.strip('%')
                        data.append({"date": formatted_date, "percentage": int(percentage)})

    return data

# URL of the webpage to scrape
url = "https://lifearchitect.ai/agi/"

# Scrape the data
scraped_data = scrape_agi_data(url)

# Sort the data by date (most recent first)
agi_data = sorted(scraped_data, key=lambda x: x['date'], reverse=True)

# Convert JSON data to DataFrame
df = pd.DataFrame(agi_data)
df['Date'] = pd.to_datetime(df['date'])
df['Percentage'] = df['percentage'].astype(float) / 100.0
df = df.sort_values('Date')
df['Days'] = (df['Date'] - df['Date'].min()).dt.days

# Polynomial Regression (degree 2)
poly_features = PolynomialFeatures(degree=2, include_bias=False)
X = df[['Days']]
X.columns = ['Days']  # Explicitly set feature name
X_poly = poly_features.fit_transform(X)
feature_names = poly_features.get_feature_names_out(['Days'])
X_poly_df = pd.DataFrame(X_poly, columns=feature_names)

poly_reg = LinearRegression()
poly_reg.fit(X_poly_df, df['Percentage'])
poly_pred = poly_reg.predict(X_poly_df)
poly_r2 = r2_score(df['Percentage'], poly_pred)

# Predict 100% date
def predict_100(model, poly_features):
    days = np.arange(df['Days'].max(), df['Days'].max() + 1000)
    X_future = pd.DataFrame(days, columns=['Days'])
    X_future_poly = pd.DataFrame(
        poly_features.transform(X_future), 
        columns=poly_features.get_feature_names_out(['Days'])
    )
    pred = model.predict(X_future_poly)
    if any(pred >= 1):
        return df['Date'].min() + timedelta(days=int(days[pred >= 1][0]))
    return None

poly_100 = predict_100(poly_reg, poly_features)

# Plotting
plt.figure(figsize=(12, 6))
plt.scatter(df['Date'], df['Percentage'], color='blue', label='Actual Data')
plt.plot(df['Date'], poly_pred, color='green', label=f'Polynomial (R² = {poly_r2:.3f})')

# Extend prediction
future_dates = pd.date_range(start=df['Date'].max(), end=poly_100 + timedelta(days=30), freq='D')
future_days = (future_dates - df['Date'].min()).days.values
future_X = pd.DataFrame(future_days, columns=['Days'])
future_X_poly = pd.DataFrame(
    poly_features.transform(future_X),
    columns=poly_features.get_feature_names_out(['Days'])
)
future_pred = poly_reg.predict(future_X_poly)
plt.plot(future_dates, future_pred, color='green', linestyle='--')

plt.axhline(y=1, color='purple', linestyle='--', label='100% Target')

# Add 100% date indicator
if poly_100:
    plt.axvline(x=poly_100, color='red', linestyle=':', label='100% Date')
    plt.plot(poly_100, 1, 'ro')  # Red dot at intersection
    plt.annotate(f'100% on {poly_100.strftime("%Y-%m-%d")}', 
                 xy=(poly_100, 1), xytext=(10, -10),
                 textcoords='offset points', ha='left', va='top',
                 bbox=dict(boxstyle='round,pad=0.5', fc='yellow', alpha=0.5),
                 arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0'))
# Print results
print(f"Polynomial Regression 100% Date: {poly_100.strftime('%B %d, %Y') if poly_100 else 'Not reached'}")
print(f"R-squared value: {poly_r2:.3f}")

# Print the most recent data point
latest_data = df.iloc[-1]
print(f"\nMost recent data point:")
print(f"Date: {latest_data['Date'].strftime('%B %d, %Y')}")
print(f"Percentage: {latest_data['Percentage']*100:.1f}%")

plt.title('AGI Progression to 100% - Polynomial Model')
plt.xlabel('Date')
plt.ylabel('Percentage')
plt.legend()
plt.grid(True)
plt.gcf().autofmt_xdate()
plt.tight_layout()
plt.show()

