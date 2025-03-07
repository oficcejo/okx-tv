import os
import logging
import threading
import time
import datetime
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from werkzeug.middleware.proxy_fix import ProxyFix
from models.database import init_db, get_db, close_db
from services.email_service import start_email_checker, stop_email_checker, test_email_connection, get_recent_emails
from services.trading_service import execute_trade, test_api_connection, get_account_info, test_trade_cycle

# 创建Flask应用
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your_secret_key')  # 使用环境变量或默认值

# 支持反向代理
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

# 配置日志
if not os.path.exists('logs'):
    os.makedirs('logs')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join('logs', 'app.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 全局变量
email_checker_thread = None
email_checker_running = False
start_time = None
last_check_time = None

# 错误处理
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    logger.error(f"服务器错误: {str(e)}")
    return render_template('500.html'), 500

# 检查是否需要重置数据库
def reset_database_if_needed():
    """如果数据库结构有问题，则重置数据库"""
    try:
        # 尝试查询processed_emails表
        db = get_db()
        db.execute('SELECT * FROM processed_emails LIMIT 1')
    except sqlite3.OperationalError as e:
        if 'no such column' in str(e):
            logger.warning("检测到数据库结构问题，正在重置数据库...")
            # 删除旧的数据库文件
            if os.path.exists('trading_bot.sqlite'):
                os.remove('trading_bot.sqlite')
            # 重新初始化数据库
            init_db()
            logger.info("数据库已重置")

@app.route('/')
def index():
    return render_template('index.html', email_checker_running=email_checker_running)

@app.route('/status')
def status():
    # 获取邮件处理记录
    db = get_db()
    try:
        emails = db.execute(
            'SELECT * FROM processed_emails ORDER BY processed_at DESC LIMIT 10'
        ).fetchall()
        
        # 获取统计信息
        email_count = db.execute('SELECT COUNT(*) FROM processed_emails').fetchone()[0]
        trade_count = db.execute('SELECT COUNT(*) FROM trades').fetchone()[0]
    except sqlite3.OperationalError:
        # 如果查询失败，可能是数据库结构问题
        reset_database_if_needed()
        emails = []
        email_count = 0
        trade_count = 0
    
    # 获取日志内容
    log_content = ""
    if os.path.exists("app.log"):
        with open("app.log", "r") as f:
            # 读取最后100行
            lines = f.readlines()[-100:]
            log_content = "".join(lines)
    
    # 计算运行时长
    running_time = None
    if email_checker_running and start_time:
        delta = datetime.datetime.now() - start_time
        hours, remainder = divmod(delta.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        running_time = f"{hours}小时{minutes}分钟{seconds}秒"
    
    # 安全地获取上次检查时间
    last_check_time_str = None
    if last_check_time:
        try:
            last_check_time_str = last_check_time.strftime("%Y-%m-%d %H:%M:%S")
        except:
            pass
    
    return render_template(
        'status.html', 
        email_checker_running=email_checker_running,
        emails=emails,
        email_count=email_count,
        trade_count=trade_count,
        log_content=log_content,
        last_check_time=last_check_time_str,
        running_time=running_time
    )

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if request.method == 'POST':
        # 保存设置到数据库
        db = get_db()
        db.execute(
            'INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)',
            ('trading_pair', request.form['trading_pair'])
        )
        db.execute(
            'INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)',
            ('trading_mode', request.form['trading_mode'])
        )
        db.execute(
            'INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)',
            ('investment_amount', request.form['investment_amount'])
        )
        db.execute(
            'INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)',
            ('leverage', request.form['leverage'])
        )
        db.execute(
            'INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)',
            ('take_profit', request.form['take_profit'])
        )
        db.execute(
            'INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)',
            ('stop_loss', request.form['stop_loss'])
        )
        db.execute(
            'INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)',
            ('email_server', request.form['email_server'])
        )
        db.execute(
            'INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)',
            ('email_username', request.form['email_username'])
        )
        db.execute(
            'INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)',
            ('email_password', request.form['email_password'])
        )
        db.execute(
            'INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)',
            ('okx_api_key', request.form['okx_api_key'])
        )
        db.execute(
            'INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)',
            ('okx_secret_key', request.form['okx_secret_key'])
        )
        db.execute(
            'INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)',
            ('okx_passphrase', request.form['okx_passphrase'])
        )
        db.commit()
        flash('设置已保存')
        return redirect(url_for('index'))
    
    # 获取当前设置
    db = get_db()
    settings = {}
    for row in db.execute('SELECT key, value FROM settings'):
        settings[row[0]] = row[1]
    
    return render_template('settings.html', settings=settings)

@app.route('/history')
def history():
    db = get_db()
    trades = db.execute('SELECT * FROM trades ORDER BY timestamp DESC').fetchall()
    return render_template('history.html', trades=trades)

@app.route('/start_checker', methods=['POST'])
def start_checker():
    global email_checker_thread, email_checker_running, start_time
    if not email_checker_running:
        logging.info("启动邮件检查器...")
        email_checker_running = True
        start_time = datetime.datetime.now()
        # 直接调用 start_email_checker 函数，它会创建并返回线程
        email_checker_thread = start_email_checker()
        logging.info("邮件检查器线程已启动")
        flash('邮件检查器已启动')
    else:
        logging.info("邮件检查器已经在运行中")
    # 重定向到状态页面，以便用户可以看到系统状态
    return redirect(url_for('status'))

@app.route('/stop_checker', methods=['POST'])
def stop_checker():
    global email_checker_running, start_time
    if email_checker_running:
        stop_email_checker()
        email_checker_running = False
        start_time = None
        flash('邮件检查器已停止')
    # 重定向到状态页面
    return redirect(url_for('status'))

@app.route('/api/status')
def status_api():
    response = {
        'email_checker_running': email_checker_running,
        'last_check_time': None,
    }
    
    # 安全地获取上次检查时间
    if last_check_time:
        try:
            response['last_check_time'] = last_check_time.strftime("%Y-%m-%d %H:%M:%S")
        except:
            pass
    
    if email_checker_running and start_time:
        delta = datetime.datetime.now() - start_time
        hours, remainder = divmod(delta.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        response['running_time'] = f"{hours}小时{minutes}分钟{seconds}秒"
    
    return jsonify(response)

@app.route('/api/logs')
def logs_api():
    log_content = ""
    if os.path.exists("app.log"):
        try:
            with open("app.log", "r", encoding='gbk') as f:
                # 读取最后100行
                lines = f.readlines()[-100:]
                log_content = "".join(lines)
        except Exception as e:
            logger.error("读取日志文件出错: %s", str(e))
            return jsonify({"error": str(e), "logs": ""})
    return jsonify({"logs": log_content})

@app.route('/test_email_connection', methods=['POST'])
def test_email():
    data = request.json
    try:
        result = test_email_connection(
            data['email_server'],
            data['email_username'],
            data['email_password']
        )
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/test_api_connection', methods=['POST'])
def test_api():
    data = request.json
    try:
        result = test_api_connection(
            data['api_key'],
            data['secret_key'],
            data['passphrase']
        )
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/reset_database', methods=['POST'])
def reset_database():
    """重置数据库"""
    # 停止邮件检查器
    global email_checker_running, start_time
    if email_checker_running:
        stop_email_checker()
        email_checker_running = False
        start_time = None
    
    # 关闭数据库连接
    close_db()
    
    # 删除数据库文件
    if os.path.exists('trading_bot.sqlite'):
        os.remove('trading_bot.sqlite')
    
    # 重新初始化数据库
    with app.app_context():
        init_db()
    
    flash('数据库已重置')
    return redirect(url_for('status'))

@app.route('/test_email_receive', methods=['POST'])
def test_email_receive():
    try:
        # 获取最近的3封邮件
        recent_emails = get_recent_emails(3)
        return jsonify({
            'success': True, 
            'emails': recent_emails
        })
    except Exception as e:
        return jsonify({
            'success': False, 
            'error': str(e)
        })

@app.route('/get_account_info', methods=['POST'])
def get_account_info():
    """获取账户信息"""
    try:
        from services.trading_service import get_account_info
        result = get_account_info()
        if isinstance(result, dict) and 'success' in result:
            return jsonify(result)
        else:
            return jsonify({
                'success': True,
                'data': result
            })
    except Exception as e:
        logger.error("获取账户信息失败: %s", str(e))
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/test_trade_cycle', methods=['POST'])
def test_trade():
    """测试交易周期（买入然后卖出）"""
    try:
        result = test_trade_cycle()
        return jsonify(result)
    except Exception as e:
        app.logger.error("测试交易周期时出错: %s", str(e))
        return jsonify({"success": False, "message": str(e)})

with app.app_context():
    init_db()
    # 检查数据库结构
    reset_database_if_needed()

if __name__ == '__main__':
    # 配置日志
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(os.path.join('logs', 'app.log')),
            logging.StreamHandler()
        ]
    )
    
    # 设置主机和端口
    host = '0.0.0.0'  # 允许外部访问
    port = int(os.environ.get('PORT', 5000))  # 支持环境变量配置端口
    
    # 启动应用
    try:
        logger.info(f"应用程序正在启动，监听地址: {host}:{port}")
        app.run(
            host=host,
            port=port,
            debug=False  # 生产环境禁用调试模式
        )
    except Exception as e:
        logger.error(f"应用程序启动失败: {str(e)}")
        raise 