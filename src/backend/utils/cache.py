"""
缓存工具类，用于缓存计算结果和数据，减少重复计算
"""
import os
import pickle
import hashlib
import json
import pandas as pd
from datetime import datetime, timedelta
from typing import Any, Optional, Dict, Callable
import logging

logger = logging.getLogger(__name__)

class CacheManager:
    """缓存管理器"""
    
    def __init__(self, cache_dir: str = "cache", default_ttl: int = 3600):
        """
        初始化缓存管理器
        
        Args:
            cache_dir: 缓存目录
            default_ttl: 默认缓存时间（秒）
        """
        self.cache_dir = cache_dir
        self.default_ttl = default_ttl
        self._ensure_cache_dir()
        
    def _ensure_cache_dir(self):
        """确保缓存目录存在"""
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
            
    def _get_cache_key(self, key: str, params: Dict = None) -> str:
        """生成缓存键"""
        if params:
            # 将参数转换为字符串并排序，确保一致性
            params_str = json.dumps(params, sort_keys=True, default=str)
            combined = f"{key}_{params_str}"
        else:
            combined = key
            
        # 使用MD5哈希生成短键名
        return hashlib.md5(combined.encode()).hexdigest()
        
    def _get_cache_path(self, cache_key: str) -> str:
        """获取缓存文件路径"""
        return os.path.join(self.cache_dir, f"{cache_key}.pkl")
        
    def _is_cache_valid(self, cache_path: str, ttl: int) -> bool:
        """检查缓存是否有效"""
        if not os.path.exists(cache_path):
            return False
            
        # 检查文件修改时间
        file_time = os.path.getmtime(cache_path)
        current_time = datetime.now().timestamp()
        
        return (current_time - file_time) < ttl
        
    def get(self, key: str, params: Dict = None, ttl: int = None) -> Optional[Any]:
        """
        获取缓存数据
        
        Args:
            key: 缓存键
            params: 参数字典
            ttl: 缓存时间（秒），None使用默认值
            
        Returns:
            缓存的数据，如果不存在或过期返回None
        """
        if ttl is None:
            ttl = self.default_ttl
            
        cache_key = self._get_cache_key(key, params)
        cache_path = self._get_cache_path(cache_key)
        
        if not self._is_cache_valid(cache_path, ttl):
            return None
            
        try:
            with open(cache_path, 'rb') as f:
                data = pickle.load(f)
                logger.debug(f"缓存命中: {key}")
                return data
        except Exception as e:
            logger.warning(f"读取缓存失败: {e}")
            return None
            
    def set(self, key: str, value: Any, params: Dict = None) -> bool:
        """
        设置缓存数据
        
        Args:
            key: 缓存键
            value: 要缓存的数据
            params: 参数字典
            
        Returns:
            是否成功设置缓存
        """
        cache_key = self._get_cache_key(key, params)
        cache_path = self._get_cache_path(cache_key)
        
        try:
            with open(cache_path, 'wb') as f:
                pickle.dump(value, f)
                logger.debug(f"缓存已设置: {key}")
                return True
        except Exception as e:
            logger.warning(f"设置缓存失败: {e}")
            return False
            
    def delete(self, key: str, params: Dict = None) -> bool:
        """
        删除缓存
        
        Args:
            key: 缓存键
            params: 参数字典
            
        Returns:
            是否成功删除
        """
        cache_key = self._get_cache_key(key, params)
        cache_path = self._get_cache_path(cache_key)
        
        try:
            if os.path.exists(cache_path):
                os.remove(cache_path)
                logger.debug(f"缓存已删除: {key}")
                return True
            return False
        except Exception as e:
            logger.warning(f"删除缓存失败: {e}")
            return False
            
    def clear_all(self) -> int:
        """
        清空所有缓存
        
        Returns:
            删除的文件数量
        """
        count = 0
        try:
            for filename in os.listdir(self.cache_dir):
                if filename.endswith('.pkl'):
                    file_path = os.path.join(self.cache_dir, filename)
                    os.remove(file_path)
                    count += 1
            logger.info(f"已清空所有缓存，删除了{count}个文件")
        except Exception as e:
            logger.warning(f"清空缓存失败: {e}")
        return count
        
    def clear_expired(self, ttl: int = None) -> int:
        """
        清理过期缓存
        
        Args:
            ttl: 缓存时间（秒），None使用默认值
            
        Returns:
            删除的文件数量
        """
        if ttl is None:
            ttl = self.default_ttl
            
        count = 0
        current_time = datetime.now().timestamp()
        
        try:
            for filename in os.listdir(self.cache_dir):
                if filename.endswith('.pkl'):
                    file_path = os.path.join(self.cache_dir, filename)
                    file_time = os.path.getmtime(file_path)
                    
                    if (current_time - file_time) >= ttl:
                        os.remove(file_path)
                        count += 1
                        
            logger.info(f"已清理过期缓存，删除了{count}个文件")
        except Exception as e:
            logger.warning(f"清理过期缓存失败: {e}")
            
        return count
        
    def cached_function(self, ttl: int = None, key_func: Callable = None):
        """
        装饰器：缓存函数结果
        
        Args:
            ttl: 缓存时间（秒）
            key_func: 自定义键生成函数
            
        Returns:
            装饰器函数
        """
        def decorator(func):
            def wrapper(*args, **kwargs):
                # 生成缓存键
                if key_func:
                    cache_key = key_func(*args, **kwargs)
                else:
                    cache_key = f"{func.__name__}_{hash(str(args) + str(sorted(kwargs.items())))}"
                
                # 尝试从缓存获取
                cached_result = self.get(cache_key, ttl=ttl)
                if cached_result is not None:
                    return cached_result
                
                # 执行函数并缓存结果
                result = func(*args, **kwargs)
                self.set(cache_key, result)
                
                return result
            return wrapper
        return decorator


