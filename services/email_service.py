import imaplib
import email
import time
import threading
from models.database import get_db
from services.trading_service import execute_trade, get_trading_settings
import logging
import smtplib
import datetime
from flask import current_app
from models.account import AccountAPI as Account

logger = logging.getLogger(__name__)

# 全局变量控制邮件检查器
stop_flag = False
last_check_time = None

def get_email_settings():
    """从数据库获取邮件设置"""
    db = get_db()
    settings = {}
    for row in db.execute('SELECT key, value FROM settings WHERE key IN (?, ?, ?)', 
                         ('email_server', 'email_username', 'email_password')):
        settings[row[0]] = row[1]
    return settings

def check_emails():
    """检查邮件并处理交易信号"""
    global last_check_time
    last_check_time = datetime.datetime.now()
    
    settings = get_email_settings()
    
    if not all(key in settings for key in ['email_server', 'email_username', 'email_password']):
        logger.error("邮件设置不完整，无法检查邮件")
        return
    
    logger.info("开始检查邮件 - 服务器: %s, 用户: %s", settings['email_server'], settings['email_username'])
    
    try:
        # 使用SSL连接到邮件服务器
        mail = imaplib.IMAP4_SSL(settings['email_server'], 993)
        logger.info("已连接到服务器")
        
        # 登录
        try:
            mail.login(settings['email_username'], settings['email_password'])
            logger.info("已登录")
        except Exception as e:
            logger.error("登录失败: %s", str(e))
            return
        
        # 选择收件箱
        try:
            status, data = mail.select('INBOX')
            logger.info("选择收件箱状态: %s, 数据: %s", status, data)
            
            if status != 'OK':
                logger.error("无法选择收件箱")
                return
        except Exception as e:
            logger.error("选择收件箱时出错: %s", str(e))
            return
        
        # 搜索未读邮件
        logger.info("搜索未读邮件...")
        status, messages = mail.search(None, 'UNSEEN')
        
        if status != 'OK':
            logger.error("无法搜索邮件: %s", status)
            return
        
        message_count = len(messages[0].split())
        logger.info("找到 %d 封未读邮件", message_count)
        
        if message_count == 0:
            logger.info("没有新邮件需要处理")
            return
        
        for num in messages[0].split():
            try:
                logger.info("获取邮件 ID: %s", num)
                status, message = mail.fetch(num, '(RFC822)')
                
                if status != 'OK':
                    logger.error("获取邮件失败")
                    continue
                
                # 解析邮件内容
                msg = email.message_from_bytes(message[0][1])
                
                # 获取邮件信息
                email_id = msg.get('Message-ID') or f"unknown-{num.decode('utf-8')}"
                
                # 解码主题
                subject_header = email.header.decode_header(msg.get('subject', '无主题'))
                subject = str_to_unicode(subject_header[0][0], subject_header[0][1]) if subject_header else '无主题'
                
                # 解码发件人
                sender_header = email.header.decode_header(msg.get('from', '未知发件人'))
                sender = str_to_unicode(sender_header[0][0], sender_header[0][1]) if sender_header else '未知发件人'
                
                logger.info("收到邮件 - 发件人: %s, 主题: %s", sender, subject)
                
                # 检查是否已处理过该邮件
                db = get_db()
                if db.execute('SELECT 1 FROM processed_emails WHERE email_id = ?', (email_id,)).fetchone():
                    logger.info("邮件已处理过，跳过")
                    continue
                
                logger.info("处理邮件 - ID: %s, 主题: %s", email_id, subject)
                
                # 检查是否是交易信号
                trade_executed = False
                
                # 将主题转换为小写，便于不区分大小写比较
                subject_lower = subject.lower() if subject else ""
                logger.info("转换为小写后的主题: '%s'", subject_lower)
                
                # 检查是否包含做多或做空信号（不区分大小写）
                if "long" in subject_lower:
                    logger.info("检测到做多信号，执行交易...")
                    try:
                        # 执行买入交易
                        buy_result = execute_trade("LONG")
                        if buy_result and buy_result.get('success'):
                            trade_executed = True
                            logger.info("做多交易执行成功，订单ID: %s", buy_result.get('order_id'))
                        else:
                            logger.error("做多交易执行失败: %s", buy_result.get('message'))
                    except Exception as e:
                        logger.error("执行做多交易时出错: %s", str(e))
                elif "short" in subject_lower:
                    logger.info("检测到做空信号，执行交易...")
                    try:
                        # 查询账户余额，获取实际持有的TRUMP数量
                        settings = get_trading_settings()
                        api_key = settings['okx_api_key']
                        secret_key = settings['okx_secret_key']
                        passphrase = settings['okx_passphrase']
                        flag = "0"  # 生产环境
                        debug = True
                        
                        account_api = Account(api_key, secret_key, passphrase, debug, flag)
                        balance_result = account_api.get_account_balance()
                        
                        if balance_result.get('code') == '0' and balance_result.get('data'):
                            # 获取TRUMP余额
                            available_trump = 0
                            for detail in balance_result['data'][0]['details']:
                                if detail.get('ccy') == 'TRUMP':
                                    available_trump = float(detail.get('availBal', '0'))
                                    break
                            
                            if available_trump > 0:
                                logger.info("可用TRUMP余额: %s", available_trump)
                                # 修改设置中的交易数量
                                settings['trump_quantity'] = available_trump
                                # 执行卖出交易
                                sell_result = execute_trade("SHORT")
                                if sell_result and sell_result.get('success'):
                                    trade_executed = True
                                    logger.info("做空交易执行成功，订单ID: %s", sell_result.get('order_id'))
                                else:
                                    logger.error("做空交易执行失败: %s", sell_result.get('message'))
                            else:
                                logger.error("TRUMP余额为0，无法执行卖出交易")
                        else:
                            logger.error("获取账户余额失败: %s", balance_result.get('msg', '未知错误'))
                    except Exception as e:
                        logger.error("执行做空交易时出错: %s", str(e))
                else:
                    logger.info("未检测到交易信号，邮件主题不匹配交易关键词")
                    logger.info("主题中是否包含'long': %s", "long" in subject_lower)
                    logger.info("主题中是否包含'short': %s", "short" in subject_lower)
                
                # 标记邮件为已处理
                db.execute(
                    'INSERT INTO processed_emails (email_id, subject, sender, processed_at, trade_executed) VALUES (?, ?, ?, datetime("now"), ?)',
                    (email_id, subject, sender, 1 if trade_executed else 0)
                )
                db.commit()
                logger.info("邮件已标记为处理完成")
                
            except Exception as e:
                logger.error("处理邮件时出错: %s", str(e))
                import traceback
                logger.error("处理邮件详细错误: %s", traceback.format_exc())
        
        # 关闭连接
        try:
            mail.close()
            mail.logout()
            logger.info("已关闭邮箱连接")
        except Exception as e:
            logger.error("关闭连接时出错: %s", str(e))
            
    except Exception as e:
        logger.error("检查邮件时出错: %s", str(e))
        import traceback
        logger.error("错误详情: %s", traceback.format_exc())

