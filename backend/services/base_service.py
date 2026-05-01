"""
推理服务抽象基类
定义统一的模型服务接口
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class RecognitionResult:
    """识别结果数据类"""
    brand: str
    model: str
    color: str
    confidence: float
    bbox: Dict[str, float]
    purchase_advice: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'brand': self.brand,
            'model': self.model,
            'color': self.color,
            'confidence': self.confidence,
            'bbox': self.bbox,
            'purchase_advice': self.purchase_advice
        }


@dataclass
class TaskStatus:
    """任务状态数据类"""
    task_id: str
    status: str  # pending, processing, completed, failed
    progress: int  # 0-100
    result: Optional[RecognitionResult] = None
    error: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class BaseModelService(ABC):
    """模型服务抽象基类"""
    
    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(f"{__name__}.{name}")
    
    @abstractmethod
    def recognize(self, image_path: str, **kwargs) -> List[RecognitionResult]:
        """
        同步识别图片中的车辆
        
        Args:
            image_path: 图片路径
            **kwargs: 额外参数（如progress_callback）
            
        Returns:
            List[RecognitionResult]: 识别结果列表
        """
        pass
    
    @abstractmethod
    async def recognize_async(self, image_path: str, task_id: str, 
                             progress_callback: Optional[Callable] = None) -> List[RecognitionResult]:
        """
        异步识别图片中的车辆（用于Celery任务）
        
        Args:
            image_path: 图片路径
            task_id: 任务ID
            progress_callback: 进度回调函数
            
        Returns:
            List[RecognitionResult]: 识别结果列表
        """
        pass
    
    @abstractmethod
    def get_purchase_advice(self, brand: str, model: str) -> Dict[str, Any]:
        """
        获取购买建议
        
        Args:
            brand: 车辆品牌
            model: 车辆型号
            
        Returns:
            Dict: 购买建议字典
        """
        pass
    
    @abstractmethod
    def health_check(self) -> bool:
        """
        健康检查
        
        Returns:
            bool: 服务是否正常
        """
        pass
    
    def _validate_image(self, image_path: str) -> bool:
        """
        验证图片文件
        
        Args:
            image_path: 图片路径
            
        Returns:
            bool: 是否有效
        """
        import os
        from PIL import Image
        
        if not os.path.exists(image_path):
            self.logger.error(f"图片不存在: {image_path}")
            return False
        
        try:
            with Image.open(image_path) as img:
                img.verify()
            return True
        except Exception as e:
            self.logger.error(f"图片验证失败: {e}")
            return False
    
    def _report_progress(self, callback: Optional[Callable], task_id: str, 
                        progress: int, message: str = ""):
        """
        报告进度
        
        Args:
            callback: 回调函数
            task_id: 任务ID
            progress: 进度百分比
            message: 进度消息
        """
        if callback:
            try:
                callback(task_id, progress, message)
            except Exception as e:
                self.logger.warning(f"进度回调失败: {e}")