import sqlite3
import logging
from datetime import datetime
from contextlib import contextmanager
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class UserModel:
    """用户数据模型"""
    
    def __init__(self, db_path):
        self.db_path = db_path
        self._create_tables()
        self._migrate_history_table()
    
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
        """创建用户表"""
        create_users_sql = """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE,
            password_hash TEXT NOT NULL,
            avatar_url TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            last_login_at DATETIME,
            is_active INTEGER DEFAULT 1
        );
        """
        
        # 创建token黑名单表（用于登出）
        create_token_blacklist_sql = """
        CREATE TABLE IF NOT EXISTS token_blacklist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token TEXT UNIQUE NOT NULL,
            expires_at DATETIME NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """
        
        try:
            with self.get_cursor() as cursor:
                if cursor:
                    cursor.execute(create_users_sql)
                    cursor.execute(create_token_blacklist_sql)
                    logger.info("用户表创建/验证成功")
        except Exception as e:
            logger.error(f"创建用户表失败: {e}")
    
    def _migrate_history_table(self):
        """迁移历史记录表，添加user_id字段"""
        try:
            with self.get_cursor() as cursor:
                if cursor:
                    # 检查是否已有user_id字段
                    cursor.execute("PRAGMA table_info(car_recognition_history)")
                    columns = [row['name'] for row in cursor.fetchall()]
                    
                    if 'user_id' not in columns:
                        # 添加user_id字段
                        cursor.execute("""
                            ALTER TABLE car_recognition_history 
                            ADD COLUMN user_id INTEGER DEFAULT NULL
                        """)
                        logger.info("历史记录表迁移成功：添加user_id字段")
                        
                        # 创建索引
                        cursor.execute("""
                            CREATE INDEX IF NOT EXISTS idx_history_user_id 
                            ON car_recognition_history(user_id)
                        """)
                        logger.info("创建历史记录user_id索引成功")
        except Exception as e:
            logger.error(f"迁移历史记录表失败: {e}")
    
    def create_user(self, username, password, email=None):
        """创建新用户"""
        password_hash = generate_password_hash(password)
        
        sql = """
        INSERT INTO users (username, email, password_hash)
        VALUES (?, ?, ?)
        """
        
        try:
            with self.get_cursor() as cursor:
                if cursor:
                    cursor.execute(sql, (username, email, password_hash))
                    user_id = cursor.lastrowid
                    logger.info(f"用户创建成功: {username} (ID: {user_id})")
                    return {
                        'id': user_id,
                        'username': username,
                        'email': email,
                        'created_at': datetime.now().isoformat()
                    }
        except sqlite3.IntegrityError as e:
            if 'username' in str(e):
                logger.warning(f"用户名已存在: {username}")
                return None
            if 'email' in str(e):
                logger.warning(f"邮箱已存在: {email}")
                return None
        except Exception as e:
            logger.error(f"创建用户失败: {e}")
        
        return None
    
    def get_user_by_username(self, username):
        """根据用户名获取用户信息"""
        sql = """
        SELECT id, username, email, password_hash, avatar_url, 
               created_at, last_login_at, is_active
        FROM users
        WHERE username = ? AND is_active = 1
        """
        
        try:
            with self.get_cursor() as cursor:
                if cursor:
                    cursor.execute(sql, (username,))
                    row = cursor.fetchone()
                    if row:
                        return dict(row)
        except Exception as e:
            logger.error(f"查询用户失败: {e}")
        
        return None
    
    def get_user_by_id(self, user_id):
        """根据ID获取用户信息（不包含密码）"""
        sql = """
        SELECT id, username, email, avatar_url, 
               created_at, last_login_at, is_active
        FROM users
        WHERE id = ? AND is_active = 1
        """
        
        try:
            with self.get_cursor() as cursor:
                if cursor:
                    cursor.execute(sql, (user_id,))
                    row = cursor.fetchone()
                    if row:
                        return dict(row)
        except Exception as e:
            logger.error(f"查询用户失败: {e}")
        
        return None
    
    def verify_password(self, username, password):
        """验证用户密码"""
        user = self.get_user_by_username(username)
        if not user:
            return None
        
        if check_password_hash(user['password_hash'], password):
            # 更新最后登录时间
            self._update_last_login(user['id'])
            return {
                'id': user['id'],
                'username': user['username'],
                'email': user['email'],
                'avatar_url': user['avatar_url'],
                'created_at': user['created_at'],
                'last_login_at': datetime.now().isoformat()
            }
        
        return None
    
    def _update_last_login(self, user_id):
        """更新最后登录时间"""
        sql = """
        UPDATE users 
        SET last_login_at = CURRENT_TIMESTAMP,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """
        
        try:
            with self.get_cursor() as cursor:
                if cursor:
                    cursor.execute(sql, (user_id,))
        except Exception as e:
            logger.error(f"更新登录时间失败: {e}")
    
    def update_user(self, user_id, **kwargs):
        """更新用户信息"""
        allowed_fields = ['email', 'avatar_url']
        updates = []
        values = []
        
        for field in allowed_fields:
            if field in kwargs:
                updates.append(f"{field} = ?")
                values.append(kwargs[field])
        
        if not updates:
            return False
        
        values.append(user_id)
        sql = f"""
        UPDATE users 
        SET {', '.join(updates)}, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """
        
        try:
            with self.get_cursor() as cursor:
                if cursor:
                    cursor.execute(sql, values)
                    return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"更新用户信息失败: {e}")
        
        return False
    
    def change_password(self, user_id, old_password, new_password):
        """修改密码"""
        # 先验证旧密码
        sql = "SELECT password_hash FROM users WHERE id = ?"
        
        try:
            with self.get_cursor() as cursor:
                if cursor:
                    cursor.execute(sql, (user_id,))
                    row = cursor.fetchone()
                    if not row:
                        return False, "用户不存在"
                    
                    if not check_password_hash(row['password_hash'], old_password):
                        return False, "原密码错误"
                    
                    # 更新密码
                    new_hash = generate_password_hash(new_password)
                    cursor.execute("""
                        UPDATE users 
                        SET password_hash = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """, (new_hash, user_id))
                    
                    return True, "密码修改成功"
        except Exception as e:
            logger.error(f"修改密码失败: {e}")
            return False, "修改失败"
        
        return False, "修改失败"
    
    def add_token_to_blacklist(self, token, expires_at):
        """将token加入黑名单（用于登出）"""
        sql = """
        INSERT OR REPLACE INTO token_blacklist (token, expires_at)
        VALUES (?, ?)
        """
        
        try:
            with self.get_cursor() as cursor:
                if cursor:
                    cursor.execute(sql, (token, expires_at))
                    return True
        except Exception as e:
            logger.error(f"添加token到黑名单失败: {e}")
        
        return False
    
    def is_token_blacklisted(self, token):
        """检查token是否在黑名单中"""
        sql = """
        SELECT 1 FROM token_blacklist 
        WHERE token = ? AND expires_at > CURRENT_TIMESTAMP
        """
        
        try:
            with self.get_cursor() as cursor:
                if cursor:
                    cursor.execute(sql, (token,))
                    return cursor.fetchone() is not None
        except Exception as e:
            logger.error(f"检查token黑名单失败: {e}")
        
        return False
    
    def cleanup_expired_tokens(self):
        """清理过期的黑名单token"""
        sql = "DELETE FROM token_blacklist WHERE expires_at < CURRENT_TIMESTAMP"
        
        try:
            with self.get_cursor() as cursor:
                if cursor:
                    cursor.execute(sql)
                    deleted = cursor.rowcount
                    if deleted > 0:
                        logger.info(f"清理过期token: {deleted}个")
                    return deleted
        except Exception as e:
            logger.error(f"清理过期token失败: {e}")
        
        return 0