def email_checker_loop():
    """邮件检查循环"""
    global stop_flag
    logger.info("邮件检查器已启动")
    
    while not stop_flag:
        try:
            logger.info("执行邮件检查...")
            check_emails()
        except Exception as e:
            logger.error("邮件检查循环出错: %s", str(e))
            
        # 每30秒检查一次
        logger.info("等待20秒后进行下一次检查...")
        for i in range(20):
            if stop_flag:
                break
            time.sleep(1)
    
    logger.info("邮件检查器已停止")
    stop_flag = False

def start_email_checker():
    """启动邮件检查器"""
    global stop_flag
    stop_flag = False
    logger.info("准备启动邮件检查器...")
    
    # 获取当前应用实例
    app = current_app._get_current_object()
    
    # 创建一个新线程，在线程中使用应用上下文
    def run_checker_with_app_context():
        with app.app_context():
            email_checker_loop()
    
    thread = threading.Thread(target=run_checker_with_app_context)
    thread.daemon = True
    thread.start()
    return thread

def stop_email_checker():
    """停止邮件检查器"""
    global stop_flag
    stop_flag = True

def test_email_connection(server, username, password):
    """测试邮件服务器连接"""
    try:
        # 使用IMAP SSL连接测试
        imap = imaplib.IMAP4_SSL(server, 993)
        imap.login(username, password)
        imap.select('INBOX')
        imap.close()
        imap.logout()
        return True
    except Exception as e:
        logger.error("邮箱连接测试详细错误: %s", str(e))
        raise Exception(f"邮箱连接测试失败: {str(e)}")

