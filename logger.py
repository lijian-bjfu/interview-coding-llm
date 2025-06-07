"""
自定义日志记录器模块
"""

from datetime import datetime
import os

class Logger:
    def __init__(self, log_file: str = 'workflow.log'):
        self.log_file = log_file
        
    def log(self, operation: str, status: str, details: str):
        """
        记录日志
        
        Args:
            operation: 操作名称
            status: 状态（如 "开始"、"成功"、"失败"、"错误" 等）
            details: 详细信息
        """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_message = f"[{timestamp}] {status}: {operation} - {details}"
        
        # 打印到控制台
        print(log_message)
        
        # 写入日志文件
        try:
            log_dir = os.path.dirname(self.log_file)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir)
                
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(log_message + '\n')
        except Exception as e:
            print(f"Warning: Failed to write to log file: {e}")

# 创建全局logger实例
logger = Logger() 