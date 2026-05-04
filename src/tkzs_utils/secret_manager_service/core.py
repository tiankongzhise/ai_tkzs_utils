from cryptography.fernet import Fernet
from cryptography.fernet import InvalidToken
import json
import time
from typing import Optional, Dict, Any, TypedDict
from .config_center import get_project_config_center_client,ConfigCenterFiles
from dotenv import dotenv_values
import io
import tomllib
from pathlib import Path

class SecretData(TypedDict):
    encrypted_value: bytes
    created_at: float
    expire_at: Optional[float]

class SecretManager:
    """
    安全机密信息管理类
    功能：加密存储、安全读取、自动脱敏、过期控制、文件持久化
    """

    def __init__(self, encryption_key: Optional[bytes] = None, encoding: str = "utf-8"):
        """
        初始化机密管理器
        :param encryption_key: 加密密钥（不传则自动生成）
        """
        # 如果没有传入密钥，自动生成一个安全密钥
        self._encryption_key = encryption_key or Fernet.generate_key()
        self._cipher = Fernet(self._encryption_key)

        # 内存中存储加密后的机密（绝不存明文）
        self._secrets: Dict[str, Dict[str, SecretData]] = {}
        self._encoding = encoding


    def _to_bytes(self, data: Any) -> bytes:
        """
        任意类型 → bytes（带类型信息，可还原）
        """
        # 包装：存原始类型 + 数据
        payload = {
            "type": type(data).__name__,  # 存类型名
            "data": data
        }
        # 转 JSON 字符串再编码成 bytes
        return json.dumps(payload, ensure_ascii=False).encode(self._encoding)


    def _from_bytes(self, b_data: bytes) -> Any:
        """
        bytes → 还原成原来的 Any 类型
        """
        # 先解码成 JSON 字符串
        json_str = b_data.decode(self._encoding)
        payload = json.loads(json_str)
        
        type_name = payload["type"]
        data = payload["data"]
        
        # 自动恢复原始类型
        if type_name == "str":
            return str(data)
        elif type_name == "int":
            return int(data)
        elif type_name == "float":
            return float(data)
        elif type_name == "bool":
            return bool(data)
        elif type_name == "NoneType":
            return None
        elif type_name == "bytes":
            return data.encode(self._encoding)  # 还原 bytes
        else:
            # 其他类型直接返回
            return data

    def add_secret(
        self,
        platform_name: str,
        name: str,
        value: Any,
        expire_seconds: Optional[int] = None
    ) -> None:
        """
        添加一个机密（自动加密）
        :param platform_name: 平台名称
        :param name: 机密名称
        :param value: 机密明文
        :param expire_seconds: 过期时间（秒），None 表示永不过期
        """

        # 加密
        encrypted_value = self._cipher.encrypt(self._to_bytes(value))

        # 存储结构
        secret_data: SecretData = {
            "encrypted_value": encrypted_value,
            "created_at": time.time(),
            "expire_at": time.time() + expire_seconds if expire_seconds else None
        }

        self._secrets.setdefault(platform_name, {}).setdefault(name, secret_data)

    def get_secret_value(self, platform_name: str, name: str) -> Optional[Any]:
        """
        安全获取机密明文（自动检查过期）
        :param name: 机密名称
        :return: 明文 / None
        """
        secret = self._secrets.get(platform_name, {}).get(name)
        if not secret:
            return None

        # 检查是否过期
        if secret["expire_at"] and time.time() > secret["expire_at"]:
            self.delete_secret(platform_name, name)
            return None

        # 解密
        try:
            decrypted = self._cipher.decrypt(secret["encrypted_value"])
            return self._from_bytes(decrypted)
        except InvalidToken:
            raise ValueError("解密失败：密钥错误或数据被篡改")

    def delete_secret(self, platform_name: str, name: str) -> None:
        """删除机密"""
        self._secrets.pop(platform_name, {}).pop(name, None)


    def load_from_config_center(self,config_center_files:ConfigCenterFiles|None = None) -> None:
        """从配置中心加载加密机密"""
        if config_center_files is None:
            config_center_files = ConfigCenterFiles()
        config_center_client = get_project_config_center_client()
        def get_env_data(env_file:str) -> dict[str, Any]:
            env_data = config_center_client.get_config(env_file)
            return dotenv_values(stream = io.StringIO(env_data.decode("utf-8")))
        def get_config_data(config_file:str) -> dict[str, Any]:
            config_data = config_center_client.get_config(config_file)
            return tomllib.loads(config_data.decode("utf-8"))
        try:
            self._secrets.clear()
            for env_file in config_center_files.env_files:
                env_data = get_env_data(env_file)
                for name, value in env_data.items():
                    self.add_secret(Path(env_file).stem, name, value)
            for config_file in config_center_files.config_file:
                config_data = get_config_data(config_file)
                for platform_name, platform_data in config_data.items():
                    for name, secret_data in platform_data.items():
                        self.add_secret(platform_name, name, secret_data)
        except Exception as e:
            raise ValueError(f"从配置中心加载加密机密失败: {e}")

    def get_key(self) -> str:
        """获取加密密钥（务必保存好）"""
        return self._encryption_key.decode("utf-8")
    
    def get_encoding(self) -> str:
        """获取编码"""
        return self._encoding
    
    def set_encoding(self, encoding: str) -> None:
        """设置编码"""
        self._encoding = encoding
    
    def list_platforms(self) -> list[str]:
        """获取平台列表"""
        return list(self._secrets.keys())
    
    def list_secrets(self, platform_name: str) -> list[str]:
        """获取平台下的机密列表"""
        return list(self._secrets.get(platform_name, {}).keys())
    def get_secret(self, platform_name: str, name: str) -> SecretData|None:
        """获取机密数据"""
        return self._secrets.get(platform_name, {}).get(name)
    def set_secrets(self,secrets:Dict[str,Dict[str,SecretData]]) -> None:
        """设置机密数据"""
        self._secrets = secrets
    def get_secrets(self) -> Dict[str,Dict[str,SecretData]]:
        """获取所有机密数据"""
        return self._secrets
    def __str__(self) -> str:
        """脱敏打印（防止日志泄露）"""
        return f"SecureSecretManager(secrets={list(self._secrets.keys())})"

    def __repr__(self) -> str:
        return self.__str__()





