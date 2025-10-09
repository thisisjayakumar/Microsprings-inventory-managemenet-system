"""
Inventory utility functions
"""
import uuid
from datetime import datetime


def generate_transaction_id(prefix='TXN'):
    """
    Generate a unique transaction ID with prefix and timestamp
    Format: PREFIX-YYYYMMDD-HHMMSS-XXXX
    """
    now = datetime.now()
    timestamp = now.strftime('%Y%m%d-%H%M%S')
    unique_suffix = str(uuid.uuid4())[:4].upper()
    
    return f"{prefix}-{timestamp}-{unique_suffix}"


def generate_batch_id(prefix='BATCH'):
    """
    Generate a unique batch ID with prefix and timestamp
    Format: PREFIX-YYYYMMDD-HHMMSS-XXXX
    """
    now = datetime.now()
    timestamp = now.strftime('%Y%m%d-%H%M%S')
    unique_suffix = str(uuid.uuid4())[:4].upper()
    
    return f"{prefix}-{timestamp}-{unique_suffix}"
