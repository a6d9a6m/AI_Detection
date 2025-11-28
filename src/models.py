"""
数据库模型定义
使用SQLite作为轻量级数据库
"""

import sqlite3
import json
import hashlib
import secrets
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path
import os

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'database.db')


class Database:
    """数据库管理类"""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.init_database()

    def get_connection(self):
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_database(self):
        """初始化数据库表"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # 用户表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                email TEXT,
                role TEXT DEFAULT 'user',
                tenant_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 租户表（多租户支持）
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tenants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                logo_url TEXT,
                brand_color TEXT,
                resource_quota TEXT,
                billing_plan TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 声纹数据表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS voiceprint_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                tenant_id INTEGER,
                filename TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_size INTEGER,
                file_format TEXT,
                duration REAL,
                sample_rate INTEGER,
                machine_type TEXT,
                section TEXT,
                metadata TEXT,
                tags TEXT,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (tenant_id) REFERENCES tenants(id)
            )
        ''')

        # 特征数据表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS feature_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                voiceprint_id INTEGER NOT NULL,
                feature_type TEXT,
                feature_params TEXT,
                feature_path TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (voiceprint_id) REFERENCES voiceprint_data(id)
            )
        ''')

        # 模型表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS models (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                tenant_id INTEGER,
                name TEXT NOT NULL,
                version TEXT NOT NULL,
                machine_type TEXT NOT NULL,
                model_type TEXT,
                model_path TEXT NOT NULL,
                config TEXT,
                metrics TEXT,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (tenant_id) REFERENCES tenants(id),
                UNIQUE(name, version, tenant_id)
            )
        ''')

        # 训练任务表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS training_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                tenant_id INTEGER,
                name TEXT NOT NULL,
                machine_type TEXT NOT NULL,
                model_id INTEGER,
                config TEXT,
                status TEXT DEFAULT 'pending',
                progress REAL DEFAULT 0.0,
                log_path TEXT,
                result TEXT,
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (tenant_id) REFERENCES tenants(id),
                FOREIGN KEY (model_id) REFERENCES models(id)
            )
        ''')

        # 报告表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                tenant_id INTEGER,
                title TEXT NOT NULL,
                report_type TEXT,
                model_id INTEGER,
                template_id INTEGER,
                content TEXT,
                file_path TEXT,
                status TEXT DEFAULT 'generated',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (tenant_id) REFERENCES tenants(id),
                FOREIGN KEY (model_id) REFERENCES models(id),
                FOREIGN KEY (template_id) REFERENCES report_templates(id)
            )
        ''')

        # 报告模板表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS report_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                tenant_id INTEGER,
                name TEXT NOT NULL,
                description TEXT,
                template_content TEXT NOT NULL,
                fields TEXT,
                chart_config TEXT,
                style_config TEXT,
                language TEXT DEFAULT 'zh_CN',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (tenant_id) REFERENCES tenants(id)
            )
        ''')

        # API密钥表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS api_keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                tenant_id INTEGER,
                key_hash TEXT UNIQUE NOT NULL,
                key_prefix TEXT NOT NULL,
                name TEXT,
                permissions TEXT,
                rate_limit INTEGER DEFAULT 1000,
                expires_at TIMESTAMP,
                last_used_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (tenant_id) REFERENCES tenants(id)
            )
        ''')

        # 计费记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS billing_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                tenant_id INTEGER,
                resource_type TEXT NOT NULL,
                quantity REAL NOT NULL,
                unit_price REAL NOT NULL,
                total_amount REAL NOT NULL,
                billing_cycle TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (tenant_id) REFERENCES tenants(id)
            )
        ''')

        # 审计日志表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                tenant_id INTEGER,
                action TEXT NOT NULL,
                resource_type TEXT,
                resource_id INTEGER,
                details TEXT,
                ip_address TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (tenant_id) REFERENCES tenants(id)
            )
        ''')

        # 服务监控表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS service_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                metric_type TEXT NOT NULL,
                metric_value REAL NOT NULL,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 告警表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                message TEXT NOT NULL,
                details TEXT,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                resolved_at TIMESTAMP
            )
        ''')

        conn.commit()
        conn.close()

        # 创建默认管理员用户和租户
        self.create_default_data()

    def create_default_data(self):
        """创建默认数据"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # 检查是否已有默认租户
        cursor.execute("SELECT id FROM tenants WHERE name = ?", ('Default Tenant',))
        if not cursor.fetchone():
            cursor.execute('''
                INSERT INTO tenants (name, resource_quota, billing_plan)
                VALUES (?, ?, ?)
            ''', ('Default Tenant', '{"storage": 10000, "compute": 1000}', 'free'))
            tenant_id = cursor.lastrowid
        else:
            cursor.execute("SELECT id FROM tenants WHERE name = ?", ('Default Tenant',))
            tenant_id = cursor.fetchone()[0]

        # 检查是否已有管理员用户
        cursor.execute("SELECT id FROM users WHERE username = ?", ('admin',))
        if not cursor.fetchone():
            password_hash = hashlib.sha256('admin123'.encode()).hexdigest()
            cursor.execute('''
                INSERT INTO users (username, password_hash, email, role, tenant_id)
                VALUES (?, ?, ?, ?, ?)
            ''', ('admin', password_hash, 'admin@example.com', 'admin', tenant_id))

        conn.commit()
        conn.close()


