from typing import Callable
from .exception import LoggerServiceException
_filter_func_name_cache: dict[str, Callable] = {}

def register_logger_filter_func(func: Callable) -> Callable:
    if func.__name__ in _filter_func_name_cache:
        raise LoggerServiceException(f"logger_filter_func:{func.__name__} already exists")
    _filter_func_name_cache[func.__name__] = func
    return func

def get_logger_filter_rules() -> dict[str, Callable]:
    return _filter_func_name_cache