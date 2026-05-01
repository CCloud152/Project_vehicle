import os
import base64
import json
import logging
from typing import Optional, List, Dict, Any
import ollama
from PIL import Image

logger = logging.getLogger(__name__)


class OllamaClient:
    """Ollama模型客户端"""

    def __init__(self, model_name: str):
        """
        初始化客户端

        Args:
            model_name: 模型名称
        """
        self.model_name = model_name

    def image_to_base64(self, image_path: str) -> Optional[str]:
        """将图片转换为Base64编码"""
        try:
            # 验证图片文件
            if not os.path.exists(image_path):
                logger.error(f"图片文件不存在: {image_path}")
                return None

            # 尝试打开图片验证格式
            try:
                with Image.open(image_path) as img:
                    img.verify()  # 验证图片完整性
            except Exception as e:
                logger.error(f"图片验证失败: {e}")
                return None

            # 转换为Base64
            with open(image_path, "rb") as f:
                image_data = f.read()

            # 检测图片格式
            img_format = self._detect_image_format(image_path)
            if not img_format:
                img_format = "jpeg"  # 默认格式

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

    def recognize_vehicle(self, image_path: str) -> Optional[List[Dict[str, Any]]]:
        """
        识别车辆信息

        Args:
            image_path: 图片路径

        Returns:
            车辆信息列表，识别失败返回None
        """
        # 转换图片为Base64
        image_base64 = self.image_to_base64(image_path)
        if not image_base64:
            return None

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
            # 调用Ollama API (使用chat接口)
            response = ollama.chat(
                model='qwen3-vl:8b',
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                        "images": [image_path]
                    }
                ],
                format="json"
            )

            # 解析响应
            logger.debug(f"完整API响应: {response}")
            raw_text = response.get('message', {}).get('content', '').strip()
            logger.debug(f"API原始响应: {raw_text}")

            # 清理响应文本
            cleaned_text = self._clean_response_text(raw_text)

            # 检查响应文本是否为空
            if not cleaned_text:
                logger.error("响应文本为空")
                return None

            # 解析JSON
            vehicle_info = json.loads(cleaned_text)

            # 验证数据结构
            if isinstance(vehicle_info, dict):
                vehicle_info = [vehicle_info]

            if not isinstance(vehicle_info, list):
                logger.error(f"返回数据格式错误: {type(vehicle_info)}")
                return None

            # 验证每个车辆信息
            for vehicle in vehicle_info:
                self._validate_vehicle_data(vehicle)

            logger.info(f"识别成功: {len(vehicle_info)}辆车")
            return vehicle_info

        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {e}")
            return None

        except Exception as e:
            logger.error(f"API调用失败: {e}")
            return None

    def get_purchase_advice(self, brand: str, model: str) -> Dict[str, Any]:
        """
        获取购买建议

        Args:
            brand: 车辆品牌
            model: 车辆型号

        Returns:
            购买建议字典
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
            # 调用Ollama API (使用chat接口)
            response = ollama.chat(
                model=self.model_name,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            # 解析响应
            model_text = response.get('message', {}).get('content', '').strip()
            advice = self._parse_advice(model_text)
            logger.info(f"获取购买建议成功: {brand} {model}")
            return advice

        except Exception as e:
            logger.error(f"获取购买建议失败: {e}")
            return self._get_default_advice()

    def _clean_response_text(self, text: str) -> str:
        """清理响应文本"""
        # 去除可能的代码块标记
        if text.startswith('```json'):
            text = text[7:]
        if text.endswith('```'):
            text = text[:-3]

        # 去除空白字符
        text = text.strip()

        # 处理常见的JSON格式问题
        text = text.replace('，', ',')  # 中文逗号转英文逗号
        text = text.replace('：', ':')  # 中文冒号转英文冒号

        return text

    def _validate_vehicle_data(self, vehicle: Dict[str, Any]):
        """验证车辆数据"""
        # 确保必要字段存在
        vehicle.setdefault('brand', '未知')
        vehicle.setdefault('model', '未知')
        vehicle.setdefault('color', '未知')
        vehicle.setdefault('confidence', 0.0)
        vehicle.setdefault('bbox', {})

        # 验证置信度
        try:
            confidence = float(vehicle['confidence'])
            if not 0 <= confidence <= 1:
                vehicle['confidence'] = 0.0
        except (ValueError, TypeError):
            vehicle['confidence'] = 0.0

        # 验证bbox
        bbox = vehicle['bbox']
        bbox.setdefault('x1', 0.0)
        bbox.setdefault('y1', 0.0)
        bbox.setdefault('x2', 1.0)
        bbox.setdefault('y2', 1.0)

        # 确保坐标在合理范围内
        for key in ['x1', 'y1', 'x2', 'y2']:
            try:
                value = float(bbox[key])
                if not 0 <= value <= 1:
                    bbox[key] = 0.0 if '1' in key else 1.0
            except (ValueError, TypeError):
                bbox[key] = 0.0 if '1' in key else 1.0

    def _parse_advice(self, text: str) -> Dict[str, Any]:
        """解析建议文本"""
        advice = self._get_default_advice()

        if not text or not isinstance(text, str):
            return advice

        # 预处理文本
        text = text.strip()
        lines = [line.strip() for line in text.split('\n') if line.strip()]

        for line in lines:
            # 统一冒号格式
            line = line.replace(':', '：')

            if "指导价：" in line:
                advice["price"] = line.split("指导价：")[1].strip()
            elif "用户体验：" in line:
                experience = line.split("用户体验：")[1].strip()
                advice["experience"] = experience[:30]  # 限制长度
            elif "优缺点：" in line:
                pros_cons = line.split("优缺点：")[1].strip()
                advice["pros_cons"] = pros_cons[:30]  # 限制长度
            elif "购买指数：" in line:
                rating = line.split("购买指数：")[1].strip()
                advice["rating"] = self._validate_rating(rating)

        return advice

    def _validate_rating(self, rating: str) -> str:
        """验证购买指数格式"""
        # 统计星号数量
        star_count = rating.count('★') + rating.count('☆') * 0.5

        if 0 <= star_count <= 5:
            return rating

        # 格式错误时返回默认
        default_ratings = ["★☆☆☆☆", "★★☆☆☆", "★★★☆☆", "★★★★☆", "★★★★★"]
        import random
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