class User:
    """用户模型"""

    @staticmethod
    def create(username: str, password: str, email: str = None,
               role: str = 'user', tenant_id: int = None) -> Optional[int]:
        """创建用户"""
        db = Database()
        conn = db.get_connection()
        cursor = conn.cursor()

        password_hash = hashlib.sha256(password.encode()).hexdigest()

        try:
            cursor.execute('''
                INSERT INTO users (username, password_hash, email, role, tenant_id)
                VALUES (?, ?, ?, ?, ?)
            ''', (username, password_hash, email, role, tenant_id))
            conn.commit()
            user_id = cursor.lastrowid
            conn.close()
            return user_id
        except sqlite3.IntegrityError:
            conn.close()
            return None

    @staticmethod
    def authenticate(username: str, password: str) -> Optional[Dict]:
        """用户认证"""
        db = Database()
        conn = db.get_connection()
        cursor = conn.cursor()

        password_hash = hashlib.sha256(password.encode()).hexdigest()
        cursor.execute('''
            SELECT id, username, email, role, tenant_id
            FROM users
            WHERE username = ? AND password_hash = ?
        ''', (username, password_hash))

        row = cursor.fetchone()
        conn.close()

        if row:
            return dict(row)
        return None

    @staticmethod
    def get_by_id(user_id: int) -> Optional[Dict]:
        """通过ID获取用户"""
        db = Database()
        conn = db.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, username, email, role, tenant_id, created_at
            FROM users
            WHERE id = ?
        ''', (user_id,))

        row = cursor.fetchone()
        conn.close()

        if row:
            return dict(row)
        return None


class VoiceprintData:
    """声纹数据模型"""

    @staticmethod
    def create(user_id: int, filename: str, file_path: str,
               tenant_id: int = None, **kwargs) -> int:
        """创建声纹数据记录"""
        db = Database()
        conn = db.get_connection()
        cursor = conn.cursor()

        metadata = json.dumps(kwargs.get('metadata', {}))
        tags = json.dumps(kwargs.get('tags', []))

        cursor.execute('''
            INSERT INTO voiceprint_data
            (user_id, tenant_id, filename, file_path, file_size, file_format,
             duration, sample_rate, machine_type, section, metadata, tags)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, tenant_id, filename, file_path, kwargs.get('file_size'),
              kwargs.get('file_format'), kwargs.get('duration'),
              kwargs.get('sample_rate'), kwargs.get('machine_type'),
              kwargs.get('section'), metadata, tags))

        conn.commit()
        data_id = cursor.lastrowid
        conn.close()

        return data_id

    @staticmethod
    def get_by_id(data_id: int) -> Optional[Dict]:
        """通过ID获取声纹数据"""
        db = Database()
        conn = db.get_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM voiceprint_data WHERE id = ?', (data_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            result = dict(row)
            result['metadata'] = json.loads(result.get('metadata', '{}'))
            result['tags'] = json.loads(result.get('tags', '[]'))
            return result
        return None

    @staticmethod
    def list_all(user_id: int = None, tenant_id: int = None,
                 limit: int = 100, offset: int = 0) -> List[Dict]:
        """列出所有声纹数据"""
        db = Database()
        conn = db.get_connection()
        cursor = conn.cursor()

        query = 'SELECT * FROM voiceprint_data WHERE 1=1'
        params = []

        if user_id:
            query += ' AND user_id = ?'
            params.append(user_id)

        if tenant_id:
            query += ' AND tenant_id = ?'
            params.append(tenant_id)

        query += ' ORDER BY uploaded_at DESC LIMIT ? OFFSET ?'
        params.extend([limit, offset])

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        results = []
        for row in rows:
            result = dict(row)
            result['metadata'] = json.loads(result.get('metadata', '{}'))
            result['tags'] = json.loads(result.get('tags', '[]'))
            results.append(result)

        return results

    @staticmethod
    def search(query: str, user_id: int = None, tenant_id: int = None) -> List[Dict]:
        """搜索声纹数据"""
        db = Database()
        conn = db.get_connection()
        cursor = conn.cursor()

        sql = '''
            SELECT * FROM voiceprint_data
            WHERE (filename LIKE ? OR machine_type LIKE ? OR section LIKE ?)
        '''
        params = [f'%{query}%', f'%{query}%', f'%{query}%']

        if user_id:
            sql += ' AND user_id = ?'
            params.append(user_id)

        if tenant_id:
            sql += ' AND tenant_id = ?'
            params.append(tenant_id)

        sql += ' ORDER BY uploaded_at DESC'

        cursor.execute(sql, params)
        rows = cursor.fetchall()
        conn.close()

        results = []
        for row in rows:
            result = dict(row)
            result['metadata'] = json.loads(result.get('metadata', '{}'))
            result['tags'] = json.loads(result.get('tags', '[]'))
            results.append(result)

        return results

    @staticmethod
    def delete(data_id: int) -> bool:
        """删除声纹数据"""
        db = Database()
        conn = db.get_connection()
        cursor = conn.cursor()

        # 获取文件路径以便删除文件
        cursor.execute('SELECT file_path FROM voiceprint_data WHERE id = ?', (data_id,))
        row = cursor.fetchone()

        if row:
            file_path = row['file_path']
            if os.path.exists(file_path):
                os.remove(file_path)

            cursor.execute('DELETE FROM voiceprint_data WHERE id = ?', (data_id,))
            conn.commit()
            conn.close()
            return True

        conn.close()
        return False


