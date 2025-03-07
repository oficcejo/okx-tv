from models.database import get_db

def get_trading_settings():
    """从数据库获取交易设置"""
    db = get_db()
    settings = {}
    required_settings = [
        'trading_pair', 'trading_mode', 'investment_amount', 
        'leverage', 'take_profit', 'stop_loss',
        'okx_api_key', 'okx_secret_key', 'okx_passphrase'
    ]
    
    for row in db.execute('SELECT key, value FROM settings WHERE key IN ({})'.format(
        ','.join('?' * len(required_settings))), required_settings):
        settings[row[0]] = row[1]
    
    return settings 