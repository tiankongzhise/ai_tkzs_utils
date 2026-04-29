from tkzs_uils.logger_service.models import LoggerParams,StandardLoggerParams,CustomLoggerLevel
from tkzs_uils.logger_service.core import init_logger, add_custom_logger_level, update_logger_config
from tkzs_uils.logger_service.filter_rule import register_logger_filter_func,get_logger_filter_rules
from tkzs_uils.logger_service.exception import LoggerServiceException
from tkzs_uils.config_service.core import get_config_service,ConfigService
from pathlib import Path
from tkzs_uils.config_service.protocol import LoggerProtocol


def _get_logger_config(config: ConfigService) -> tuple[list[CustomLoggerLevel]|None,list[LoggerParams]|None]:
    logger_config = config.get_config_values("logger",{})
    if not logger_config:
        return None,None
    logger_params_config = logger_config.get("sink")
    custom_logger_levels_config = logger_config.get("custom_level")
    if custom_logger_levels_config is None:
        logger_levels = None
    else:
        logger_levels = []
        for key,value in custom_logger_levels_config.items():
            logger_levels.append(CustomLoggerLevel(level_name=key, level_num=value.get("level_num"), color=value.get("color"), icon=value.get("icon")))
    if logger_params_config is None:
        logger_params = None
    else:
        logger_params = []
        for _,value in logger_params_config.items():
            logger_params.append(LoggerParams(**value))
    return logger_levels,logger_params





def default_init_logger(env_file: list[str | Path] = [".env"],config_file: list[str | Path] = ["config.toml"],default_logger_level: str = "DEBUG",is_print_logger: bool = False) -> LoggerProtocol:
    logger = init_logger()
    config_service = get_config_service(env_file,config_file,logger,default_logger_level,is_print_logger)
    config_service.load_config_values()
    logger_levels,logger_params = _get_logger_config(config_service)
    def _update_logger_settings(logger_levels: list[CustomLoggerLevel]|None,logger_params: list[LoggerParams]|None):
        try:
            if logger_levels is not None:
                add_custom_logger_level(logger_levels)
            if logger_params is not None:
                update_logger_config(logger_params)
        except Exception as e:
            logger.error(f"更新日志配置失败: {e},将使用默认日志配置")
            raise e 
    _update_logger_settings(logger_levels,logger_params)
    return logger