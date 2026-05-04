import loguru
from loguru import logger
import sys
from typing import Optional
from dataclasses import dataclass
import sys
from typing import TextIO
from typing import Callable
from .exception import LoggerServiceException
from .filter_rule import get_logger_filter_rules
from .models import CustomLoggerLevel, LoggerParams, StandardLoggerParams

# --------------------------
# 第一步：项目启动时 优先初始化基础日志
# --------------------------
# 移除默认控制台输出（自定义格式）
_default_stdout_handler_id = None
def init_logger() -> 'loguru.Logger':
    global _default_stdout_handler_id
    logger.debug("初始化日志器")
    logger.remove()    
    # 初始化临时基础日志（后续会被配置覆盖）
    _default_stdout_handler_id = logger.add(
        sys.stdout,
        level="DEBUG",
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        enqueue=True  # 异步日志，高并发安全
    )
    logger.debug(f"初始化默认控制台输出完成: {_default_stdout_handler_id}")
    return logger
# --------------------------
# 第二步：添加自定义日志级别
# --------------------------


def add_custom_logger_level(custom_level: list[CustomLoggerLevel]):
    try:
        logger.debug(f"开始添加自定义日志级别共{len(custom_level)}个")
        success_custom_level = []
        for level in custom_level:
            logger.level(level.level_name, no=level.level_num, color=level.color, icon=level.icon)
            logger.debug(f"添加自定义日志级别: {level.level_name}")
            success_custom_level.append(level.level_name)
        logger.info(f"添加自定义日志级别完成: {success_custom_level}")
    except Exception as e:
        raise LoggerServiceException(f"添加自定义日志级别失败: {e}") from e



# --------------------------
# 第三步：动态更新日志配置（根据 config 修改）
# --------------------------








def _transform_str_to_bool(bool_value: str) -> bool:
    if bool_value.lower() in ['true', 'yes','t','y', '1']:
        return True
    elif bool_value.lower() in ['false', 'no', 'f', 'n', '0']:
        return False
    else:
        raise LoggerServiceException(f"LoggerParams: bool_value:{bool_value} is invalid")
def _transform_sink_str_to_standard_sink(sink_value: str) -> str|TextIO:
    if sink_value.lower() in ['stdout', 'console','sys.stdout']:
        return sys.stdout
    elif sink_value.lower() in ['stderr', 'error','sys.stderr']:
        return sys.stderr
    else:
        return sink_value

def _transform_filter_func_name_to_callable(filter_func_name: str|None) -> Callable|None:
    if filter_func_name is None:
        return None
    rules: dict[str, Callable] = get_logger_filter_rules()
    if filter_func_name in rules:
        return rules[filter_func_name]
    else:
        raise LoggerServiceException(f"logger_filter_func:{filter_func_name} not exists")

def _transform_logger_params_to_standard_logger_params(params: LoggerParams) -> StandardLoggerParams:
    return StandardLoggerParams(
        sink=_transform_sink_str_to_standard_sink(params.sink),
        level=params.level,
        format=params.format,
        colorize=_transform_str_to_bool(params.colorize),
        rotation=params.rotation,
        retention=params.retention,
        compression=params.compression,
        backtrace=_transform_str_to_bool(params.backtrace),
        diagnose=_transform_str_to_bool(params.diagnose),
        enqueue=_transform_str_to_bool(params.enqueue),
        encoding=params.encoding,
        filter=_transform_filter_func_name_to_callable(params.filter_func_name),
        serialize=_transform_str_to_bool(params.serialize))
def _get_unnone_standard_logger_params(params: StandardLoggerParams)->dict:
    return {key: value for key, value in params.__dict__.items() if value is not None}

def update_logger_config(config: list[LoggerParams]):
    global _default_stdout_handler_id
    try:
        logger.debug(f"开始更新日志配置共{len(config)}个")
        standard_config: list[StandardLoggerParams] = [_transform_logger_params_to_standard_logger_params(cfg) for cfg in config]
        success_config = []
        for cfg in standard_config:
            logger.debug(f"更新日志配置: {cfg}")
            if cfg.sink is sys.stdout:
                logger.debug("移除默认控制台输出")
                if _default_stdout_handler_id is not None:
                    logger.remove(_default_stdout_handler_id)
                    _default_stdout_handler_id = None
            logger.add(**_get_unnone_standard_logger_params(cfg))
            logger.debug(f"添加日志配置完成: {cfg.sink}")
            success_config.append(cfg.sink)
        logger.info(f"更新日志配置完成: {success_config}")
    except Exception as e:
        raise LoggerServiceException(f"更新日志配置失败: {e}") from e

