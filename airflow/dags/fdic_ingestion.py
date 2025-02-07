"""
Author: Xiaoting Kuang
FDIC data ingestion module for collecting and processing bank data.
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.dummy import DummyOperator
import requests
import pandas as pd
import json
import os
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

# FDIC API Configuration
FDIC_API_BASE_URL = "https://banks.data.fdic.gov/api"
FDIC_INSTITUTIONS_ENDPOINT = "/institutions"
FDIC_HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json"
}

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
}

def fetch_fdic_data(**context) -> str:
    """
    Fetch bank data from FDIC API with pagination and error handling
    """
    logger.info("Starting FDIC data fetch")
    
    params = {
        'filters': 'ACTIVE:1',  # Only active institutions
        'fields': 'NAME,CERT,WEBADDR,CITY,STNAME,ASSET,DEP,DEPDOM,BKCLASS,STALP,ZIP',
        'limit': 1000,
        'offset': 0,
        'sort_by': 'NAME',
        'sort_order': 'ASC'
    }
    
    all_data = []
    total_fetched = 0
    
    try:
        while True:
            logger.info(f"Fetching FDIC data with offset {params['offset']}")
            response = requests.get(
                f"{FDIC_API_BASE_URL}{FDIC_INSTITUTIONS_ENDPOINT}",
                params=params,
                headers=FDIC_HEADERS,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            if not data.get('data'):
                break
                
            institutions = data['data']
            all_data.extend(institutions)
            total_fetched += len(institutions)
            
            logger.info(f"Fetched {len(institutions)} institutions. Total: {total_fetched}")
            
            if len(institutions) < params['limit']:
                break
                
            params['offset'] += params['limit']
            
        # Save raw data
        output_path = f"/opt/airflow/data/raw/fdic_{context['ds']}.json"
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(all_data, f)
        
        logger.info(f"Successfully saved {total_fetched} institutions to {output_path}")
        return output_path
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching FDIC data: {str(e)}")
        raise

def transform_fdic_data(**context) -> str:
    """
    Transform FDIC data into standardized format with data validation
    """
    logger.info("Starting FDIC data transformation")
    input_path = context['task_instance'].xcom_pull(task_ids='fetch_fdic_data')
    
    with open(input_path, 'r') as f:
        data = json.load(f)
    
    transformed_data = []
    for bank in data:
        try:
            # Convert assets and deposits to float, handling any formatting issues
            assets = float(bank.get('ASSET', 0))
            deposits = float(bank.get('DEP', 0))
            domestic_deposits = float(bank.get('DEPDOM', 0))
            
            # Determine asset tier
            asset_tier = get_asset_tier(assets)
            
            transformed_bank = {
                'institution_type': 'BANK',
                'charter_number': str(bank.get('CERT', '')),
                'name': bank.get('NAME', ''),
                'web_domain': bank.get('WEBADDR', ''),
                'city': bank.get('CITY', ''),
                'state': bank.get('STALP', ''),
                'zip_code': bank.get('ZIP', ''),
                'bank_class': bank.get('BKCLASS', ''),
                'total_assets': assets,
                'total_deposits': deposits,
                'domestic_deposits': domestic_deposits,
                'asset_tier': asset_tier,
                'data_date': context['ds']
            }
            transformed_data.append(transformed_bank)
            
        except (ValueError, TypeError) as e:
            logger.warning(f"Error transforming bank data {bank.get('CERT')}: {str(e)}")
            continue
    
    # Save transformed data
    output_path = f"/opt/airflow/data/processed/fdic_{context['ds']}.json"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(transformed_data, f)
    
    logger.info(f"Successfully transformed {len(transformed_data)} institutions")
    return output_path

def get_asset_tier(assets: float) -> str:
    """
    Determine asset tier based on total assets
    """
    if assets < 100_000_000:  # Less than $100M
        return '<$100M'
    elif assets < 500_000_000:  # $100M to $500M
        return '$100M-$500M'
    elif assets < 1_000_000_000:  # $500M to $1B
        return '$500M-$1B'
    elif assets < 10_000_000_000:  # $1B to $10B
        return '$1B-$10B'
    else:  # Greater than $10B
        return '>$10B'

def load_to_database(**context):
    """
    Load transformed data into the database using Django models
    """
    logger.info("Starting database load")
    input_path = context['task_instance'].xcom_pull(task_ids='transform_fdic_data')
    
    with open(input_path, 'r') as f:
        data = json.load(f)
    
    from django.db import transaction
    from prospects.models import FinancialInstitution, QuarterlyStats
    from django.utils import timezone
    
    stats_date = timezone.now().date()
    stats_created = 0
    institutions_created = 0
    institutions_updated = 0
    
    try:
        with transaction.atomic():
            for bank_data in data:
                # Get or create the financial institution
                institution, created = FinancialInstitution.objects.update_or_create(
                    charter_number=bank_data['charter_number'],
                    defaults={
                        'institution_type': bank_data['institution_type'],
                        'web_domain': bank_data['web_domain'],
                        'city': bank_data['city'],
                        'state': bank_data['state'],
                        'asset_tier': bank_data['asset_tier']
                    }
                )
                
                if created:
                    institutions_created += 1
                else:
                    institutions_updated += 1
                
                # Create quarterly stats
                stats = QuarterlyStats.objects.create(
                    institution=institution,
                    quarter_end_date=stats_date,
                    total_assets=bank_data['total_assets'],
                    total_deposits=bank_data['total_deposits'],
                    deposit_change_pct=0  # Will be calculated in a separate task
                )
                stats_created += 1
                
        logger.info(
            f"Successfully loaded data: "
            f"{institutions_created} institutions created, "
            f"{institutions_updated} institutions updated, "
            f"{stats_created} quarterly stats created"
        )
        return "Data loaded successfully"
        
    except Exception as e:
        logger.error(f"Error loading data to database: {str(e)}")
        raise

# Create DAG
dag = DAG(
    'fdic_data_ingestion',
    default_args=default_args,
    description='Ingest and process FDIC bank data',
    schedule_interval='0 0 * * 1',  # Run every Monday at midnight
    catchup=False,
    tags=['fdic', 'financial_data'],
)

# Define tasks
start = DummyOperator(task_id='start', dag=dag)

fetch_task = PythonOperator(
    task_id='fetch_fdic_data',
    python_callable=fetch_fdic_data,
    dag=dag,
)

transform_task = PythonOperator(
    task_id='transform_fdic_data',
    python_callable=transform_fdic_data,
    dag=dag,
)

load_task = PythonOperator(
    task_id='load_fdic_data',
    python_callable=load_to_database,
    dag=dag,
)

end = DummyOperator(task_id='end', dag=dag)

# Set task dependencies
start >> fetch_task >> transform_task >> load_task >> end 