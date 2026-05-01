"""
推理服务工厂模块
根据配置创建对应的后端服务实例
"""

import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def get_model_service():
    """
    获取模型服务实例（工厂模式）
    
    根据环境变量 MODEL_SERVICE_TYPE 创建对应的服务：
    - ollama: 本地Ollama服务
    - vllm: 云端vLLM服务
    - mock: Mock服务（用于测试）
    
    Returns:
        BaseModelService: 模型服务实例
    """
    # 优先使用 MODEL_SERVICE_TYPE，兼容旧的 INFERENCE_BACKEND
    backend = os.getenv('MODEL_SERVICE_TYPE', os.getenv('INFERENCE_BACKEND', 'ollama')).lower()
    
    if backend == 'ollama':
        from .ollama_service import OllamaService
        import config
        model_name = config.OLLAMA_MODEL
        # 支持远程Ollama
        host = config.OLLAMA_HOST
        logger.info(f"使用Ollama后端，模型: {model_name}, 地址: {host}")
        service = OllamaService(model_name)
        # 如果配置了远程host，需要特殊处理
        if host and host != 'http://localhost:11434':
            os.environ['OLLAMA_HOST'] = host
        return service
    
    elif backend == 'vllm':
        from .vllm_service import VLLMService
        import config
        api_url = config.VLLM_HOST
        # vLLM使用OpenAI兼容API，需要添加 /v1 路径
        if not api_url.endswith('/v1'):
            api_url = f"{api_url.rstrip('/')}/v1"
        api_key = os.getenv('VLLM_API_KEY', '')
        model_name = config.VLLM_MODEL
        timeout = config.VLLM_TIMEOUT
        logger.info(f"使用vLLM后端，地址: {api_url}, 模型: {model_name}, 超时: {timeout}s")
        return VLLMService(api_url, api_key, model_name)
    
    elif backend == 'mock':
        from .mock_service import MockService
        logger.info("使用Mock后端（测试模式）")
        return MockService()
    
    else:
        raise ValueError(f"未知的推理后端: {backend}，可选: ollama, vllm, mock")


# 全局服务实例（单例模式）
_model_service = None


def get_service():
    """获取全局模型服务实例（懒加载）"""
    global _model_service
    if _model_service is None:
        _model_service = get_model_service()
    return _model_service


def reset_service():
    """重置服务实例（用于配置变更后）"""
    global _model_service
    _model_service = None
    logger.info("模型服务实例已重置")