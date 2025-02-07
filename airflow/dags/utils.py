import requests
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def check_fdic_data_available():
    """
    Check if new FDIC data is available by comparing the last modified timestamp
    of the API endpoint with our last processed timestamp.
    """
    try:
        # TODO: Replace with actual FDIC API endpoint for metadata
        response = requests.head("https://banks.data.fdic.gov/api/institutions")
        if response.status_code == 200:
            last_modified = response.headers.get('last-modified')
            if last_modified:
                # Convert to datetime for comparison
                last_modified_date = datetime.strptime(last_modified, '%a, %d %b %Y %H:%M:%S GMT')
                # TODO: Compare with last processed timestamp from database/storage
                return True
        return False
    except Exception as e:
        logger.error(f"Error checking FDIC data: {e}")
        return False

def check_ncua_data_available():
    """
    Check if new NCUA quarterly data is available by comparing the current quarter
    with our last processed quarter.
    """
    try:
        current_date = datetime.now()
        current_quarter = (current_date.month - 1) // 3 + 1
        current_year = current_date.year
        
        # TODO: Replace with actual NCUA data URL for the current quarter
        test_url = f"https://www.ncua.gov/analysis/credit-union-corporate-call-report-data/{current_year}-Q{current_quarter}"
        response = requests.head(test_url)
        
        if response.status_code == 200:
            # TODO: Compare with last processed quarter from database/storage
            return True
        return False
    except Exception as e:
        logger.error(f"Error checking NCUA data: {e}")
        return False

def get_current_quarter_info():
    """
    Get the current year and quarter information
    """
    current_date = datetime.now()
    current_quarter = (current_date.month - 1) // 3 + 1
    current_year = current_date.year
    return current_year, current_quarter 