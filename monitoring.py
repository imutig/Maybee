"""
Health Check and Monitoring System for Maybee
Provides system health monitoring, metrics collection, and diagnostics
"""

import time
import logging
import asyncio
import psutil
import traceback
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field 
from datetime import datetime, timedelta
from collections import defaultdict, deque
import json
import os

logger = logging.getLogger(__name__)

@dataclass
class HealthMetrics:
    """Container for health metrics"""
    timestamp: datetime = field(default_factory=datetime.now)
    
    # System metrics
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    disk_usage: float = 0.0
    
    # Bot metrics
    guilds_count: int = 0
    users_count: int = 0
    commands_executed: int = 0
    errors_count: int = 0
    
    # Database metrics
    db_connections: int = 0
    db_response_time: float = 0.0
    db_errors: int = 0
    
    # Performance metrics
    average_response_time: float = 0.0
    cache_hit_rate: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary"""
        return {
            'timestamp': self.timestamp.isoformat(),
            'system': {
                'cpu_usage': self.cpu_usage,
                'memory_usage': self.memory_usage,
                'disk_usage': self.disk_usage
            },
            'bot': {
                'guilds_count': self.guilds_count,
                'users_count': self.users_count,
                'commands_executed': self.commands_executed,
                'errors_count': self.errors_count
            },
            'database': {
                'connections': self.db_connections,
                'response_time': self.db_response_time,
                'errors': self.db_errors
            },
            'performance': {
                'average_response_time': self.average_response_time,
                'cache_hit_rate': self.cache_hit_rate
            }
        }

class HealthCheck:
    """Health check system for monitoring bot status"""
    
    def __init__(self, bot, database_manager=None, cache_manager=None):
        self.bot = bot
        self.database_manager = database_manager
        self.cache_manager = cache_manager
        
        # Metrics storage
        self.metrics_history: deque = deque(maxlen=1000)  # Keep last 1000 metrics
        self.error_log: deque = deque(maxlen=100)  # Keep last 100 errors
        
        # Performance tracking
        self.command_times: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self.response_times: deque = deque(maxlen=100)
        
        # Health status
        self.is_healthy = True
        self.last_check = datetime.now()
        
        # Monitoring task
        self.monitoring_task = None
        
        logger.info("Health check system initialized")
    
    async def start_monitoring(self, interval: int = 60):
        """Start continuous monitoring"""
        if self.monitoring_task:
            logger.warning("Monitoring already started")
            return
        
        self.monitoring_task = asyncio.create_task(self._monitor_loop(interval))
        logger.info(f"Health monitoring started with {interval}s interval")
    
    async def stop_monitoring(self):
        """Stop continuous monitoring"""
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
            self.monitoring_task = None
            logger.info("Health monitoring stopped")
    
    async def _monitor_loop(self, interval: int):
        """Main monitoring loop"""
        while True:
            try:
                await self.collect_metrics()
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(interval)
    
    async def collect_metrics(self) -> HealthMetrics:
        """Collect current health metrics"""
        metrics = HealthMetrics()
        
        try:
            # System metrics
            metrics.cpu_usage = psutil.cpu_percent(interval=1)
            metrics.memory_usage = psutil.virtual_memory().percent
            metrics.disk_usage = psutil.disk_usage('/').percent
            
            # Bot metrics
            if self.bot and hasattr(self.bot, 'guilds'):
                metrics.guilds_count = len(self.bot.guilds)
                metrics.users_count = len(self.bot.users)
            
            # Database metrics
            if self.database_manager:
                metrics.db_connections = await self._get_db_connections()
                metrics.db_response_time = await self._test_db_response_time()
            
            # Performance metrics
            if self.response_times:
                metrics.average_response_time = sum(self.response_times) / len(self.response_times)
            
            if self.cache_manager:
                metrics.cache_hit_rate = await self._get_cache_hit_rate()
            
            # Store metrics
            self.metrics_history.append(metrics)
            self.last_check = datetime.now()
            
            # Update health status
            self.is_healthy = self._assess_health(metrics)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error collecting metrics: {e}")
            self.log_error("metrics_collection", str(e))
            return metrics
    
    async def _get_db_connections(self) -> int:
        """Get current database connection count"""
        try:
            if hasattr(self.database_manager, 'pool') and self.database_manager.pool:
                return self.database_manager.pool.size
            return 0
        except:
            return 0
    
    async def _test_db_response_time(self) -> float:
        """Test database response time"""
        try:
            start_time = time.time()
            await self.database_manager.execute("SELECT 1")
            return time.time() - start_time
        except:
            return 0.0
    
    async def _get_cache_hit_rate(self) -> float:
        """Get cache hit rate"""
        try:
            if hasattr(self.cache_manager, 'hits') and hasattr(self.cache_manager, 'misses'):
                total = self.cache_manager.hits + self.cache_manager.misses
                return (self.cache_manager.hits / total * 100) if total > 0 else 0.0
            return 0.0
        except:
            return 0.0
    
    def _assess_health(self, metrics: HealthMetrics) -> bool:
        """Assess overall health based on metrics"""
        # Critical thresholds
        if metrics.cpu_usage > 90:
            logger.warning(f"High CPU usage: {metrics.cpu_usage}%")
            return False
        
        if metrics.memory_usage > 90:
            logger.warning(f"High memory usage: {metrics.memory_usage}%")
            return False
        
        if metrics.disk_usage > 95:
            logger.warning(f"High disk usage: {metrics.disk_usage}%")
            return False
        
        if metrics.db_response_time > 5.0:
            logger.warning(f"Slow database response: {metrics.db_response_time}s")
            return False
        
        return True
    
    def log_error(self, source: str, error: str, traceback_str: str = None):
        """Log an error for monitoring"""
        error_entry = {
            'timestamp': datetime.now().isoformat(),
            'source': source,
            'error': error,
            'traceback': traceback_str or traceback.format_exc()
        }
        
        self.error_log.append(error_entry)
        logger.error(f"Error logged from {source}: {error}")
    
    def track_command_execution(self, command_name: str, execution_time: float):
        """Track command execution time"""
        self.command_times[command_name].append(execution_time)
        self.response_times.append(execution_time)
    
    def get_health_report(self) -> Dict[str, Any]:
        """Generate comprehensive health report"""
        if not self.metrics_history:
            return {"status": "no_data", "message": "No metrics collected yet"}
        
        latest_metrics = self.metrics_history[-1]
        
        # Calculate averages from last 10 metrics
        recent_metrics = list(self.metrics_history)[-10:]
        avg_cpu = sum(m.cpu_usage for m in recent_metrics) / len(recent_metrics)
        avg_memory = sum(m.memory_usage for m in recent_metrics) / len(recent_metrics)
        avg_response = sum(m.average_response_time for m in recent_metrics) / len(recent_metrics)
        
        # Command statistics
        command_stats = {}
        for cmd, times in self.command_times.items():
            if times:
                command_stats[cmd] = {
                    'total_executions': len(times),
                    'average_time': sum(times) / len(times),
                    'max_time': max(times),
                    'min_time': min(times)
                }
        
        # Recent errors
        recent_errors = list(self.error_log)[-10:]
        
        return {
            'status': 'healthy' if self.is_healthy else 'unhealthy',
            'last_check': self.last_check.isoformat(),
            'current_metrics': latest_metrics.to_dict(),
            'averages': {
                'cpu_usage': avg_cpu,
                'memory_usage': avg_memory,
                'response_time': avg_response
            },
            'command_statistics': command_stats,
            'recent_errors': recent_errors,
            'uptime': self.get_uptime(),
            'bot_info': {
                'guilds': latest_metrics.guilds_count,
                'users': latest_metrics.users_count,
                'latency': round(self.bot.latency * 1000, 2) if self.bot else 0
            }
        }
    
    def get_uptime(self) -> str:
        """Get bot uptime"""
        if hasattr(self.bot, 'start_time'):
            uptime = datetime.now() - self.bot.start_time
            return str(uptime).split('.')[0]  # Remove microseconds
        return "Unknown"
    
    async def export_metrics(self, filepath: str = None):
        """Export metrics to JSON file"""
        if not filepath:
            filepath = f"health_metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        try:
            data = {
                'export_time': datetime.now().isoformat(),
                'metrics_history': [m.to_dict() for m in self.metrics_history],
                'error_log': list(self.error_log),
                'health_report': self.get_health_report()
            }
            
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"Metrics exported to {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Failed to export metrics: {e}")
            return None
    
    async def cleanup_old_data(self, days: int = 7):
        """Clean up old metric data"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # Filter metrics history
        filtered_metrics = deque(maxlen=1000)
        for metric in self.metrics_history:
            if metric.timestamp > cutoff_date:
                filtered_metrics.append(metric)
        
        self.metrics_history = filtered_metrics
        
        # Filter error log
        filtered_errors = deque(maxlen=100)
        for error in self.error_log:
            error_date = datetime.fromisoformat(error['timestamp'])
            if error_date > cutoff_date:
                filtered_errors.append(error)
        
        self.error_log = filtered_errors
        
        logger.info(f"Cleaned up data older than {days} days")

