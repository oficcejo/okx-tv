// 定期检查系统状态
function checkStatus() {
    fetch('/api/status')
        .then(response => response.json())
        .then(data => {
            const statusElement = document.getElementById('checker-status');
            const startButton = document.querySelector('.btn-start');
            const stopButton = document.querySelector('.btn-stop');
            const statusMessage = document.querySelector('.status-message p');
            
            if (statusElement) {
                if (data.email_checker_running) {
                    statusElement.textContent = '运行中';
                    statusElement.className = 'status-value running';
                    
                    if (startButton) startButton.disabled = true;
                    if (stopButton) stopButton.disabled = false;
                    if (statusMessage) statusMessage.textContent = '系统正在监控TradingView邮件信号，收到信号后将自动执行交易。';
                } else {
                    statusElement.textContent = '已停止';
                    statusElement.className = 'status-value stopped';
                    
                    if (startButton) startButton.disabled = false;
                    if (stopButton) stopButton.disabled = true;
                    if (statusMessage) statusMessage.textContent = '系统当前已停止，点击"启动"按钮开始监控邮件信号。';
                }
            }
        })
        .catch(error => console.error('获取状态时出错:', error));
}

// 页面加载完成后开始检查
document.addEventListener('DOMContentLoaded', function() {
    // 立即检查一次
    checkStatus();
    
    // 每5秒检查一次
    setInterval(checkStatus, 5000);
    
    // 自动隐藏闪现消息
    const flashMessages = document.querySelectorAll('.message');
    flashMessages.forEach(message => {
        setTimeout(() => {
            message.style.opacity = '0';
            message.style.transition = 'opacity 0.5s';
            setTimeout(() => {
                message.style.display = 'none';
            }, 500);
        }, 3000);
    });
    
    // 获取所有表单
    const startForm = document.querySelector('form[action*="start_checker"]');
    const stopForm = document.querySelector('form[action*="stop_checker"]');
    
    // 添加启动确认
    if (startForm) {
        startForm.addEventListener('submit', function(e) {
            if (!confirm('确定要启动系统吗？系统将开始监控邮件并执行交易。')) {
                e.preventDefault();
            }
        });
    }
    
    // 添加停止确认
    if (stopForm) {
        stopForm.addEventListener('submit', function(e) {
            if (!confirm('确定要停止系统吗？停止后将不再监控邮件和执行交易。')) {
                e.preventDefault();
            }
        });
    }
}); 