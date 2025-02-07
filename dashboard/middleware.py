from functools import wraps
from django.core.cache import cache
from django.http import HttpResponseForbidden
import time

def rate_limit_decorator(requests=100, interval=60):
    """
    Rate limiting decorator that allows a specified number of requests within a time interval
    :param requests: Number of allowed requests in the interval
    :param interval: Time interval in seconds
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            # Create a unique cache key for this IP
            client_ip = request.META.get('REMOTE_ADDR')
            cache_key = f'rate_limit_{client_ip}'
            
            # Get the current request times from cache
            request_times = cache.get(cache_key, [])
            now = time.time()
            
            # Remove old requests outside the time window
            request_times = [t for t in request_times if now - t < interval]
            
            # Check if we're over the limit
            if len(request_times) >= requests:
                return HttpResponseForbidden("Rate limit exceeded. Please try again later.")
            
            # Add current request time and update cache
            request_times.append(now)
            cache.set(cache_key, request_times, interval)
            
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator 