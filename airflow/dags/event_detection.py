from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.dummy import DummyOperator
import json
import os
import pandas as pd
from typing import List, Dict

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

def load_quarterly_data(data_dir: str, quarter_date: str) -> List[Dict]:
    """
    Load and combine FDIC and NCUA data for a specific quarter
    """
    fdic_path = os.path.join(data_dir, f"fdic_{quarter_date}.json")
    ncua_path = os.path.join(data_dir, f"ncua_{quarter_date}.json")
    
    all_data = []
    
    # Load FDIC data
    if os.path.exists(fdic_path):
        with open(fdic_path, 'r') as f:
            all_data.extend(json.load(f))
    
    # Load NCUA data
    if os.path.exists(ncua_path):
        with open(ncua_path, 'r') as f:
            all_data.extend(json.load(f))
    
    return all_data

def detect_deposit_decline(**context):
    """
    Detect institutions with >5% deposit decline
    """
    # Get the current and previous quarter dates
    execution_date = context['execution_date']
    current_quarter = execution_date.strftime('%Y-%m-%d')
    previous_quarter = (execution_date - timedelta(days=90)).strftime('%Y-%m-%d')
    
    # Load data from both quarters
    data_dir = "/opt/airflow/data/processed"
    current_data = load_quarterly_data(data_dir, current_quarter)
    previous_data = load_quarterly_data(data_dir, previous_quarter)
    
    # Convert to DataFrames for easier analysis
    df_current = pd.DataFrame(current_data)
    df_previous = pd.DataFrame(previous_data)
    
    # Merge current and previous quarter data
    df_merged = pd.merge(
        df_current,
        df_previous[['charter_number', 'total_deposits']],
        on='charter_number',
        suffixes=('', '_prev')
    )
    
    # Calculate deposit change percentage
    df_merged['deposit_change_pct'] = (
        (df_merged['total_deposits'] - df_merged['total_deposits_prev']) 
        / df_merged['total_deposits_prev'] * 100
    )
    
    # Filter institutions with >5% decline
    declining_institutions = df_merged[df_merged['deposit_change_pct'] < -5].to_dict('records')
    
    # Save results
    output_path = f"/opt/airflow/data/events/deposit_decline_{current_quarter}.json"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(declining_institutions, f)
    
    return output_path

def analyze_by_asset_tier(**context):
    """
    Analyze institutions by asset tier
    """
    execution_date = context['execution_date']
    current_quarter = execution_date.strftime('%Y-%m-%d')
    
    # Load current quarter data
    data_dir = "/opt/airflow/data/processed"
    current_data = load_quarterly_data(data_dir, current_quarter)
    
    df = pd.DataFrame(current_data)
    
    # Define asset tiers
    df['asset_tier'] = pd.cut(
        df['total_assets'],
        bins=[0, 100e6, 500e6, 1e9, 10e9, float('inf')],
        labels=['<$100M', '$100M-$500M', '$500M-$1B', '$1B-$10B', '>$10B']
    )
    
    # Analyze by tier
    tier_analysis = df.groupby('asset_tier').agg({
        'charter_number': 'count',
        'total_assets': 'sum',
        'total_deposits': 'sum'
    }).reset_index()
    
    # Save results
    output_path = f"/opt/airflow/data/analysis/asset_tiers_{current_quarter}.json"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(tier_analysis.to_dict('records'), f)
    
    return output_path

def notify_events(**context):
    """
    Send notifications about detected events
    """
    execution_date = context['execution_date']
    current_quarter = execution_date.strftime('%Y-%m-%d')
    
    # Load deposit decline events
    events_path = context['task_instance'].xcom_pull(task_ids='detect_deposit_decline')
    with open(events_path, 'r') as f:
        declining_institutions = json.load(f)
    
    # TODO: Implement notification logic (email, Slack, etc.)
    print(f"Found {len(declining_institutions)} institutions with significant deposit decline")

with DAG(
    'financial_event_detection',
    default_args=default_args,
    description='Detect significant events in financial institution data',
    schedule_interval='0 6 1 */3 *',  # Run at 6 AM on 1st of every quarter
    catchup=False
) as dag:
    
    start = DummyOperator(task_id='start')
    
    detect_decline = PythonOperator(
        task_id='detect_deposit_decline',
        python_callable=detect_deposit_decline
    )
    
    analyze_tiers = PythonOperator(
        task_id='analyze_asset_tiers',
        python_callable=analyze_by_asset_tier
    )
    
    send_notifications = PythonOperator(
        task_id='notify_events',
        python_callable=notify_events
    )
    
    end = DummyOperator(task_id='end')
    
    start >> [detect_decline, analyze_tiers] >> send_notifications >> end 