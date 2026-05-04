from pathlib import Path
from .protocol import LoggerProtocol
from typing import Any, Callable
import tomllib
from dotenv import dotenv_values
from .exception import ConfigServiceException
class NoOpLogger:
    """一个什么都不做的日志器，符合 LoggerParamsProtocol 接口"""
    def __getattr__(self, name: str) -> Any:
        # 动态拦截所有方法调用，返回一个空函数
        return lambda *args, **kwargs: None
    def info(self, *args, **kwargs) -> None:
        pass
    def debug(self, *args, **kwargs) -> None:
        pass
    def warning(self, *args, **kwargs) -> None:
        pass
    def error(self, *args, **kwargs) -> None:
        pass
    def critical(self, *args, **kwargs) -> None:
        pass


class ConfigService:
    def __init__(self,env_file: list[str | Path] = [".env"],config_file: list[str | Path] = ["config.toml"],logger: LoggerProtocol|None = None,default_logger_level: str = "DEBUG",is_print_logger: bool = False):
        self._env_file = env_file
        self._config_file = config_file
        self._logger = logger or self._default_logger(default_logger_level)
        self._is_print_logger = is_print_logger
        self._config_values = {}
        self.logger.info(f"ConfigService 初始化完成")
    def _default_logger(self,default_logger_level: str = "DEBUG") -> LoggerProtocol:
        import logging
        logger = logging.getLogger(__name__)
        logger.setLevel(getattr(logging,default_logger_level.upper()))
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        return logger
    @property
    def logger(self) -> LoggerProtocol:
        if self._is_print_logger:
            return self._logger
        else:
            return NoOpLogger()
    @logger.setter
    def logger(self, logger: LoggerProtocol) -> None:
        self._logger = logger

    def load_env_values(self) -> dict[str, str]:
        self.logger.info(f"ConfigService 开始读取机密信息文件...共{len(self._env_file)}个")
        env_values = {}
        try:
            for file in self._env_file:
                self.logger.debug(f"加载机密信息文件: {file}")
                env_values.update(dotenv_values(file))
                self.logger.debug(f"加载机密信息文件完成: {file}")
        except Exception as e:
            self.logger.error(f"加载机密信息文件失败: {e}") 
            raise ConfigServiceException(f"加载机密信息文件失败:  {e}") from e
        self.logger.info(f"ConfigService 加载机密信息文件完成...共{len(self._env_file)}个")
        return env_values
    
    def load_config_values(self) -> dict[str, Any]:
        self.logger.info(f"ConfigService 开始加载配置文件...共{len(self._config_file)}个")
        for file in self._config_file:
            self.logger.debug(f"加载配置文件: {file}")
            try:
                with open(file, "rb") as f:
                    self._config_values.update(tomllib.load(f))
                    self.logger.debug(f"加载配置文件完成: {file}")
            except Exception as e:
                self.logger.error(f"加载配置文件失败: {file} {e}")
                raise ConfigServiceException(f"加载配置文件失败: {file} {e}") from e
        self.logger.info(f"ConfigService 加载配置文件完成...共{len(self._config_file)}个")
        return self._config_values

    def get_config_values(self,key: str,default: Any = None) -> Any:
        return self._config_values.get(key,default)


_config_service = None
def get_config_service(env_file: list[str | Path] = [".env"],config_file: list[str | Path] = ["config.toml"],logger: LoggerProtocol|None = None,default_logger_level: str = "DEBUG",is_print_logger: bool = False) -> ConfigService:
    global _config_service
    if _config_service is None:
        _config_service = ConfigService(env_file,config_file,logger,default_logger_level,is_print_logger)
        _config_service.logger.info(f"创建config_service实例完成")
    else:
        _config_service.logger.debug(f"config_service实例已存在,返回现有实例")
    return _config_service