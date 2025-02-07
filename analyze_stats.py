import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Read the data
df = pd.read_csv('data/fdic_data_with_changes.csv')

# Asset Tier Analysis
print("\nAsset Tier Statistics:")
print("----------------------")
tier_stats = df.groupby('asset_tier').agg({
    'ASSET': ['count', 'mean', 'median', 'min', 'max'],
    'DEPDOM': ['mean', 'sum'],
    'deposit_change_pct': ['mean', 'min', 'max']
}).round(2)

print(tier_stats)

# Create visualizations directory if it doesn't exist
import os
os.makedirs('dashboard/static/visualizations', exist_ok=True)

# Asset Distribution by Tier
plt.figure(figsize=(12, 6))
sns.boxplot(data=df, x='asset_tier', y='ASSET')
plt.xticks(rotation=45)
plt.title('Asset Distribution by Tier')
plt.tight_layout()
plt.savefig('dashboard/static/visualizations/asset_distribution.png')
plt.close()

# Deposit Changes by Tier
plt.figure(figsize=(12, 6))
sns.boxplot(data=df, x='asset_tier', y='deposit_change_pct')
plt.xticks(rotation=45)
plt.title('Deposit Changes by Tier')
plt.tight_layout()
plt.savefig('dashboard/static/visualizations/deposit_changes.png')
plt.close()

# Correlation between Assets and Deposits
plt.figure(figsize=(10, 6))
plt.scatter(df['ASSET'], df['DEPDOM'])
plt.xlabel('Assets')
plt.ylabel('Deposits')
plt.title('Assets vs Deposits Correlation')
plt.tight_layout()
plt.savefig('dashboard/static/visualizations/asset_deposit_correlation.png')
plt.close()

# Save summary statistics to CSV
tier_stats.to_csv('dashboard/static/visualizations/tier_statistics.csv')

print("\nVisualization files have been saved to dashboard/static/visualizations/") 