import structlog
import logging
import sys
from structlog.exceptions import DropEvent
from .structlog_config_manager import (
    StructLogSettings,
    CustomLoggerLevel,
    ProcessChainSettings,
    ConsoleHandlerSettings,
    FileHandlerSettings,
)
import time
import datetime


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



def _create_console_handler(console_settings: "ConsoleHandlerSettings"):
    """创建控制台日志处理器"""
    import logging
    import sys

    level_str = console_settings.level.upper()
    if not hasattr(logging, level_str):
        raise ValueError(f"Invalid log level: {console_settings.level}")
    level = getattr(logging, level_str)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    return handler


def _create_rotating_file_handler(file_settings: "FileHandlerSettings"):
    """创建 RotatingFileHandler"""
    import logging
    from logging.handlers import RotatingFileHandler

    level_str = file_settings.level.upper()
    if not hasattr(logging, level_str):
        raise ValueError(f"Invalid log level: {file_settings.level}")
    level = getattr(logging, level_str)

    rotating_settings = file_settings.rotating_file_handler
    handler = RotatingFileHandler(
        filename=file_settings.file_path,
        maxBytes=rotating_settings.max_bytes,
        backupCount=rotating_settings.backup_count,
        encoding="utf-8",
    )
    handler.setLevel(level)
    return handler


def _create_timed_rotating_file_handler(file_settings: "FileHandlerSettings"):
    """创建 TimedRotatingFileHandler"""
    import logging
    from logging.handlers import TimedRotatingFileHandler

    level_str = file_settings.level.upper()
    if not hasattr(logging, level_str):
        raise ValueError(f"Invalid log level: {file_settings.level}")
    level = getattr(logging, level_str)

    timed_settings = file_settings.timed_rotating_file_handler
    handler = TimedRotatingFileHandler(
        filename=file_settings.file_path,
        when=timed_settings.when,
        interval=timed_settings.interval,
        backupCount=timed_settings.backup_count,
        encoding="utf-8",
    )
    handler.setLevel(level)
    return handler


def _create_custom_rotating_file_handler(file_settings: "FileHandlerSettings"):
    """预留接口：创建自定义 RotatingFileHandler
    
    该接口预留用于实现更复杂的日志轮转策略，
    例如同时按大小和时间进行轮转。
    """
    # TODO: 实现自定义日志轮转逻辑
    # 支持以下特性:
    # - 按大小和时间双重条件轮转
    # - 压缩备份文件
    # - 自定义文件名格式
    raise NotImplementedError(
        "CustomRotatingFileHandler is not yet implemented. "
        "Please use 'rotating', 'timed_rotating', or 'no_rotating' instead."
    )


def _create_processor_formatter(renderer):
    """创建 structlog 格式化器"""
    return structlog.stdlib.ProcessorFormatter(
        processor=renderer,
        foreign_pre_chain=create_process_chain(
            ProcessChainSettings(timestamp_format="ISO", utc=False, stack_info=True, exc_info=True)
        ),
    )


def _setup_handlers(structlog_settings: StructLogSettings):
    """根据配置设置日志处理器"""
    import logging

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    # console handler
    console_handler = _create_console_handler(structlog_settings.console_handler)
    console_renderer = structlog.dev.ConsoleRenderer(
        colors=structlog_settings.console_handler.corlor
    )
    console_handler.setFormatter(_create_processor_formatter(console_renderer))
    root_logger.addHandler(console_handler)

    # file handler
    rotating_rule = structlog_settings.file_handler.active_rotating_rule
    if rotating_rule != 'no_rotating':
        if rotating_rule == 'rotating':
            file_handler = _create_rotating_file_handler(structlog_settings.file_handler)
        elif rotating_rule == 'timed_rotating':
            file_handler = _create_timed_rotating_file_handler(structlog_settings.file_handler)
        elif rotating_rule == 'custom_rotating':
            file_handler = _create_custom_rotating_file_handler(structlog_settings.file_handler)
        else:
            raise ValueError(f"Unknown rotating rule: {rotating_rule}")

        file_handler.setFormatter(
            _create_processor_formatter(
                structlog.processors.JSONRenderer(ensure_ascii=False)
            )
        )
        root_logger.addHandler(file_handler)


def update_structlog_configuration(structlog_settings: StructLogSettings):
    # 设置 logging handlers
    _setup_handlers(structlog_settings)

    process_chain_processors = create_process_chain(structlog_settings.process_chain)
    process_chain_processors.append(
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



