# Financial Data Pipeline Technical Overview

## Architecture/Flow Review, Data Loading Mechanics, and Transformation

### 1. Overall Architecture
The system follows a multi-layered architecture:
```
Data Sources → Data Pipeline → Database → Web Application
     ↓              ↓            ↓            ↓
   FDIC          Airflow    PostgreSQL     Django
   NCUA          Redis                    REST API
                                      Chat Interface
```

### 2. Data Loading Flow

#### Data Source Integration
- **FDIC Data Collection**:
  ```python
  def check_fdic_data():
      """Checks FDIC website for updates using BeautifulSoup"""
      url = "https://www.fdic.gov/resources/data-tools/"
      response = requests.get(url)
      # Implements idempotency through content hash checking
      return check_content_hash(response.content)
  ```

- **NCUA Data Collection**:
  ```python
  def check_ncua_data():
      """Scrapes NCUA website for new data"""
      url = "https://www.ncua.gov/analysis/credit-union-corporate-call-report-data"
      response = requests.get(url)
      # Implements idempotency through last-modified checking
      return check_last_modified(response.headers)
  ```

#### Airflow DAG Orchestration
```python
# refresh_financial_data_dag.py
dag = DAG(
    'refresh_financial_data',
    schedule_interval='0 6 * * *',  # Daily at 6 AM
    default_args={
        'retries': 1,
        'retry_delay': timedelta(minutes=5),
        'email_on_failure': True
    }
)

# Task Dependencies
start >> [check_fdic, check_ncua] >> generate_report >> cleanup >> end
```

### 3. Key Data Models

#### Financial Institution Model
```python
class FinancialInstitution(models.Model):
    INSTITUTION_TYPES = [
        ('BANK', 'Bank'),
        ('CREDIT_UNION', 'Credit Union')
    ]
    
    ASSET_TIERS = [
        ('<$100M', 'Less than $100M'),
        ('$100M-$1B', '$100M to $1B'),
        ('$1B-$10B', '$1B to $10B'),
        ('>$10B', 'Greater than $10B')
    ]
    
    institution_type = models.CharField(choices=INSTITUTION_TYPES)
    charter_number = models.CharField(unique=True)
    asset_tier = models.CharField(choices=ASSET_TIERS)
    city = models.CharField()
    state = models.CharField()
    web_domain = models.URLField()
```

#### Quarterly Stats Model
```python
class QuarterlyStats(models.Model):
    institution = models.ForeignKey(FinancialInstitution)
    quarter_end_date = models.DateField()
    total_assets = models.DecimalField()
    total_deposits = models.DecimalField()
    deposit_change_pct = models.DecimalField()
    
    class Meta:
        unique_together = ['institution', 'quarter_end_date']
```

### 4. Data Transformation Process

#### Data Cleaning
```python
def clean_financial_data(df):
    """Cleans and standardizes financial data"""
    # Remove invalid entries
    df = df.dropna(subset=['charter_number', 'total_assets'])
    
    # Standardize numeric fields
    df['total_assets'] = pd.to_numeric(df['total_assets'], errors='coerce')
    df['total_deposits'] = pd.to_numeric(df['total_deposits'], errors='coerce')
    
    return df
```

#### Asset Tier Classification
```python
def calculate_asset_tier(assets):
    """Determines asset tier based on total assets"""
    if assets >= 10_000_000_000:  # $10B+
        return '>$10B'
    elif assets >= 1_000_000_000:  # $1B-$10B
        return '$1B-$10B'
    elif assets >= 100_000_000:    # $100M-$1B
        return '$100M-$1B'
    else:
        return '<$100M'
```

### 5. Data Loading Mechanics

#### Idempotent Processing
```python
def load_institution_data(data):
    """Loads institution data with idempotency"""
    with transaction.atomic():
        institution, created = FinancialInstitution.objects.update_or_create(
            charter_number=data['charter_number'],
            defaults={
                'institution_type': data['type'],
                'asset_tier': calculate_asset_tier(data['total_assets']),
                'city': data['city'],
                'state': data['state']
            }
        )
        return institution
```

#### Batch Processing
```python
def batch_load_quarterly_stats(stats_data):
    """Processes quarterly stats in batches"""
    BATCH_SIZE = 1000
    
    for i in range(0, len(stats_data), BATCH_SIZE):
        batch = stats_data[i:i + BATCH_SIZE]
        QuarterlyStats.objects.bulk_create(batch)
```

### 6. Data Quality Assurance

#### Validation Checks
```python
def validate_financial_data(df):
    """Validates financial data quality"""
    validation_results = {
        'missing_fields': df.isnull().sum().to_dict(),
        'negative_assets': (df['total_assets'] < 0).sum(),
        'duplicate_charters': df['charter_number'].duplicated().sum()
    }
    
    return validation_results
```

#### Data Quality Monitoring
```sql
-- Monitor data completeness
SELECT 
    COUNT(*) as total_records,
    COUNT(CASE WHEN total_assets IS NOT NULL THEN 1 END) as valid_assets,
    COUNT(CASE WHEN total_deposits IS NOT NULL THEN 1 END) as valid_deposits
FROM quarterly_stats
WHERE quarter_end_date = CURRENT_DATE;
```

### 7. Performance Optimization

#### Database Indexing
```sql
-- Optimize common queries
CREATE INDEX idx_institution_assets ON financial_institutions(asset_tier, total_assets);
CREATE INDEX idx_quarterly_date ON quarterly_stats(quarter_end_date);
```

#### Caching Strategy
```python
# Cache expensive computations
@cache_page(60 * 15)  # Cache for 15 minutes
def get_institution_summary(request):
    summary = FinancialInstitution.objects.aggregate(
        total_count=Count('id'),
        total_assets=Sum('total_assets'),
        avg_deposits=Avg('total_deposits')
    )
    return JsonResponse(summary)
```

### 8. Monitoring and Maintenance

#### Performance Monitoring
```python
def log_performance_metrics():
    """Logs key performance metrics"""
    metrics = {
        'load_time': measure_load_time(),
        'processing_time': measure_processing_time(),
        'memory_usage': get_memory_usage(),
        'db_connections': get_db_connection_count()
    }
    logger.info(f"Performance metrics: {metrics}")
```

#### Cleanup Procedures
```python
def cleanup_old_reports():
    """Removes reports older than 30 days"""
    cutoff_date = datetime.now() - timedelta(days=30)
    old_reports = Report.objects.filter(created_at__lt=cutoff_date)
    old_reports.delete()
``` 