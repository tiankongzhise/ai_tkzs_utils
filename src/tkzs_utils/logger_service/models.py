from dataclasses import dataclass
from typing import Callable,TextIO

@dataclass
class CustomLoggerLevel: 
    level_name: str
    level_num: int
    color: str = "<white>"
    icon: str|None = None

@dataclass
class LoggerParams:
    sink: str 
    level: str = "DEBUG"
    format: str ="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
    colorize: str = 'False'
    rotation: str|None = None
    retention: str|None = None
    compression: str|None = None
    backtrace: str = 'False'
    diagnose: str = 'False'
    enqueue: str = 'False'
    encoding: str|None = None
    filter_func_name: str|None = None
    serialize: str = 'False'

@dataclass
class StandardLoggerParams:
    sink: str |TextIO 
    level: str 
    format: str 
    colorize: bool
    rotation: str|None
    retention: str|None
    compression: str|None
    backtrace: bool
    diagnose: bool
    enqueue: bool
    encoding: str|None
    filter: Callable|None
    serialize: bool