import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
import os
import logging

from ..config import PROCESSED_DATA_DIR

logger = logging.getLogger(__name__)

class PerformanceAnalyzer:
    """性能分析器，用于分析回测结果并生成报告"""
    
    def __init__(self, backtest_results=None):
        """
        初始化性能分析器
        
        Args:
            backtest_results (dict, optional): 回测结果
        """
        self.results = backtest_results
        
    def set_results(self, results):
        """设置回测结果"""
        self.results = results
        
    def analyze(self):
        """
        分析回测结果
        
        Returns:
            dict: 分析结果
        """
        if not self.results:
            return {}
            
        # 确保结果包含必要的字段
        if 'trades' not in self.results or 'performance' not in self.results:
            logger.warning("回测结果不完整，无法进行分析")
            return {}
            
        # 计算各项指标
        metrics = self.calculate_metrics()
        
        # 生成交易统计
        trade_stats = self.analyze_trades()
        
        # 组合所有分析结果
        analysis = {
            'metrics': metrics,
            'trade_stats': trade_stats
        }
        
        return analysis
    
    def calculate_metrics(self):
        """
        计算性能指标
        
        Returns:
            dict: 性能指标
        """
        if not self.results or 'performance' not in self.results:
            return {}
            
        performance = self.results['performance']
        
        # 计算其他指标
        metrics = performance.copy()
        
        # 计算月度收益率
        if 'equity_curve' in self.results and self.results['equity_curve'] is not None:
            equity_curve = self.results['equity_curve']
            
            # 将日期转换为datetime
            if 'date' in equity_curve.columns and equity_curve['date'].dtype != 'datetime64[ns]':
                equity_curve['date'] = pd.to_datetime(equity_curve['date'])
                
            # 计算每日收益率
            equity_curve['daily_return'] = equity_curve['equity'].pct_change()
            
            # 计算月度收益率
            equity_curve['year_month'] = equity_curve['date'].dt.strftime('%Y-%m')
            monthly_returns = equity_curve.groupby('year_month')['daily_return'].apply(
                lambda x: (1 + x).prod() - 1
            )
            
            # 添加到指标中
            metrics['monthly_returns'] = monthly_returns.to_dict()
            metrics['positive_months'] = (monthly_returns > 0).sum()
            metrics['negative_months'] = (monthly_returns <= 0).sum()
            
            # 计算最大连续盈利/亏损月数
            pos_streak, neg_streak = self._calculate_streaks(monthly_returns)
            metrics['max_consecutive_positive_months'] = pos_streak
            metrics['max_consecutive_negative_months'] = neg_streak
        
        return metrics
    
    def analyze_trades(self):
        """
        分析交易记录
        
        Returns:
            dict: 交易统计
        """
        if not self.results or 'trades' not in self.results or not self.results['trades']:
            return {}
            
        # 将交易转换为DataFrame
        trades_df = pd.DataFrame(self.results['trades'])
        
        # 确保日期是datetime类型
        if 'date' in trades_df.columns:
            trades_df['date'] = pd.to_datetime(trades_df['date'])
        
        # 基础统计
        stats = {
            'total_trades': len(trades_df),
            'buy_trades': len(trades_df[trades_df['action'] == 'BUY']),
            'sell_trades': len(trades_df[trades_df['action'] == 'SELL']),
            'total_commission': trades_df['commission'].sum()
        }
        
        # 计算盈利和亏损交易
        if 'revenue' in trades_df.columns and 'cost' in trades_df.columns:
            # 只考虑卖出交易
            sell_trades = trades_df[trades_df['action'] == 'SELL'].copy()
            if not sell_trades.empty:
                # 计算每笔交易的盈亏
                sell_trades['profit'] = sell_trades['revenue'] - sell_trades['cost']
                
                # 分类为盈利和亏损交易
                winning_trades = sell_trades[sell_trades['profit'] > 0]
                losing_trades = sell_trades[sell_trades['profit'] <= 0]
                
                # 统计胜率
                stats['win_rate'] = len(winning_trades) / len(sell_trades) if len(sell_trades) > 0 else 0
                
                # 平均盈亏
                stats['avg_profit'] = winning_trades['profit'].mean() if not winning_trades.empty else 0
                stats['avg_loss'] = losing_trades['profit'].mean() if not losing_trades.empty else 0
                
                # 盈亏比
                stats['profit_loss_ratio'] = abs(stats['avg_profit'] / stats['avg_loss']) if stats['avg_loss'] != 0 else float('inf')
                
                # 最大盈利和亏损
                stats['max_profit'] = winning_trades['profit'].max() if not winning_trades.empty else 0
                stats['max_loss'] = losing_trades['profit'].min() if not losing_trades.empty else 0
        
        # 计算持仓时间
        if 'buy_date' in trades_df.columns and 'sell_date' in trades_df.columns:
            trades_df['holding_period'] = (trades_df['sell_date'] - trades_df['buy_date']).dt.days
            stats['avg_holding_period'] = trades_df['holding_period'].mean()
            stats['max_holding_period'] = trades_df['holding_period'].max()
            stats['min_holding_period'] = trades_df['holding_period'].min()
        
        return stats
    
    def _calculate_streaks(self, returns_series):
        """
        计算最大连续盈利/亏损期数
        
        Args:
            returns_series (pandas.Series): 收益率序列
            
        Returns:
            tuple: (最大连续盈利期数, 最大连续亏损期数)
        """
        # 转换为1（盈利）和-1（亏损）的序列
        streak_series = np.where(returns_series > 0, 1, -1)
        
        # 计算连续盈利/亏损
        pos_streak = 0
        neg_streak = 0
        current_pos_streak = 0
        current_neg_streak = 0
        
        for val in streak_series:
            if val > 0:
                current_pos_streak += 1
                current_neg_streak = 0
                pos_streak = max(pos_streak, current_pos_streak)
            else:
                current_neg_streak += 1
                current_pos_streak = 0
                neg_streak = max(neg_streak, current_neg_streak)
                
        return pos_streak, neg_streak
    
    def generate_report(self, output_dir=None, filename=None, plot=True):
        """
        生成回测报告
        
        Args:
            output_dir (str, optional): 输出目录
            filename (str, optional): 报告文件名
            plot (bool, optional): 是否生成图表
            
        Returns:
            str: 报告文件路径
        """
        if not self.results:
            logger.warning("无法生成报告: 未提供回测结果")
            return None
            
        # 设置输出目录
        if output_dir is None:
            output_dir = PROCESSED_DATA_DIR
            
        os.makedirs(output_dir, exist_ok=True)
        
        # 设置报告文件名
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            strategy_name = self.results.get('strategy_name', 'strategy')
            filename = f"backtest_report_{strategy_name}_{timestamp}.html"
            
        # 分析结果
        analysis = self.analyze()
        
        # 生成HTML报告
        html_content = self._generate_html_report(analysis, plot)
        
        # 保存报告
        report_path = os.path.join(output_dir, filename)
        with open(report_path, 'w') as f:
            f.write(html_content)
            
        logger.info(f"回测报告已生成: {report_path}")
        
        return report_path
    
    def _generate_html_report(self, analysis, plot=True):
        """
        生成HTML格式的回测报告
        
        Args:
            analysis (dict): 分析结果
            plot (bool): 是否生成图表
            
        Returns:
            str: HTML内容
        """
        # 获取策略信息
        strategy_name = self.results.get('strategy_name', 'Unknown Strategy')
        parameters = self.results.get('parameters', {})
        start_date = self.results.get('start_date', '')
        end_date = self.results.get('end_date', '')
        initial_capital = self.results.get('initial_capital', 0)
        
        # 获取绩效指标
        metrics = analysis.get('metrics', {})
        trade_stats = analysis.get('trade_stats', {})
        
        # 生成HTML头部
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>回测报告 - {strategy_name}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; }}
                h1, h2, h3 {{ color: #333; }}
                table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                tr:nth-child(even) {{ background-color: #f9f9f9; }}
                .summary {{ background-color: #f0f0f0; padding: 15px; border-radius: 5px; margin: 20px 0; }}
                .chart {{ width: 100%; height: 400px; margin: 20px 0; }}
            </style>
        </head>
        <body>
            <h1>回测报告</h1>
            
            <div class="summary">
                <h2>策略摘要</h2>
                <p><strong>策略名称:</strong> {strategy_name}</p>
                <p><strong>回测期间:</strong> {start_date} 至 {end_date}</p>
                <p><strong>初始资金:</strong> {initial_capital}</p>
                <p><strong>最终资金:</strong> {initial_capital * (1 + metrics.get('total_return', 0)):.2f}</p>
                <p><strong>总收益率:</strong> {metrics.get('total_return', 0) * 100:.2f}%</p>
                <p><strong>年化收益率:</strong> {metrics.get('annual_return', 0) * 100:.2f}%</p>
                <p><strong>夏普比率:</strong> {metrics.get('sharpe_ratio', 0):.2f}</p>
                <p><strong>最大回撤:</strong> {metrics.get('max_drawdown', 0) * 100:.2f}%</p>
            </div>
            
            <h2>策略参数</h2>
            <table>
                <tr>
                    <th>参数</th>
                    <th>值</th>
                </tr>
        """
        
        # 添加策略参数
        for param, value in parameters.items():
            html += f"""
                <tr>
                    <td>{param}</td>
                    <td>{value}</td>
                </tr>
            """
            
        html += """
            </table>
            
            <h2>绩效指标</h2>
            <table>
                <tr>
                    <th>指标</th>
                    <th>值</th>
                </tr>
        """
        
        # 添加绩效指标
        for metric, value in metrics.items():
            if metric != 'monthly_returns' and not isinstance(value, dict):
                if isinstance(value, float):
                    html += f"""
                        <tr>
                            <td>{metric}</td>
                            <td>{value:.4f}</td>
                        </tr>
                    """
                else:
                    html += f"""
                        <tr>
                            <td>{metric}</td>
                            <td>{value}</td>
                        </tr>
                    """
                    
        html += """
            </table>
            
            <h2>交易统计</h2>
            <table>
                <tr>
                    <th>指标</th>
                    <th>值</th>
                </tr>
        """
        
        # 添加交易统计
        for stat, value in trade_stats.items():
            if isinstance(value, float):
                html += f"""
                    <tr>
                        <td>{stat}</td>
                        <td>{value:.4f}</td>
                    </tr>
                """
            else:
                html += f"""
                    <tr>
                        <td>{stat}</td>
                        <td>{value}</td>
                    </tr>
                """
        
        # 添加图表占位符
        if plot and 'equity_curve' in self.results and self.results['equity_curve'] is not None:
            html += """
            </table>
            
            <h2>权益曲线</h2>
            <div class="chart" id="equity_chart"></div>
            
            <h2>回撤</h2>
            <div class="chart" id="drawdown_chart"></div>
            
            <script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
            <script>
                // 权益曲线图表
                var equityChart = echarts.init(document.getElementById('equity_chart'));
                var equityOption = {
                    title: {
                        text: '权益曲线'
                    },
                    tooltip: {
                        trigger: 'axis'
                    },
                    xAxis: {
                        type: 'time',
                        name: '日期'
                    },
                    yAxis: {
                        type: 'value',
                        name: '资金'
                    },
                    series: [{
                        name: '权益',
                        type: 'line',
                        data: [
            """
            
            # 添加权益曲线数据
            equity_curve = self.results['equity_curve']
            for i, row in equity_curve.iterrows():
                date = row['date'].strftime('%Y-%m-%d') if hasattr(row['date'], 'strftime') else row['date']
                equity = row['equity']
                html += f"['{date}', {equity}],"
                
            html += """
                        ],
                        markPoint: {
                            data: [
                                {type: 'max', name: '最大值'},
                                {type: 'min', name: '最小值'}
                            ]
                        }
                    }]
                };
                equityChart.setOption(equityOption);
                
                // 回撤图表
                var drawdownChart = echarts.init(document.getElementById('drawdown_chart'));
                var drawdownOption = {
                    title: {
                        text: '回撤'
                    },
                    tooltip: {
                        trigger: 'axis'
                    },
                    xAxis: {
                        type: 'time',
                        name: '日期'
                    },
                    yAxis: {
                        type: 'value',
                        name: '回撤',
                        axisLabel: {
                            formatter: '{value}%'
                        }
                    },
                    series: [{
                        name: '回撤',
                        type: 'line',
                        data: [
            """
            
            # 添加回撤数据
            drawdowns = self.results['drawdowns']
            for i, row in drawdowns.iterrows():
                date = row['date'].strftime('%Y-%m-%d') if hasattr(row['date'], 'strftime') else row['date']
                drawdown = row['drawdown'] * 100  # 转换为百分比
                html += f"['{date}', {drawdown}],"
                
            html += """
                        ],
                        markPoint: {
                            data: [
                                {type: 'min', name: '最大回撤'}
                            ]
                        },
                        areaStyle: {opacity: 0.5}
                    }]
                };
                drawdownChart.setOption(drawdownOption);
            </script>
            """
        else:
            html += """
            </table>
            """
            
        # 添加页脚
        html += f"""
            <div style="margin-top: 50px; text-align: center; color: #888;">
                <p>Generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
        </body>
        </html>
        """
        
        return html 