import time
from functools import wraps
from flask import jsonify
import requests
from config import CACHE_DURATION, DEFAULT_HEADERS, QUBIC_API_KEY
from network_stats import log_network_stats_event

# Cache storage
cache = {}

def cache_response(duration=CACHE_DURATION):
    """Cache decorator"""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            cache_key = f.__name__ + str(args) + str(kwargs)
            now = time.time()

            if cache_key in cache:
                result, timestamp = cache[cache_key]
                if now - timestamp < duration:
                    return result

            result = f(*args, **kwargs)
            cache[cache_key] = (result, now)
            return result
        return wrapper
    return decorator

def get_qubic_headers():
    """Get Qubic API request headers"""
    headers = DEFAULT_HEADERS.copy()
    if QUBIC_API_KEY:
        headers['Authorization'] = f'Bearer {QUBIC_API_KEY}'
    return headers

def safe_request(url, method='GET', headers=None, json=None, params=None):
    """Safe HTTP request wrapper"""
    try:
        response = requests.request(
            method=method,
            url=url,
            headers=headers,
            json=json,
            params=params
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        error_msg = f"Error in request to {url}: {str(e)}"
        log_network_stats_event('error', error_msg, {
            'url': url,
            'method': method,
            'status_code': getattr(e.response, 'status_code', None) if hasattr(e, 'response') else None,
            'response_text': getattr(e.response, 'text', None) if hasattr(e, 'response') else None
        })
        print(error_msg)
        return None
    except Exception as e:
        error_msg = f"Unexpected error in request to {url}: {str(e)}"
        log_network_stats_event('error', error_msg, {
            'url': url,
            'method': method
        })
        print(error_msg)
        return None

def error_response(message, status_code=500):
    """Unified error response format"""
    return jsonify({
        'status': 'error',
        'message': str(message)
    }), status_code

def success_response(data):
    """Unified successful response format"""
    return jsonify({
        'status': 'success',
        'data': data,
        'timestamp': time.time()
    })