def get_recent_emails(count=3):
    """获取最近的邮件
    
    Args:
        count: 要获取的邮件数量
        
    Returns:
        list: 包含邮件信息的列表，每个元素是一个字典
    """
    settings = get_email_settings()
    
    if not all(key in settings for key in ['email_server', 'email_username', 'email_password']):
        logger.error("邮件设置不完整，无法获取邮件")
        return []
    
    logger.info("获取最近 %d 封邮件 - 服务器: %s, 用户: %s", count, settings['email_server'], settings['email_username'])
    
    recent_emails = []
    
    try:
        # 使用SSL连接到邮件服务器
        mail = imaplib.IMAP4_SSL(settings['email_server'], 993)
        logger.info("已连接到服务器")
        
        # 登录
        try:
            mail.login(settings['email_username'], settings['email_password'])
            logger.info("已登录")
        except Exception as e:
            logger.error("登录失败: %s", str(e))
            return []
        
        # 选择收件箱
        try:
            status, data = mail.select('INBOX')
            logger.info("选择收件箱状态: %s, 数据: %s", status, data)
            
            if status != 'OK':
                logger.error("无法选择收件箱")
                return []
        except Exception as e:
            logger.error("选择收件箱时出错: %s", str(e))
            return []
        
        # 搜索邮件
        try:
            # 搜索所有邮件
            status, data = mail.search(None, 'ALL')
            if status != 'OK':
                logger.error("搜索邮件失败")
                return []
            
            # 获取邮件ID列表
            email_ids = data[0].split()
            logger.info("找到 %d 封邮件", len(email_ids))
            
            if not email_ids:
                logger.info("未找到任何邮件")
                return []
            
            # 获取最新的count封邮件
            target_ids = email_ids[-count:] if len(email_ids) > count else email_ids
            logger.info("准备获取 %d 封最新邮件", len(target_ids))
            
            for num in target_ids:
                try:
                    logger.info("获取邮件 ID: %s", num)
                    status, message = mail.fetch(num, '(RFC822)')
                    
                    if status != 'OK':
                        logger.error("获取邮件失败")
                        continue
                    
                    # 解析邮件内容
                    msg = email.message_from_bytes(message[0][1])
                    
                    # 获取邮件信息
                    email_id = msg.get('Message-ID') or f"unknown-{num.decode('utf-8')}"
                    
                    # 解码主题
                    subject_header = email.header.decode_header(msg.get('subject', '无主题'))
                    subject = str_to_unicode(subject_header[0][0], subject_header[0][1]) if subject_header else '无主题'
                    
                    # 解码发件人
                    sender_header = email.header.decode_header(msg.get('from', '未知发件人'))
                    sender = str_to_unicode(sender_header[0][0], sender_header[0][1]) if sender_header else '未知发件人'
                    
                    # 解码日期
                    date_header = email.header.decode_header(msg.get('Date', '未知日期'))
                    date = str_to_unicode(date_header[0][0], date_header[0][1]) if date_header else '未知日期'
                    
                    logger.info("邮件信息 - ID: %s, 发件人: %s, 主题: %s, 日期: %s",
                               email_id, sender, subject, date)
                    
                    # 添加到结果列表
                    email_info = {
                        'id': str(email_id),
                        'subject': str(subject),
                        'sender': str(sender),
                        'date': str(date)
                    }
                    
                    recent_emails.append(email_info)
                    logger.info("成功添加邮件到列表")
                    
                except Exception as e:
                    logger.error("处理邮件 %s 时出错: %s", num, str(e))
                    import traceback
                    logger.error("处理邮件详细错误: %s", traceback.format_exc())
            
        except Exception as e:
            logger.error("搜索或获取邮件时出错: %s", str(e))
            import traceback
            logger.error("错误详情: %s", traceback.format_exc())
        
        # 关闭连接
        try:
            mail.close()
            mail.logout()
            logger.info("已关闭邮箱连接")
        except Exception as e:
            logger.error("关闭连接时出错: %s", str(e))
        
        # 返回最新的邮件（倒序排列）
        result = list(reversed(recent_emails))
        logger.info("返回 %d 封邮件", len(result))
        return result
        
    except Exception as e:
        logger.error("获取邮件时出错: %s", str(e))
        import traceback
        logger.error("错误详情: %s", traceback.format_exc())
        return []

def str_to_unicode(s, encoding=None):
    """将字符串转换为Unicode编码
    
    Args:
        s: 要转换的字符串
        encoding: 编码方式
        
    Returns:
        str: 转换后的Unicode字符串
    """
    if isinstance(s, bytes):
        return str(s, encoding) if encoding else str(s, 'utf-8', errors='replace')
    return str(s) 