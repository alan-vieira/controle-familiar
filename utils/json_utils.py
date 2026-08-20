"""JSON utilities for Decimal serialization support.

This module provides a custom JSON encoder that serializes Decimal values
as strings to preserve precision in financial calculations.
"""
import json
from decimal import Decimal
from datetime import datetime, date


class DecimalEncoder(json.JSONEncoder):
    """JSON Encoder that serializes Decimal as string to preserve precision."""

    def default(self, obj):
        if isinstance(obj, Decimal):
            return str(obj)
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return super().default(obj)


def json_response(data, status=200):
    """Helper to return Flask response with Decimal serialization support.

    Args:
        data: Data to serialize (can contain Decimal values)
        status: HTTP status code
        
    Returns:
        Flask Response object with proper JSON content-type
    """
    from flask import current_app
    return current_app.response_class(
        response=json.dumps(data, cls=DecimalEncoder),
        status=status,
        mimetype='application/json'
    )