import os
import re
import sys

def check_sensitive_patterns():
    """检查敏感信息模式"""
    sensitive_patterns = [
        r'api[_-]?key\s*=\s*[\'"](.*?)[\'"]',
        r'secret[_-]?key\s*=\s*[\'"](.*?)[\'"]',
        r'password\s*=\s*[\'"](.*?)[\'"]',
        r'passphrase\s*=\s*[\'"](.*?)[\'"]',
        r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    ]
    
    issues_found = False
    
    for root, _, files in os.walk('.'):
        if 'venv' in root or '.git' in root:
            continue
            
        for file in files:
            if file.endswith(('.py', '.html', '.js', '.txt')):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        for pattern in sensitive_patterns:
                            matches = re.finditer(pattern, content)
                            for match in matches:
                                print(f'警告: 在文件 {file_path} 中发现可能的敏感信息:')
                                print(f'  - 匹配: {match.group()}')
                                issues_found = True
                except Exception as e:
                    print(f'无法读取文件 {file_path}: {str(e)}')
    
    return issues_found

def check_ignored_files():
    """检查是否有应该被忽略的文件未被忽略"""
    ignored_patterns = [
        '*.log',
        '*.sqlite',
        '*.db',
        '__pycache__',
        '*.pyc',
        '.env',
        'config.ini'
    ]
    
    issues_found = False
    
    for root, dirs, files in os.walk('.'):
        if 'venv' in root or '.git' in root:
            continue
            
        for pattern in ignored_patterns:
            if pattern.startswith('*'):
                # 检查文件
                ext = pattern[1:]
                matching_files = [f for f in files if f.endswith(ext)]
                if matching_files:
                    print(f'警告: 发现应该被忽略的文件:')
                    for file in matching_files:
                        print(f'  - {os.path.join(root, file)}')
                    issues_found = True
            else:
                # 检查目录
                if pattern in dirs:
                    print(f'警告: 发现应该被忽略的目录:')
                    print(f'  - {os.path.join(root, pattern)}')
                    issues_found = True
    
    return issues_found

def main():
    print('开始安全检查...\n')
    
    issues = False
    
    print('检查敏感信息...')
    if check_sensitive_patterns():
        issues = True
    else:
        print('未发现敏感信息。\n')
    
    print('检查应该被忽略的文件...')
    if check_ignored_files():
        issues = True
    else:
        print('未发现应该被忽略的文件。\n')
    
    if issues:
        print('\n警告：发现潜在问题！请在提交代码前解决这些问题。')
        sys.exit(1)
    else:
        print('\n检查完成：未发现问题。')
        sys.exit(0)

if __name__ == '__main__':
    main() 