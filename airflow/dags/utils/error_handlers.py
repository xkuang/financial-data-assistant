import logging
from typing import Dict, Any
from airflow.models import TaskInstance
from airflow.utils.email import send_email
from datetime import datetime

logger = logging.getLogger(__name__)

class DataPipelineError(Exception):
    """Base exception for data pipeline errors"""
    pass

class DataFetchError(DataPipelineError):
    """Exception for data fetch failures"""
    pass

class DataValidationError(DataPipelineError):
    """Exception for data validation failures"""
    pass

class DataProcessingError(DataPipelineError):
    """Exception for data processing failures"""
    pass

def log_error(error: Exception, context: Dict[str, Any]) -> None:
    """Log error details with context"""
    task: TaskInstance = context['task_instance']
    execution_date = context.get('execution_date', datetime.now())
    
    error_details = {
        'task_id': task.task_id,
        'dag_id': task.dag_id,
        'execution_date': execution_date,
        'error_type': type(error).__name__,
        'error_message': str(error)
    }
    
    logger.error(
        "Task failed: %(task_id)s in DAG: %(dag_id)s at %(execution_date)s\n"
        "Error: %(error_type)s - %(error_message)s",
        error_details
    )

def send_error_notification(context: Dict[str, Any]) -> None:
    """Send email notification for task failure"""
    task: TaskInstance = context['task_instance']
    dag_id = task.dag_id
    task_id = task.task_id
    execution_date = context.get('execution_date', datetime.now())
    
    subject = f"Airflow Alert: Task {task_id} in DAG {dag_id} failed"
    html_content = f"""
        <h3>Task Failure Alert</h3>
        <p><strong>DAG:</strong> {dag_id}</p>
        <p><strong>Task:</strong> {task_id}</p>
        <p><strong>Execution Date:</strong> {execution_date}</p>
        <p><strong>Exception:</strong> {context.get('exception', 'Unknown error')}</p>
        <p>Please check the Airflow logs for more details.</p>
    """
    
    try:
        send_email(
            to=['your-email@example.com'],  # Configure with actual email
            subject=subject,
            html_content=html_content
        )
    except Exception as e:
        logger.error(f"Failed to send error notification email: {str(e)}")

def handle_task_failure(context: Dict[str, Any]) -> None:
    """Comprehensive task failure handler"""
    try:
        # Log the error
        error = context.get('exception')
        log_error(error, context)
        
        # Send notification
        send_error_notification(context)
        
        # Update task metadata
        task: TaskInstance = context['task_instance']
        task.xcom_push(key='error_timestamp', value=datetime.now().isoformat())
        task.xcom_push(key='error_type', value=type(error).__name__)
        task.xcom_push(key='error_message', value=str(error))
        
    except Exception as e:
        logger.error(f"Error in failure handling: {str(e)}")

def retry_handler(context: Dict[str, Any]) -> None:
    """Handle task retries"""
    task: TaskInstance = context['task_instance']
    retries = task.try_number - 1
    
    logger.warning(
        f"Task {task.task_id} in DAG {task.dag_id} is being retried for the {retries} time"
    )
    
    # Log retry metadata
    task.xcom_push(key='retry_count', value=retries)
    task.xcom_push(key='last_retry_timestamp', value=datetime.now().isoformat())

def get_default_task_args() -> Dict[str, Any]:
    """Get default arguments for tasks with error handling"""
    return {
        'owner': 'airflow',
        'depends_on_past': False,
        'email_on_failure': True,
        'email_on_retry': False,
        'retries': 3,
        'retry_delay': 300,  # 5 minutes
        'on_failure_callback': handle_task_failure,
        'on_retry_callback': retry_handler
    } 