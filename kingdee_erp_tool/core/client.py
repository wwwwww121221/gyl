import json
import os
import configparser
from k3cloud_webapi_sdk.main import K3CloudApiSdk

class KingdeeClient:
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(KingdeeClient, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
            
        # 定位配置文件
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.config_path = os.path.join(self.base_dir, "conf.ini")
        
        if not os.path.exists(self.config_path):
            print(f"Warning: Configuration file not found at {self.config_path}")
            self.config = {}
        else:
            self.config = self._read_config()
        
        self.server_url = self.config.get('X-KDApi-ServerUrl', "http://erp.julan.com.cn:8081/k3cloud/")
        if not self.server_url.endswith('/'):
            self.server_url += '/'
            
        # 初始化 SDK
        self.sdk = K3CloudApiSdk(self.server_url)
        
        # 如果配置文件存在，尝试初始化 SDK 配置
        if os.path.exists(self.config_path):
            try:
                # 注意：Init 方法通常返回 True/False，或者抛出异常
                self.sdk.Init(config_path=self.config_path, config_node="config")
                print("K3Cloud SDK initialized successfully.")
            except Exception as e:
                print(f"Failed to initialize K3Cloud SDK: {e}")

        self._initialized = True

    def _read_config(self):
        """读取 conf.ini 中的配置 (辅助方法，主要用于调试或备用)"""
        cf = configparser.ConfigParser()
        try:
            cf.read(self.config_path, encoding='utf-8')
        except Exception:
            cf.read(self.config_path)
            
        config = {}
        if 'config' in cf.sections():
            for key, value in cf.items('config'):
                config[key] = value
                
        # 再次尝试手动解析以获取正确的大小写 Key
        raw_config = {}
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#') or line.startswith(';'):
                        continue
                    if '=' in line:
                        parts = line.split('=', 1)
                        key = parts[0].strip()
                        value = parts[1].strip()
                        raw_config[key] = value
        
        return {**config, **raw_config}

    def execute_query(self, para):
        """执行单据查询"""
        try:
            # 直接调用 SDK 的 ExecuteBillQuery
            # SDK 返回的是 JSON 字符串
            response_str = self.sdk.ExecuteBillQuery(para)
            
            # 尝试解析 JSON
            try:
                response_data = json.loads(response_str)
                return response_data
            except json.JSONDecodeError:
                print(f"Failed to decode JSON response: {response_str}")
                # 如果返回的不是 JSON，可能是错误信息字符串
                # 尝试重新初始化并重试一次 (简单的重试机制)
                print("Retrying with re-initialization...")
                self.sdk.Init(config_path=self.config_path, config_node="config")
                response_str = self.sdk.ExecuteBillQuery(para)
                return json.loads(response_str)

        except Exception as e:
            print(f"Execute query failed: {e}")
            raise e

# 全局单例
client = KingdeeClient()
