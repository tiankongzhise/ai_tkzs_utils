import os
from typing import Literal
from pydantic import BaseModel, Field,field_validator
from pydantic_settings import (
    BaseSettings,
    JsonConfigSettingsSource,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

class CustomLoggerLevel(BaseModel):
    level_name:str
    level_value:int
    model_config = SettingsConfigDict(extra='ignore')


class ReprSettings(BaseModel):
    maxlist: int = 10
    maxtuple: int = 10
    maxset: int = 10
    maxfrozenset: int = 10
    maxarray: int = 10
    maxdict: int = 10
    maxstring: int = 10
    model_config = SettingsConfigDict(extra='ignore')


class ProcessChainSettings(BaseModel):
    timestamp_format:str = 'ISO'
    utc:bool = False
    stack_info:bool = True
    exc_info:bool = True
    model_config = SettingsConfigDict(extra='ignore')


class ConsoleHandlerSettings(BaseModel):
    level:str = "INFO"
    corlor:bool = True
    model_config = SettingsConfigDict(extra='ignore')


class RotatingFileHandlerSettings(BaseModel):
    max_bytes: int = 10 * 1024 * 1024      # 单个文件最大字节数 (10MB)
    backup_count: int = 5                  # 保留的备份文件数量
    model_config = SettingsConfigDict(extra='ignore')

    @field_validator('max_bytes', mode='before')
    def parse_max_bytes(cls, v):
        # 如果是字符串，解析乘法表达式
        if isinstance(v, str):
            v = v.strip()
            parts = v.split('*')
            result = 1
            for part in parts:
                part = part.strip()
                if part.isdigit():
                    result *= int(part)
                else:
                    raise ValueError(f"Invalid expression part: {part}")
            return result
        # 如果是整数或其他数值，直接返回（保持兼容）
        return v        

class TimedRotatingFileHandlerSettings(BaseModel):
    when: str = "midnight"                  # 时间间隔类型: 'S'秒, 'M'分, 'H'小时, 'D'天, 'W0'-'W6' 周一到周日, 'W0'表示周一
    interval: int = 1                       # 时间间隔数量 (当 when='S' 时无效)
    backup_count: int = 7                   # 保留的备份文件数量
    model_config = SettingsConfigDict(extra='ignore')
class CustomRotatingFileHandlerSettings(BaseModel):
    max_bytes: int = 10 * 1024 * 1024      # 单个文件最大字节数 (10MB)
    when: str = "midnight"                  # 时间间隔类型: 'S'秒, 'M'分, 'H'小时, 'D'天, 'W0'-'W6' 周一到周日, 'W0'表示周一
    interval: int = 1                       # 时间间隔数量 (当 when='S' 时无效)
    backup_count: int = 7                   # 保留最近X天的日志文件
    compression: bool = True                # 是否压缩
    encoding: str = "utf-8"                 # 编码
    model_config = SettingsConfigDict(extra='ignore')

    @field_validator('max_bytes', mode='before')
    def parse_max_bytes(cls, v):
        # 如果是字符串，解析乘法表达式
        if isinstance(v, str):
            v = v.strip()
            parts = v.split('*')
            result = 1
            for part in parts:
                part = part.strip()
                if part.isdigit():
                    result *= int(part)
                else:
                    raise ValueError(f"Invalid expression part: {part}")
            return result
        # 如果是整数或其他数值，直接返回（保持兼容）
        return v     

class FileHandlerSettings(BaseModel):
    level:str = "DEBUG"
    file_path: str = "logs/app.log"        # 日志文件路径
    active_rotating_rule:Literal['no_rotating', 'rotating', 'timed_rotating', 'custom_rotating'] = 'no_rotating'
    rotating_file_handler: RotatingFileHandlerSettings = Field(default_factory=RotatingFileHandlerSettings)
    timed_rotating_file_handler: TimedRotatingFileHandlerSettings = Field(default_factory=TimedRotatingFileHandlerSettings)
    custom_rotating_file_handler: CustomRotatingFileHandlerSettings = Field(default_factory=CustomRotatingFileHandlerSettings)
    model_config = SettingsConfigDict(extra='ignore')





class StructLogSettings(BaseSettings):
    custom_logger_level: list[CustomLoggerLevel] = Field(default_factory=list)
    process_chain: ProcessChainSettings = Field(default_factory=ProcessChainSettings)
    console_handler: ConsoleHandlerSettings = Field(default_factory=ConsoleHandlerSettings)
    file_handler: FileHandlerSettings = Field(default_factory=FileHandlerSettings)
    model_config = SettingsConfigDict(
    json_file='structlog_config.json',
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

