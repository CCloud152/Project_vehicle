"""
Ollama本地推理服务实现
"""

import os
import json
import logging
import base64
from typing import Optional, List, Dict, Any, Callable
import ollama
from PIL import Image

from .base_service import BaseModelService, RecognitionResult

logger = logging.getLogger(__name__)


class OllamaService(BaseModelService):
    """Ollama本地推理服务"""
    
    def __init__(self, model_name: str = 'qwen3-vl:8b'):
        super().__init__(f"OllamaService-{model_name}")
        self.model_name = model_name
        self.client = ollama
        
    def _image_to_base64(self, image_path: str) -> Optional[str]:
        """将图片转换为Base64编码"""
        try:
            if not os.path.exists(image_path):
                logger.error(f"图片文件不存在: {image_path}")
                return None
            
            # 验证图片格式
            try:
                with Image.open(image_path) as img:
                    img.verify()
            except Exception as e:
                logger.error(f"图片验证失败: {e}")
                return None
            
            # 读取并编码
            with open(image_path, "rb") as f:
                image_data = f.read()
            
            # 检测图片格式
            img_format = self._detect_image_format(image_path) or "jpeg"
            base64_data = base64.b64encode(image_data).decode("utf-8")
            return f"data:image/{img_format};base64,{base64_data}"
            
        except Exception as e:
            logger.error(f"图片转换失败: {e}")
            return None
    
    def _detect_image_format(self, image_path: str) -> Optional[str]:
        """检测图片格式"""
        try:
            with Image.open(image_path) as img:
                return img.format.lower() if img.format else None
        except:
            return None
    
    def _clean_response_text(self, text: str) -> str:
        """清理响应文本"""
        # 去除代码块标记
        if text.startswith('```json'):
            text = text[7:]
        if text.endswith('```'):
            text = text[:-3]
        
        text = text.strip()
        
        # 处理常见格式问题
        text = text.replace('，', ',')
        text = text.replace('：', ':')
        
        return text
    
    def _validate_vehicle_data(self, vehicle: Dict[str, Any]) -> Dict[str, Any]:
        """验证并补全车辆数据"""
        # 处理brand和model的智能提取
        brand = str(vehicle.get('brand', '')).strip() if vehicle.get('brand') else ''
        model = str(vehicle.get('model', '')).strip() if vehicle.get('model') else ''
        color = str(vehicle.get('color', '')).strip() if vehicle.get('color') else ''
        
        # 如果brand为空或等于model，尝试从model中提取
        if not brand or brand == '未知' or brand.lower() == model.lower():
            if model and model != '未知':
                import re
                # 尝试匹配中文品牌（2-4字）或英文品牌
                match = re.match(r'^([\u4e00-\u9fa5]{2,4}|[A-Za-z][A-Za-z0-9]*)', model)
                if match:
                    extracted_brand = match.group(1)
                    # 如果提取的品牌和原model不同，则拆分
                    if len(extracted_brand) < len(model):
                        brand = extracted_brand
                        model = model[len(extracted_brand):].strip()
                    else:
                        brand = extracted_brand
        
        vehicle['brand'] = brand if brand else '未知'
        vehicle['model'] = model if model else '未知'
        vehicle['color'] = color if color else '未知'
        vehicle.setdefault('confidence', 0.0)
        vehicle.setdefault('bbox', {})
        
        # 验证置信度
        try:
            confidence = float(vehicle['confidence'])
            vehicle['confidence'] = max(0.0, min(1.0, confidence))
        except (ValueError, TypeError):
            vehicle['confidence'] = 0.0
        
        # 验证bbox
        bbox = vehicle['bbox']
        bbox.setdefault('x1', 0.0)
        bbox.setdefault('y1', 0.0)
        bbox.setdefault('x2', 1.0)
        bbox.setdefault('y2', 1.0)
        
        # 确保坐标在合理范围
        for key in ['x1', 'y1', 'x2', 'y2']:
            try:
                value = float(bbox[key])
                bbox[key] = max(0.0, min(1.0, value))
            except (ValueError, TypeError):
                bbox[key] = 0.0 if '1' in key else 1.0
        
        return vehicle
    
    def recognize(self, image_path: str, **kwargs) -> List[RecognitionResult]:
        """
        同步识别车辆
        """
        if not self._validate_image(image_path):
            return []
        
        progress_callback = kwargs.get('progress_callback')
        self._report_progress(progress_callback, kwargs.get('task_id', ''), 10, "准备识别...")
        
        # 转换图片为Base64
        image_base64 = self._image_to_base64(image_path)
        if not image_base64:
            return []
        
        self._report_progress(progress_callback, kwargs.get('task_id', ''), 30, "调用模型...")
        
        # 构造提示词
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
            # 调用Ollama API
            response = self.client.chat(
                model=self.model_name,
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                        "images": [image_path]
                    }
                ],
                format="json"
            )
            
            self._report_progress(progress_callback, kwargs.get('task_id', ''), 70, "解析结果...")
            
            # 解析响应
            raw_text = response.get('message', {}).get('content', '').strip()
            cleaned_text = self._clean_response_text(raw_text)
            
            if not cleaned_text:
                logger.error("响应文本为空")
                return []
            
            # 解析JSON
            vehicle_info = json.loads(cleaned_text)
            
            # 统一为列表格式
            if isinstance(vehicle_info, dict):
                vehicle_info = [vehicle_info]
            
            if not isinstance(vehicle_info, list):
                logger.error(f"返回数据格式错误: {type(vehicle_info)}")
                return []
            
            # 验证每个车辆数据
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
            
            # 获取购买建议
            for result in results:
                result.purchase_advice = self.get_purchase_advice(result.brand, result.model)
            
            self._report_progress(progress_callback, kwargs.get('task_id', ''), 100, "完成")
            logger.info(f"识别成功: {len(results)}辆车")
            return results
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {e}")
            return []
        except Exception as e:
            logger.error(f"API调用失败: {e}")
            return []
    
    async def recognize_async(self, image_path: str, task_id: str, 
                             progress_callback: Optional[Callable] = None) -> List[RecognitionResult]:
        """
        异步识别（实际调用同步方法，Ollama不支持真正的异步）
        """
        return self.recognize(image_path, task_id=task_id, progress_callback=progress_callback)
    
    def get_purchase_advice(self, brand: str, model: str) -> Dict[str, Any]:
        """
        获取购买建议
        """
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
            response = self.client.chat(
                model=self.model_name,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            
            model_text = response.get('message', {}).get('content', '').strip()
            return self._parse_advice(model_text)
            
        except Exception as e:
            logger.error(f"获取购买建议失败: {e}")
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
                experience = line.split("用户体验：")[1].strip()
                advice["experience"] = experience[:30]
            elif "优缺点：" in line:
                pros_cons = line.split("优缺点：")[1].strip()
                advice["pros_cons"] = pros_cons[:30]
            elif "购买指数：" in line:
                rating = line.split("购买指数：")[1].strip()
                advice["rating"] = self._validate_rating(rating)
        
        return advice
    
    def _validate_rating(self, rating: str) -> str:
        """验证购买指数格式"""
        import random
        import re
        
        if not rating or not isinstance(rating, str):
            return "★★★☆☆"
        
        # 清理文本
        rating = rating.strip()
        
        # 统计星星
        full_stars = rating.count('★')
        half_stars = rating.count('☆')
        other_chars = len([c for c in rating if c not in ['★', '☆', ' ']])
        
        # 如果包含其他字符，尝试提取数字
        if other_chars > 0 or (full_stars + half_stars) == 0:
            numbers = re.findall(r'\d+\.?\d*', rating)
            if numbers:
                try:
                    score = float(numbers[0])
                    if 0 <= score <= 5:
                        full = int(score)
                        has_half = (score - full) >= 0.5
                        return '★' * full + ('☆' if has_half else '') + '☆' * (5 - full - (1 if has_half else 0))
                except:
                    pass
            return "★★★☆☆"
        
        # 确保总共5个星星
        total = full_stars + half_stars
        if total < 5:
            return '★' * full_stars + '☆' * half_stars + '☆' * (5 - total)
        elif total > 5:
            # 优先保留实星
            if full_stars >= 5:
                return '★' * 5
            else:
                return '★' * full_stars + '☆' * (5 - full_stars)
        
        return rating
    
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
        """
        健康检查
        """
        try:
            # 尝试列出模型
            self.client.list()
            return True
        except Exception as e:
            logger.error(f"Ollama健康检查失败: {e}")
            return False