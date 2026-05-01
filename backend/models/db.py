import sqlite3
import logging
from datetime import datetime
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class CarDatabase:
    """车辆数据库操作类"""

    def __init__(self, db_path):
        """
        初始化数据库连接

        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        self._create_tables()

    def _create_connection(self):
        """创建数据库连接"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            return conn
        except sqlite3.Error as e:
            logger.error(f"创建数据库连接失败: {e}")
            return None

    @contextmanager
    def get_cursor(self):
        """获取数据库游标的上下文管理器"""
        conn = self._create_connection()
        if not conn:
            yield None
            return
        
        cursor = None
        try:
            cursor = conn.cursor()
            yield cursor
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"数据库操作失败: {e}")
            yield None
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    def _create_tables(self):
        """创建必要的数据库表"""
        create_history_sql = """
        CREATE TABLE IF NOT EXISTS car_recognition_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            brand TEXT NOT NULL,
            model TEXT NOT NULL,
            color TEXT NOT NULL,
            confidence REAL NOT NULL,
            image_filename TEXT NOT NULL,
            bbox TEXT NULL,
            price TEXT NULL,
            experience TEXT NULL,
            pros_cons TEXT NULL,
            rating TEXT NULL,
            create_time DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """
        
        # 表结构说明：
        # id: 自增主键
        # brand: 车辆品牌
        # model: 车辆型号
        # color: 车辆颜色
        # confidence: 识别置信度
        # image_filename: 图片文件名
        # price: 指导价
        # experience: 用户体验
        # pros_cons: 优缺点
        # rating: 购买指数
        # create_time: 识别时间

        try:
            with self.get_cursor() as cursor:
                if cursor:
                    cursor.execute(create_history_sql)
                    logger.info("历史记录表创建/验证成功")
        except Exception as e:
            logger.error(f"创建表失败: {e}")

    def insert_history(self, **kwargs):
        """插入历史记录"""
        sql = """
        INSERT INTO car_recognition_history 
        (user_id, brand, model, color, confidence, image_filename, 
         bbox, price, experience, pros_cons, rating)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        params = (
            kwargs.get('user_id'),  # 新增：用户ID
            kwargs.get('brand', ''),
            kwargs.get('model', ''),
            kwargs.get('color', ''),
            float(kwargs.get('confidence', 0)),
            kwargs.get('image_filename', ''),
            kwargs.get('bbox') or None,
            kwargs.get('price') or None,
            kwargs.get('experience') or None,
            kwargs.get('pros_cons') or None,
            kwargs.get('rating') or None
        )

        try:
            with self.get_cursor() as cursor:
                if cursor:
                    cursor.execute(sql, params)
                    return cursor.lastrowid
        except Exception as e:
            logger.error(f"插入历史记录失败: {e}")
        return None

    def get_history_records(self, limit=100, user_id=None):
        """获取历史记录列表
        Args:
            limit: 返回记录数限制
            user_id: 用户ID，为None时返回所有记录（管理员用）
        """
        if user_id is not None:
            # 按用户查询
            query_sql = """
            SELECT id, brand, model, color, confidence, 
                   image_filename, create_time
            FROM car_recognition_history
            WHERE user_id = ?
            ORDER BY create_time DESC
            LIMIT ?
            """
            params = (user_id, limit)
        else:
            # 查询所有（兼容旧逻辑）
            query_sql = """
            SELECT id, brand, model, color, confidence, 
                   image_filename, create_time
            FROM car_recognition_history
            ORDER BY create_time DESC
            LIMIT ?
            """
            params = (limit,)

        try:
            with self.get_cursor() as cursor:
                if cursor:
                    cursor.execute(query_sql, params)
                    return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"查询历史记录失败: {e}")
        return []

    def get_history_by_id(self, record_id):
        """根据ID获取历史记录"""
        query_sql = """
        SELECT id, brand, model, color, confidence, 
               image_filename, bbox, create_time,
               price, experience, pros_cons, rating
        FROM car_recognition_history
        WHERE id = ?
        """

        try:
            with self.get_cursor() as cursor:
                if cursor:
                    cursor.execute(query_sql, (record_id,))
                    row = cursor.fetchone()
                    return dict(row) if row else None
        except Exception as e:
            logger.error(f"查询历史记录详情失败: {e}")
        return None

    def delete_history_by_id(self, record_id, user_id=None):
        """删除历史记录
        Args:
            record_id: 记录ID
            user_id: 用户ID，为None时不检查用户权限（管理员用）
        """
        if user_id is not None:
            # 普通用户只能删除自己的记录
            delete_sql = "DELETE FROM car_recognition_history WHERE id = ? AND user_id = ?"
            params = (record_id, user_id)
        else:
            # 管理员可删除任意记录
            delete_sql = "DELETE FROM car_recognition_history WHERE id = ?"
            params = (record_id,)

        try:
            with self.get_cursor() as cursor:
                if cursor:
                    cursor.execute(delete_sql, params)
                    affected_rows = cursor.rowcount
                    return {
                        'success': affected_rows > 0,
                        'affected_rows': affected_rows
                    }
        except Exception as e:
            logger.error(f"删除历史记录失败: {e}")
        return {'success': False, 'affected_rows': 0}

    def get_history_by_id_with_permission(self, record_id, user_id=None):
        """根据ID获取历史记录（带权限检查）
        Args:
            record_id: 记录ID
            user_id: 用户ID，为None时不检查权限（管理员用）
        Returns:
            记录字典，无权限或不存在返回None
        """
        query_sql = """
        SELECT id, brand, model, color, confidence, 
               image_filename, bbox, create_time,
               price, experience, pros_cons, rating, user_id
        FROM car_recognition_history
        WHERE id = ?
        """
        
        try:
            with self.get_cursor() as cursor:
                if cursor:
                    cursor.execute(query_sql, (record_id,))
                    row = cursor.fetchone()
                    if not row:
                        return None
                    
                    record = dict(row)
                    
                    # 检查权限
                    if user_id is not None and record.get('user_id') != user_id:
                        logger.warning(f"用户 {user_id} 尝试访问记录 {record_id} 被拒绝")
                        return None
                    
                    return record
        except Exception as e:
            logger.error(f"查询历史记录详情失败: {e}")
        return None
