import os
import json
from dotenv import load_dotenv

load_dotenv()

MODELS_FILE = os.path.join(os.path.dirname(__file__), 'models.json')

def get_default_models():
    """返回默认模型配置（从 .env 读取 API Key）"""
    return {
        "deepseek": {
            "name": "DeepSeek Coder",
            "provider": "openai",
            "api_key": os.getenv("DEEPSEEK_API_KEY"),
            "api_base": "https://api.deepseek.com",
            "model": "deepseek-v4-flash",
        },
        "doubao": {
            "name": "Doubao-Code",
            "provider": "openai",
            "api_key": os.getenv("DOUBAO_API_KEY"),
            "api_base": "https://ark.cn-beijing.volces.com/api/v3",
            "model": "ep-20260605180645-xcfkc",
            "max_tokens": 32768,
            "temperature": 0.1,
        },
    }


def load_models():
    """从 JSON 文件加载模型配置，如果文件不存在则创建默认配置"""
    if os.path.exists(MODELS_FILE):
        try:
            with open(MODELS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if data:
                return data
        except:
            pass
    
    # 首次启动：写入默认配置
    default = get_default_models()
    save_models(default)
    return default


def save_models(models_dict):
    """保存模型配置到 JSON 文件"""
    with open(MODELS_FILE, 'w', encoding='utf-8') as f:
        json.dump(models_dict, f, ensure_ascii=False, indent=2)


# 全局模型配置（运行时加载）
MODELS = load_models()
