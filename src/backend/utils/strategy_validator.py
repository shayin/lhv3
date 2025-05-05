import ast
import inspect
import importlib.util
import sys
import os
import logging
import re
from typing import List, Dict, Any, Tuple

logger = logging.getLogger(__name__)

class StrategyValidator:
    """
    策略代码验证器
    用于验证用户创建的策略代码是否符合平台要求
    """
    
    @staticmethod
    def validate_strategy_code(code: str) -> Tuple[bool, List[str]]:
        """
        验证策略代码是否符合平台规范
        
        Args:
            code: 策略代码字符串
            
        Returns:
            验证是否通过，错误消息列表
        """
        errors = []
        
        # 记录原始代码，用于日志调试
        logger.debug(f"原始代码:\n{code}")
        
        # 处理相对导入问题，替换为绝对导入
        code = StrategyValidator._fix_relative_imports(code)
        
        # 记录修改后的代码，用于日志调试
        logger.debug(f"修改后代码:\n{code}")
        
        # 检查代码语法是否正确
        try:
            ast.parse(code)
        except SyntaxError as e:
            errors.append(f"语法错误: 第{e.lineno}行, {e.msg}")
            return False, errors
        
        # 检查必要的导入
        if "StrategyTemplate" not in code:
            errors.append("缺少必要的导入: 需要导入StrategyTemplate")
        
        # 检查类继承关系
        try:
            tree = ast.parse(code)
            class_found = False
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    class_found = True
                    # 检查是否继承自StrategyTemplate
                    if not any(base.id == 'StrategyTemplate' for base in node.bases if isinstance(base, ast.Name)):
                        errors.append(f"类'{node.name}'未继承自StrategyTemplate")
                    
                    # 检查是否实现了必要的方法
                    method_names = [method.name for method in node.body if isinstance(method, ast.FunctionDef)]
                    if 'generate_signals' not in method_names:
                        errors.append(f"类'{node.name}'必须实现generate_signals方法")
                    
                    # 检查__init__方法是否正确调用父类初始化
                    for method in node.body:
                        if isinstance(method, ast.FunctionDef) and method.name == '__init__':
                            init_calls_super = False
                            for stmt in ast.walk(method):
                                # 检查调用super()的任何形式
                                if (isinstance(stmt, ast.Call) and 
                                   isinstance(stmt.func, ast.Name) and
                                   stmt.func.id == 'super'):
                                    init_calls_super = True
                                    break
                                # 检查super().__init__的调用
                                elif (isinstance(stmt, ast.Call) and
                                     isinstance(stmt.func, ast.Attribute) and
                                     isinstance(stmt.func.value, ast.Call) and
                                     isinstance(stmt.func.value.func, ast.Name) and
                                     stmt.func.value.func.id == 'super'):
                                    init_calls_super = True
                                    break
                            
                            if not init_calls_super:
                                errors.append(f"类'{node.name}'的__init__方法必须调用super().__init__()")
            
            if not class_found:
                errors.append("代码中未找到策略类定义")
        
        except Exception as e:
            errors.append(f"代码分析错误: {str(e)}")
        
        # 检查是否可以动态加载执行
        if not errors:
            try:
                # 创建临时模块
                success, load_errors = StrategyValidator.test_load_strategy(code)
                if not success:
                    errors.extend(load_errors)
            except Exception as e:
                errors.append(f"策略加载测试失败: {str(e)}")
        
        # 返回验证结果
        return len(errors) == 0, errors
    
    @staticmethod
    def _fix_relative_imports(code: str) -> str:
        """
        修复代码中的相对导入问题，将相对导入转换为绝对导入
        
        Args:
            code: 原始代码字符串
            
        Returns:
            修复后的代码字符串
        """
        # 尝试获取当前工作目录的系统路径信息来决定如何处理导入
        src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
        sys.path.append(src_path)
        
        try:
            # 确认策略模板的实际位置
            import importlib
            try:
                # 优先使用项目中已存在的导入路径
                importlib.import_module("src.backend.strategy.templates.strategy_template")
                template_path = "src.backend.strategy.templates.strategy_template"
            except (ImportError, ModuleNotFoundError):
                try:
                    # 也可能是不使用src前缀的路径
                    importlib.import_module("backend.strategy.templates.strategy_template")
                    template_path = "backend.strategy.templates.strategy_template"
                except (ImportError, ModuleNotFoundError):
                    # 如果两种都不行，尝试相对于当前位置的导入
                    template_path = "strategy.templates.strategy_template"
            
            logger.info(f"找到策略模板路径: {template_path}")
        except Exception as e:
            logger.warning(f"无法确定策略模板路径: {e}")
            # 默认使用相对于src的路径
            template_path = "src.backend.strategy.templates.strategy_template"
        
        # 替换相对导入 (.strategy_template)
        code = re.sub(
            r'from\s+\.strategy_template\s+import\s+StrategyTemplate', 
            f'from {template_path} import StrategyTemplate',
            code
        )
        
        # 替换相对导入 (from . import strategy_template)
        base_path = ".".join(template_path.split(".")[:-1])
        code = re.sub(
            r'from\s+\.\s+import\s+strategy_template', 
            f'from {base_path} import strategy_template',
            code
        )
        
        # 如果需要父级目录的导入也一并处理
        parent_path = ".".join(template_path.split(".")[:-2])
        code = re.sub(
            r'from\s+\.\.\s+import\s+', 
            f'from {parent_path} import ',
            code
        )
        
        return code
    
    @staticmethod
    def test_load_strategy(code: str) -> Tuple[bool, List[str]]:
        """
        尝试加载和实例化策略，检查是否可以正常工作
        
        Args:
            code: 策略代码字符串
            
        Returns:
            加载是否成功，错误消息列表
        """
        errors = []
        temp_module_name = f"temp_strategy_module_{hash(code) % 10000}"
        
        # 确保代码使用绝对导入
        code = StrategyValidator._fix_relative_imports(code)
        
        try:
            # 创建临时模块规范
            spec = importlib.util.spec_from_loader(temp_module_name, loader=None)
            module = importlib.util.module_from_spec(spec)
            sys.modules[temp_module_name] = module
            
            # 添加src目录到系统路径
            src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
            if src_path not in sys.path:
                sys.path.insert(0, src_path)
                logger.info(f"添加路径到sys.path: {src_path}")
            
            # 执行代码，注入模块
            exec(code, module.__dict__)
            
            # 查找策略类
            strategy_class = None
            try:
                try:
                    # 尝试从项目路径导入
                    from src.backend.strategy.templates.strategy_template import StrategyTemplate
                except (ImportError, ModuleNotFoundError):
                    try:
                        # 尝试不带src前缀的导入
                        from backend.strategy.templates.strategy_template import StrategyTemplate
                    except (ImportError, ModuleNotFoundError):
                        # 直接相对当前位置导入
                        sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
                        from strategy.templates.strategy_template import StrategyTemplate
                
                for name, obj in module.__dict__.items():
                    if (isinstance(obj, type) and 
                        obj is not StrategyTemplate and 
                        issubclass(obj, StrategyTemplate)):
                        strategy_class = obj
                        break
            except Exception as e:
                logger.error(f"导入StrategyTemplate失败: {e}")
                errors.append(f"无法导入StrategyTemplate: {str(e)}")
                return False, errors
            
            if strategy_class is None:
                errors.append("未找到继承自StrategyTemplate的策略类")
                return False, errors
            
            # 实例化策略类
            try:
                strategy_instance = strategy_class()
                
                # 检查必须的方法是否被正确实现
                if hasattr(strategy_instance, 'generate_signals') and hasattr(strategy_instance.generate_signals, '__qualname__'):
                    if strategy_instance.generate_signals.__qualname__ == 'StrategyTemplate.generate_signals':
                        errors.append("generate_signals方法未被正确实现")
                
            except Exception as e:
                errors.append(f"实例化策略类失败: {str(e)}")
                return False, errors
                
        except Exception as e:
            errors.append(f"加载策略代码失败: {str(e)}")
            return False, errors
        
        finally:
            # 清理临时模块
            if temp_module_name in sys.modules:
                del sys.modules[temp_module_name]
        
        return len(errors) == 0, errors 