class TechnicalIndicatorCache:
    """技术指标缓存类"""
    
    def __init__(self, cache_manager: CacheManager):
        self.cache_manager = cache_manager
        
    def get_indicator(self, symbol: str, indicator_name: str, params: Dict, data_hash: str) -> Optional[pd.Series]:
        """
        获取技术指标缓存
        
        Args:
            symbol: 股票代码
            indicator_name: 指标名称
            params: 指标参数
            data_hash: 数据哈希值（用于检测数据变化）
            
        Returns:
            缓存的指标数据
        """
        cache_key = f"indicator_{symbol}_{indicator_name}"
        cache_params = {**params, 'data_hash': data_hash}
        
        return self.cache_manager.get(cache_key, cache_params, ttl=86400)  # 1天缓存
        
    def set_indicator(self, symbol: str, indicator_name: str, params: Dict, data_hash: str, indicator_data: pd.Series):
        """
        设置技术指标缓存
        
        Args:
            symbol: 股票代码
            indicator_name: 指标名称
            params: 指标参数
            data_hash: 数据哈希值
            indicator_data: 指标数据
        """
        cache_key = f"indicator_{symbol}_{indicator_name}"
        cache_params = {**params, 'data_hash': data_hash}
        
        self.cache_manager.set(cache_key, indicator_data, cache_params)


class BacktestResultCache:
    """回测结果缓存类"""
    
    def __init__(self, cache_manager: CacheManager):
        self.cache_manager = cache_manager
        
    def get_backtest_result(self, strategy_id: str, symbol: str, params: Dict, data_hash: str) -> Optional[Dict]:
        """
        获取回测结果缓存
        
        Args:
            strategy_id: 策略ID
            symbol: 股票代码
            params: 策略参数
            data_hash: 数据哈希值
            
        Returns:
            缓存的回测结果
        """
        cache_key = f"backtest_{strategy_id}_{symbol}"
        cache_params = {**params, 'data_hash': data_hash}
        
        return self.cache_manager.get(cache_key, cache_params, ttl=3600)  # 1小时缓存
    
    def get(self, cache_key: str, data_hash: str) -> Optional[Dict]:
        """
        兼容性方法：直接通过缓存键获取回测结果
        
        Args:
            cache_key: 缓存键
            data_hash: 数据哈希值
            
        Returns:
            缓存的回测结果
        """
        cache_params = {'data_hash': data_hash}
        return self.cache_manager.get(cache_key, cache_params, ttl=3600)  # 1小时缓存
        
    def set(self, cache_key: str, result: Dict, data_hash: str):
        """
        兼容性方法：直接通过缓存键设置回测结果
        
        Args:
            cache_key: 缓存键
            result: 回测结果
            data_hash: 数据哈希值
        """
        cache_params = {'data_hash': data_hash}
        self.cache_manager.set(cache_key, result, cache_params)
        
    def set_backtest_result(self, strategy_id: str, symbol: str, params: Dict, data_hash: str, result: Dict):
        """
        设置回测结果缓存
        
        Args:
            strategy_id: 策略ID
            symbol: 股票代码
            params: 策略参数
            data_hash: 数据哈希值
            result: 回测结果
        """
        cache_key = f"backtest_{strategy_id}_{symbol}"
        cache_params = {**params, 'data_hash': data_hash}
        
        self.cache_manager.set(cache_key, result, cache_params)
        
    def delete(self, cache_key: str, data_hash: str) -> bool:
        """
        删除回测结果缓存
        
        Args:
            cache_key: 缓存键
            data_hash: 数据哈希值
            
        Returns:
            是否成功删除
        """
        cache_params = {'data_hash': data_hash}
        return self.cache_manager.delete(cache_key, cache_params)


# 全局缓存实例
cache_manager = CacheManager(cache_dir="cache", default_ttl=3600)
indicator_cache = TechnicalIndicatorCache(cache_manager)
backtest_cache = BacktestResultCache(cache_manager)