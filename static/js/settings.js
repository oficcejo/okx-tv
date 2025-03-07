document.addEventListener('DOMContentLoaded', function() {
    // 邮件连接测试
    const testEmailBtn = document.getElementById('test-email-btn');
    const emailTestResult = document.getElementById('email-test-result');
    
    if (testEmailBtn) {
        testEmailBtn.addEventListener('click', function() {
            // 获取邮件设置
            const emailServer = document.getElementById('email_server').value;
            const emailUsername = document.getElementById('email_username').value;
            const emailPassword = document.getElementById('email_password').value;
            
            // 验证输入
            if (!emailServer || !emailUsername || !emailPassword) {
                emailTestResult.textContent = '请填写所有邮箱设置';
                emailTestResult.className = 'test-result test-error';
                return;
            }
            
            // 显示加载状态
            emailTestResult.innerHTML = '<div class="loading"></div>';
            
            // 发送测试请求
            fetch('/test_email_connection', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    email_server: emailServer,
                    email_username: emailUsername,
                    email_password: emailPassword
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    emailTestResult.textContent = '连接成功！';
                    emailTestResult.className = 'test-result test-success';
                } else {
                    emailTestResult.textContent = '连接失败: ' + data.error;
                    emailTestResult.className = 'test-result test-error';
                }
            })
            .catch(error => {
                emailTestResult.textContent = '测试请求失败';
                emailTestResult.className = 'test-result test-error';
                console.error('Error:', error);
            });
        });
    }
    
    // API连接测试
    const testApiBtn = document.getElementById('test-api-btn');
    const apiTestResult = document.getElementById('api-test-result');
    
    if (testApiBtn) {
        testApiBtn.addEventListener('click', function() {
            // 获取API设置
            const apiKey = document.getElementById('okx_api_key').value;
            const secretKey = document.getElementById('okx_secret_key').value;
            const passphrase = document.getElementById('okx_passphrase').value;
            
            // 验证输入
            if (!apiKey || !secretKey || !passphrase) {
                apiTestResult.textContent = '请填写所有API设置';
                apiTestResult.className = 'test-result test-error';
                return;
            }
            
            // 显示加载状态
            apiTestResult.innerHTML = '<div class="loading"></div>';
            
            // 发送测试请求
            fetch('/test_api_connection', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    api_key: apiKey,
                    secret_key: secretKey,
                    passphrase: passphrase
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    apiTestResult.textContent = '连接成功！';
                    apiTestResult.className = 'test-result test-success';
                } else {
                    apiTestResult.textContent = '连接失败: ' + data.error;
                    apiTestResult.className = 'test-result test-error';
                }
            })
            .catch(error => {
                apiTestResult.textContent = '测试请求失败';
                apiTestResult.className = 'test-result test-error';
                console.error('Error:', error);
            });
        });
    }
}); 