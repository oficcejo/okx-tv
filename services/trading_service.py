from okx import Account, MarketData, Trade, SubAccount, PublicData
from models.database import get_db
import logging
import time

logger = logging.getLogger(__name__)

def get_trading_settings():
    """从数据库获取交易设置"""
    db = get_db()
    settings = {}
    for row in db.execute('SELECT key, value FROM settings'):
        settings[row[0]] = row[1]
    return settings

def cancel_all_pending_orders(trade_api, trading_pair):
    """取消所有未完成的订单"""
    logger = logging.getLogger(__name__)
    try:
        # 取消普通未完成订单
        logger.info("正在获取未完成订单...")
        pending_orders = trade_api.get_order_list(instId=trading_pair, state="live")
        
        if pending_orders.get('code') != '0':
            logger.warning("获取未完成订单失败: %s", pending_orders.get('msg', '未知错误'))
            return False
            
        if pending_orders.get('data'):
            logger.info("找到 %d 个未完成订单，准备取消", len(pending_orders['data']))
            for order in pending_orders['data']:
                order_id = order['ordId']
                logger.info("正在取消订单 %s", order_id)
                cancel_result = trade_api.cancel_order(instId=trading_pair, ordId=order_id)
                if cancel_result.get('code') != '0':
                    logger.warning("取消订单 %s 失败: %s", order_id, cancel_result.get('msg', '未知错误'))
                else:
                    logger.info("订单 %s 已取消", order_id)
        else:
            logger.info("没有普通未完成订单")

        # 取消仅减仓订单
        logger.info("正在获取仅减仓订单...")
        algo_orders = trade_api.get_algo_order_list(instId=trading_pair, ordType="conditional,oco,trigger")
        
        if algo_orders.get('code') != '0':
            logger.warning("获取仅减仓订单失败: %s", algo_orders.get('msg', '未知错误'))
            return False
            
        if algo_orders.get('data'):
            logger.info("找到 %d 个仅减仓订单，准备取消", len(algo_orders['data']))
            for order in algo_orders['data']:
                algo_id = order['algoId']
                logger.info("正在取消仅减仓订单 %s", algo_id)
                cancel_result = trade_api.cancel_algo_order([{"algoId": algo_id, "instId": trading_pair}])
                if cancel_result.get('code') != '0':
                    logger.warning("取消仅减仓订单 %s 失败: %s", algo_id, cancel_result.get('msg', '未知错误'))
                else:
                    logger.info("仅减仓订单 %s 已取消", algo_id)
        else:
            logger.info("没有仅减仓订单")
                
        return True
    except Exception as e:
        logger.error("取消订单时出错: %s", str(e))
        return False

