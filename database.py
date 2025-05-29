import sqlite3
from typing import Optional, List
from models import UserInfo
import hashlib

class DatabaseManager:
    def __init__(self, db_path='users.db'):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    password_md5 TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()
            conn.close()
            print(f"db init sucess {self.db_path}")
        except Exception as e:
            print(f"db init error : {e}")
    
    def validate_user(self, username: str, password_md5: str) -> Optional[int]:
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id FROM users 
                WHERE username = ? AND password_md5 = ?
            ''', (username, password_md5))
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return result[0]
            return None
        except Exception as e:
            print(f"db validation error: {e}")
            return None
    
    def get_user_info(self, user_id: int) -> Optional[UserInfo]:
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, username, created_at FROM users 
                WHERE id = ?
            ''', (user_id,))
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return UserInfo(
                    id=result[0],
                    username=result[1],
                    created_at=result[2]
                )
            return None
        except Exception as e:
            print(f"db user error: {e}")
            return None
    
    def get_all_users(self) -> List[UserInfo]:
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, username, created_at FROM users 
                ORDER BY created_at DESC
            ''')
            results = cursor.fetchall()
            conn.close()
            
            return [UserInfo(id=r[0], username=r[1], created_at=r[2]) for r in results]
        except Exception as e:
            print(f"db all users error: {e}")
            return []