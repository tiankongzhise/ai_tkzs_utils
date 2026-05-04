from tkzs_utils.logger_service.structlog_manager import get_minimal_console_logger,update_structlog_configuration
from tkzs_utils.logger_service.structlog_config_manager import StructLogSettings

if __name__ == "__main__":
    logger = get_minimal_console_logger()
    structlog_settings = StructLogSettings()
    update_structlog_configuration(structlog_settings)
    logger.service_info("structlog service info")