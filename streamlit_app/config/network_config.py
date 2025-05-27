"""
网络配置管理模块

用于管理DashScope API连接、代理设置和网络配置
"""

import os
import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class NetworkConfig:
    """网络配置管理器"""
    
    def __init__(self):
        """初始化网络配置"""
        self.proxy_settings = self._load_proxy_settings()
        self.api_settings = self._load_api_settings()
    
    def _load_proxy_settings(self) -> Dict[str, Any]:
        """加载代理设置"""
        return {
            "http_proxy": os.environ.get("HTTP_PROXY"),
            "https_proxy": os.environ.get("HTTPS_PROXY"),
            "no_proxy": os.environ.get("NO_PROXY"),
            "use_proxy": os.environ.get("USE_PROXY", "false").lower() == "true"
        }
    
    def _load_api_settings(self) -> Dict[str, Any]:
        """加载API设置"""
        return {
            "dashscope_api_key": os.environ.get("DASHSCOPE_API_KEY"),
            "dashscope_base_url": os.environ.get("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com"),
            "connection_timeout": int(os.environ.get("CONNECTION_TIMEOUT", "30")),
            "max_retries": int(os.environ.get("MAX_RETRIES", "3"))
        }
    
    def configure_dashscope_environment(self) -> bool:
        """配置DashScope环境变量"""
        try:
            # 设置代理（如果需要）
            if self.proxy_settings["use_proxy"]:
                if self.proxy_settings["http_proxy"]:
                    os.environ["HTTP_PROXY"] = self.proxy_settings["http_proxy"]
                if self.proxy_settings["https_proxy"]:
                    os.environ["HTTPS_PROXY"] = self.proxy_settings["https_proxy"]
                if self.proxy_settings["no_proxy"]:
                    os.environ["NO_PROXY"] = self.proxy_settings["no_proxy"]
                    
                logger.info("已配置代理设置")
            else:
                # 清除代理设置
                for key in ["HTTP_PROXY", "HTTPS_PROXY", "NO_PROXY"]:
                    os.environ.pop(key, None)
                    
                logger.info("已禁用代理设置")
            
            # 设置API密钥
            if self.api_settings["dashscope_api_key"]:
                os.environ["DASHSCOPE_API_KEY"] = self.api_settings["dashscope_api_key"]
                logger.info("已设置DashScope API密钥")
                return True
            else:
                logger.warning("未设置DASHSCOPE_API_KEY")
                return False
                
        except Exception as e:
            logger.error(f"配置DashScope环境失败: {str(e)}")
            return False
    
    def test_connection(self) -> Dict[str, Any]:
        """测试网络连接"""
        import requests
        
        test_results = {
            "dashscope_accessible": False,
            "proxy_working": False,
            "error_message": ""
        }
        
        try:
            # 测试DashScope连接
            url = self.api_settings["dashscope_base_url"]
            timeout = self.api_settings["connection_timeout"]
            
            response = requests.get(
                url, 
                timeout=timeout,
                proxies=self._get_proxy_dict() if self.proxy_settings["use_proxy"] else None
            )
            
            if response.status_code in [200, 404, 403]:  # 这些状态码表示能够连接到服务器
                test_results["dashscope_accessible"] = True
                test_results["proxy_working"] = self.proxy_settings["use_proxy"]
                logger.info("DashScope连接测试成功")
            else:
                test_results["error_message"] = f"服务器返回状态码: {response.status_code}"
                
        except requests.exceptions.ProxyError as e:
            test_results["error_message"] = f"代理错误: {str(e)}"
            logger.error(f"代理连接失败: {str(e)}")
        except requests.exceptions.ConnectTimeout as e:
            test_results["error_message"] = f"连接超时: {str(e)}"
            logger.error(f"连接超时: {str(e)}")
        except requests.exceptions.ConnectionError as e:
            test_results["error_message"] = f"连接错误: {str(e)}"
            logger.error(f"连接错误: {str(e)}")
        except Exception as e:
            test_results["error_message"] = f"未知错误: {str(e)}"
            logger.error(f"连接测试失败: {str(e)}")
        
        return test_results
    
    def _get_proxy_dict(self) -> Dict[str, str]:
        """获取代理字典"""
        proxy_dict = {}
        if self.proxy_settings["http_proxy"]:
            proxy_dict["http"] = self.proxy_settings["http_proxy"]
        if self.proxy_settings["https_proxy"]:
            proxy_dict["https"] = self.proxy_settings["https_proxy"]
        return proxy_dict
    
    def get_connection_suggestions(self, test_results: Dict[str, Any]) -> List[str]:
        """根据测试结果提供连接建议"""
        suggestions = []
        
        if not test_results["dashscope_accessible"]:
            suggestions.extend([
                "🔍 检查网络连接是否正常",
                "🔑 确认DASHSCOPE_API_KEY环境变量已正确设置",
                "🌐 如果在企业网络环境，请确认代理设置是否正确"
            ])
            
            if "ProxyError" in test_results.get("error_message", ""):
                suggestions.extend([
                    "🔧 代理配置可能有问题，请检查HTTP_PROXY和HTTPS_PROXY设置",
                    "🚫 尝试禁用代理：设置环境变量 USE_PROXY=false"
                ])
            
            if "timeout" in test_results.get("error_message", "").lower():
                suggestions.extend([
                    "⏱️ 网络可能较慢，尝试增加CONNECTION_TIMEOUT值",
                    "🔄 检查防火墙是否阻止了对dashscope.aliyuncs.com的访问"
                ])
        
        return suggestions
    
    def export_configuration_template(self) -> str:
        """导出配置模板"""
        template = """# DashScope网络配置环境变量模板
# 请根据您的网络环境配置以下变量

# DashScope API密钥（必需）
export DASHSCOPE_API_KEY="your_api_key_here"

# 代理设置（可选，仅在需要时配置）
export USE_PROXY=false
export HTTP_PROXY="http://your_proxy_server:port"
export HTTPS_PROXY="http://your_proxy_server:port"
export NO_PROXY="localhost,127.0.0.1"

# 连接参数（可选）
export CONNECTION_TIMEOUT=30
export MAX_RETRIES=3
export DASHSCOPE_BASE_URL="https://dashscope.aliyuncs.com"
"""
        return template


def get_network_config() -> NetworkConfig:
    """获取网络配置实例"""
    return NetworkConfig()


def diagnose_connection_issues() -> Dict[str, Any]:
    """诊断连接问题"""
    config = get_network_config()
    
    # 配置环境
    env_configured = config.configure_dashscope_environment()
    
    # 测试连接
    test_results = config.test_connection()
    
    # 获取建议
    suggestions = config.get_connection_suggestions(test_results)
    
    return {
        "environment_configured": env_configured,
        "connection_test": test_results,
        "suggestions": suggestions,
        "configuration_template": config.export_configuration_template()
    } 