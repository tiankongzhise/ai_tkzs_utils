import structlog
import time
import re
from functools import wraps
from typing import Any, Callable
from tkzs_utils.utils.repr import SmartRepr
# ===================== structlog 初始化（生产标准配置） =====================
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S"),  # 时间戳
        structlog.processors.add_log_level,                        # 日志级别
        structlog.processors.JSONRenderer(ensure_ascii=False),                       # 输出 JSON
    ],
)
logger = structlog.get_logger("service")

# ===================== 敏感信息配置 =====================
SENSITIVE_FIELDS = {
    "password", "pwd", "token", "access_token", "secret", "key",
    "phone", "mobile", "id_card", "identity", "card_no"
}

SENSITIVE_PATTERNS = {
    "phone": re.compile(r'1[3-9]\d{9}'),
    "id_card": re.compile(r'\d{18}|\d{17}X', re.I),
}

MAX_LOG_LENGTH = 512
TRUNCATE_SUFFIX = "...[truncated]"

# ===================== 工具函数（与原版兼容） =====================
def filter_sensitive_data(data: Any) -> Any:
    if isinstance(data, dict):
        result = {}
        for key, value in data.items():
            key_lower = str(key).lower()
            if any(s in key_lower for s in SENSITIVE_FIELDS):
                result[key] = "***FILTERED***"
            else:
                result[key] = filter_sensitive_data(value)
        return result

    elif isinstance(data, (list, tuple)):
        return [filter_sensitive_data(item) for item in data]

    elif isinstance(data, str):
        masked = data
        for pattern in SENSITIVE_PATTERNS.values():
            masked = pattern.sub("***FILTERED***", masked)
        return masked
    return data

def truncate_log(content: Any) -> str:
    s = str(content)
    if len(s) > MAX_LOG_LENGTH:
        return s[:MAX_LOG_LENGTH] + TRUNCATE_SUFFIX
    return s

# ===================== structlog 版 AOP 日志切面（核心） =====================
def log_aspect(
    log_args: bool = True,
    log_result: bool = True,
    log_time: bool = True
) -> Callable:
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            func_name = func.__name__
            start_time = time.time()
            log_ctx = {"func": func_name}  # structlog 结构化上下文

            try:
                # 1. 过滤入参
                if log_args:
                    clean_args = filter_sensitive_data(args)
                    clean_kwargs = filter_sensitive_data(kwargs)
                    log_ctx["args"] = truncate_log(clean_args)
                    log_ctx["kwargs"] = truncate_log(clean_kwargs)

                logger.info(**log_ctx, event="函数开始执行")

                # 2. 执行函数
                result = func(*args, **kwargs)

                # 3. 记录返回值
                if log_result:
                    clean_result = filter_sensitive_data(result)
                    log_ctx["result"] = truncate_log(clean_result)

                logger.info(**log_ctx, event="函数执行成功")
                return result

            except Exception as e:
                log_ctx["error"] = str(e)
                logger.error(**log_ctx, event="函数执行异常", exc_info=True)
                raise

            finally:
                if log_time:
                    cost = round((time.time() - start_time) * 1000, 2)
                    logger.info(**log_ctx, cost_ms=cost, event="函数执行耗时")

        return wrapper
    return decorator

# ===================== 使用示例（完全不变） =====================
if __name__ == '__main__':
    @log_aspect()
    def user_login(username: str, password: str, token: str):
        return {"code": 200, "msg": "登录成功", "user_id": 1001}

    @log_aspect()
    def get_user_info(phone: str, id_card: str):
        return {"name": "张三", "phone": phone, "id_card": id_card}

    # 测试
    user_login("zhangsan", "mypassword123", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9")
    get_user_info("13800138000", "110101199003074567")