def execute_trade(direction):
    """执行交易
    
    Args:
        direction: 交易方向，"LONG" 或 "SHORT"
    """
    settings = get_trading_settings()
    
    # 检查必要的设置是否存在
    required_settings = [
        'trading_pair', 'trading_mode', 'investment_amount', 
        'leverage', 'take_profit', 'stop_loss',
        'okx_api_key', 'okx_secret_key', 'okx_passphrase'
    ]
    
    if not all(key in settings for key in required_settings):
        missing_settings = [key for key in required_settings if key not in settings]
        logger.error("交易设置不完整，缺少以下设置: %s", missing_settings)
        return False
    
    try:
        # 初始化OKX API
        api_key = settings['okx_api_key']
        secret_key = settings['okx_secret_key']
        passphrase = settings['okx_passphrase']
        
        # 使用生产环境
        flag = "0"  # 0: 生产环境, 1: 测试环境
        debug = True  # 启用调试模式
        
        logger.info("正在初始化API客户端 - 环境: 生产环境, 调试模式: 开启")
        
        # 初始化API客户端
        account_api = Account.AccountAPI(api_key, secret_key, passphrase, debug, flag)
        trade_api = Trade.TradeAPI(api_key, secret_key, passphrase, debug, flag)
        market_api = MarketData.MarketAPI(flag=flag)  # 行情数据不需要认证
        
        # 获取交易对信息
        trading_pair = settings['trading_pair']
        logger.info("使用交易对: %s", trading_pair)
        
        # 获取当前市场价格
        logger.info("正在获取 %s 的市场价格", trading_pair)
        ticker = market_api.get_ticker(instId=trading_pair)
        if ticker.get('code') != '0':
            raise Exception(f"获取市场价格失败: {ticker.get('msg', '未知错误')}")
            
        current_price = float(ticker['data'][0]['last'])
        logger.info("当前市场价格: %s", current_price)
        
        # 获取交易对信息，了解最小交易量
        logger.info("获取交易对详细信息...")
        public_data_api = PublicData.PublicAPI(flag=flag)
        instruments_info = public_data_api.get_instruments(instType="SPOT", instId=trading_pair)
        
        if instruments_info.get('code') != '0' or not instruments_info.get('data'):
            raise Exception("获取交易对信息失败")
            
        min_size = float(instruments_info['data'][0].get('minSz', '0'))
        lot_size = float(instruments_info['data'][0].get('lotSz', '0.0001'))
        logger.info("交易对 %s 的最小交易量: %s, 交易量步长: %s", trading_pair, min_size, lot_size)
        
        # 设置交易模式
        trading_mode = settings.get('trading_mode', 'cash')
        if trading_mode == 'margin':
            td_mode = "isolated"  # 杠杆交易使用逐仓模式
        elif trading_mode == 'swap':
            td_mode = "cross"     # 合约交易使用全仓模式
        else:
            td_mode = "cash"      # 默认使用现货现金交易模式
            
        logger.info("使用交易模式: %s", td_mode)
        
        # 获取投资金额
        investment_amount = float(settings['investment_amount'])
        logger.info("设置的投资金额: %s USDT", investment_amount)

        # 如果是杠杆交易，计算实际投资金额
        if td_mode in ["isolated", "cross"]:
            leverage = float(settings.get('leverage', '1'))
            investment_amount = investment_amount * leverage  # 将投资金额乘以杠杆倍数
            logger.info("使用杠杆倍数: %s, 实际投资金额: %s USDT", leverage, investment_amount)
        
        # 计算交易数量
        if direction == "SHORT" and 'trump_quantity' in settings:
            trade_quantity = float(settings['trump_quantity'])
            logger.info("卖出操作，使用实际持有的TRUMP数量: %s", trade_quantity)
        else:
            # 计算交易数量（基于当前价格和投资金额）
            trade_quantity = round(investment_amount / current_price, 4)  # 保留4位小数
            logger.info("根据投资金额计算的交易数量: %s", trade_quantity)
            
            # 确保交易数量不小于最小交易量
            if trade_quantity < min_size:
                logger.warning("计算的交易数量 %s 小于最小交易量 %s", trade_quantity, min_size)
                trade_quantity = min_size
                logger.info("将使用最小交易量: %s", min_size)
        
        # 确保交易数量是lotSize的整数倍
        if lot_size > 0:
            trade_quantity = round(trade_quantity / lot_size) * lot_size
            trade_quantity = round(trade_quantity, 8)  # 保留8位小数，避免浮点数精度问题
            logger.info("调整后的最终交易数量: %s", trade_quantity)
        
        # 确定交易方向
        side = "buy" if direction == "LONG" else "sell"
        
        # 构建订单参数
        order_params = {
            "instId": trading_pair,
            "tdMode": td_mode,
            "side": side,
            "ordType": "market",
            "tgtCcy": "base_ccy",  # 使用base_ccy表示用数量交易
            "ccy": "USDT",  # 添加ccy参数
        }
        
        # 如果是买入操作，使用quote_ccy指定USDT金额
        if direction == "LONG":
            order_params["tgtCcy"] = "quote_ccy"  # 使用quote_ccy表示用金额交易
            order_params["sz"] = str(investment_amount)
            logger.info("买入操作，指定USDT金额: %s", investment_amount)
        else:
            # 如果是卖出操作，使用base_ccy指定TRUMP数量
            order_params["tgtCcy"] = "base_ccy"  # 使用base_ccy表示用数量交易
            order_params["sz"] = str(trade_quantity)
            logger.info("卖出操作，指定TRUMP数量: %s", trade_quantity)
        
        # 如果是杠杆交易，添加杠杆倍数
        if td_mode in ["isolated", "cross"]:
            leverage = settings.get('leverage', '1')
            logger.info("设置杠杆倍数: %s", leverage)
            try:
                account_api.set_leverage(
                    lever=leverage,
                    mgnMode=td_mode,
                    instId=trading_pair
                )
                logger.info("杠杆倍数设置成功")
            except Exception as e:
                logger.error("设置杠杆倍数失败: %s", str(e))
                raise Exception(f"设置杠杆倍数失败: {str(e)}")
        
        # 添加止盈止损参数
        take_profit = float(settings.get('take_profit', '0'))
        stop_loss = float(settings.get('stop_loss', '0'))
        
        if take_profit > 0:
            if direction == "LONG":
                tp_trigger_price = current_price * (1 + take_profit / 100)
            else:
                tp_trigger_price = current_price * (1 - take_profit / 100)
            order_params["tpTriggerPx"] = str(round(tp_trigger_price, 3))
            order_params["tpOrdPx"] = str(round(tp_trigger_price, 3))
            logger.info("设置止盈价格: %s", tp_trigger_price)
            
        if stop_loss > 0:
            if direction == "LONG":
                sl_trigger_price = current_price * (1 - stop_loss / 100)
            else:
                sl_trigger_price = current_price * (1 + stop_loss / 100)
            order_params["slTriggerPx"] = str(round(sl_trigger_price, 3))
            order_params["slOrdPx"] = str(round(sl_trigger_price, 3))
            logger.info("设置止损价格: %s", sl_trigger_price)
        
        logger.info("准备下单，参数: %s", order_params)
        
        # 先取消所有未完成的订单
        logger.info("尝试取消所有未完成订单...")
        cancel_all_pending_orders(trade_api, trading_pair)
        
        # 执行下单
        logger.info("正在执行下单...")
        order_result = trade_api.place_order(**order_params)
        
        if order_result.get('code') != '0':
            error_code = order_result.get('data', [{}])[0].get('sCode', 'unknown')
            error_msg = order_result.get('data', [{}])[0].get('sMsg', '未知错误')
            logger.error("交易执行失败: 错误码=%s, 错误信息=%s", error_code, error_msg)
            return {
                "success": False,
                "message": f"交易执行失败: {error_msg}",
                "error_code": error_code,
                "order_result": order_result
            }
            
        # 获取订单ID
        order_id = order_result.get('data', [{}])[0].get('ordId', '')
        
        logger.info("%s交易执行成功，订单ID: %s", "做多" if direction == "LONG" else "做空", order_id)
        
        # 记录交易到数据库
        try:
            db = get_db()
            db.execute(
                'INSERT INTO trades (trading_pair, direction, amount, price, status, order_id, take_profit, stop_loss) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                (trading_pair, direction, investment_amount, current_price, 'EXECUTED', order_id, take_profit, stop_loss)
            )
            db.commit()
            logger.info("交易记录已保存到数据库")
        except Exception as e:
            logger.error("保存交易记录到数据库时出错: %s", str(e))
        
        # 返回成功结果
        return {
            "success": True,
            "message": f"{direction}交易执行成功",
            "order_id": order_id,
            "order_result": order_result
        }
    except Exception as e:
        logger.error("交易执行出错: %s", str(e))
        import traceback
        logger.error("错误详情: %s", traceback.format_exc())
        return {
            "success": False,
            "message": f"交易执行出错: {str(e)}"
        }

