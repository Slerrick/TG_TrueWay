import sqlite3
from contextlib import contextmanager
import os
class DatabaseManager:
    def __init__(self, db_path=None):
        if db_path is None:
            project_root = os.path.dirname(os.path.dirname(__file__))
            db_path = os.path.join(project_root, "data", "data.db")
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

    @contextmanager
    def connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def init_db(self):
        with self.connect() as conn:
            conn.executescript('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER UNIQUE,
                    login VARCHAR(20) UNIQUE,
                    password VARCHAR(20),
                    email VARCHAR(100),
                    role VARCHAR(10) DEFAULT 'student',
                    paid BOOLEAN DEFAULT 0,
                    paid_at DATETIME,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    status VARCHAR(20) DEFAULT 'active',
                    messages TEXT,
                    result_tracks TEXT,
                    result_review TEXT,
                    parent_code VARCHAR(10),
                    telegram_id INTEGER,  -- Для упрощения получения данных
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    completed_at DATETIME,
                    FOREIGN KEY(user_id) REFERENCES users(id)
                );
            ''')