class PerformanceProfiler:
    """Performance profiler for tracking slow operations"""
    
    def __init__(self):
        self.slow_operations: deque = deque(maxlen=100)
        self.operation_counts: Dict[str, int] = defaultdict(int)
        
    def profile_operation(self, operation_name: str):
        """Decorator for profiling operations"""
        def decorator(func):
            import functools
            
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = await func(*args, **kwargs)
                    execution_time = time.time() - start_time
                    
                    self.operation_counts[operation_name] += 1
                    
                    # Track slow operations (>1 second)
                    if execution_time > 1.0:
                        self.slow_operations.append({
                            'operation': operation_name,
                            'execution_time': execution_time,
                            'timestamp': datetime.now().isoformat(),
                            'args': str(args)[:100],  # Truncate for privacy
                            'kwargs': str(kwargs)[:100]
                        })
                    
                    return result
                except Exception as e:
                    execution_time = time.time() - start_time
                    logger.error(f"Error in {operation_name}: {e} (took {execution_time:.2f}s)")
                    raise
            
            return wrapper
        return decorator
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Generate performance report"""
        return {
            'slow_operations': list(self.slow_operations),
            'operation_counts': dict(self.operation_counts),
            'total_operations': sum(self.operation_counts.values())
        }

# Global instances
health_checker = None
performance_profiler = PerformanceProfiler()

def initialize_monitoring(bot, database_manager=None, cache_manager=None):
    """Initialize monitoring system"""
    global health_checker
    health_checker = HealthCheck(bot, database_manager, cache_manager)
    logger.info("Monitoring system initialized")
    return health_checker

def get_health_checker():
    """Get the global health checker instance"""
    return health_checker

def profile_performance(operation_name: str):
    """Decorator for profiling performance"""
    return performance_profiler.profile_operation(operation_name)
