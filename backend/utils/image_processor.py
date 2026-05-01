import os
import logging
from PIL import Image
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


def allowed_file(filename: str) -> bool:
    """检查文件是否为允许的图片格式"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'bmp', 'webp'}


def validate_image(image_path: str) -> Tuple[bool, str]:
    """
    验证图像文件

    Args:
        image_path: 图像路径

    Returns:
        (是否有效, 错误信息)
    """
    try:
        # 检查文件是否存在
        if not os.path.exists(image_path):
            return False, "文件不存在"

        # 检查文件大小
        file_size = os.path.getsize(image_path)
        if file_size > 10 * 1024 * 1024:  # 10MB
            return False, "文件过大"

        # 尝试打开图像
        with Image.open(image_path) as img:
            img.verify()  # 验证图像完整性

            # 检查图像尺寸
            if img.width > 5000 or img.height > 5000:
                return False, "图像尺寸过大"

            if img.width < 50 or img.height < 50:
                return False, "图像尺寸过小"

        return True, "图像有效"

    except Exception as e:
        return False, f"图像验证失败: {str(e)}"


def resize_image(image_path: str, output_path: str, max_size: Tuple[int, int] = (800, 800)) -> bool:
    """
    调整图像大小

    Args:
        image_path: 输入图像路径
        output_path: 输出图像路径
        max_size: 最大尺寸 (width, height)

    Returns:
        是否成功
    """
    try:
        img = Image.open(image_path).convert('RGB')

        # 计算缩放比例
        width, height = img.size
        max_width, max_height = max_size

        if width > max_width or height > max_height:
            ratio = min(max_width / width, max_height / height)
            new_size = (int(width * ratio), int(height * ratio))
            img = img.resize(new_size, Image.Resampling.LANCZOS)

        img.save(output_path, quality=85)
        return True

    except Exception as e:
        logger.error(f"图像调整失败: {e}")
        return False


def get_image_info(file_path: str) -> Optional[dict]:
    """
    获取图像信息

    Args:
        file_path: 图像路径

    Returns:
        图像信息字典
    """
    try:
        with Image.open(file_path) as img:
            return {
                'format': img.format,
                'size': img.size,
                'mode': img.mode,
                'width': img.width,
                'height': img.height
            }
    except Exception as e:
        logger.error(f"获取图像信息失败: {e}")
        return None
