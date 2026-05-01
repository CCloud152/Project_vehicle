"""
vLLM云端推理服务实现
通过OpenAI兼容API调用云端GPU服务
"""

import os
import json
import logging
import base64
from typing import Optional, List, Dict, Any, Callable
import httpx

from .base_service import BaseModelService, RecognitionResult

logger = logging.getLogger(__name__)


class VLLMService(BaseModelService):
    """vLLM云端推理服务（OpenAI兼容API）"""
    
    def __init__(self, api_url: str, api_key: str = '', model_name: str = 'qwen3-vl:8b'):
        super().__init__(f"VLLMService-{model_name}")
        self.api_url = api_url.rstrip('/')
        self.api_key = api_key
        self.model_name = model_name
        
        # 创建HTTP客户端
        self.client = httpx.Client(
            base_url=self.api_url,
            headers={
                "Authorization": f"Bearer {api_key}" if api_key else "",
                "Content-Type": "application/json"
            },
            timeout=120.0
        )
    
    def _image_to_base64(self, image_path: str) -> Optional[str]:
        """将图片转换为Base64编码"""
        try:
            if not os.path.exists(image_path):
                logger.error(f"图片文件不存在: {image_path}")
                return None
            
            with open(image_path, "rb") as f:
                image_data = f.read()
            
            import imghdr
            img_format = imghdr.what(image_path) or "jpeg"
            base64_data = base64.b64encode(image_data).decode("utf-8")
            return f"data:image/{img_format};base64,{base64_data}"
            
        except Exception as e:
            logger.error(f"图片转换失败: {e}")
            return None
    
    def _clean_response_text(self, text: str) -> str:
        """清理响应文本"""
        if text.startswith('```json'):
            text = text[7:]
        if text.endswith('```'):
            text = text[:-3]
        
        text = text.strip()
        text = text.replace('，', ',')
        text = text.replace('：', ':')
        
        return text
    
    def _validate_vehicle_data(self, vehicle: Dict[str, Any]) -> Dict[str, Any]:
        """验证并补全车辆数据"""
        vehicle.setdefault('brand', '未知')
        vehicle.setdefault('model', '未知')
        vehicle.setdefault('color', '未知')
        vehicle.setdefault('confidence', 0.0)
        vehicle.setdefault('bbox', {})
        
        try:
            confidence = float(vehicle['confidence'])
            vehicle['confidence'] = max(0.0, min(1.0, confidence))
        except (ValueError, TypeError):
            vehicle['confidence'] = 0.0
        
        bbox = vehicle['bbox']
        bbox.setdefault('x1', 0.0)
        bbox.setdefault('y1', 0.0)
        bbox.setdefault('x2', 1.0)
        bbox.setdefault('y2', 1.0)
        
        for key in ['x1', 'y1', 'x2', 'y2']:
            try:
                value = float(bbox[key])
                bbox[key] = max(0.0, min(1.0, value))
            except (ValueError, TypeError):
                bbox[key] = 0.0 if '1' in key else 1.0
        
        return vehicle
    
    def recognize(self, image_path: str, **kwargs) -> List[RecognitionResult]:
        """同步识别车辆"""
        if not self._validate_image(image_path):
            return []
        
        progress_callback = kwargs.get('progress_callback')
        self._report_progress(progress_callback, kwargs.get('task_id', ''), 10, "准备识别...")
        
        image_base64 = self._image_to_base64(image_path)
        if not image_base64:
            return []
        
        self._report_progress(progress_callback, kwargs.get('task_id', ''), 30, "调用云端vLLM...")
        
        prompt = """请仔细识别图片中的所有车辆，返回JSON格式数组：
[
    {
        "brand": "品牌名（如宝马）",
        "model": "型号（如宝马X5）",
        "color": "颜色（如黑色）",
        "confidence": 0.95,
        "bbox": {
            "x1": 0.1,
            "y1": 0.2,
            "x2": 0.5,
            "y2": 0.6
        }
    }
]
要求：
1. bbox坐标为相对图片尺寸的比例值，范围0-1
2. 置信度为0-1之间的小数
3. 只返回JSON数组，不要添加其他内容
4. 如果图片中没有车辆，请返回空数组"""
        
        try:
            payload = {
                "model": self.model_name,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": image_base64}}
                        ]
                    }
                ],
                "max_tokens": 2048,
                "temperature": 0.1
            }
            
            response = self.client.post("/chat/completions", json=payload)
            response.raise_for_status()
            
            self._report_progress(progress_callback, kwargs.get('task_id', ''), 70, "解析结果...")
            
            data = response.json()
            raw_text = data['choices'][0]['message']['content'].strip()
            cleaned_text = self._clean_response_text(raw_text)
            
            if not cleaned_text:
                logger.error("响应文本为空")
                return []
            
            vehicle_info = json.loads(cleaned_text)
            
            if isinstance(vehicle_info, dict):
                vehicle_info = [vehicle_info]
            
            if not isinstance(vehicle_info, list):
                logger.error(f"返回数据格式错误: {type(vehicle_info)}")
                return []
            
            results = []
            for vehicle in vehicle_info:
                validated = self._validate_vehicle_data(vehicle)
                result = RecognitionResult(
                    brand=validated['brand'],
                    model=validated['model'],
                    color=validated['color'],
                    confidence=validated['confidence'],
                    bbox=validated['bbox']
                )
                results.append(result)
            
            self._report_progress(progress_callback, kwargs.get('task_id', ''), 90, "获取购买建议...")
            
            for result in results:
                result.purchase_advice = self.get_purchase_advice(result.brand, result.model)
            
            self._report_progress(progress_callback, kwargs.get('task_id', ''), 100, "完成")
            logger.info(f"vLLM识别成功: {len(results)}辆车")
            return results
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {e}")
            return []
        except httpx.HTTPError as e:
            logger.error(f"vLLM HTTP请求失败: {e}")
            return []
        except Exception as e:
            logger.error(f"vLLM API调用失败: {e}")
            return []
    
    async def recognize_async(self, image_path: str, task_id: str, 
                             progress_callback: Optional[Callable] = None) -> List[RecognitionResult]:
        """异步识别"""
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, 
            self.recognize, 
            image_path, 
            task_id=task_id, 
            progress_callback=progress_callback
        )
    
    def get_purchase_advice(self, brand: str, model: str) -> Dict[str, Any]:
        """获取购买建议"""
        prompt = f"""请针对{brand}{model}生成购买建议，严格遵循以下格式：
1. 指导价：[具体价格，如20-30万元]
2. 用户体验：[20字内的用户体验描述]
3. 优缺点：[20字内的优缺点分析]
4. 购买指数：[五星制评分，如★★★★☆]

要求：
- 每行仅包含一个字段
- 总字数控制在80字以内
- 保持客观中立
- 不要添加额外说明"""
        
        try:
            payload = {
                "model": self.model_name,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 512,
                "temperature": 0.3
            }
            
            response = self.client.post("/chat/completions", json=payload)
            response.raise_for_status()
            
            data = response.json()
            model_text = data['choices'][0]['message']['content'].strip()
            return self._parse_advice(model_text)
            
        except Exception as e:
            logger.error(f"vLLM获取购买建议失败: {e}")
            return self._get_default_advice()
    
    def _parse_advice(self, text: str) -> Dict[str, Any]:
        """解析建议文本"""
        advice = self._get_default_advice()
        
        if not text or not isinstance(text, str):
            return advice
        
        text = text.strip()
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        for line in lines:
            line = line.replace(':', '：')
            
            if "指导价：" in line:
                advice["price"] = line.split("指导价：")[1].strip()
            elif "用户体验：" in line:
                advice["experience"] = line.split("用户体验：")[1].strip()[:30]
            elif "优缺点：" in line:
                advice["pros_cons"] = line.split("优缺点：")[1].strip()[:30]
            elif "购买指数：" in line:
                advice["rating"] = self._validate_rating(line.split("购买指数：")[1].strip())
        
        return advice
    
    def _validate_rating(self, rating: str) -> str:
        """验证购买指数格式"""
        import random
        
        star_count = rating.count('★') + rating.count('☆') * 0.5
        
        if 0 <= star_count <= 5:
            return rating
        
        default_ratings = ["★☆☆☆☆", "★★☆☆☆", "★★★☆☆", "★★★★☆", "★★★★★"]
        return random.choice(default_ratings)
    
    def _get_default_advice(self) -> Dict[str, Any]:
        """获取默认建议"""
        return {
            "price": "暂无数据",
            "experience": "数据获取中",
            "pros_cons": "暂无评价",
            "rating": "★★★☆☆",
            "official_url": ""
        }
    
    def health_check(self) -> bool:
        """健康检查"""
        try:
            response = self.client.get("/models")
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"vLLM健康检查失败: {e}")
            return False