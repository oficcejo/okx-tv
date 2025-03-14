# TradingView邮件信号的okx自动交易系统
**此程序旨在为tradingview免费用户使用邮件报警信号进行自动交易，如您在交易中能赚到钱，请购买tradingview正式服务**
这是一个基于 TradingView 信号的自动化交易系统，可以自动监控邮件中的交易信号并在 OKX 交易所执行相应的交易操作。
![image](https://github.com/user-attachments/assets/806faa00-d38a-4a1d-b33a-bf05f57a2bd2)

## 基本条件
### 1、本地部署（大陆地区需要科学上网环境）
win10以上系统，linux推荐ubuntu20以上系统，MACOS未测试，python3.12版本，能访问tradingview官网。
### 2、服务器部署，最好用美国vps服务器部署
推荐美国老牌服务器厂商RackNerd稳定服务器**支持支付宝付款**
- [满足要求型：1核心1G内存24GSSD2T带宽11.29美元/年](https://my.racknerd.com/aff.php?aff=13902&pid=903)
- [进阶型：1核心2G内存40GSSD3.5T带宽18.29美元/年](https://my.racknerd.com/aff.php?aff=13902&pid=904)
- [推荐型：2核心3.5G内存65GSSD7T带宽32.49美元/年](https://my.racknerd.com/aff.php?aff=13902&pid=905)
- [高端型：4核心6G内存140GSSD12T带宽59.99美元/年](https://my.racknerd.com/aff.php?aff=13902&pid=907)
## 主要功能

### 1. 信号监控
- 自动监控指定邮箱接收 TradingView 发送的交易信号
- 支持多种邮箱服务器（Gmail、QQ邮箱、163邮箱等）推荐QQ邮箱
- 实时处理交易信号，自动执行相应交易

### 2. 交易功能
- 支持现货、杠杆和合约交易
- 自动计算交易数量和实际投资金额
- 支持止盈止损设置
- 自动处理最小交易量和交易量步长要求

### 3. 系统管理
- Web界面实时监控系统状态
- 查看交易历史记录
- 实时日志查看
- 账户信息查询
- 交易参数配置

## 安装说明

### 1. 环境要求
- Python 3.12 或更高版本
- Windows/Linux/MacOS 操作系统

### 2. 安装步骤

1. 克隆代码仓库：
```bash
git clone [repository_url]
cd gupiao-tv
```

2. 创建并激活虚拟环境：
```bash
python -m venv venv
# Windows
.venv\Scripts\activate
# Linux/MacOS
source venv/bin/activate
```

3. 安装依赖：
```bash
pip install -r requirements.txt
```

4. 运行程序：
```bash
python app.py
```

## 配置说明

### 1. OKX API 配置
1. 登录 OKX 交易所
2. 创建 API Key（需要交易权限）
3. 在系统设置页面填入：
   - API Key
   - Secret Key
   - Passphrase

### 2. 邮箱配置
1. 准备一个邮箱账号（推荐使用QQ邮箱）
2. 获取邮箱的 IMAP 授权码
3. 在系统设置页面填入：
   - 邮件服务器地址
   - 邮箱地址
   - 授权码

### 3. 交易参数配置
- 交易对：选择要交易的币对（例如：TRUMP-USDT）
- 交易模式：现货/杠杆/合约
- 投资金额：每次交易的基础投资额（USDT）
- 杠杆倍数：使用杠杆时的倍数设置
- 止盈百分比：达到该百分比自动平仓
- 止损百分比：达到该百分比自动平仓
#### 交易参数配置示例
```bash
交易对:BTC-USDT
交易模式:杠杆
投入金额 (USDT)：100
杠杆倍率:10
止盈百分比 (%):1.5
止损百分比 (%):1
```

## 运行说明

1. 启动系统：
```bash
python app.py
```

2. 访问Web界面：
- 打开浏览器访问：`http://127.0.0.1:5000`
- 进入设置页面完成相关配置
- 点击"启动系统"开始运行

## 使用流程

1. 在 TradingView 中设置警报：
   - 选择发送邮件提醒
   - 邮件主题中包含 "long" 表示做多信号
   - 邮件主题中包含 "short" 表示做空信号
![image](https://github.com/user-attachments/assets/47bb8622-b574-46c5-bc6d-dc634dbd881b)
2. 系统运行后会：
   - 自动检查邮件信号
   - 根据信号执行相应交易
   - 记录交易历史
   - 实时更新系统状态

## 注意事项

1. 资金安全：
   - 建议先使用小额资金测试
   - 合理设置止盈止损
   - 定期检查交易记录

2. 系统维护：
   - 定期检查系统日志
   - 确保邮箱和API正常工作
   - 及时更新系统配置

3. 风险提示：
   - 数字货币交易有风险
   - 建议仅使用风险承受范围内的资金
   - 系统可能存在延迟，请预留足够的价格空间
   - **邮件收取和检查有延迟，请勿用于1分钟等超短线交易**

## 常见问题

1. 邮件无法接收
   - 检查邮箱配置是否正确
   - 确认邮箱开启了IMAP服务
   - 验证授权码是否有效

2. 交易执行失败
   - 检查API配置是否正确
   - 确认账户余额是否充足
   - 查看日志了解具体错误原因

3. 系统无响应
   - 检查网络连接
   - 查看系统日志
   - 重启应用程序

## 技术支持

如有问题请提交 Issue 或联系技术支持。 
