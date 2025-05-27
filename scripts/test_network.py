#!/usr/bin/env python3
"""
DashScope网络连接测试脚本

独立的命令行工具，用于测试和诊断DashScope API连接问题
"""

import os
import sys
import json
import argparse
import logging
from typing import Dict, Any

def setup_logging(verbose: bool = False):
    """设置日志"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

def print_banner():
    """打印横幅"""
    print("\n" + "="*60)
    print("🔧 DashScope 网络连接测试工具")
    print("="*60)

def test_basic_imports():
    """测试基本模块导入"""
    print("\n📦 测试模块导入...")
    
    try:
        import requests
        print("✅ requests - OK")
    except ImportError as e:
        print(f"❌ requests - 失败: {e}")
        return False
    
    try:
        import dashscope
        print("✅ dashscope - OK")
    except ImportError as e:
        print(f"❌ dashscope - 失败: {e}")
        print("请安装: pip install dashscope")
        return False
    
    return True

def test_environment_variables():
    """测试环境变量配置"""
    print("\n🔍 检查环境变量...")
    
    # 检查API密钥
    api_key = os.environ.get("DASHSCOPE_API_KEY")
    if api_key:
        masked_key = f"{api_key[:8]}...{api_key[-4:]}" if len(api_key) > 12 else "*" * 8
        print(f"✅ DASHSCOPE_API_KEY: {masked_key}")
    else:
        print("❌ DASHSCOPE_API_KEY: 未设置")
        return False
    
    # 检查代理设置
    use_proxy = os.environ.get("USE_PROXY", "false").lower() == "true"
    print(f"🌐 使用代理: {'是' if use_proxy else '否'}")
    
    if use_proxy:
        http_proxy = os.environ.get("HTTP_PROXY")
        https_proxy = os.environ.get("HTTPS_PROXY")
        no_proxy = os.environ.get("NO_PROXY")
        
        if http_proxy:
            print(f"   HTTP代理: {http_proxy}")
        if https_proxy:
            print(f"   HTTPS代理: {https_proxy}")
        if no_proxy:
            print(f"   代理例外: {no_proxy}")
    
    return True

def test_basic_connectivity():
    """测试基本网络连接"""
    print("\n🌐 测试基本网络连接...")
    
    try:
        import requests
        
        # 测试基本互联网连接
        response = requests.get("https://www.baidu.com", timeout=10)
        if response.status_code == 200:
            print("✅ 基本互联网连接 - OK")
        else:
            print(f"⚠️ 基本互联网连接 - 异常状态码: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ 基本互联网连接 - 失败: {e}")
        return False
    
    return True

def test_dashscope_connectivity():
    """测试DashScope连接"""
    print("\n🔗 测试DashScope连接...")
    
    try:
        import requests
        
        dashscope_url = "https://dashscope.aliyuncs.com"
        proxies = None
        
        # 设置代理（如果配置了）
        if os.environ.get("USE_PROXY", "false").lower() == "true":
            proxies = {}
            if os.environ.get("HTTP_PROXY"):
                proxies["http"] = os.environ.get("HTTP_PROXY")
            if os.environ.get("HTTPS_PROXY"):
                proxies["https"] = os.environ.get("HTTPS_PROXY")
        
        response = requests.get(dashscope_url, timeout=30, proxies=proxies)
        
        if response.status_code in [200, 403, 404]:
            print("✅ DashScope服务 - 可访问")
            return True
        else:
            print(f"⚠️ DashScope服务 - 异常状态码: {response.status_code}")
            return False
            
    except requests.exceptions.ProxyError as e:
        print(f"❌ DashScope连接 - 代理错误: {e}")
        print("建议: 禁用代理或检查代理配置")
        return False
    except requests.exceptions.ConnectTimeout as e:
        print(f"❌ DashScope连接 - 连接超时: {e}")
        print("建议: 检查网络连接或增加超时时间")
        return False
    except requests.exceptions.ConnectionError as e:
        print(f"❌ DashScope连接 - 连接错误: {e}")
        print("建议: 检查网络设置和防火墙")
        return False
    except Exception as e:
        print(f"❌ DashScope连接 - 未知错误: {e}")
        return False

def test_dashscope_api():
    """测试DashScope API调用"""
    print("\n🤖 测试DashScope API...")
    
    try:
        import dashscope
        from dashscope import MultiModalConversation
        
        # 设置API密钥
        api_key = os.environ.get("DASHSCOPE_API_KEY")
        if not api_key:
            print("❌ API测试跳过 - 未设置API密钥")
            return False
        
        dashscope.api_key = api_key
        
        # 简单的API测试调用
        messages = [
            {
                "role": "user", 
                "content": [{"text": "你好"}]
            }
        ]
        
        try:
            response = MultiModalConversation.call(
                model='qwen-vl-plus',
                messages=messages
            )
            
            if response.status_code == 200:
                print("✅ DashScope API - 调用成功")
                return True
            else:
                print(f"❌ DashScope API - 调用失败: 状态码 {response.status_code}")
                if hasattr(response, 'message'):
                    print(f"   错误信息: {response.message}")
                return False
                
        except Exception as api_error:
            error_msg = str(api_error)
            if "ProxyError" in error_msg or "Max retries exceeded" in error_msg:
                print(f"❌ DashScope API - 网络连接失败: {error_msg}")
                print("建议: 检查网络设置和代理配置")
            elif "HTTPSConnectionPool" in error_msg:
                print(f"❌ DashScope API - HTTPS连接失败: {error_msg}")
                print("建议: 检查网络连接")
            else:
                print(f"❌ DashScope API - 调用异常: {error_msg}")
            return False
            
    except ImportError as e:
        print(f"❌ API测试跳过 - 导入失败: {e}")
        return False
    except Exception as e:
        print(f"❌ API测试失败: {e}")
        return False

def provide_solutions():
    """提供解决方案建议"""
    print("\n💡 问题解决建议:")
    print("\n1. 🚫 禁用代理 (最常见解决方案):")
    print("   export USE_PROXY=false")
    print("   unset HTTP_PROXY")
    print("   unset HTTPS_PROXY")
    print("   unset NO_PROXY")
    
    print("\n2. 🔑 设置API密钥:")
    print("   export DASHSCOPE_API_KEY='your_api_key_here'")
    
    print("\n3. 🌐 网络故障排除:")
    print("   - 检查防火墙设置")
    print("   - 确认网络连接稳定")
    print("   - 尝试使用不同的网络环境")
    
    print("\n4. 🔧 重新启动应用:")
    print("   在终端中按 Ctrl+C 停止应用")
    print("   然后重新运行: streamlit run streamlit_app/主页.py")

def save_test_results(results: Dict[str, Any], output_file: str):
    """保存测试结果到文件"""
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"\n📝 测试结果已保存到: {output_file}")
    except Exception as e:
        print(f"\n❌ 保存测试结果失败: {e}")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="DashScope网络连接测试工具")
    parser.add_argument("-v", "--verbose", action="store_true", help="详细输出")
    parser.add_argument("-o", "--output", help="保存测试结果到JSON文件")
    parser.add_argument("--fix", action="store_true", help="自动应用常见修复")
    
    args = parser.parse_args()
    
    setup_logging(args.verbose)
    print_banner()
    
    # 自动修复选项
    if args.fix:
        print("\n🔧 应用常见修复...")
        os.environ["USE_PROXY"] = "false"
        for key in ["HTTP_PROXY", "HTTPS_PROXY", "NO_PROXY"]:
            os.environ.pop(key, None)
        print("✅ 已禁用代理设置")
    
    # 运行测试
    test_results = {
        "basic_imports": False,
        "environment_variables": False,
        "basic_connectivity": False,
        "dashscope_connectivity": False,
        "dashscope_api": False
    }
    
    try:
        test_results["basic_imports"] = test_basic_imports()
        test_results["environment_variables"] = test_environment_variables()
        test_results["basic_connectivity"] = test_basic_connectivity()
        test_results["dashscope_connectivity"] = test_dashscope_connectivity()
        test_results["dashscope_api"] = test_dashscope_api()
        
    except KeyboardInterrupt:
        print("\n\n⚠️ 测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {e}")
        sys.exit(1)
    
    # 显示测试摘要
    print("\n" + "="*60)
    print("📊 测试结果摘要")
    print("="*60)
    
    all_passed = True
    for test_name, result in test_results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name.replace('_', ' ').title()}: {status}")
        if not result:
            all_passed = False
    
    if all_passed:
        print("\n🎉 所有测试通过！DashScope连接正常。")
    else:
        print("\n⚠️ 存在连接问题，请参考解决建议。")
        provide_solutions()
    
    # 保存结果
    if args.output:
        save_test_results(test_results, args.output)
    
    print("\n" + "="*60)
    sys.exit(0 if all_passed else 1)

if __name__ == "__main__":
    main() 