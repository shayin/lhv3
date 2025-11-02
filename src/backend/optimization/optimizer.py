"""
策略参数优化器
"""
import logging
import optuna
import asyncio
from typing import Dict, Any, Tuple, Optional, List
from datetime import datetime
from sqlalchemy.orm import Session

from ..models import OptimizationJob, OptimizationTrial
from ..api.backtest_service import BacktestService

logger = logging.getLogger(__name__)


class StrategyOptimizer:
    """策略参数优化器"""
    
    def __init__(self, db: Session, job: OptimizationJob):
        self.db = db
        self.job = job
        self.backtest_service = BacktestService(db)
        self.config = job.optimization_config
        self.objective_function = job.objective_function
        
    def optimize(self) -> Tuple[Optional[Dict[str, Any]], Optional[float]]:
        """执行参数优化（同步）

        注意：Optuna 的 study.optimize 是阻塞的，我们在外部应将此方法放入线程执行以避免阻塞事件循环。
        """
        try:
            # 创建Optuna研究
            study = optuna.create_study(
                direction='maximize' if self._is_maximize_objective() else 'minimize',
                study_name=f"optimization_job_{self.job.id}"
            )

            # 设置优化参数
            n_trials = self.config.get('n_trials', 100)
            timeout = self.config.get('timeout', 3600)

            logger.info(f"开始优化，试验次数: {n_trials}, 超时时间: {timeout}秒")

            # 执行优化（阻塞）
            study.optimize(
                self._objective_function,
                n_trials=n_trials,
                timeout=timeout,
                callbacks=[self._trial_callback]
            )

            # 获取最优结果
            if study.best_trial:
                best_params = study.best_trial.params
                best_score = study.best_trial.value

                logger.info(f"优化完成，最优参数: {best_params}, 最优得分: {best_score}")
                return best_params, best_score
            else:
                logger.warning("优化未找到有效结果")
                return None, None

        except Exception as e:
            logger.error(f"优化过程中发生错误: {str(e)}")
            raise e
    
    def _objective_function(self, trial: optuna.Trial) -> float:
        """目标函数"""
        trial_record = None
        try:
            # 根据参数空间生成参数
            parameters = self._generate_parameters(trial)
            
            # 添加随机种子确保每次试验结果不同
            import time
            import random
            random_seed = int(time.time() * 1000) + trial.number + random.randint(1, 10000)
            parameters['random_seed'] = random_seed
            
            # 记录试验开始
            trial_record = OptimizationTrial(
                job_id=self.job.id,
                trial_number=trial.number,
                parameters=parameters,
                status='running'
            )
            self.db.add(trial_record)
            self.db.commit()
            
            start_time = datetime.utcnow()
            
            # 执行回测
            backtest_config = self.config['backtest_config']
            
            # 直接传递参数，不要包装在parameters字段中
            backtest_parameters = {
                'parameters': parameters,  # 确保参数正确传递给策略
                'save_backtest': False  # 不保存单个试验的回测
            }
            
            logger.info(f"试验{trial.number}: 参数={parameters}, 随机种子={random_seed}")
            logger.info(f"传递给回测的参数结构: {backtest_parameters}")
            
            result = self.backtest_service.run_backtest(
                strategy_id=self.job.strategy_id,
                symbol=backtest_config['symbol'],
                start_date=backtest_config['start_date'],
                end_date=backtest_config['end_date'],
                initial_capital=backtest_config['initial_capital'],
                parameters=backtest_parameters,
                data_source=backtest_config.get('data_source', 'database'),
                features=backtest_config.get('features', [])
            )
            
            if result.get('status') != 'success':
                raise Exception(f"回测失败: {result.get('message', '未知错误')}")
            
            # 计算目标值
            backtest_data = result.get('data', {})
            objective_value = self._calculate_objective_value(backtest_data)
            
            # 更新试验记录
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            trial_record.objective_value = objective_value
            trial_record.backtest_results = backtest_data  # 保存完整的回测结果
            trial_record.status = 'completed'
            trial_record.execution_time = execution_time
            trial_record.completed_at = datetime.utcnow()
            self.db.commit()
            
            logger.info(f"试验{trial.number}完成，参数: {parameters}, 得分: {objective_value}")
            
            return objective_value
            
        except Exception as e:
            logger.error(f"试验{trial.number}失败: {str(e)}")
            
            # 更新试验记录为失败（如果已创建）
            if trial_record is not None:
                trial_record.status = 'failed'
                trial_record.error_message = str(e)
                trial_record.completed_at = datetime.utcnow()
                self.db.commit()
            
            # 对于失败的试验，返回极差值
            return float('-inf') if self._is_maximize_objective() else float('inf')
    
    def _generate_parameters(self, trial: optuna.Trial) -> Dict[str, Any]:
        """根据参数空间生成参数"""
        parameters = {}
        parameter_spaces = self.config['parameter_spaces']
        
        for space in parameter_spaces:
            param_name = space['parameter_name']
            param_type = space['parameter_type']
            
            if param_type == 'int':
                min_v = int(space['min_value'])
                max_v = int(space['max_value'])
                step_v = space.get('step_size')
                if step_v is None:
                    parameters[param_name] = trial.suggest_int(param_name, min_v, max_v)
                else:
                    parameters[param_name] = trial.suggest_int(param_name, min_v, max_v, step=int(step_v))
            elif param_type == 'float':
                min_v = float(space['min_value'])
                max_v = float(space['max_value'])
                step_v = space.get('step_size')
                if step_v is None:
                    parameters[param_name] = trial.suggest_float(param_name, min_v, max_v)
                else:
                    parameters[param_name] = trial.suggest_float(param_name, min_v, max_v, step=float(step_v))
            elif param_type == 'choice':
                parameters[param_name] = trial.suggest_categorical(param_name, space['choices'])
            elif param_type in ('bool', 'boolean'):
                choices = space.get('choices') or [True, False]
                parameters[param_name] = trial.suggest_categorical(param_name, choices)
            else:
                raise ValueError(f"不支持的参数类型: {param_type}")
        
        return parameters
    
    def _calculate_objective_value(self, backtest_data: Dict[str, Any]) -> float:
        """计算目标函数值"""
        if self.objective_function == 'sharpe_ratio':
            return backtest_data.get('sharpe_ratio', 0.0)
        elif self.objective_function == 'total_return':
            return backtest_data.get('total_return', 0.0)
        elif self.objective_function == 'annual_return':
            return backtest_data.get('annual_return', 0.0)
        elif self.objective_function == 'max_drawdown':
            # 最大回撤越小越好，所以返回负值
            return -abs(backtest_data.get('max_drawdown', 1.0))
        elif self.objective_function == 'profit_factor':
            return backtest_data.get('profit_factor', 0.0)
        elif self.objective_function == 'win_rate':
            return backtest_data.get('win_rate', 0.0)
        else:
            raise ValueError(f"不支持的目标函数: {self.objective_function}")
    
    def _is_maximize_objective(self) -> bool:
        """判断是否为最大化目标"""
        maximize_objectives = [
            'sharpe_ratio', 'total_return', 'annual_return', 
            'profit_factor', 'win_rate'
        ]
        return self.objective_function in maximize_objectives
    
    def _trial_callback(self, study: optuna.Study, trial: optuna.Trial):
        """试验回调函数，用于更新进度"""
        try:
            completed_trials = len([t for t in study.trials if t.state == optuna.trial.TrialState.COMPLETE])
            total_trials = self.config.get('n_trials', 100)
            progress = (completed_trials / total_trials) * 100
            
            # 更新任务进度
            self.job.completed_trials = completed_trials
            self.job.progress = progress
            
            # 更新最佳结果
            if study.best_trial:
                self.job.best_parameters = study.best_trial.params
                self.job.best_score = study.best_trial.value
            
            self.db.commit()
            
            logger.info(f"优化进度: {progress:.1f}% ({completed_trials}/{total_trials})")
            
        except Exception as e:
            logger.error(f"更新进度失败: {str(e)}")


