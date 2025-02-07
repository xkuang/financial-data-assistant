from decimal import Decimal
from typing import Dict, Any
import re

class ValidationError(Exception):
    """Custom exception for validation errors"""
    pass

def validate_charter_number(charter_number: str) -> bool:
    """Validate charter number format"""
    if not charter_number or not isinstance(charter_number, str):
        raise ValidationError("Charter number must be a non-empty string")
    # Add specific charter number format validation based on FDIC/NCUA requirements
    if not re.match(r'^\d{4,8}$', charter_number):
        raise ValidationError("Invalid charter number format")
    return True

def validate_web_domain(domain: str) -> bool:
    """Validate web domain format"""
    if not domain:
        return True  # Domain can be empty
    domain_pattern = r'^([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$'
    if not re.match(domain_pattern, domain):
        raise ValidationError("Invalid web domain format")
    return True

def validate_state(state: str) -> bool:
    """Validate US state code"""
    valid_states = {
        'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA',
        'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD',
        'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ',
        'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC',
        'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY',
        'DC', 'PR', 'VI', 'GU', 'AS', 'MP'
    }
    if not state or state.upper() not in valid_states:
        raise ValidationError("Invalid US state code")
    return True

def validate_financial_value(value: Any) -> bool:
    """Validate financial values (assets, deposits)"""
    try:
        decimal_value = Decimal(str(value))
        if decimal_value < 0:
            raise ValidationError("Financial values cannot be negative")
        return True
    except (TypeError, ValueError):
        raise ValidationError("Invalid financial value format")

def validate_institution_type(inst_type: str) -> bool:
    """Validate institution type"""
    valid_types = {'BANK', 'CREDIT_UNION'}
    if not inst_type or inst_type.upper() not in valid_types:
        raise ValidationError("Invalid institution type")
    return True

def validate_institution_data(data: Dict[str, Any]) -> bool:
    """Validate complete institution data record"""
    required_fields = {
        'charter_number': validate_charter_number,
        'web_domain': validate_web_domain,
        'city': lambda x: bool(x and isinstance(x, str)),
        'state': validate_state,
        'total_assets': validate_financial_value,
        'total_deposits': validate_financial_value,
        'institution_type': validate_institution_type
    }

    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        raise ValidationError(f"Missing required fields: {', '.join(missing_fields)}")

    for field, validator in required_fields.items():
        try:
            validator(data[field])
        except ValidationError as e:
            raise ValidationError(f"Validation error for {field}: {str(e)}")
        except Exception as e:
            raise ValidationError(f"Unexpected error validating {field}: {str(e)}")

    return True

def validate_report_date(date_str: str) -> bool:
    """Validate report date format (YYYY-MM-DD)"""
    try:
        if not re.match(r'^\d{4}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\d|3[01])$', date_str):
            raise ValidationError("Invalid date format. Expected YYYY-MM-DD")
        return True
    except Exception:
        raise ValidationError("Invalid date format") 