def test_api_connection(api_key, secret_key, passphrase):
    """测试OKX API连接"""
    try:
        logger.info("开始测试API连接 - 环境: 生产环境")
        
        # 初始化OKX API
        account_api = Account.AccountAPI(
            api_key=api_key,
            api_secret_key=secret_key,
            passphrase=passphrase,
            flag="0",  # 0: 生产环境
            debug=True
        )
        
        # 获取账户余额，测试连接
        logger.info("正在获取账户余额...")
        result = account_api.get_account_balance()
        logger.info("API响应: %s", result)
        
        # 检查API返回结果
        if result.get('code') == '0':
            logger.info("API连接测试成功")
            return True
        else:
            error_msg = result.get('msg', '未知错误')
            logger.error("API连接测试失败: %s", error_msg)
            raise Exception(f"API返回错误: {error_msg}")
            
    except Exception as e:
        logger.error("API连接测试失败: %s", str(e))
        raise Exception(f"API连接测试失败: {str(e)}")

def get_account_info():
    """获取账户信息"""
    settings = get_trading_settings()
    
    # 检查API设置是否存在
    required_settings = ['okx_api_key', 'okx_secret_key', 'okx_passphrase']
    if not all(key in settings for key in required_settings):
        missing_settings = [key for key in required_settings if key not in settings]
        raise Exception(f"API设置不完整，缺少: {missing_settings}")
    
    try:
        # 初始化OKX API
        api_key = settings['okx_api_key']
        secret_key = settings['okx_secret_key']
        passphrase = settings['okx_passphrase']
        
        # 使用生产环境
        flag = "0"  # 0: 生产环境, 1: 测试环境
        debug = True  # 启用调试模式
        
        logger.info("正在初始化API客户端 - 环境: 生产环境")
        
        # 初始化API客户端
        account_api = Account.AccountAPI(api_key, secret_key, passphrase, debug, flag)
        
        # 获取账户配置
        logger.info("获取账户配置...")
        account_config = account_api.get_account_config()
        logger.info("账户配置响应: %s", account_config)
        
        # 获取账户余额
        logger.info("获取账户余额...")
        balance = account_api.get_account_balance()
        logger.info("账户余额响应: %s", balance)
        
        # 获取持仓信息
        logger.info("获取持仓信息...")
        positions = account_api.get_positions()
        logger.info("持仓信息响应: %s", positions)
        
        # 格式化账户配置信息
        config_data = account_config.get('data', [{}])[0]
        formatted_config = {
            "账户信息": {
                "账户级别": f"Lv{config_data.get('level', '未知')[2:]}" if config_data.get('level', '').startswith('Lv') else config_data.get('level', '未知'),
                "KYC等级": f"{config_data.get('kycLv', '未知')}级",
                "账户标签": config_data.get('label', '未知'),
                "账户权限": config_data.get('perm', '未知').replace('read_only', '只读').replace('trade', '交易'),
                "持仓模式": config_data.get('posMode', '未知').replace('net_mode', '净持仓模式')
            }
        }
        
        # 格式化余额信息
        balance_data = balance.get('data', [{}])[0]
        formatted_balance = {
            "账户余额": {
                "总账户权益": f"{float(balance_data.get('totalEq', 0)):.2f} USD"
            },
            "币种明细": []
        }
        
        # 处理每个币种的详细信息
        for detail in balance_data.get('details', []):
            if float(detail.get('eq', 0)) > 0 or float(detail.get('availBal', 0)) > 0:
                coin_info = {
                    "币种": detail.get('ccy', '未知'),
                    "可用余额": f"{float(detail.get('availBal', 0)):.8f}",
                    "冻结余额": f"{float(detail.get('frozenBal', 0)):.8f}",
                    "总数量": f"{float(detail.get('eq', 0)):.8f}",
                    "美元价值": f"{float(detail.get('eqUsd', 0)):.2f} USD"
                }
                formatted_balance["币种明细"].append(coin_info)
        
        # 格式化持仓信息
        positions_data = positions.get('data', [])
        formatted_positions = {
            "当前持仓": "暂无持仓" if not positions_data else []
        }
        
        if positions_data:
            for pos in positions_data:
                position_info = {
                    "交易对": pos.get('instId', '未知'),
                    "持仓方向": pos.get('posSide', '未知'),
                    "持仓数量": pos.get('pos', '0'),
                    "开仓均价": pos.get('avgPx', '0'),
                    "未实现盈亏": f"{float(pos.get('upl', 0)):.2f} USD"
                }
                formatted_positions["当前持仓"].append(position_info)
        
        # 整理返回数据
        result = {
            'success': True,
            'data': {
                'account_config': formatted_config,
                'balance': formatted_balance,
                'positions': formatted_positions
            }
        }
        
        return result
        
    except Exception as e:
        logger.error("获取账户信息时出错: %s", str(e))
        import traceback
        logger.error("详细错误信息: %s", traceback.format_exc())
        raise Exception(f"获取账户信息失败: {str(e)}")

