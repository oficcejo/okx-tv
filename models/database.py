import sqlite3
import click
from flask import current_app, g
from flask.cli import with_appcontext

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(
            'trading_bot.sqlite',
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row
    return g.db

def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    db = get_db()
    
    # 创建设置表
    db.execute('''
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )
    ''')
    
    # 创建交易记录表
    db.execute('''
    CREATE TABLE IF NOT EXISTS trades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        trading_pair TEXT,
        direction TEXT,
        amount REAL,
        price REAL,
        status TEXT,
        order_id TEXT,
        take_profit REAL,
        stop_loss REAL
    )
    ''')
    
    # 创建邮件记录表，避免重复处理
    db.execute('''
    CREATE TABLE IF NOT EXISTS processed_emails (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email_id TEXT UNIQUE,
        subject TEXT,
        sender TEXT,
        processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        trade_executed INTEGER DEFAULT 0
    )
    ''')
    
    db.commit() 