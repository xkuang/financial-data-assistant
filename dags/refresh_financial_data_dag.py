from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.empty import EmptyOperator
import logging
import requests
from bs4 import BeautifulSoup
import json
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# DAG default arguments
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
    'start_date': datetime(2025, 2, 6),
}

def check_fdic_data():
    """Check FDIC website for new data"""
    try:
        url = "https://www.fdic.gov/resources/data-tools/"
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        logger.info("Successfully checked FDIC website")
        return True
    except Exception as e:
        logger.error(f"Error checking FDIC data: {str(e)}")
        raise

def check_ncua_data():
    """Check NCUA website for new data"""
    try:
        url = "https://www.ncua.gov/analysis/credit-union-corporate-call-report-data"
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        logger.info("Successfully checked NCUA website")
        return True
    except Exception as e:
        logger.error(f"Error checking NCUA data: {str(e)}")
        raise

def generate_report(**context):
    """Generate a report of the data freshness check"""
    try:
        report = {
            'timestamp': datetime.now().isoformat(),
            'fdic_check': context['task_instance'].xcom_pull(task_ids='check_fdic_data'),
            'ncua_check': context['task_instance'].xcom_pull(task_ids='check_ncua_data')
        }
        
        # Ensure reports directory exists
        os.makedirs('data/reports', exist_ok=True)
        
        # Write report
        report_path = f"data/reports/freshness_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Report generated successfully: {report_path}")
        return report_path
    except Exception as e:
        logger.error(f"Error generating report: {str(e)}")
        raise

# Create DAG
dag = DAG(
    'refresh_financial_data',
    default_args=default_args,
    description='Check for new financial data from FDIC and NCUA',
    schedule_interval='0 6 * * *',  # Run at 6 AM every day
    catchup=False,
    max_active_runs=1
)

# Define tasks
start = EmptyOperator(task_id='start', dag=dag)

check_fdic = PythonOperator(
    task_id='check_fdic_data',
    python_callable=check_fdic_data,
    dag=dag
)

check_ncua = PythonOperator(
    task_id='check_ncua_data',
    python_callable=check_ncua_data,
    dag=dag
)

generate_report_task = PythonOperator(
    task_id='generate_report',
    python_callable=generate_report,
    provide_context=True,
    dag=dag
)

end = EmptyOperator(task_id='end', dag=dag)

# Set task dependencies
start >> [check_fdic, check_ncua] >> generate_report_task >> end 