class Model:
    """模型模型"""

    @staticmethod
    def create(user_id: int, name: str, version: str, machine_type: str,
               model_path: str, tenant_id: int = None, **kwargs) -> int:
        """创建模型记录"""
        db = Database()
        conn = db.get_connection()
        cursor = conn.cursor()

        config = json.dumps(kwargs.get('config', {}))
        metrics = json.dumps(kwargs.get('metrics', {}))

        try:
            cursor.execute('''
                INSERT INTO models
                (user_id, tenant_id, name, version, machine_type, model_type,
                 model_path, config, metrics, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, tenant_id, name, version, machine_type,
                  kwargs.get('model_type', 'mobilenetv2'), model_path,
                  config, metrics, kwargs.get('status', 'active')))

            conn.commit()
            model_id = cursor.lastrowid
            conn.close()
            return model_id
        except sqlite3.IntegrityError:
            conn.close()
            return None

    @staticmethod
    def get_by_id(model_id: int) -> Optional[Dict]:
        """通过ID获取模型"""
        db = Database()
        conn = db.get_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM models WHERE id = ?', (model_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            result = dict(row)
            result['config'] = json.loads(result.get('config', '{}'))
            result['metrics'] = json.loads(result.get('metrics', '{}'))
            return result
        return None

    @staticmethod
    def list_all(user_id: int = None, tenant_id: int = None,
                 machine_type: str = None) -> List[Dict]:
        """列出所有模型"""
        db = Database()
        conn = db.get_connection()
        cursor = conn.cursor()

        query = 'SELECT * FROM models WHERE 1=1'
        params = []

        if user_id:
            query += ' AND user_id = ?'
            params.append(user_id)

        if tenant_id:
            query += ' AND tenant_id = ?'
            params.append(tenant_id)

        if machine_type:
            query += ' AND machine_type = ?'
            params.append(machine_type)

        query += ' ORDER BY created_at DESC'

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        results = []
        for row in rows:
            result = dict(row)
            result['config'] = json.loads(result.get('config', '{}'))
            result['metrics'] = json.loads(result.get('metrics', '{}'))
            results.append(result)

        return results


class Report:
    """报告模型"""

    @staticmethod
    def create(user_id: int, title: str, report_type: str,
               tenant_id: int = None, **kwargs) -> int:
        """创建报告记录"""
        db = Database()
        conn = db.get_connection()
        cursor = conn.cursor()

        content = json.dumps(kwargs.get('content', {}))

        cursor.execute('''
            INSERT INTO reports
            (user_id, tenant_id, title, report_type, model_id, template_id,
             content, file_path, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, tenant_id, title, report_type, kwargs.get('model_id'),
              kwargs.get('template_id'), content, kwargs.get('file_path'),
              kwargs.get('status', 'generated')))

        conn.commit()
        report_id = cursor.lastrowid
        conn.close()

        return report_id

    @staticmethod
    def get_by_id(report_id: int) -> Optional[Dict]:
        """通过ID获取报告"""
        db = Database()
        conn = db.get_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM reports WHERE id = ?', (report_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            result = dict(row)
            result['content'] = json.loads(result.get('content', '{}'))
            return result
        return None

    @staticmethod
    def list_all(user_id: int = None, tenant_id: int = None) -> List[Dict]:
        """列出所有报告"""
        db = Database()
        conn = db.get_connection()
        cursor = conn.cursor()

        query = 'SELECT * FROM reports WHERE 1=1'
        params = []

        if user_id:
            query += ' AND user_id = ?'
            params.append(user_id)

        if tenant_id:
            query += ' AND tenant_id = ?'
            params.append(tenant_id)

        query += ' ORDER BY created_at DESC'

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        results = []
        for row in rows:
            result = dict(row)
            result['content'] = json.loads(result.get('content', '{}'))
            results.append(result)

        return results


