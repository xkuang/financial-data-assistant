"""
Author: Xiaoting Kuang
Main DAG file for refreshing financial data from FDIC and NCUA sources.
"""

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.utils.dates import days_ago
from airflow.utils.email import send_email
from datetime import datetime, timedelta
import os
import sys
import logging
import pytz
import requests
from bs4 import BeautifulSoup

# Add project root to Python path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(PROJECT_ROOT)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def send_success_email(context):
    """Send success email with execution details"""
    dag_run = context['dag_run']
    task_instances = dag_run.get_task_instances()
    execution_date = context['execution_date']
    
    email_body = f"""
    Data Refresh Completed Successfully
    
    Execution Date: {execution_date.strftime('%Y-%m-%d %H:%M:%S')} UTC
    Duration: {dag_run.end_date - dag_run.start_date}
    
    Task Summary:
    """
    
    for ti in task_instances:
        email_body += f"- {ti.task_id}: {ti.state} ({ti.duration} seconds)\n"
    
    send_email(
        to=context['dag'].default_args['email'],
        subject=f'Data Refresh Success - {execution_date.strftime("%Y-%m-%d")}',
        html_content=email_body
    )

def send_failure_email(context):
    """Send failure email with error details"""
    exception = context.get('exception')
    execution_date = context['execution_date']
    task_instance = context['task_instance']
    
    email_body = f"""
    Data Refresh Failed
    
    Task: {task_instance.task_id}
    Execution Date: {execution_date.strftime('%Y-%m-%d %H:%M:%S')} UTC
    Error: {str(exception)}
    
    Log URL: {task_instance.log_url}
    """
    
    send_email(
        to=context['dag'].default_args['email'],
        subject=f'Data Refresh Failed - {execution_date.strftime("%Y-%m-%d")}',
        html_content=email_body
    )

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email': ['your-email@example.com'],  # Replace with your email
    'email_on_failure': True,
    'email_on_retry': False,
    'email_on_success': True,
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
    'execution_timeout': timedelta(hours=1),
    'on_success_callback': send_success_email,
    'on_failure_callback': send_failure_email,
}

# Schedule to run daily at 6 AM UTC
dag = DAG(
    'refresh_financial_data',
    default_args=default_args,
    description='Refresh financial institution data from FDIC and NCUA',
    schedule_interval='0 6 * * *',  # Daily at 6 AM UTC
    start_date=datetime(2024, 1, 1, tzinfo=pytz.UTC),
    catchup=False,
    tags=['financial', 'data-refresh'],
)

def check_fdic_data_freshness(**context):
    """Check if new FDIC data is available"""
    try:
        logger.info("Checking FDIC website for new data...")
        
        # FDIC data check URL
        fdic_url = "https://www.fdic.gov/resources/data-tools/"
        response = requests.get(fdic_url)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Look for last update date in the page
        # This is a placeholder - adjust the selector based on actual FDIC website structure
        update_element = soup.find('div', {'class': 'last-updated'})
        if update_element:
            last_update = update_element.text.strip()
            logger.info(f"FDIC data last updated: {last_update}")
            context['task_instance'].xcom_push(key='fdic_last_update', value=last_update)
            return True
        
        logger.warning("Could not determine FDIC data freshness")
        return False
    except Exception as e:
        logger.error(f"Error checking FDIC data freshness: {str(e)}")
        raise

def check_ncua_data_freshness(**context):
    """Check if new NCUA data is available"""
    try:
        logger.info("Checking NCUA website for new data...")
        
        # NCUA data check URL
        ncua_url = "https://www.ncua.gov/analysis/credit-union-corporate-call-report-data"
        response = requests.get(ncua_url)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Look for last update date in the page
        # This is a placeholder - adjust the selector based on actual NCUA website structure
        update_element = soup.find('div', {'class': 'last-updated'})
        if update_element:
            last_update = update_element.text.strip()
            logger.info(f"NCUA data last updated: {last_update}")
            context['task_instance'].xcom_push(key='ncua_last_update', value=last_update)
            return True
            
        logger.warning("Could not determine NCUA data freshness")
        return False
    except Exception as e:
        logger.error(f"Error checking NCUA data freshness: {str(e)}")
        raise

def trigger_data_ingestion(**context):
    """Trigger FDIC and NCUA data ingestion DAGs if new data is available"""
    try:
        from airflow.api.client.local_client import Client
        
        client = Client(None, None)
        
        # Check if new FDIC data is available
        fdic_update = context['task_instance'].xcom_pull(
            task_ids='check_fdic_data_freshness',
            key='fdic_last_update'
        )
        if fdic_update:
            logger.info("Triggering FDIC data ingestion...")
            client.trigger_dag(dag_id='fdic_data_ingestion')
        
        # Check if new NCUA data is available
        ncua_update = context['task_instance'].xcom_pull(
            task_ids='check_ncua_data_freshness',
            key='ncua_last_update'
        )
        if ncua_update:
            logger.info("Triggering NCUA data ingestion...")
            client.trigger_dag(dag_id='ncua_data_ingestion')
        
        return True
    except Exception as e:
        logger.error(f"Error triggering data ingestion: {str(e)}")
        raise

def generate_freshness_report(**context):
    """Generate a report of data freshness checks"""
    try:
        logger.info("Generating data freshness report...")
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'fdic_last_update': context['task_instance'].xcom_pull(
                task_ids='check_fdic_data_freshness',
                key='fdic_last_update'
            ),
            'ncua_last_update': context['task_instance'].xcom_pull(
                task_ids='check_ncua_data_freshness',
                key='ncua_last_update'
            )
        }
        
        # Save report
        report_dir = os.path.join(PROJECT_ROOT, 'data', 'reports')
        os.makedirs(report_dir, exist_ok=True)
        
        report_file = os.path.join(
            report_dir,
            f'freshness_report_{context["execution_date"].strftime("%Y%m%d")}.json'
        )
        
        import json
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
            
        logger.info(f"Report saved to: {report_file}")
        return True
    except Exception as e:
        logger.error(f"Error generating freshness report: {str(e)}")
        raise

# Define tasks
check_fdic = PythonOperator(
    task_id='check_fdic_data_freshness',
    python_callable=check_fdic_data_freshness,
    provide_context=True,
    dag=dag,
)

check_ncua = PythonOperator(
    task_id='check_ncua_data_freshness',
    python_callable=check_ncua_data_freshness,
    provide_context=True,
    dag=dag,
)

trigger_ingestion = PythonOperator(
    task_id='trigger_data_ingestion',
    python_callable=trigger_data_ingestion,
    provide_context=True,
    dag=dag,
)

generate_report = PythonOperator(
    task_id='generate_freshness_report',
    python_callable=generate_freshness_report,
    provide_context=True,
    dag=dag,
)

# Clean up old reports (keep last 30 days)
cleanup_old_files = BashOperator(
    task_id='cleanup_old_files',
    bash_command=f'''
        find {PROJECT_ROOT}/data/reports -name "freshness_report_*.json" -mtime +30 -delete
    ''',
    dag=dag,
)

# Define task dependencies
[check_fdic, check_ncua] >> trigger_ingestion >> generate_report >> cleanup_old_files 