class AdPlatformSecretManager(SecretManager):
    def __init__(self, platform_name: str, encoding: str = "utf-8"):
        super().__init__(encoding=encoding)
        self._platform_name = platform_name
    
    def pf_add_secret(self, name: str, value: Any, expire_seconds: Optional[int] = None) -> None:
        """添加机密"""
        super().add_secret(self._platform_name, name, value, expire_seconds)
    
    def pf_get_secret_value(self, name: str) -> Optional[Any]:
        """获取机密"""
        return super().get_secret_value(self._platform_name, name)
    
    def pf_delete_secret(self, name: str) -> None:
        """删除机密"""
        super().delete_secret(self._platform_name, name)
    def pf_get_secret(self, name: str) -> SecretData|None:
        """获取机密数据"""
        return super().get_secret(self._platform_name, name)

    def pf_list_secrets(self) -> list[str]:
        """获取平台下的机密列表"""
        return super().list_secrets(self._platform_name)
    
    def pf_load_from_config_center(self,config_center_files:ConfigCenterFiles|None = None) -> None:
        """从配置中心加载加密机密"""
        if config_center_files is None:
            config_center_files = ConfigCenterFiles()
        config_center_client = get_project_config_center_client()
        def get_env_data(env_file:str) -> dict[str, Any]:
            env_data = config_center_client.get_config(env_file)
            return dotenv_values(stream = io.StringIO(env_data.decode("utf-8")))
        def get_config_data(config_file:str) -> dict[str, Any]:
            config_data = config_center_client.get_config(config_file)
            return tomllib.loads(config_data.decode("utf-8"))
        try:
            self._secrets.clear()
            for env_file in config_center_files.env_files:
                if Path(env_file).stem != self._platform_name:
                    continue
                env_data = get_env_data(env_file)
                for name, value in env_data.items():
                    self.add_secret(Path(env_file).stem, name, value)
            for config_file in config_center_files.config_file:
                config_data = get_config_data(config_file)
                for platform_name, platform_data in config_data.items():
                    if platform_name != self._platform_name:
                        continue
                    for name, secret_data in platform_data.items():
                        self.add_secret(platform_name, name, secret_data)
        except Exception as e:
            raise ValueError(f"从配置中心加载加密机密失败: {e}")
    def get_platform_name(self) -> str:
        """获取平台名称"""
        return self._platform_name