import structlog
import logging
import sys

from structlog.exceptions import DropEvent

from .structlog_config_manager import StructLogSettings, CustomLoggerLevel, ProcessChainSettings
import time
import datetime
class DefaultStructlogManager:
    def __init__(self):
        self._is_production = False
        self._log_level = logging.INFO
    @staticmethod
    def configure_stdlib_logging():
        """配置 logging 模块的根 Logger，仅控制最终输出流向"""
        # 设置一个较低的门槛，实际门槛由 structlog 的 filtering 决定
        logging.basicConfig(
            format="%(message)s",  # structlog 自己负责格式化，这里仅占位
            stream=sys.stdout,
            level=logging.DEBUG,   # 允许所有日志通过，structlog 自己过滤
        )
    def minimal_console_logger(self):
        """阶段 1: 基础控制台输出，保证启动日志不丢失"""
        self.configure_stdlib_logging()
        structlog.configure(
            processors=[
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.dev.ConsoleRenderer(),
            ],
            logger_factory=structlog.stdlib.LoggerFactory(),
        )
        logger = structlog.get_logger()
        logger.info("日志系统已启动", phase="minimal")

    def update_structlog_configuration(self,structlog_settings: StructLogSettings):
        ...



def get_minimal_console_logger():
    import logging
    import structlog

    # 设置一个较低的门槛，实际门槛由 structlog 的 filtering 决定
    logging.basicConfig(
        format="%(message)s",  # structlog 自己负责格式化，这里仅占位
        stream=sys.stdout,
        level=logging.DEBUG,   # 允许所有日志通过，structlog 自己过滤
    )
    structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer(),
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
)
    logger = structlog.get_logger()
    logger.info("最小日志系统已启动")
    return logger


def _make_custom_level_method(level_value: int, method_name: str):
    """为自定义日志级别创建一个 BoundLogger 方法"""
    mname = method_name.lower()

    def level_method(self, event=None, *args, **kwargs):
        event_kw = dict(kwargs)
        if args:
            event_kw["positional_args"] = args
        try:
            proc_args, proc_kw = self._process_event(mname, event, event_kw)
        except DropEvent:
            return None
        return self._logger.log(level_value, *proc_args, **proc_kw)

    level_method.__name__ = mname
    return level_method


def create_custom_logger_class(custom_levels: list[CustomLoggerLevel]):
    """自动生成带自定义日志级别方法的 BoundLogger 子类

    与 ``LoggerFactory`` 配合时使用 ``structlog.stdlib.BoundLogger`` 作为基类；
    自定义数值级别通过 ``logging.Logger.log(level, msg, ...)`` 输出。
    """
    for cl in custom_levels:
        logging.addLevelName(cl.level_value, cl.level_name)

    class_attrs = {
        cl.level_name.lower(): _make_custom_level_method(cl.level_value, cl.level_name)
        for cl in custom_levels
    }

    return type(
        "CustomBoundLogger",
        (structlog.stdlib.BoundLogger,),
        class_attrs,
    )

# 自定义 processor：同时加 原始timestamp 和 格式化时间
def _dual_time_stamper(
    fmt: str = "%Y-%m-%d %H:%M:%S",
    utc: bool = False,
    raw_key: str = "timestamp",
    fmt_key: str = "datetime"
):
    """
    兼容官方 TimeStamper 的双时间戳处理器
    :param fmt: 格式化字符串，同 TimeStamper（如 "%Y-%m-%d %H:%M:%S.%f"）
    :param utc: 是否使用 UTC 时间
    :param raw_key: 原始时间戳字段名（默认 timestamp，float 秒）
    :param fmt_key: 格式化时间字段名（默认 datetime）
    """
    from structlog.processors import TimeStamper
    # 直接复用官方 TimeStamper 生成格式化时间
    ts = TimeStamper(fmt=fmt, utc=utc, key=fmt_key)

    def processor(logger, method_name, event_dict):
        # 1. 获取当前时间戳（float 秒）
        now = time.time()
        event_dict[raw_key] = now

        # 2. 调用官方 TimeStamper 生成格式化时间（完全复用逻辑）
        return ts(logger, method_name, event_dict)

    return processor

def create_process_chain(process_chain: ProcessChainSettings):
    import structlog
     # 共享处理器（在时间戳和上下文绑定之后，渲染之前）
    shared_processors = []
    shared_processors.append(structlog.stdlib.add_logger_name) # 添加 logger 名称
    shared_processors.append(structlog.stdlib.add_log_level) # 添加 level 字段
    shared_processors.append(structlog.stdlib.PositionalArgumentsFormatter()) # 添加 positional_args 字段
    shared_processors.append(_dual_time_stamper(fmt=process_chain.timestamp_format,utc=process_chain.utc)) # 添加 timestamp 字段 (默认格式ISO 8601)
    shared_processors.append(structlog.contextvars.merge_contextvars) # 合并通过 bind_contextvars 绑定的变量
    if process_chain.stack_info: 
        # 如果stack_info为True，则添加StackInfoRenderer处理器
        shared_processors.append(structlog.processors.StackInfoRenderer())
    if process_chain.exc_info:
        # 如果exc_info为True，则添加format_exc_info处理器
        shared_processors.append(structlog.processors.format_exc_info)
    return shared_processors



def update_structlog_configuration(structlog_settings: StructLogSettings):
    # create_custom_logger_level(structlog_settings.custom_logger_level)
    process_chain_processors = create_process_chain(structlog_settings.process_chain)
    # create_console_handler(structlog_settings.console_handler)
    # create_file_handler(structlog_settings.file_handler)
    process_chain_processors.append(
        # structlog.dev.ConsoleRenderer(colors=True,)
        structlog.processors.JSONRenderer(ensure_ascii=False)
        )
    structlog.configure(
        processors=process_chain_processors,
        # 使用 stdlib 的 LoggerFactory，让 structlog 写入标准库的日志系统
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=create_custom_logger_class(structlog_settings.custom_logger_level),
        # 缓存 logger 对象以提升性能（生产环境建议开启）
        cache_logger_on_first_use=True,
    )
    logger = structlog.get_logger()
    logger.info("structlog 配置已更新")
    return logger



