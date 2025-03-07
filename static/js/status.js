document.addEventListener('DOMContentLoaded', function() {
    // 更新系统状态
    function updateStatus() {
        fetch('/api/status')
            .then(response => response.json())
            .then(data => {
                // 更新检查器状态
                const checkerStatus = document.getElementById('checker-status');
                if (checkerStatus) {
                    checkerStatus.textContent = data.email_checker_running ? '运行中' : '已停止';
                    checkerStatus.className = 'status-value ' + (data.email_checker_running ? 'running' : 'stopped');
                }
                
                // 更新上次检查时间
                const lastCheckTime = document.getElementById('last-check-time');
                if (lastCheckTime) {
                    lastCheckTime.textContent = data.last_check_time || '无';
                }
                
                // 更新运行时长
                const runningTime = document.getElementById('running-time');
                if (runningTime) {
                    runningTime.textContent = data.running_time || '未运行';
                }
            })
            .catch(error => {
                console.error('获取状态时出错:', error);
            });
    }
    
    // 刷新日志
    function refreshLogs() {
        fetch('/api/logs')
            .then(response => response.json())
            .then(data => {
                const logContent = document.getElementById('log-content');
                if (logContent) {
                    logContent.textContent = data.logs;
                    // 滚动到日志底部
                    logContent.scrollTop = logContent.scrollHeight;
                }
            })
            .catch(error => {
                console.error('获取日志时出错:', error);
            });
    }
    
    // 测试邮件接收
    function testEmailReceive() {
        const resultElement = document.getElementById('email-receive-result');
        const emailsList = document.getElementById('recent-emails-list');
        const resultContainer = document.getElementById('recent-emails-test-result');
        
        if (resultElement) {
            resultElement.textContent = '正在获取邮件...';
            resultElement.className = 'test-result loading-text';
        }
        
        if (emailsList) {
            // 清空现有内容
            emailsList.innerHTML = '<tr><td colspan="3" class="loading-text">正在获取邮件，请稍候...</td></tr>';
            
            // 显示结果容器
            if (resultContainer) {
                resultContainer.style.display = 'block';
            }
        }
        
        fetch('/test_email_receive', {
            method: 'POST'
        })
        .then(response => {
            console.log('收到响应:', response.status);
            if (!response.ok) {
                throw new Error(`HTTP错误! 状态: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            console.log('解析响应数据:', data);
            
            if (resultElement) {
                if (data.success) {
                    resultElement.textContent = '邮件接收测试成功';
                    resultElement.className = 'test-result test-success';
                } else {
                    resultElement.textContent = '邮件接收测试失败: ' + data.error;
                    resultElement.className = 'test-result test-error';
                }
            }
            
            if (emailsList) {
                // 清空现有内容
                emailsList.innerHTML = '';
                
                if (data.emails && data.emails.length > 0) {
                    console.log('找到 ' + data.emails.length + ' 封邮件');
                    
                    // 添加邮件到列表
                    data.emails.forEach(email => {
                        const row = document.createElement('tr');
                        
                        const dateCell = document.createElement('td');
                        dateCell.textContent = email.date || '未知日期';
                        row.appendChild(dateCell);
                        
                        const senderCell = document.createElement('td');
                        senderCell.textContent = email.sender || '未知发件人';
                        row.appendChild(senderCell);
                        
                        const subjectCell = document.createElement('td');
                        subjectCell.textContent = email.subject || '无主题';
                        row.appendChild(subjectCell);
                        
                        emailsList.appendChild(row);
                    });
                } else {
                    console.log('没有找到邮件');
                    // 如果没有邮件，显示提示信息
                    const row = document.createElement('tr');
                    const cell = document.createElement('td');
                    cell.setAttribute('colspan', '3');
                    cell.textContent = '没有找到邮件';
                    row.appendChild(cell);
                    emailsList.appendChild(row);
                }
            }
        })
        .catch(error => {
            console.error('测试邮件接收时出错:', error);
            
            if (resultElement) {
                resultElement.textContent = '测试失败: ' + error.message;
                resultElement.className = 'test-result test-error';
            }
            
            if (emailsList) {
                emailsList.innerHTML = '';
                const row = document.createElement('tr');
                const cell = document.createElement('td');
                cell.setAttribute('colspan', '3');
                cell.className = 'error-text';
                cell.textContent = '获取邮件时出错: ' + error.message;
                row.appendChild(cell);
                emailsList.appendChild(row);
            }
        });
    }
    
    // 获取账户信息
    function getAccountInfo() {
        const resultElement = document.getElementById('account-info-result');
        const detailsElement = document.getElementById('account-info-details');
        
        if (resultElement) {
            resultElement.textContent = '正在获取账户信息...';
            resultElement.className = 'test-result loading-text';
        }
        
        fetch('/get_account_info', {
            method: 'POST'
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                resultElement.textContent = '获取成功';
                resultElement.className = 'test-result test-success';
                
                // 显示详细信息
                detailsElement.style.display = 'block';
                
                // 获取要显示的数据
                const accountData = data.data || data;
                
                // 更新各部分信息
                document.getElementById('account-config').textContent = 
                    JSON.stringify(accountData.account_config || [], null, 2);
                document.getElementById('account-balance').textContent = 
                    JSON.stringify(accountData.balance || [], null, 2);
                document.getElementById('account-positions').textContent = 
                    JSON.stringify(accountData.positions || [], null, 2);
            } else {
                resultElement.textContent = '获取失败: ' + data.error;
                resultElement.className = 'test-result test-error';
                detailsElement.style.display = 'none';
            }
        })
        .catch(error => {
            console.error('获取账户信息时出错:', error);
            resultElement.textContent = '获取失败: ' + error.message;
            resultElement.className = 'test-result test-error';
            detailsElement.style.display = 'none';
        });
    }
    
    // 测试交易周期
    function testTradeCycle() {
        const resultElement = document.getElementById('account-info-result');
        resultElement.textContent = '正在测试交易周期...';
        resultElement.className = 'test-result loading';
        
        fetch('/test_trade_cycle', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                resultElement.textContent = '测试成功: ' + data.message;
                resultElement.className = 'test-result test-success';
            } else {
                resultElement.textContent = '测试失败: ' + data.message;
                resultElement.className = 'test-result test-error';
            }
            console.log('测试交易周期结果:', data);
        })
        .catch(error => {
            resultElement.textContent = '测试出错: ' + error.message;
            resultElement.className = 'test-result test-error';
            console.error('测试交易周期出错:', error);
        });
    }
    
    // 初始更新状态
    updateStatus();
    
    // 每5秒更新一次状态
    setInterval(updateStatus, 5000);
    
    // 绑定刷新日志按钮
    const refreshLogsButton = document.getElementById('refresh-logs');
    if (refreshLogsButton) {
        refreshLogsButton.addEventListener('click', refreshLogs);
    }
    
    // 绑定测试邮件接收按钮
    const testEmailReceiveButton = document.getElementById('test-email-receive');
    if (testEmailReceiveButton) {
        testEmailReceiveButton.addEventListener('click', testEmailReceive);
    }
    
    // 绑定获取账户信息按钮
    const getAccountInfoButton = document.getElementById('get-account-info');
    if (getAccountInfoButton) {
        getAccountInfoButton.addEventListener('click', getAccountInfo);
    }
    
    // 绑定测试交易周期按钮
    document.getElementById('test-trade-cycle').addEventListener('click', testTradeCycle);
}); 