class MultiObjectiveOptimizer(StrategyOptimizer):
    """多目标优化器"""
    
    def __init__(self, db: Session, job: OptimizationJob, objectives: List[str]):
        super().__init__(db, job)
        self.objectives = objectives
    
    def optimize(self) -> Tuple[Optional[List[Dict[str, Any]]], Optional[List[float]]]:
        """执行多目标优化（同步实现）"""
        try:
            # 创建多目标优化研究
            study = optuna.create_study(
                directions=['maximize' if self._is_maximize_objective(obj) else 'minimize' 
                          for obj in self.objectives],
                study_name=f"multi_objective_job_{self.job.id}"
            )

            n_trials = self.config.get('n_trials', 100)
            timeout = self.config.get('timeout', 3600)

            # 执行优化（阻塞）
            study.optimize(
                self._multi_objective_function,
                n_trials=n_trials,
                timeout=timeout,
                callbacks=[self._trial_callback]
            )

            # 获取帕累托最优解
            if study.best_trials:
                best_params_list = [trial.params for trial in study.best_trials]
                best_scores_list = [trial.values for trial in study.best_trials]

                logger.info(f"多目标优化完成，找到{len(best_params_list)}个帕累托最优解")
                return best_params_list, best_scores_list
            else:
                return None, None

        except Exception as e:
            logger.error(f"多目标优化过程中发生错误: {str(e)}")
            raise e
    
    def _multi_objective_function(self, trial: optuna.Trial) -> List[float]:
        """多目标函数"""
        # 生成参数并执行回测（与单目标相同）
        parameters = self._generate_parameters(trial)
        
        # 执行回测
        backtest_config = self.config['backtest_config']
        
        # 构造正确的参数结构，包装策略参数
        backtest_parameters = {
            'parameters': parameters,  # 策略参数
            'save_backtest': False     # 不保存单个试验的回测
        }
        
        result = self.backtest_service.run_backtest(
            strategy_id=self.job.strategy_id,
            symbol=backtest_config['symbol'],
            start_date=backtest_config['start_date'],
            end_date=backtest_config['end_date'],
            initial_capital=backtest_config['initial_capital'],
            parameters=backtest_parameters,
            data_source=backtest_config.get('data_source', 'database'),
            features=backtest_config.get('features', [])
        )
        
        if result.get('status') != 'success':
            raise Exception(f"回测失败: {result.get('message', '未知错误')}")
        
        # 计算所有目标值
        backtest_data = result.get('data', {})
        objective_values = []
        
        for objective in self.objectives:
            self.objective_function = objective  # 临时设置当前目标函数
            value = self._calculate_objective_value(backtest_data)
            objective_values.append(value)
        
        return objective_values
