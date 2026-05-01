"""
Mock推理服务实现
用于开发和前端测试，返回固定数据
"""

import random
import logging
from typing import Optional, List, Dict, Any, Callable
import time

from .base_service import BaseModelService, RecognitionResult

logger = logging.getLogger(__name__)


class MockService(BaseModelService):
    """Mock推理服务（用于开发和测试）"""
    
    # 预设的车辆数据
    MOCK_VEHICLES = [
        {
            "brand": "宝马",
            "model": "宝马X5",
            "color": "黑色",
            "confidence": 0.95,
            "bbox": {"x1": 0.1, "y1": 0.2, "x2": 0.6, "y2": 0.8}
        },
        {
            "brand": "奔驰",
            "model": "奔驰C级",
            "color": "白色",
            "confidence": 0.88,
            "bbox": {"x1": 0.2, "y1": 0.3, "x2": 0.7, "y2": 0.9}
        },
        {
            "brand": "奥迪",
            "model": "奥迪A6L",
            "color": "银色",
            "confidence": 0.92,
            "bbox": {"x1": 0.05, "y1": 0.15, "x2": 0.55, "y2": 0.75}
        },
        {
            "brand": "特斯拉",
            "model": "Model 3",
            "color": "红色",
            "confidence": 0.96,
            "bbox": {"x1": 0.15, "y1": 0.25, "x2": 0.65, "y2": 0.85}
        }
    ]
    
    def __init__(self):
        super().__init__("MockService")
        self.delay = float(__import__('os').getenv('MOCK_DELAY', '2.0'))  # 默认延迟2秒
    
    def recognize(self, image_path: str, **kwargs) -> List[RecognitionResult]:
        """模拟识别车辆"""
        progress_callback = kwargs.get('progress_callback')
        task_id = kwargs.get('task_id', 'mock-task')
        
        self.logger.info(f"Mock识别开始: {image_path}")
        
        # 模拟进度
        self._report_progress(progress_callback, task_id, 10, "准备识别...")
        time.sleep(self.delay * 0.2)
        
        self._report_progress(progress_callback, task_id, 40, "分析图片...")
        time.sleep(self.delay * 0.3)
        
        self._report_progress(progress_callback, task_id, 70, "解析结果...")
        
        # 随机选择1-2辆车
        num_vehicles = random.randint(1, min(2, len(self.MOCK_VEHICLES)))
        selected = random.sample(self.MOCK_VEHICLES, num_vehicles)
        
        results = []
        for vehicle_data in selected:
            result = RecognitionResult(
                brand=vehicle_data['brand'],
                model=vehicle_data['model'],
                color=vehicle_data['color'],
                confidence=vehicle_data['confidence'],
                bbox=vehicle_data['bbox'],
                purchase_advice=self._generate_mock_advice(vehicle_data['brand'], vehicle_data['model'])
            )
            results.append(result)
        
        time.sleep(self.delay * 0.3)
        self._report_progress(progress_callback, task_id, 90, "获取购买建议...")
        
        time.sleep(self.delay * 0.2)
        self._report_progress(progress_callback, task_id, 100, "完成")
        
        self.logger.info(f"Mock识别完成: {len(results)}辆车")
        return results
    
    async def recognize_async(self, image_path: str, task_id: str, 
                             progress_callback: Optional[Callable] = None) -> List[RecognitionResult]:
        """异步识别（实际调用同步方法）"""
        return self.recognize(image_path, task_id=task_id, progress_callback=progress_callback)
    
    def get_purchase_advice(self, brand: str, model: str) -> Dict[str, Any]:
        """获取购买建议"""
        return self._generate_mock_advice(brand, model)
    
    def _generate_mock_advice(self, brand: str, model: str) -> Dict[str, Any]:
        """生成Mock购买建议"""
        # 根据品牌生成不同的建议
        advice_templates = {
            "宝马": {
                "price": "42-80万元",
                "experience": "操控精准，驾驶乐趣高",
                "pros_cons": "动力强但油耗偏高",
                "rating": "★★★★☆"
            },
            "奔驰": {
                "price": "35-100万元",
                "experience": "舒适豪华，品牌力强",
                "pros_cons": "舒适性好但维修贵",
                "rating": "★★★★★"
            },
            "奥迪": {
                "price": "38-75万元",
                "experience": "科技感强，内饰精致",
                "pros_cons": "四驱好但性价比一般",
                "rating": "★★★★☆"
            },
            "特斯拉": {
                "price": "23-35万元",
                "experience": "加速快，智能化高",
                "pros_cons": "续航好但内饰简单",
                "rating": "★★★★☆"
            }
        }
        
        # 返回对应品牌的建议，或默认建议
        return advice_templates.get(brand, {
            "price": "20-50万元",
            "experience": "性能均衡，适合家用",
            "pros_cons": "性价比高但品牌一般",
            "rating": "★★★☆☆"
        })
    
    def health_check(self) -> bool:
        """健康检查"""
        return True  # Mock服务总是健康