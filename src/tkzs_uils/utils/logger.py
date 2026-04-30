from tkzs_uils.logger_service.models import LoggerParams,StandardLoggerParams,CustomLoggerLevel
from tkzs_uils.logger_service.core import init_logger, add_custom_logger_level, update_logger_config
from tkzs_uils.logger_service.filter_rule import register_logger_filter_func,get_logger_filter_rules
from tkzs_uils.logger_service.exception import LoggerServiceException
from tkzs_uils.config_service.core import get_config_service,ConfigService
from pathlib import Path
from tkzs_uils.config_service.protocol import LoggerProtocol

from pydantic import BaseModel, Field
from pydantic_settings import (
    BaseSettings,
    JsonConfigSettingsSource,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

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


class CustomLoggerLevel(BaseModel):
    level_name:str
    level_value:int
    model_config = SettingsConfigDict(extra='ignore')

class ProcessChainSettings(BaseModel):
    timestamp_format:str|None = 'iso'
    utc:bool = False
    stack_info:bool = True
    exc_info:bool = True
    model_config = SettingsConfigDict(extra='ignore')


class ConsoleHandlerSettings(BaseModel):
    level:str = "INFO"
    corlor:bool = True
    model_config = SettingsConfigDict(extra='ignore')

class FileHandlerSettings(BaseModel):
    level:str = "DEBUG"
    when:str = "midnight"
    rotation:int = 1
    retention:int = 7
    compression:bool = True
    encoding:str = "utf-8"
    model_config = SettingsConfigDict(extra='ignore')


class HandlerConfigBundle(BaseModel):
    process_chain: ProcessChainSettings = Field(default_factory=ProcessChainSettings)
    console_handler: ConsoleHandlerSettings = Field(default_factory=ConsoleHandlerSettings)
    file_handler: FileHandlerSettings = Field(default_factory=FileHandlerSettings)
    model_config = SettingsConfigDict(extra="ignore")


class DefaultStructLogSettings(BaseSettings):
    custom_logger_level: list[CustomLoggerLevel] = Field(default_factory=list)
    handler_config: HandlerConfigBundle = Field(default_factory=HandlerConfigBundle)
    model_config = SettingsConfigDict(
        json_file='logger_config.json',
        extra="ignore",
        json_file_encoding="utf-8",
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            JsonConfigSettingsSource(settings_cls),
            env_settings,
            dotenv_settings,
            file_secret_settings,
        )

if __name__ == "__main__":
    # dict_config = DatabaseSettings().model_dump()
    # for key,value in dict_config.items():
    #     if isinstance(value,SecretStr):
    #         print(f"{key}: {value.get_secret_value()}")
    #     else:
    #         print(f"{key}: {value}")
    dict_config = DefaultStructLogSettings().model_dump()
    for key,value in dict_config.items():
        print(f"{key}: {value}")