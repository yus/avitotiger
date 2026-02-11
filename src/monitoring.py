import psutil
import platform
from datetime import datetime
from loguru import logger

class BotMonitor:
    @staticmethod
    def get_system_info():
        return {
            'cpu_percent': psutil.cpu_percent(interval=1),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_usage': psutil.disk_usage('/').percent,
            'uptime': datetime.now().timestamp() - psutil.boot_time(),
            'python_version': platform.python_version(),
            'hostname': platform.node()
        }
    
    @staticmethod
    def log_stats():
        stats = BotMonitor.get_system_info()
        logger.info(f"System stats: CPU: {stats['cpu_percent']}%, "
                   f"Memory: {stats['memory_percent']}%, "
                   f"Disk: {stats['disk_usage']}%")
        return stats
