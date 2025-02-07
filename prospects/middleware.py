from django.core.cache import cache
from django.http import HttpResponseTooManyRequests
from django.conf import settings
from typing import Callable, Optional
import time
from functools import wraps

class RateLimitExceeded(Exception):
    """Exception raised when rate limit is exceeded"""
    pass

def get_client_ip(request) -> str:
    """Get client IP from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0]
    return request.META.get('REMOTE_ADDR')

class RateLimitMiddleware:
    """Rate limiting middleware for API requests"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        # Default rate limits
        self.rate_limits = getattr(settings, 'API_RATE_LIMITS', {
            'DEFAULT': {'calls': 100, 'period': 60},  # 100 calls per minute
            'AUTHENTICATED': {'calls': 1000, 'period': 60},  # 1000 calls per minute
        })
    
    def __call__(self, request):
        if not self._should_rate_limit(request):
            return self.get_response(request)

        try:
            self._check_rate_limit(request)
            response = self.get_response(request)
            return response
        except RateLimitExceeded:
            return HttpResponseTooManyRequests("Rate limit exceeded")

    def _should_rate_limit(self, request) -> bool:
        """Determine if request should be rate limited"""
        # Only rate limit API endpoints
        return request.path.startswith('/api/')

    def _get_cache_key(self, request) -> str:
        """Generate cache key for rate limiting"""
        client_ip = get_client_ip(request)
        if request.user.is_authenticated:
            return f"rate_limit_auth_{request.user.id}"
        return f"rate_limit_{client_ip}"

    def _check_rate_limit(self, request) -> None:
        """Check if request exceeds rate limit"""
        cache_key = self._get_cache_key(request)
        
        # Get appropriate rate limit based on authentication status
        limit_key = 'AUTHENTICATED' if request.user.is_authenticated else 'DEFAULT'
        rate_limit = self.rate_limits[limit_key]
        
        # Get current window data
        window_data = cache.get(cache_key)
        current_time = time.time()
        
        if window_data is None:
            # First request in window
            window_data = {
                'start_time': current_time,
                'count': 1
            }
        else:
            # Check if we're in a new window
            if current_time - window_data['start_time'] > rate_limit['period']:
                window_data = {
                    'start_time': current_time,
                    'count': 1
                }
            else:
                # Increment count in current window
                window_data['count'] += 1
        
        # Check if limit exceeded
        if window_data['count'] > rate_limit['calls']:
            raise RateLimitExceeded()
        
        # Update cache
        cache.set(
            cache_key,
            window_data,
            rate_limit['period']
        )

def rate_limit_decorator(
    calls: Optional[int] = None,
    period: Optional[int] = None
) -> Callable:
    """Decorator for rate limiting specific views"""
    def decorator(view_func):
        @wraps(view_func)
        def wrapped_view(request, *args, **kwargs):
            # Use provided limits or defaults
            rate_limit = {
                'calls': calls or 100,
                'period': period or 60
            }
            
            cache_key = f"view_rate_limit_{get_client_ip(request)}_{view_func.__name__}"
            window_data = cache.get(cache_key)
            current_time = time.time()
            
            if window_data is None:
                window_data = {
                    'start_time': current_time,
                    'count': 1
                }
            else:
                if current_time - window_data['start_time'] > rate_limit['period']:
                    window_data = {
                        'start_time': current_time,
                        'count': 1
                    }
                else:
                    window_data['count'] += 1
            
            if window_data['count'] > rate_limit['calls']:
                return HttpResponseTooManyRequests("Rate limit exceeded")
            
            cache.set(
                cache_key,
                window_data,
                rate_limit['period']
            )
            
            return view_func(request, *args, **kwargs)
        return wrapped_view
    return decorator 