class APIKey:
    """API密钥模型"""

    @staticmethod
    def generate_key() -> tuple:
        """生成API密钥"""
        key = secrets.token_urlsafe(32)
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        key_prefix = key[:8]
        return key, key_hash, key_prefix

    @staticmethod
    def create(user_id: int, name: str, tenant_id: int = None, **kwargs) -> tuple:
        """创建API密钥"""
        db = Database()
        conn = db.get_connection()
        cursor = conn.cursor()

        key, key_hash, key_prefix = APIKey.generate_key()
        permissions = json.dumps(kwargs.get('permissions', ['read', 'write']))

        cursor.execute('''
            INSERT INTO api_keys
            (user_id, tenant_id, key_hash, key_prefix, name, permissions,
             rate_limit, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, tenant_id, key_hash, key_prefix, name, permissions,
              kwargs.get('rate_limit', 1000), kwargs.get('expires_at')))

        conn.commit()
        key_id = cursor.lastrowid
        conn.close()

        return key_id, key

    @staticmethod
    def verify(key: str) -> Optional[Dict]:
        """验证API密钥"""
        db = Database()
        conn = db.get_connection()
        cursor = conn.cursor()

        key_hash = hashlib.sha256(key.encode()).hexdigest()

        cursor.execute('''
            SELECT * FROM api_keys
            WHERE key_hash = ? AND (expires_at IS NULL OR expires_at > datetime('now'))
        ''', (key_hash,))

        row = cursor.fetchone()

        if row:
            # 更新最后使用时间
            cursor.execute('''
                UPDATE api_keys SET last_used_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (row['id'],))
            conn.commit()

            result = dict(row)
            result['permissions'] = json.loads(result.get('permissions', '[]'))
            conn.close()
            return result

        conn.close()
        return None


class AuditLog:
    """审计日志模型"""

    @staticmethod
    def log(action: str, user_id: int = None, tenant_id: int = None, **kwargs):
        """记录审计日志"""
        db = Database()
        conn = db.get_connection()
        cursor = conn.cursor()

        details = json.dumps(kwargs.get('details', {}))

        cursor.execute('''
            INSERT INTO audit_logs
            (user_id, tenant_id, action, resource_type, resource_id, details, ip_address)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, tenant_id, action, kwargs.get('resource_type'),
              kwargs.get('resource_id'), details, kwargs.get('ip_address')))

        conn.commit()
        conn.close()

    @staticmethod
    def get_logs(user_id: int = None, tenant_id: int = None,
                 limit: int = 100) -> List[Dict]:
        """获取审计日志"""
        db = Database()
        conn = db.get_connection()
        cursor = conn.cursor()

        query = 'SELECT * FROM audit_logs WHERE 1=1'
        params = []

        if user_id:
            query += ' AND user_id = ?'
            params.append(user_id)

        if tenant_id:
            query += ' AND tenant_id = ?'
            params.append(tenant_id)

        query += ' ORDER BY created_at DESC LIMIT ?'
        params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        results = []
        for row in rows:
            result = dict(row)
            result['details'] = json.loads(result.get('details', '{}'))
            results.append(result)

        return results


# 初始化数据库
if __name__ == '__main__':
    db = Database()
    print("Database initialized successfully!")
    print(f"Database path: {DB_PATH}")