def test_trade_cycle():
    """测试交易周期（买入然后卖出）"""
    logger = logging.getLogger(__name__)
    
    try:
        # 先执行买入
        logger.info("===== 开始测试交易周期 =====")
        logger.info("第1步: 执行买入交易")
        buy_result = execute_trade("LONG")
        
        if not buy_result or not buy_result.get('success'):
            logger.error("买入交易失败，测试终止")
            return {
                "success": False,
                "message": "买入交易失败",
                "buy_result": buy_result
            }
            
        logger.info("买入交易成功，等待5秒后执行卖出")
        time.sleep(5)
        
        # 查询账户余额，获取实际持有的TRUMP数量
        logger.info("查询账户余额，获取实际持有的TRUMP数量")
        settings = get_trading_settings()
        
        # 初始化API客户端
        api_key = settings['okx_api_key']
        secret_key = settings['okx_secret_key']
        passphrase = settings['okx_passphrase']
        flag = "0"  # 0: 生产环境, 1: 测试环境
        debug = True  # 启用调试模式
        
        account_api = Account.AccountAPI(api_key, secret_key, passphrase, debug, flag)
        
        # 获取账户余额
        try:
            balance_result = account_api.get_account_balance()
            logger.info("账户余额响应: %s", balance_result)
            
            if balance_result.get('code') != '0':
                logger.error("获取账户余额失败: %s", balance_result.get('msg', '未知错误'))
                return {
                    "success": False,
                    "message": "获取账户余额失败，无法执行卖出交易",
                    "buy_result": buy_result
                }
                
            # 获取TRUMP余额
            available_trump = 0
            if balance_result.get('data') and balance_result['data'][0].get('details'):
                for detail in balance_result['data'][0]['details']:
                    if detail.get('ccy') == 'TRUMP':
                        available_trump = float(detail.get('availBal', '0'))
                        break
                        
            logger.info("可用TRUMP余额: %s", available_trump)
            
            if available_trump <= 0:
                logger.error("TRUMP余额为0，无法执行卖出交易")
                return {
                    "success": False,
                    "message": "TRUMP余额为0，无法执行卖出交易",
                    "buy_result": buy_result
                }
                
            # 修改设置中的交易数量
            settings['trump_quantity'] = available_trump
            logger.info("将使用实际持有的TRUMP数量进行卖出: %s", available_trump)
            
        except Exception as e:
            logger.error("获取账户余额时出错: %s", str(e))
            import traceback
            logger.error("错误详情: %s", traceback.format_exc())
            return {
                "success": False,
                "message": f"获取账户余额时出错: {str(e)}",
                "buy_result": buy_result
            }
        
        # 然后执行卖出
        logger.info("第2步: 执行卖出交易")
        sell_result = execute_trade("SHORT")
        
        if not sell_result or not sell_result.get('success'):
            logger.error("卖出交易失败")
            return {
                "success": False,
                "message": "卖出交易失败",
                "buy_result": buy_result,
                "sell_result": sell_result
            }
            
        logger.info("卖出交易成功，交易周期测试完成")
        
        return {
            "success": True,
            "message": "交易周期测试成功",
            "buy_result": buy_result,
            "sell_result": sell_result
        }
        
    except Exception as e:
        logger.error("测试交易周期时出错: %s", str(e))
        import traceback
        logger.error("错误详情: %s", traceback.format_exc())
        
        return {
            "success": False,
            "message": f"测试过程中出错: {str(e)}"
        } 