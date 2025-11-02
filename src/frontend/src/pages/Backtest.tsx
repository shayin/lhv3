import React, { useState, useEffect, useCallback, useRef, memo, useMemo } from 'react';
import { Card, Form, Button, DatePicker, Select, InputNumber, Row, Col, Divider, Typography, Tabs, Table, Statistic, Spin, message as antdMessage, Alert, Space, Tooltip, Modal, Tag, App, message, Slider, Input, Switch } from 'antd';
import { useNavigate } from 'react-router-dom';
import { LineChartOutlined, PlayCircleOutlined, DownloadOutlined, SaveOutlined, InfoCircleOutlined, MinusCircleOutlined, PlusOutlined, SettingOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import ReactECharts from 'echarts-for-react';
import { fetchStockList, fetchDataSources as fetchDataSourcesAPI, fetchStockDateRange, Stock, DataSource } from '../services/apiService';
import axios from 'axios';
import moment from 'moment';
import type { Moment } from 'moment';
import 'moment/locale/zh-cn'; // 添加中文支持
import type { RangePickerProps } from 'antd/es/date-picker';
import dayjs from 'dayjs';
import type { Dayjs } from 'dayjs';
import * as echarts from 'echarts/core';
import { CandlestickChart, LineChart, BarChart } from 'echarts/charts';
import {
  TitleComponent, TooltipComponent, GridComponent, DataZoomComponent,
  ToolboxComponent, LegendComponent, MarkPointComponent, MarkLineComponent
} from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';
import { getStrategies, backtestStrategy, backtestStrategyForceRefresh, submitAsyncBacktest, getAsyncBacktestStatus, getAsyncBacktestResult } from '../services/strategyService';
import OptimizedTable from '../components/OptimizedTable';
import OptimizedChart from '../components/OptimizedChart';
import { useDebounce } from '../hooks/useDebounce';

// 注册 ECharts 必要的组件
echarts.use([
  TitleComponent, TooltipComponent, GridComponent, DataZoomComponent,
  ToolboxComponent, LegendComponent, MarkPointComponent, MarkLineComponent,
  CandlestickChart, LineChart, BarChart, CanvasRenderer
]);

moment.locale('zh-cn'); // 设置为中文

const { RangePicker } = DatePicker;
const { Title, Paragraph } = Typography;
const { Option } = Select;

interface TradeRecord {
  key: string;
  date: string;
  symbol: string;
  direction: string;
  entryPrice?: number;
  exitPrice?: number;
  shares: number;
  value: number;  // 交易金额
  profitLoss: number;
  returnPct: number;
  duration: number;
  beforeCash: number;  // 交易前现金
  afterCash: number;   // 交易后现金
  beforeEquity: number; // 交易前总资产
  afterEquity: number;  // 交易后总资产
  trigger_reason?: string; // 交易触发原因
  available_capital?: number; // 交易后的可用资金
  allocated_capital?: number; // 已分配的资金
  position_size?: number; // 单次交易仓位比例
  cumulative_position_ratio?: number; // 累计仓位比例
}

const Backtest: React.FC = () => {
  const navigate = useNavigate();
  
  // 状态变量
  const [running, setRunning] = useState(false);
  const [hasResults, setHasResults] = useState(false);
  const [initialCapital, setInitialCapital] = useState(100000);
  const [commissionRate, setCommissionRate] = useState(0.15);
  const [slippage, setSlippage] = useState(0.1);
  const [stockList, setStockList] = useState<Stock[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedStrategy, setSelectedStrategy] = useState<number>(1); // 默认使用ID为1的策略
  const [selectedStrategyName, setSelectedStrategyName] = useState('MA交叉策略');
  const [selectedStock, setSelectedStock] = useState<Stock | null>(null);
  const [dateRange, setDateRange] = useState<[Dayjs, Dayjs]>([
    dayjs().subtract(1, 'year').startOf('day'),
    dayjs().endOf('day')
  ]);
  const [dataSources, setDataSources] = useState<DataSource[]>([]);
  const [tradeRecords, setTradeRecords] = useState<TradeRecord[]>([]);
  const [klineData, setKlineData] = useState<any[]>([]);
  const [equityCurveData, setEquityCurveData] = useState<any[]>([]);
  const [drawdownData, setDrawdownData] = useState<any[]>([]);
  const [performanceData, setPerformanceData] = useState<any>({
    totalReturn: 0,
    annualReturn: 0,
    sharpeRatio: 0,
    maxDrawdown: 0,
    winRate: 0,
    profitFactor: 0,
    alpha: 0,
    beta: 0
  });
  // 添加策略列表状态
  const [strategiesList, setStrategiesList] = useState<any[]>([]);
  const [backtestResults, setBacktestResults] = useState<any>(null);
  const [tradesData, setTradesData] = useState<any[]>([]);
  const [equityData, setEquityData] = useState<any[]>([]);
  const resultsRef = useRef<HTMLDivElement>(null);
  const initializedRef = useRef<boolean>(false); // 防止重复初始化
  // 添加策略参数状态
  const [strategyParameters, setStrategyParameters] = useState<Record<string, any>>({});
  const [showParametersModal, setShowParametersModal] = useState(false);
  const [parameterSpaces, setParameterSpaces] = useState<any[]>([]);
  const [currentStrategyInfo, setCurrentStrategyInfo] = useState<any>(null);
  const [showOptimizationResultsModal, setShowOptimizationResultsModal] = useState(false);
  const [optimizationResults, setOptimizationResults] = useState<any[]>([]);
  
  // 添加保存回测相关状态
  const [saveModalVisible, setSaveModalVisible] = useState(false);
  const [saveLoading, setSaveLoading] = useState(false);
  const [backtestName, setBacktestName] = useState('');
  const [backtestDescription, setBacktestDescription] = useState('');
  
  // 异步回测相关状态
  const [asyncMode, setAsyncMode] = useState(false);
  const [currentTaskId, setCurrentTaskId] = useState<string | null>(null);
  const [taskStatus, setTaskStatus] = useState<string>('');
  const [taskProgress, setTaskProgress] = useState<number>(0);
  const [pollingInterval, setPollingInterval] = useState<NodeJS.Timeout | null>(null);
  
  // 规范化日期字符串的函数，确保格式一致
  const normalizeDate = (dateStr: string | any): string => {
    if (typeof dateStr !== 'string') {
      return String(dateStr);
    }
    
    // 处理带T的ISO格式
    if (dateStr.includes('T')) {
      return dateStr.split('T')[0];
    }
    
    // 处理带空格的格式
    if (dateStr.includes(' ')) {
      return dateStr.split(' ')[0];
    }
    
    // 如果已经是YYYY-MM-DD格式
    if (/^\d{4}-\d{2}-\d{2}$/.test(dateStr)) {
      return dateStr;
    }
    
    // 如果是其他格式，返回前10个字符
    return dateStr.substring(0, 10);
  };

  // 保存回测函数
  const handleSaveBacktest = async () => {
    if (!backtestResults || !hasResults) {
      message.error('没有可保存的回测结果');
      return;
    }

    if (!backtestName.trim()) {
      message.error('请输入回测名称');
      return;
    }

    setSaveLoading(true);
    try {
      // 重新运行回测并保存结果
      const startDate = dateRange[0].format('YYYY-MM-DD');
      const endDate = dateRange[1].format('YYYY-MM-DD');
      
      const result = await backtestStrategy(
        selectedStrategy,
        selectedStock!.symbol,
        startDate,
        endDate,
        initialCapital,
        {
          save_backtest: true, // 启用保存
          backtest_name: backtestName,
          backtest_description: backtestDescription,
          parameters: strategyParameters // 添加策略参数
        },
        commissionRate,
        slippage,
        'database',
        []
      );

      if (result.error) {
        message.error(`保存失败: ${result.error}`);
        return;
      }

      if (result.saved) {
        message.success('回测保存成功！');
        setSaveModalVisible(false);
        setBacktestName('');
        setBacktestDescription('');
        
        // 询问用户是否跳转到回测历史页面
        Modal.confirm({
          title: '保存成功',
          content: '回测已成功保存，是否查看回测历史？',
          okText: '查看历史',
          cancelText: '继续回测',
          onOk: () => {
            navigate('/backtest/history');
          },
        });
      } else {
        message.error('保存失败，请重试');
      }
    } catch (error: any) {
      console.error('保存回测失败:', error);
      message.error(error.response?.data?.detail || '保存失败，请重试');
    } finally {
      setSaveLoading(false);
    }
  };
  
  // 清理轮询定时器
  const clearPolling = useCallback(() => {
    console.log('清理轮询定时器，当前pollingIntervalRef.current:', pollingIntervalRef.current);
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
      pollingIntervalRef.current = null;
      setPollingInterval(null);
      console.log('轮询定时器已清理');
    }
  }, []);

  // 组件卸载时清理定时器
  useEffect(() => {
    return () => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
        pollingIntervalRef.current = null;
      }
    };
  }, []);

  // 使用 useRef 来存储定时器ID，避免闭包问题
  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // 轮询任务状态
  const pollTaskStatus = useCallback(async (taskId: string) => {
    try {
      const status = await getAsyncBacktestStatus(taskId);
      console.log('任务状态:', status);
      
      setTaskStatus(status.status);
      setTaskProgress(status.progress || 0);
      
      if (status.status === 'completed') {
        console.log('任务已完成，准备清理轮询');
        
        // 立即清理轮询定时器
        if (pollingIntervalRef.current) {
          console.log('立即清理轮询定时器，ID:', pollingIntervalRef.current);
          clearInterval(pollingIntervalRef.current);
          pollingIntervalRef.current = null;
          setPollingInterval(null);
        }
        
        // 获取回测结果 - 优化：检查status中是否已包含结果
        try {
          let result;
          
          // 如果状态响应中已包含结果，直接使用，避免额外请求
          if (status.result && Object.keys(status.result).length > 0) {
            console.log('从状态响应中获取结果，避免额外请求');
            result = status.result;
          } else {
            console.log('状态响应中无结果，发起结果请求');
            result = await getAsyncBacktestResult(taskId);
          }
          
          console.log('异步回测结果:', result);
          
          // 检查结果是否为错误格式
          if (result && result.status === 'error') {
            console.error('回测执行失败:', result.message);
            antdMessage.error(`回测失败: ${result.message}`);
          } else {
            // 处理结果数据 - 提取data字段中的实际回测结果
            const backtestData = result.data || result;
            console.log('提取的回测数据:', backtestData);
            processBacktestResult(backtestData);
            message.success('异步回测完成');
          }
        } catch (error: any) {
          console.error('获取回测结果失败:', error);
          antdMessage.error(`获取回测结果失败: ${error.message}`);
        }
        
        setLoading(false);
        setCurrentTaskId(null);
      } else if (status.status === 'failed') {
        console.log('任务失败，准备清理轮询');
        
        // 立即清理轮询定时器
        if (pollingIntervalRef.current) {
          console.log('立即清理轮询定时器，ID:', pollingIntervalRef.current);
          clearInterval(pollingIntervalRef.current);
          pollingIntervalRef.current = null;
          setPollingInterval(null);
        }
        
        setLoading(false);
        setCurrentTaskId(null);
        antdMessage.error(`异步回测失败: ${status.error || '未知错误'}`);
      }
    } catch (error: any) {
      console.error('获取任务状态失败:', error);
      // 如果获取状态失败，继续轮询，但减少频率
    }
  }, []);

  // 处理回测结果的通用函数
  const processBacktestResult = useCallback((result: any) => {
    if (result.error) {
      antdMessage.error(`回测失败: ${result.error}`);
      return;
    }
    
    console.log('回测结果:', result);
    
    // 详细输出回测结果中的关键字段，用于调试
    console.log('回测结果关键字段:');
    console.log('- total_return:', result.total_return);
    console.log('- annual_return:', result.annual_return);
    console.log('- sharpe_ratio:', result.sharpe_ratio);
    console.log('- max_drawdown:', result.max_drawdown);
    console.log('- win_rate:', result.win_rate);
    console.log('- profit_factor:', result.profit_factor);
    console.log('- trades 数量:', result.trades?.length);
    console.log('- equity_curve 数量:', result.equity_curve?.length);
    console.log('- drawdowns 数量:', result.drawdowns?.length);
    
    // 确保trades数组存在
    if (!result.trades) {
      result.trades = [];
      console.warn('未找到交易记录，设置为空数组');
    }
    
    // 确保equity_curve数组存在
    if (!result.equity_curve) {
      result.equity_curve = [];
      console.warn('未找到权益曲线数据，设置为空数组');
    }
    
    // 确保drawdowns数组存在
    if (!result.drawdowns) {
      result.drawdowns = [];
      console.warn('未找到回撤数据，设置为空数组');
    }
    
    // 设置性能指标
    setPerformanceData({
      totalReturn: (result.total_return || 0) * 100,
      annualReturn: (result.annual_return || 0) * 100,
      sharpeRatio: result.sharpe_ratio || 0,
      maxDrawdown: (result.max_drawdown || 0) * 100,
      winRate: (result.win_rate || 0) * 100,
      profitFactor: result.profit_factor || 0,
      alpha: (result.alpha || 0) * 100,
      beta: result.beta || 0
    });
    
    // 打印处理后的性能指标
    console.log('处理后的性能指标:', {
      totalReturn: (result.total_return || 0) * 100,
      annualReturn: (result.annual_return || 0) * 100,
      sharpeRatio: result.sharpe_ratio || 0,
      maxDrawdown: (result.max_drawdown || 0) * 100,
      winRate: (result.win_rate || 0) * 100,
      profitFactor: result.profit_factor || 0
    });
    
    // 处理回测结果
    setBacktestResults(result);
    
    // 更新图表数据
    // 设置交易记录（即使为空也要处理）
    if (result.trades && result.trades.length > 0) {
      const trades = result.trades.map((trade: any, index: number) => {
        console.log('处理交易记录:', trade);
        return {
          key: index.toString(),
          date: normalizeDate(trade.date),
          symbol: selectedStock?.symbol || '',
          direction: trade.action === 'BUY' ? '买入' : '卖出',
          // 根据交易类型设置不同的价格字段
          entryPrice: trade.action === 'BUY' ? trade.price : undefined,
          exitPrice: trade.action === 'SELL' ? trade.price : undefined,
          shares: trade.shares,
          value: trade.value,
          profitLoss: trade.profit || 0,
          returnPct: (trade.profit_percent || 0) * 100,
          duration: trade.holding_days || 0,
          beforeCash: trade.before_cash,
          afterCash: trade.after_cash,
          beforeEquity: trade.before_equity,
          afterEquity: trade.after_equity,
          trigger_reason: trade.trigger_reason,
          available_capital: trade.available_capital,
          allocated_capital: trade.allocated_capital,
          position_size: trade.position_size,
          cumulative_position_ratio: trade.cumulative_position_ratio
        };
      });
      
      // 按交易时间倒序排序（最新的在前面）
      const sortedTrades = trades.sort((a: any, b: any) => {
        return new Date(b.date).getTime() - new Date(a.date).getTime();
      });
      
      setTradeRecords(sortedTrades);
      setTradesData(sortedTrades);
    } else {
      // 如果没有交易记录，设置为空数组
      setTradeRecords([]);
      setTradesData([]);
    }
    
    // 更新资产曲线数据
    if (result.equity_curve && result.equity_curve.length > 0) {
      console.log('处理权益曲线数据:', result.equity_curve[0]);
      
      // 权益曲线数据
      const equityData = result.equity_curve.map((item: any) => ({
        date: normalizeDate(item.date),
        equity: item.equity
      }));
      setEquityCurveData(equityData);
      setEquityData(equityData);
      
      // K线数据应该直接来自后端，而不是前端模拟
      // 取出K线数据并进行格式转换
      const kData = result.equity_curve.map((item: any) => {
        const dateStr = normalizeDate(item.date);
        
        // 使用后端返回的OHLC数据，如果没有则保持为0
        const open = Number(item.open) || 0;
        const close = Number(item.close) || 0;
        const low = Number(item.low) || 0;
        const high = Number(item.high) || 0;
        const volume = Number(item.volume) || 0;
        
        // 返回K线格式数据：[日期, 开盘价, 收盘价, 最低价, 最高价, 成交量]
        return [
          dateStr,
          open,
          close,
          low,
          high,
          volume
        ];
      });
      
      console.log('K线数据示例(前3条):', kData.slice(0, 3));
      setKlineData(kData);
    } else {
      // 如果没有权益曲线数据，设置为空数组
      setEquityCurveData([]);
      setEquityData([]);
      setKlineData([]);
    }
    
    // 更新回撤曲线
    if (result.drawdowns && result.drawdowns.length > 0) {
      const drawdownsData = result.drawdowns.map((item: any) => ({
        date: normalizeDate(item.date),
        drawdown: (item.drawdown || 0) * 100 // 转为百分比
      }));
      setDrawdownData(drawdownsData);
    } else {
      // 如果没有回撤数据，设置为空数组
      setDrawdownData([]);
    }
    
    // 标记有回测结果
    setHasResults(true);
    
    // 滚动到结果区域
    resultsRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [normalizeDate, selectedStock]);

  // 运行回测
  const handleRunBacktest = useCallback(async () => {
    if (!selectedStrategy || !selectedStock || !dateRange[0] || !dateRange[1]) {
      antdMessage.error('请选择策略、交易品种和回测周期');
      return;
    }

    setLoading(true);
    setBacktestResults(null);
    setHasResults(false); // 重置结果状态
    
    try {
      const startDate = dateRange[0].format('YYYY-MM-DD');
      const endDate = dateRange[1].format('YYYY-MM-DD');
      
      if (asyncMode) {
        // 异步模式
        console.log('使用异步模式提交回测任务');
        
        const taskResponse = await submitAsyncBacktest(
          selectedStrategy,
          selectedStock.symbol,
          startDate,
          endDate,
          initialCapital,
          {
            save_backtest: false,
            parameters: strategyParameters
          },
          commissionRate,
          slippage,
          'database',
          [],
          'normal' // 默认优先级
        );
        
        console.log('异步任务提交成功:', taskResponse);
        setCurrentTaskId(taskResponse.task_id);
        setTaskStatus('pending');
        setTaskProgress(0);
        
        // 开始轮询任务状态
        const interval = setInterval(() => {
          pollTaskStatus(taskResponse.task_id);
        }, 2000); // 每2秒轮询一次
        
        // 同时保存到ref和state
        pollingIntervalRef.current = interval;
        setPollingInterval(interval);
        
        message.info('回测任务已提交，正在后台执行...');
      } else {
        // 同步模式（原有逻辑）
        console.log('使用同步模式执行回测');
        
        const result = await backtestStrategy(
          selectedStrategy,
          selectedStock.symbol,
          startDate,
          endDate,
          initialCapital,
          {
            save_backtest: false,
            parameters: strategyParameters
          },
          commissionRate,
          slippage,
          'database',
          []
        );
        
        // 处理同步回测结果
        processBacktestResult(result);
        
        const showSuccessMessage = () => {
          message.success('回测完成');
        };
        showSuccessMessage();
        
        setLoading(false);
      }
    } catch (error: any) {
      console.error('回测执行失败:', error);
      antdMessage.error(`回测失败: ${error.message || '未知错误'}`);
      setLoading(false);
      setCurrentTaskId(null);
      clearPolling();
    }
  }, [
    selectedStrategy, 
    selectedStock, 
    dateRange, 
    initialCapital, 
    commissionRate, 
    slippage, 
    strategyParameters,
    asyncMode,
    processBacktestResult,
    pollTaskStatus,
    clearPolling
  ]);
  
  // 强制刷新回测（清除缓存并重新运行）
  const handleForceRefreshBacktest = useCallback(async () => {
    if (!selectedStrategy || !selectedStock || !dateRange[0] || !dateRange[1]) {
      antdMessage.error('请选择策略、交易品种和回测周期');
      return;
    }

    setLoading(true);
    setBacktestResults(null);
    setHasResults(false); // 重置结果状态
    
    try {
      const startDate = dateRange[0].format('YYYY-MM-DD');
      const endDate = dateRange[1].format('YYYY-MM-DD');
      
      // 使用强制刷新的backtestStrategy方法进行回测
      const result = await backtestStrategyForceRefresh(
        selectedStrategy, // 已经是number类型
        selectedStock.symbol,
        startDate,
        endDate,
        initialCapital,
        {
          save_backtest: false, // 暂时不自动保存，等用户手动保存
          parameters: strategyParameters // 添加策略参数
        }, // 参数对象
        commissionRate,
        slippage,
        'database', // 使用数据库作为数据源
        [] // 默认特征列表
      );
      
      if (result.error) {
        antdMessage.error(`强制刷新回测失败: ${result.error}`);
        return;
      }
      
      console.log('强制刷新回测结果:', result);
      
      // 详细输出回测结果中的关键字段，用于调试
      console.log('回测结果关键字段:');
      console.log('- total_return:', result.total_return);
      console.log('- annual_return:', result.annual_return);
      console.log('- sharpe_ratio:', result.sharpe_ratio);
      console.log('- max_drawdown:', result.max_drawdown);
      console.log('- win_rate:', result.win_rate);
      console.log('- profit_factor:', result.profit_factor);
      console.log('- trades 数量:', result.trades?.length);
      console.log('- equity_curve 数量:', result.equity_curve?.length);
      console.log('- drawdowns 数量:', result.drawdowns?.length);
      
      // 确保trades数组存在
      if (!result.trades) {
        result.trades = [];
        console.warn('未找到交易记录，设置为空数组');
      }
      
      // 确保equity_curve数组存在
      if (!result.equity_curve) {
        result.equity_curve = [];
        console.warn('未找到权益曲线数据，设置为空数组');
      }
      
      // 确保drawdowns数组存在
      if (!result.drawdowns) {
        result.drawdowns = [];
        console.warn('未找到回撤数据，设置为空数组');
      }
      
      // 设置性能指标
      setPerformanceData({
        totalReturn: (result.total_return || 0) * 100,
        annualReturn: (result.annual_return || 0) * 100,
        sharpeRatio: result.sharpe_ratio || 0,
        maxDrawdown: (result.max_drawdown || 0) * 100,
        winRate: (result.win_rate || 0) * 100,
        profitFactor: result.profit_factor || 0,
        alpha: (result.alpha || 0) * 100,
        beta: result.beta || 0
      });
      
      // 打印处理后的性能指标
      console.log('处理后的性能指标:', {
        totalReturn: (result.total_return || 0) * 100,
        annualReturn: (result.annual_return || 0) * 100,
        sharpeRatio: result.sharpe_ratio || 0,
        maxDrawdown: (result.max_drawdown || 0) * 100,
        winRate: (result.win_rate || 0) * 100,
        profitFactor: result.profit_factor || 0
      });
      
      // 处理回测结果
      setBacktestResults(result);
      
      // 更新图表数据
      // 设置交易记录（即使为空也要处理）
      if (result.trades && result.trades.length > 0) {
        const trades = result.trades.map((trade: any, index: number) => {
          console.log('处理交易记录:', trade);
          return {
            key: index.toString(),
            date: normalizeDate(trade.date),
            symbol: selectedStock.symbol,
            direction: trade.action === 'BUY' ? '买入' : '卖出',
            // 根据交易类型设置不同的价格字段
            entryPrice: trade.action === 'BUY' ? trade.price : undefined,
            exitPrice: trade.action === 'SELL' ? trade.price : undefined,
            shares: trade.shares,
            value: trade.value,
            profitLoss: trade.profit || 0,
            returnPct: (trade.profit_percent || 0) * 100,
            duration: trade.holding_days || 0,
            beforeCash: trade.before_cash,
            afterCash: trade.after_cash,
            beforeEquity: trade.before_equity,
            afterEquity: trade.after_equity,
            trigger_reason: trade.trigger_reason,
            available_capital: trade.available_capital,
            allocated_capital: trade.allocated_capital,
            position_size: trade.position_size,
            cumulative_position_ratio: trade.cumulative_position_ratio
          };
        });
        
        // 按交易时间倒序排序（最新的在前面）
        const sortedTrades = trades.sort((a: any, b: any) => {
          return new Date(b.date).getTime() - new Date(a.date).getTime();
        });
        
        setTradeRecords(sortedTrades);
        setTradesData(sortedTrades);
      } else {
        // 如果没有交易记录，设置为空数组
        setTradeRecords([]);
        setTradesData([]);
      }
      
      // 更新资产曲线数据
      if (result.equity_curve && result.equity_curve.length > 0) {
        console.log('处理权益曲线数据:', result.equity_curve[0]);
        
        // 权益曲线数据
        const equityData = result.equity_curve.map((item: any) => ({
          date: normalizeDate(item.date),
          equity: item.equity
        }));
        setEquityCurveData(equityData);
        setEquityData(equityData);
        
        // K线数据应该直接来自后端，而不是前端模拟
        // 取出K线数据并进行格式转换
        const kData = result.equity_curve.map((item: any) => {
          const dateStr = normalizeDate(item.date);
          
          // 使用后端返回的OHLC数据，如果没有则保持为0
          const open = Number(item.open) || 0;
          const close = Number(item.close) || 0;
          const low = Number(item.low) || 0;
          const high = Number(item.high) || 0;
          const volume = Number(item.volume) || 0;
          
          // 返回K线格式数据：[日期, 开盘价, 收盘价, 最低价, 最高价, 成交量]
          return [
            dateStr,
            open,
            close,
            low,
            high,
            volume
          ];
        });
        
        console.log('K线数据示例(前3条):', kData.slice(0, 3));
        setKlineData(kData);
      } else {
        // 如果没有权益曲线数据，设置为空数组
        setEquityCurveData([]);
        setEquityData([]);
        setKlineData([]);
      }
      
      // 更新回撤曲线
      if (result.drawdowns && result.drawdowns.length > 0) {
        const drawdownsData = result.drawdowns.map((item: any) => ({
          date: normalizeDate(item.date),
          drawdown: (item.drawdown || 0) * 100 // 转为百分比
        }));
        setDrawdownData(drawdownsData);
      } else {
        // 如果没有回撤数据，设置为空数组
        setDrawdownData([]);
      }
      
      // 标记有回测结果
      setHasResults(true);
      
      // 滚动到结果区域
      resultsRef.current?.scrollIntoView({ behavior: 'smooth' });
      
      // 使用函数组件包装，确保消息API调用在组件上下文中执行
      const showSuccessMessage = () => {
        message.success('强制刷新回测完成');
      };
      showSuccessMessage();
    } catch (error: any) {
      console.error('强制刷新回测执行失败:', error);
      antdMessage.error(`强制刷新回测失败: ${error.message || '未知错误'}`);
    } finally {
      setLoading(false);
    }
  }, [
    selectedStrategy, 
    selectedStock, 
    dateRange, 
    initialCapital, 
    commissionRate, 
    slippage, 
    normalizeDate, 
    setTradeRecords, 
    setTradesData, 
    setKlineData, 
    setEquityCurveData, 
    setEquityData, 
    setDrawdownData, 
    setHasResults, 
    setBacktestResults, 
    setPerformanceData, 
    setLoading
  ]);
  
  // K线图配置
  const getKlineOption = () => {
    const title = selectedStock ? `${selectedStock.name} (${selectedStock.symbol}) K线图与交易信号` : 'K线图与交易信号';
    
    // 交易信号标记数组
    let buySignals: any[] = [];
    let sellSignals: any[] = [];
    
    // 检查K线数据有效性
    if (!klineData || klineData.length === 0) {
      console.warn('K线数据为空，无法生成图表');
      return {
        title: {
          text: title,
          left: 'center'
        },
        grid: {
          left: '3%',
          right: '4%',
          bottom: '15%',
          top: '15%',
          containLabel: true
        },
        xAxis: {
          type: 'category',
          data: []
        },
        yAxis: {
          type: 'value',
          name: '资金',
          axisLabel: {
            formatter: '¥{value}'
          }
        }
      };
    }
    
    // 从交易记录中提取买入和卖出信号
    if (tradeRecords.length > 0 && klineData.length > 0) {
      console.log('准备标记交易信号，总交易记录：', tradeRecords.length);
      console.log('K线数据样本:', klineData.slice(0, 3));
      
      // 输出更详细的日期格式信息，用于调试
      if (klineData.length > 0) {
        const sampleDate = klineData[0][0];
        console.log('K线日期格式示例:', {
          original: sampleDate,
          type: typeof sampleDate,
          split: typeof sampleDate === 'string' ? sampleDate.split('T') : null
        });
      }
      
      if (tradeRecords.length > 0) {
        const sampleDate = tradeRecords[0].date;
        console.log('交易记录日期格式示例:', {
          original: sampleDate,
          type: typeof sampleDate,
          split: typeof sampleDate === 'string' ? sampleDate.split('T') : null,
          split2: typeof sampleDate === 'string' ? sampleDate.split(' ') : null
        });
      }
      
      // 建立日期与索引的映射
      const dateIndexMap = new Map<string, number>();
      const dateValueMap = new Map<string, number[]>();
      
      // 处理K线数据的日期，创建映射
      klineData.forEach((item, index) => {
        const dateStr = normalizeDate(item[0]);
        dateIndexMap.set(dateStr, index);
        
        // 记录日期对应的OHLC数据
        dateValueMap.set(dateStr, [
          Number(item[1]), // 开盘价
          Number(item[2]), // 收盘价
          Number(item[3]), // 最低价
          Number(item[4])  // 最高价
        ]);
      });
      
      console.log('日期索引映射创建完成，共计:', dateIndexMap.size);
      console.log('日期映射示例:', Array.from(dateIndexMap.entries()).slice(0, 3));
      
      // 过滤并处理买入信号
      const buyRecords = tradeRecords.filter(record => record.direction === '买入');
      console.log('买入记录:', buyRecords.length);
      
      // 构建买入标记
      buySignals = buyRecords
        .map(record => {
          const dateStr = normalizeDate(record.date);
          const index = dateIndexMap.get(dateStr);
          const price = record.entryPrice || 0;
          
          if (index === undefined || price <= 0) {
            console.warn(`未找到买入日期 ${dateStr} 对应的K线索引或价格无效`);
            return null;
          }
          
          console.log(`买入日期匹配成功: ${dateStr} -> 索引 ${index}, 价格 ${price}`);
          
          return {
            name: '买入',
            value: [index, price],
            xAxis: index,
            yAxis: price,
            itemStyle: {
              color: '#f64034'
            }
          };
        })
        .filter(item => item !== null);
      
      // 过滤并处理卖出信号
      const sellRecords = tradeRecords.filter(record => record.direction === '卖出');
      console.log('卖出记录:', sellRecords.length);
      
      // 构建卖出标记
      sellSignals = sellRecords
        .map(record => {
          const dateStr = normalizeDate(record.date);
          const index = dateIndexMap.get(dateStr);
          const price = record.exitPrice || 0;
          const profit = record.profitLoss || 0;
          const profitPercent = record.returnPct || 0;
          
          if (index === undefined || price <= 0) {
            console.warn(`未找到卖出日期 ${dateStr} 对应的K线索引或价格无效`);
            return null;
          }
          
          console.log(`卖出日期匹配成功: ${dateStr} -> 索引 ${index}, 价格 ${price}, 盈亏 ${profit}`);
          
          // 根据盈亏决定颜色
          const color = profit >= 0 ? '#f64034' : '#00b46a';
          
          return {
            name: '卖出',
            value: [index, price],
            xAxis: index,
            yAxis: price,
            itemStyle: {
              color: color
            }
          };
        })
        .filter(item => item !== null);
      
      console.log(`成功生成买入信号: ${buySignals.length}/${buyRecords.length}`);
      console.log(`成功生成卖出信号: ${sellSignals.length}/${sellRecords.length}`);
    }
    
    // 构建x轴数据，直接映射K线日期
    const xAxisData = klineData.map(item => item[0]);
    
    // 构建交易标记系列
    let markPointData: any[] = [];
    
    // 修改买入和卖出标记的位置，仿照富途交易软件风格
    markPointData = [
      // 价格位置的小圆点标记
      ...buySignals.map(signal => {
        const xIndex = signal.value[0];
        return {
          name: '买入点',
          coord: [signal.value[0], signal.value[1]],
          value: signal.value[1],
          itemStyle: {
            color: '#f64034',
            borderColor: '#ffffff',
            borderWidth: 1,
            shadowBlur: 2,
            shadowColor: 'rgba(0,0,0,0.3)'
          },
          symbol: 'circle',
          symbolSize: 8,
          label: {
            show: false
          }
        };
      }),
      ...sellSignals.map(signal => {
        return {
          name: '卖出点',
          coord: [signal.value[0], signal.value[1]],
          value: signal.value[1],
          itemStyle: {
            color: '#00b46a',
            borderColor: '#ffffff',
            borderWidth: 1,
            shadowBlur: 2,
            shadowColor: 'rgba(0,0,0,0.3)'
          },
          symbol: 'circle',
          symbolSize: 8,
          label: {
            show: false
          }
        };
      }),
      
      // K线顶部的买入标签
      ...buySignals.map(signal => {
        const xIndex = signal.value[0];
        // 计算当前K线数据的最高价
        const highPrice = klineData[xIndex][4]; // K线的第4个元素是最高价
        // 设置标签位置在最高价上方
        const labelY = highPrice * 1.10; // 最高价上方10%的位置
        
        return {
          name: '买入标签',
          coord: [signal.value[0], labelY],
          itemStyle: {
            color: '#f64034'
          },
          symbol: 'pin',
          symbolSize: 25,
          symbolOffset: [0, '50%'],
          label: {
            show: true,
            formatter: 'B',
            fontSize: 12,
            fontWeight: 'bold',
            color: '#ffffff',
            position: 'inside'
          }
        };
      }),
      
      // K线顶部的卖出标签
      ...sellSignals.map(signal => {
        const xIndex = signal.value[0];
        // 为避免与买入标签重叠，检查同一天是否有买入信号
        const hasBuyOnSameDay = buySignals.some(buySignal => {
          const buyIndex = buySignal.value[0];
          const buyDate = normalizeDate(klineData[buyIndex][0]);
          const sellDate = normalizeDate(klineData[xIndex][0]);
          return buyDate === sellDate;
        });
        
        // 计算当前K线数据的最高价
        const highPrice = klineData[xIndex][4]; // K线的第4个元素是最高价
        // 设置标签位置，如果同日有买入信号，则需稍微错开
        const labelY = hasBuyOnSameDay ? highPrice * 1.20 : highPrice * 1.10;
        
        return {
          name: '卖出标签',
          coord: [signal.value[0], labelY],
          itemStyle: {
            color: '#00b46a'
          },
          symbol: 'pin',
          symbolSize: 25,
          symbolOffset: [0, '50%'],
          label: {
            show: true,
            formatter: 'S',
            fontSize: 12,
            fontWeight: 'bold',
            color: '#ffffff',
            position: 'inside'
          }
        };
      })
    ];
    
    // 额外的价格标签数据，用于显示价格和盈亏信息
    const priceLabels = [
      ...buySignals.map(signal => ({
        name: '买入价格',
        coord: [signal.value[0], signal.value[1] * 1.03], // 稍微上移
        symbol: 'none',
        label: {
          show: true,
          formatter: `¥${signal.value[1].toFixed(2)}`,
          fontSize: 12,
          color: '#f64034',
          backgroundColor: 'rgba(255,255,255,0.7)',
          padding: [2, 4],
          borderRadius: 2,
          position: 'top',
          distance: 8
        }
      })),
      ...sellSignals.map(signal => {
        // 获取该信号对应的交易记录
        const xIndex = signal.value[0];
        const klineDate = klineData[xIndex][0];
        const sellRecord = tradeRecords.find(record => 
          record.direction === '卖出' && 
          normalizeDate(record.date) === normalizeDate(klineDate)
        );
        
        const profit = sellRecord ? (sellRecord.profitLoss || 0) : 0;
        const profitPercent = sellRecord ? (sellRecord.returnPct || 0) : 0;
        const profitText = profit >= 0 ? `+${profit.toFixed(2)}` : `${profit.toFixed(2)}`;
        const percentText = profitPercent >= 0 ? `+${profitPercent.toFixed(2)}%` : `${profitPercent.toFixed(2)}%`;
        
        return {
          name: '卖出价格',
          coord: [signal.value[0], signal.value[1] * 0.97], // 稍微下移
          symbol: 'none',
          label: {
            show: true,
            formatter: sellRecord ? 
              `¥${signal.value[1].toFixed(2)}\n${profitText}(${percentText})` : 
              `¥${signal.value[1].toFixed(2)}`,
            fontSize: 12,
            color: '#00b46a',
            backgroundColor: 'rgba(255,255,255,0.7)',
            padding: [2, 4],
            borderRadius: 2,
            position: 'bottom',
            distance: 8
          }
        };
      })
    ];

    return {
      title: {
        text: title,
        left: 'center'
      },
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'cross',
          label: {
            backgroundColor: '#555'
          }
        },
        backgroundColor: 'rgba(255, 255, 255, 0.9)',
        borderWidth: 1,
        borderColor: '#ccc',
        padding: 10,
        textStyle: {
          color: '#333'
        },
        formatter: function(params: any) {
          // 自定义提示框内容
          let result = '';
          // 判断是否为数组
          if (Array.isArray(params)) {
            // 获取第一个项的日期作为标题
            const date = params[0].axisValue;
            result = `<div style="font-weight:bold;margin-bottom:5px;color:#333;font-size:14px;">${date}</div>`;
            
            // 遍历所有系列数据
            params.forEach((item: any) => {
              // 处理K线数据
              if (item.seriesName === 'K线') {
                if (item.value && item.value.length >= 4) {
                  const open = Number(item.value[1]) || 0;
                  const close = Number(item.value[2]) || 0;
                  const low = Number(item.value[3]) || 0;
                  const high = Number(item.value[4]) || 0;
                  const color = close >= open ? '#f64034' : '#00b46a';
                  result += `<div style="color:${color};line-height:1.5;margin-bottom:8px;font-weight:bold;">
                    开盘：<span style="float:right;color:${color};">${open.toFixed(2)}</span><br/>
                    收盘：<span style="float:right;color:${color};">${close.toFixed(2)}</span><br/>
                    最低：<span style="float:right;color:${color};">${low.toFixed(2)}</span><br/>
                    最高：<span style="float:right;color:${color};">${high.toFixed(2)}</span><br/>
                  </div>`;
                }
              } 
              // 处理MA线
              else if (item.seriesName && item.seriesName.startsWith('MA') && item.value !== '-') {
                const colors: {[key: string]: string} = {
                  'MA5': '#f7b500',
                  'MA10': '#2196F3',
                  'MA20': '#8067dc', 
                  'MA30': '#00b46a',
                  'MA60': '#7cb305',
                  'MA120': '#eb2f96'
                };
                const color = colors[item.seriesName] || item.color;
                try {
                  const value = typeof item.value === 'number' ? 
                    parseFloat(item.value.toString()).toFixed(3) : 
                    parseFloat(item.value || "0").toFixed(3);
                  result += `<div style="color:${color};font-weight:bold;display:inline-block;margin-right:15px;">${item.seriesName}：${value}</div>`;
                } catch (e) {
                  console.warn('格式化MA值出错:', e);
                  result += `<div style="color:${color};font-weight:bold;display:inline-block;margin-right:15px;">${item.seriesName}：0</div>`;
                }
              }
            });
            
            // 处理买卖信号
            const dateStr = normalizeDate(date);
            
            // 查找买入信号
            const buyRecord = tradeRecords.find(record => 
              record.direction === '买入' && 
              normalizeDate(record.date) === dateStr
            );
            
            // 查找卖出信号
            const sellRecord = tradeRecords.find(record => 
              record.direction === '卖出' && 
              normalizeDate(record.date) === dateStr
            );
            
            // 显示买卖信号
            if (buyRecord || sellRecord) {
              result += `<div style="margin-top:5px;border-top:1px dashed #ddd;padding-top:5px;"></div>`;
            }
            
            // 显示买入信号
            if (buyRecord) {
              const price = buyRecord.entryPrice || 0;
              const reason = buyRecord.trigger_reason || '未记录原因';
              result += `<div style="color:#f64034;font-weight:bold;margin-top:3px;">
                买入(B)：¥${price.toFixed(2)}<br/>
                原因：${reason}
              </div>`;
            }
            
            // 显示卖出信号
            if (sellRecord) {
              const price = sellRecord.exitPrice || 0;
              const profit = sellRecord.profitLoss || 0;
              const profitPercent = sellRecord.returnPct || 0;
              const reason = sellRecord.trigger_reason || '未记录原因';
              const profitText = profit >= 0 ? `+${profit.toFixed(2)}` : `${profit.toFixed(2)}`;
              const percentText = profitPercent >= 0 ? `+${profitPercent.toFixed(2)}%` : `${profitPercent.toFixed(2)}%`;
              
              result += `<div style="color:#00b46a;font-weight:bold;margin-top:3px;">
                卖出(S)：¥${price.toFixed(2)}<br/>
                盈亏：${profitText} (${percentText})<br/>
                原因：${reason}
              </div>`;
            }
          }
          return result;
        }
      },
      legend: {
        data: ['K线', 'MA5', 'MA10', 'MA20', 'MA30'],
        bottom: 10,
        selected: {
          'MA10': false,
          'MA30': false
        },
        textStyle: {
          color: '#333'
        },
        itemGap: 20
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '15%',
        top: '15%',
        containLabel: true
      },
      xAxis: {
        type: 'category',
        data: xAxisData,
        scale: true,
        boundaryGap: false,
        axisLine: { onZero: false },
        splitLine: { show: false },
        splitNumber: 20,
        min: 'dataMin',
        max: 'dataMax'
      },
      yAxis: {
        type: 'value',
        name: '资金',
        axisLabel: {
          formatter: '¥{value}'
        },
        min: function(value: any) {
          // 设置y轴最小值为0或初始资金的80%，取较小者
          // 这确保初始资金线不会太靠近坐标轴底部
          return Math.min(0, initialCapital * 0.8);
        },
        scale: true,  // 启用比例缩放，使图表更合理地显示
        splitArea: {
          show: true  // 显示分隔区域，增强可读性
        }
      },
      dataZoom: [
        {
          type: 'inside',
          start: 0,
          end: 100
        },
        {
          show: true,
          type: 'slider',
          bottom: 60,
          start: 0,
          end: 100
        }
      ],
      series: [
        {
          name: 'K线',
          type: 'candlestick',
          data: klineData.map(item => [
            Number(item[1]), // 开盘价
            Number(item[2]), // 收盘价
            Number(item[3]), // 最低价
            Number(item[4])  // 最高价
          ]),
          itemStyle: {
            color: '#f64034',   // 阳线红色
            color0: '#00b46a',  // 阴线绿色
            borderColor: '#f64034',
            borderColor0: '#00b46a'
          },
          markPoint: {
            data: markPointData,
            animation: false,
            z: 10
          }
        },
        {
          name: '价格标签',
          type: 'scatter',
          data: [],
          markPoint: {
            symbol: 'none',
            data: priceLabels,
            animation: false,
            z: 9
          }
        },
        {
          name: 'MA5',
          type: 'line',
          data: calculateMA(5, klineData.map(item => [
            Number(item[1]), // 开盘价
            Number(item[2]), // 收盘价
            Number(item[3]), // 最低价
            Number(item[4])  // 最高价
          ])),
          smooth: true,
          lineStyle: {
            width: 1,
            color: '#f7b500'  // 参考富途的颜色
          }
        },
        {
          name: 'MA10',
          type: 'line',
          data: calculateMA(10, klineData.map(item => [
            Number(item[1]), // 开盘价
            Number(item[2]), // 收盘价
            Number(item[3]), // 最低价
            Number(item[4])  // 最高价
          ])),
          smooth: true,
          lineStyle: {
            width: 1,
            color: '#2196F3'  // 参考富途的颜色
          }
        },
        {
          name: 'MA20',
          type: 'line',
          data: calculateMA(20, klineData.map(item => [
            Number(item[1]), // 开盘价
            Number(item[2]), // 收盘价
            Number(item[3]), // 最低价
            Number(item[4])  // 最高价
          ])),
          smooth: true,
          lineStyle: {
            width: 1,
            color: '#8067dc'  // 参考富途的颜色
          }
        },
        {
          name: 'MA30',
          type: 'line',
          data: calculateMA(30, klineData.map(item => [
            Number(item[1]), // 开盘价
            Number(item[2]), // 收盘价
            Number(item[3]), // 最低价
            Number(item[4])  // 最高价
          ])),
          smooth: true,
          lineStyle: {
            width: 1,
            color: '#00b46a'  // 参考富途的颜色
          }
        }
      ]
    };
  };

  // 计算移动平均线数据
  function calculateMA(dayCount: number, data: any[]) {
    // 检查数据有效性
    if (!data || !Array.isArray(data) || data.length === 0) {
      console.warn(`计算MA${dayCount}失败: 数据无效`);
      return [];
    }
    
    console.log(`MA${dayCount}计算 - 输入数据示例:`, data.length > 0 ? data.slice(0, 3) : '无数据');
    
    // 这里data是一个数组，其中每个元素是[open, close, low, high]格式的K线数据
    // 而calculateMA函数的输入应该是K线数据，我们需要从中提取出收盘价
    const result = [];
    for (let i = 0; i < data.length; i++) {
      if (i < dayCount - 1) {
        result.push('-');
        continue;
      }
      let sum = 0;
      let validCount = 0;
      for (let j = 0; j < dayCount; j++) {
        const kData = data[i - j];
        // 注意：ECharts K线图的数据格式是[open, close, low, high]
        // 所以收盘价是第2个元素(索引1)
        if (kData && kData.length >= 4) {
          const closePrice = Number(kData[1]);
          if (!isNaN(closePrice) && closePrice > 0) {
            sum += closePrice;
            validCount++;
          }
        }
      }
      
      // 只有当有效数据点数量不为0时，才计算平均值
      if (validCount > 0) {
        result.push((sum / validCount).toFixed(2));
      } else {
        result.push('-');
      }
    }
    
    // 输出一些调试信息
    if (result.length > 0) {
      console.log(`MA${dayCount}计算结果示例:`, result.slice(0, 5));
    }
    
    return result;
  }
  
  const columns: ColumnsType<TradeRecord> = [
    {
      title: '日期',
      dataIndex: 'date',
      key: 'date',
      sorter: (a, b) => {
        // 转换为日期对象进行比较
        const dateA = new Date(a.date);
        const dateB = new Date(b.date);
        return dateA.getTime() - dateB.getTime();
      }
    },
    {
      title: '方向',
      dataIndex: 'direction',
      key: 'direction',
      filters: [
        { text: '买入', value: '买入' },
        { text: '卖出', value: '卖出' },
      ],
      onFilter: (value, record) => record.direction === value,
      render: (text) => (
        <Tag color={text === '买入' ? 'red' : 'green'}>
          {text}
        </Tag>
      )
    },
    {
      title: '触发原因',
      dataIndex: 'trigger_reason',
      key: 'trigger_reason',
      width: 120, // 缩小宽度
      ellipsis: true, // 超出部分显示省略号
      render: (text) => (
        <Tooltip title={text || '未记录'} placement="topLeft">
          <span style={{ maxWidth: 100, display: 'inline-block', overflow: 'hidden', textOverflow: 'ellipsis', verticalAlign: 'middle', whiteSpace: 'nowrap' }}>{text || '未记录'}</span>
        </Tooltip>
      )
    },
    {
      title: '期初资金',
      dataIndex: 'beforeCash',
      key: 'beforeCash',
      sorter: (a, b) => a.beforeCash - b.beforeCash,
      render: (text) => {
        const value = parseFloat(text) || 0;
        return value.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
      }
    },
    {
      title: '期末资金',
      dataIndex: 'afterCash',
      key: 'afterCash',
      sorter: (a, b) => a.afterCash - b.afterCash,
      render: (text) => {
        const value = parseFloat(text) || 0;
        return value.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
      }
    },
    {
      title: '入场价',
      dataIndex: 'entryPrice',
      key: 'entryPrice',
      sorter: (a, b) => {
        const priceA = a.entryPrice || 0;
        const priceB = b.entryPrice || 0;
        return priceA - priceB;
      },
      render: (text) => {
        const value = parseFloat(text);
        return isNaN(value) ? '-' : value.toFixed(2);
      }
    },
    {
      title: '出场价',
      dataIndex: 'exitPrice',
      key: 'exitPrice',
      sorter: (a, b) => {
        const priceA = a.exitPrice || 0;
        const priceB = b.exitPrice || 0;
        return priceA - priceB;
      },
      render: (text) => {
        const value = parseFloat(text);
        return isNaN(value) ? '-' : value.toFixed(2);
      }
    },
    {
      title: '数量(股)',
      dataIndex: 'shares',
      key: 'shares',
      sorter: (a, b) => a.shares - b.shares,
      render: (text) => {
        // 确保数量为整数
        const value = parseInt(text) || 0;
        return value.toLocaleString();
      }
    },
    {
      title: '金额(元)',
      dataIndex: 'value',
      key: 'value',
      sorter: (a, b) => a.value - b.value,
      render: (text) => {
        // 确保金额为数字并格式化显示
        const value = parseFloat(text) || 0;
        return value.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
      }
    },
    {
      title: '盈亏',
      dataIndex: 'profitLoss',
      key: 'profitLoss',
      sorter: (a, b) => a.profitLoss - b.profitLoss,
      render: (text) => {
        // 确保数值为有效数字
        const value = parseFloat(text);
        if (isNaN(value)) {
          return <span>0.00</span>;
        }
        return value >= 0 ? 
          <span style={{ color: '#f5222d' }}>+{value.toFixed(2)}</span> : 
          <span style={{ color: '#52c41a' }}>{value.toFixed(2)}</span>;
      }
    },
    {
      title: '收益率(%)',
      dataIndex: 'returnPct',
      key: 'returnPct',
      sorter: (a, b) => a.returnPct - b.returnPct,
      render: (text) => {
        // 确保数值为有效数字
        const value = parseFloat(text);
        if (isNaN(value)) {
          return <span>0.00%</span>;
        }
        return value >= 0 ? 
          <span style={{ color: '#f5222d' }}>+{value.toFixed(2)}%</span> : 
          <span style={{ color: '#52c41a' }}>{value.toFixed(2)}%</span>;
      }
    },
    {
      title: '持仓天数',
      dataIndex: 'duration',
      key: 'duration',
      sorter: (a, b) => a.duration - b.duration,
    },
    {
      title: '仓位比例',
      dataIndex: 'position_size',
      key: 'position_size',
      sorter: (a, b) => (a.position_size || 0) - (b.position_size || 0),
      render: (text) => {
        const value = parseFloat(text);
        if (isNaN(value) || value === 0) {
          return <span>0.00%</span>;
        }
        return <span>{(value * 100).toFixed(2)}%</span>;
      }
    },
    {
      title: '累计仓位',
      dataIndex: 'cumulative_position_ratio',
      key: 'cumulative_position_ratio',
      sorter: (a, b) => (a.cumulative_position_ratio || 0) - (b.cumulative_position_ratio || 0),
      render: (text) => {
        const value = parseFloat(text);
        if (isNaN(value) || value === 0) {
          return <span>0.00%</span>;
        }
        return <span>{(value * 100).toFixed(2)}%</span>;
      }
    },
  ];
  
  // 权益曲线图表配置
  const getEquityCurveOption = () => {
    console.log('生成权益曲线图表, 数据长度:', equityCurveData.length);
    
    // 检查数据，确保不为空
    if (!equityCurveData || equityCurveData.length === 0) {
      return {
        title: {
          text: '策略收益曲线 (无数据)',
          left: 'center'
        },
        grid: {
          left: '3%',
          right: '4%',
          bottom: '15%',
          top: '15%',
          containLabel: true
        },
        xAxis: {
          type: 'category',
          data: []
        },
        yAxis: {
          type: 'value',
          name: '资金',
          axisLabel: {
            formatter: '¥{value}'
          }
        }
      };
    }
    
    // 对数据进行检查，确保所有数据点都有效
    const validData = equityCurveData.filter(item => 
      item && item.date && item.equity !== undefined && !isNaN(Number(item.equity))
    );
    
    if (validData.length === 0) {
      console.error('权益曲线数据无效:', equityCurveData.slice(0, 3));
      return {
        title: {
          text: '策略收益曲线 (数据无效)',
          left: 'center'
        },
        grid: {
          left: '3%',
          right: '4%',
          bottom: '15%',
          top: '15%',
          containLabel: true
        },
        xAxis: {
          type: 'category',
          data: []
        },
        yAxis: {
          type: 'value',
          name: '资金',
          axisLabel: {
            formatter: '¥{value}'
          }
        }
      };
    }
    
    // 数据检查通过，使用有效数据构建图表
    console.log('有效数据点数量:', validData.length);
    console.log('权益曲线数据范围:', 
      validData.length > 0 ? 
      `${validData[0].date}(${validData[0].equity}) ~ ${validData[validData.length-1].date}(${validData[validData.length-1].equity})` : 
      '无数据');
    
    // 添加买卖点标记
    let buyPoints: any[] = [];
    let sellPoints: any[] = [];
    
    // 建立日期与索引的映射，用于定位买卖点
    const dateIndexMap = new Map<string, number>();
    
    // 处理权益曲线数据的日期，创建映射
    validData.forEach((item, index) => {
      const dateStr = normalizeDate(item.date);
      dateIndexMap.set(dateStr, index);
    });
    
    // 从交易记录中提取买入和卖出点
    if (tradeRecords.length > 0) {
      console.log('准备在权益曲线上标记交易点，总交易记录：', tradeRecords.length);
      
      // 遍历所有交易记录
      tradeRecords.forEach(record => {
        const dateStr = normalizeDate(record.date);
        const index = dateIndexMap.get(dateStr);
        
        if (index !== undefined) {
          // 创建交易点标记
          const point = {
            name: record.direction === '买入' ? '买入点' : '卖出点',
            value: validData[index].equity,
            xAxis: index,
            yAxis: validData[index].equity,
            itemStyle: {
              color: record.direction === '买入' ? '#f64034' : '#00b46a'
            }
          };
          
          if (record.direction === '买入') {
            buyPoints.push(point);
          } else {
            sellPoints.push(point);
          }
        }
      });
    }
    
    // 计算最大回测区间
    let maxDrawdownStartIndex = -1;
    let maxDrawdownEndIndex = -1;
    let maxDrawdownValue = 0;
    let maxDrawdownStartDate = '';
    let maxDrawdownEndDate = '';
    let maxDrawdownPeak = 0;
    let maxDrawdownBottom = 0;
    
    if (validData.length > 0 && performanceData.maxDrawdown > 0) {
      // 查找最大回测对应的区间
      let maxValue = validData[0].equity;
      let currentDrawdown = 0;
      let tempStartIndex = 0;
      
      for (let i = 1; i < validData.length; i++) {
        // 如果当前值创新高，更新最大值和起始点
        if (validData[i].equity > maxValue) {
          maxValue = validData[i].equity;
          tempStartIndex = i;
        } 
        // 计算当前回测
        else {
          currentDrawdown = (maxValue - validData[i].equity) / maxValue * 100;
          
          // 如果找到更大的回测，更新记录
          if (currentDrawdown > maxDrawdownValue) {
            maxDrawdownValue = currentDrawdown;
            maxDrawdownStartIndex = tempStartIndex;
            maxDrawdownEndIndex = i;
            maxDrawdownStartDate = validData[tempStartIndex].date;
            maxDrawdownEndDate = validData[i].date;
            maxDrawdownPeak = maxValue;
            maxDrawdownBottom = validData[i].equity;
          }
        }
      }
      
      console.log(`最大回测区间索引: ${maxDrawdownStartIndex} - ${maxDrawdownEndIndex}`);
      console.log(`最大回测: ${maxDrawdownValue.toFixed(2)}%, 从 ${maxDrawdownStartDate} 到 ${maxDrawdownEndDate}`);
    }
    
    return {
      title: {
        text: '策略收益曲线',
        left: 'center',
        textStyle: {
          fontSize: 16,
          fontWeight: 'bold'
        }
      },
      tooltip: {
        trigger: 'axis',
        formatter: function(params: any) {
          // 处理数组类型的参数
          if (Array.isArray(params) && params.length > 0) {
            const date = params[0].axisValue;
            const value = params[0].data;
            
            // 检查是否为markArea类型，显示最大回测信息
            for (let i = 0; i < params.length; i++) {
              if (params[i].componentType === 'markArea') {
                return `最大回撤: ${maxDrawdownValue.toFixed(2)}%<br/>
                        开始日期: ${maxDrawdownStartDate}<br/>
                        最高点: ¥${maxDrawdownPeak.toLocaleString('zh-CN', {minimumFractionDigits: 2})}<br/>
                        结束日期: ${maxDrawdownEndDate}<br/>
                        最低点: ¥${maxDrawdownBottom.toLocaleString('zh-CN', {minimumFractionDigits: 2})}`;
              }
            }
            
            // 查找是否有额外的买卖点信息
            let extraInfo = '';
            for (let i = 0; i < params.length; i++) {
              const param = params[i];
              if (param.seriesName === '买入点' || param.seriesName === '卖出点') {
                // 查找对应的交易记录
                const tradeDateStr = normalizeDate(date);
                const tradeRecord = tradeRecords.find(record => 
                  normalizeDate(record.date) === tradeDateStr && 
                  ((param.seriesName === '买入点' && record.direction === '买入') || 
                   (param.seriesName === '卖出点' && record.direction === '卖出'))
                );
                
                // 如果找到交易记录，添加触发原因
                if (tradeRecord) {
                  const reason = tradeRecord.trigger_reason || '未记录原因';
                  extraInfo = `<br/><span style="color:${param.color}">● ${param.seriesName}</span>`;
                  extraInfo += `<br/><span style="color:#555; font-size:12px">原因: ${reason}</span>`;
                } else {
                  extraInfo = `<br/><span style="color:${param.color}">● ${param.seriesName}</span>`;
                }
                break;
              }
            }
            
            return `${date}<br/>策略收益: ¥${parseFloat(value).toLocaleString('zh-CN', {minimumFractionDigits: 2, maximumFractionDigits: 2})}${extraInfo}`;
          }
          
          // 单个值的处理
          const value = params.value;
          return `${params.name}: ¥${parseFloat(value).toLocaleString('zh-CN', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
        },
        axisPointer: {
          type: 'cross',
          label: {
            backgroundColor: '#555'
          }
        }
      },
      legend: {
        data: ['策略收益', '初始资金'],
        bottom: 10,
        itemWidth: 25,
        itemHeight: 14,
        itemGap: 30,
        textStyle: {
          fontSize: 14
        },
        icon: 'roundRect',
        selectedMode: false  // 禁止图例切换显示/隐藏
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '15%',
        top: '15%',
        containLabel: true
      },
      xAxis: {
        type: 'category',
        data: validData.map(item => item.date)
      },
      yAxis: {
        type: 'value',
        name: '资金',
        axisLabel: {
          formatter: '¥{value}'
        }
      },
      dataZoom: [
        {
          type: 'inside',
          start: 0,
          end: 100
        },
        {
          show: true,
          type: 'slider',
          bottom: 60,
          start: 0,
          end: 100
        }
      ],
      series: [
        {
          name: '策略收益',
          type: 'line',
          data: validData.map(item => item.equity),
          smooth: true,
          showSymbol: false,
          lineStyle: {
            width: 2,
            color: '#3b7ddd'  // 柔和蓝色
          },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: 'rgba(59, 125, 221, 0.25)' },  // 顶部淡蓝色
              { offset: 1, color: 'rgba(59, 125, 221, 0.03)' }  // 底部更淡
            ]),
            opacity: 1
          },
          markPoint: {
            data: [
              ...buyPoints.map(point => ({
                name: '买入点',
                coord: [point.xAxis, point.yAxis],
                value: point.value,
                itemStyle: {
                  color: '#f64034'
                },
                symbol: 'pin',
                symbolSize: 24,
                label: {
                  formatter: 'B',
                  color: '#fff',
                  position: 'inside'
                }
              })),
              ...sellPoints.map(point => ({
                name: '卖出点',
                coord: [point.xAxis, point.yAxis],
                value: point.value,
                itemStyle: {
                  color: '#00b46a'
                },
                symbol: 'pin',
                symbolSize: 24,
                label: {
                  formatter: 'S',
                  color: '#fff',
                  position: 'inside'
                }
              }))
            ],
            symbolSize: 24
          },
          // 添加最大回测区间标记
          markArea: {
            itemStyle: {
              color: 'rgba(255, 173, 177, 0.2)',  // 淡红色半透明
              borderColor: '#f5222d',
              borderWidth: 1
            },
            label: {
              show: true,
              position: 'top',
              formatter: `最大回撤: ${maxDrawdownValue.toFixed(2)}%`,
              color: '#f5222d',
              fontSize: 12,
              fontWeight: 'bold'
            },
            data: [
              maxDrawdownStartIndex >= 0 && maxDrawdownEndIndex >= 0 ? 
              [
                {
                  name: '最大回撤开始',
                  xAxis: maxDrawdownStartIndex,
                  itemStyle: { color: 'rgba(255, 173, 177, 0.2)' }
                },
                {
                  name: '最大回撤结束',
                  xAxis: maxDrawdownEndIndex,
                  itemStyle: { color: 'rgba(255, 173, 177, 0.2)' }
                }
              ] : []
            ]
          }
        },
        {
          name: '初始资金',
          type: 'line',
          data: validData.map(() => initialCapital), // 保证长度一致
          symbol: 'none',
          lineStyle: {
            width: 2,
            type: 'solid',
            color: '#888'  // 柔和灰色
          },
          markLine: {
            silent: true,
            lineStyle: {
              color: '#888',
              width: 2,
              type: 'solid'
            },
            data: [{
              yAxis: initialCapital,
              label: {
                formatter: '初始资金: ¥' + initialCapital.toLocaleString(),
                position: 'start',
                distance: [0, -20],
                color: '#888',
                fontSize: 12,
                fontWeight: 'bold',
                backgroundColor: 'rgba(255,255,255,0.9)',
                padding: [4, 8],
                borderColor: '#888',
                borderWidth: 1,
                borderRadius: 4
              }
            }]
          },
          tooltip: {
            formatter: function(params: any) {
              return `初始资金: ¥${initialCapital.toLocaleString('zh-CN', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
            }
          }
        }
      ]
    };
  };
  
  // 回撤图表配置
  const getDrawdownOption = () => {
    // 检查数据，确保不为空
    if (!drawdownData || drawdownData.length === 0) {
      return {
        title: {
          text: '策略回撤 (无数据)',
          left: 'center'
        },
        grid: {
          left: '3%',
          right: '4%',
          bottom: '15%',
          top: '15%',
          containLabel: true
        },
        xAxis: {
          type: 'category',
          data: []
        },
        yAxis: {
          type: 'value',
          name: '回撤(%)',
          axisLabel: {
            formatter: '{value}%'
          }
        }
      };
    }
    
    return {
      title: {
        text: '策略回撤',
        left: 'center'
      },
      tooltip: {
        trigger: 'axis',
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '15%',
        top: '15%',
        containLabel: true
      },
      xAxis: {
        type: 'category',
        data: drawdownData.map(item => item.date)
      },
      yAxis: {
        type: 'value',
        name: '回撤(%)',
        axisLabel: {
          formatter: '{value}%'
        },
        inverse: true
      },
      series: [
        {
          name: '策略回撤',
          type: 'line',
          data: drawdownData.map(item => item.drawdown),
          areaStyle: {
            color: '#f5222d',
            opacity: 0.2
          },
          lineStyle: {
            color: '#f5222d'
          },
          itemStyle: {
            color: '#f5222d'
          }
        }
      ]
    };
  };

  // 加载策略列表
  const fetchStrategies = async () => {
    try {
      const strategies = await getStrategies();
      console.log('从后端获取的策略列表:', strategies);
      if (strategies && strategies.length > 0) {
        setStrategiesList(strategies);
        // 如果当前选择的策略不在列表中，则选择第一个策略
        if (!strategies.some(s => s.id === selectedStrategy)) {
          setSelectedStrategy(strategies[0].id || 1);
          setSelectedStrategyName(strategies[0].name || '移动平均线交叉策略');
        } else {
          // 找到当前选择的策略并更新名称
          const currentStrategy = strategies.find(s => s.id === selectedStrategy);
          if (currentStrategy) {
            setSelectedStrategyName(currentStrategy.name);
          }
        }
      } else {
        // 如果没有策略，则使用默认策略列表
        antdMessage.error('未找到策略列表，请先创建策略');
      }
    } catch (error) {
      console.error('获取策略列表失败:', error);
      antdMessage.error('获取策略列表失败，请检查网络连接');
    }
  };

  // 加载数据
  useEffect(() => {
    // 防止React StrictMode导致的重复初始化
    if (initializedRef.current) {
      return;
    }
    initializedRef.current = true;
    
    fetchStocks();
    fetchDataSources();
    fetchStrategies(); // 加载策略列表
    
  }, []);

  // 当策略列表加载完成后，初始化默认策略的参数
  useEffect(() => {
    if (strategiesList.length > 0 && selectedStrategy) {
      loadParameterSpaces(selectedStrategy);
    }
  }, [strategiesList, selectedStrategy]);
  
  // 处理股票选择并自动设置日期范围
  const handleStockSelection = async (stock: Stock) => {
    setSelectedStock(stock);
    
    // 获取该股票的数据日期范围
    try {
      const dateRange = await fetchStockDateRange(stock.id);
      if (dateRange.first_date && dateRange.last_date) {
        const startDate = dayjs(dateRange.first_date).startOf('day');
        const endDate = dayjs(dateRange.last_date).endOf('day');
        setDateRange([startDate, endDate]);
        antdMessage.success(`已自动设置回测周期：${dateRange.first_date} 至 ${dateRange.last_date}`);
      }
    } catch (error) {
      console.error('获取股票日期范围失败:', error);
      antdMessage.warning('无法获取该股票的数据日期范围，请手动设置回测周期');
    }
  };

  // 获取股票列表
  const fetchStocks = async () => {
    setLoading(true);
    try {
      const stocks = await fetchStockList();
      setStockList(stocks);
      if (stocks.length > 0) {
        // 默认选择第一个股票并设置日期范围
        await handleStockSelection(stocks[0]);
      }
    } catch (error) {
      console.error('获取股票列表失败:', error);
    } finally {
      setLoading(false);
    }
  };
  
  // 加载策略参数空间
  const loadParameterSpaces = async (strategyId: number) => {
    try {
      const response = await axios.get(`/api/optimization/strategies/${strategyId}/parameter-spaces`);
      if (response.data && response.data.status === 'success') {
        setParameterSpaces(response.data.data);
        
        // 根据参数空间初始化默认参数值
        const defaultParams: Record<string, any> = {};
        response.data.data.forEach((param: any) => {
          if (param.parameter_type === 'int' || param.parameter_type === 'float') {
            // 使用最小值作为默认值
            defaultParams[param.parameter_name] = param.min_value;
          }
        });
        setStrategyParameters(defaultParams);
      }
    } catch (error) {
      console.error('加载参数空间失败:', error);
      // 如果加载失败，使用默认参数
      setParameterSpaces([]);
      setStrategyParameters({});
    }
  };

  // 处理策略参数设置
  const handleParametersModal = () => {
    setShowParametersModal(true);
  };

  // 保存策略参数
  const handleSaveParameters = () => {
    setShowParametersModal(false);
    message.success('参数设置已保存');
  };

  // 重置参数为默认值
  const handleResetParameters = () => {
    const defaultParams: Record<string, any> = {};
    parameterSpaces.forEach((param: any) => {
      if (param.parameter_type === 'int' || param.parameter_type === 'float') {
        defaultParams[param.parameter_name] = param.min_value;
      }
    });
    setStrategyParameters(defaultParams);
    message.success('参数已重置为默认值');
  };

  // 从优化结果导入参数
  const handleImportFromOptimization = async () => {
    try {
      // 获取该策略的最佳参数
      const response = await axios.get(`/api/optimization/strategies/${selectedStrategy}/best-parameters`);
      
      if (response.data && response.data.status === 'success' && response.data.data.length > 0) {
        setOptimizationResults(response.data.data);
        setShowOptimizationResultsModal(true);
      } else {
        message.warning('该策略暂无优化结果，请先进行参数优化');
      }
    } catch (error) {
      console.error('获取优化结果失败:', error);
      message.error('获取优化结果失败，请检查网络连接');
    }
  };

  // 选择优化结果并导入参数
  const handleSelectOptimizationResult = (result: any) => {
    setStrategyParameters(result.best_parameters);
    setShowOptimizationResultsModal(false);
    setShowParametersModal(false);
    message.success(`已导入优化结果: ${result.job_name} (得分: ${result.best_score?.toFixed(4)})`);
  };

  // 策略选择变化处理
  const handleStrategyChange = (strategyId: number) => {
    setSelectedStrategy(strategyId);
    
    // 更新策略名称
    const strategy = strategiesList.find(s => s.id === strategyId);
    if (strategy) {
      setSelectedStrategyName(strategy.name);
      setCurrentStrategyInfo(strategy);
    }
    
    // 加载参数空间
    loadParameterSpaces(strategyId);
  };

  // 获取数据源列表
  const fetchDataSources = async () => {
    try {
      const sources = await fetchDataSourcesAPI();
      setDataSources(sources);
    } catch (error) {
      console.error('获取数据源列表失败:', error);
    }
  };

  // 替换 Tabs 组件的实现
  const renderTabsItems = () => {
    return [
      {
        key: "1",
        label: (
          <span>
            <LineChartOutlined />
            绩效分析
          </span>
        ),
        children: (
          <Row gutter={16}>
            <Col span={24} style={{ marginBottom: 16 }}>
              <OptimizedChart option={getEquityCurveOption()} style={{ height: 500 }} />
            </Col>
          </Row>
        )
      },
      {
        key: "3",
        label: (
          <span>
            <LineChartOutlined />
            K线与交易信号
          </span>
        ),
        children: (
          <Row gutter={16}>
            <Col span={24}>
              <Card 
                title={selectedStock ? `${selectedStock.name} (${selectedStock.symbol})交易图表` : '交易图表'} 
                extra={
                  <Space>
                    <Button 
                      type="primary" 
                      size="small"
                      onClick={() => {
                        const chartElement = document.querySelector('.kline-chart');
                        if (chartElement) {
                          const chartInstance = (chartElement as any).__echarts__;
                          if (chartInstance) {
                            // 重置缩放
                            chartInstance.dispatchAction({
                              type: 'dataZoom',
                              start: 0,
                              end: 100
                            });
                          }
                        }
                      }}
                    >
                      重置缩放
                    </Button>
                    <Button 
                      size="small" 
                      onClick={() => {
                        // 获取所有交易记录的日期，找到K线数据中相应的索引
                        if (tradeRecords.length > 0 && klineData.length > 0) {
                          // 创建日期映射
                          const dateIndexMap = new Map();
                          klineData.forEach((item, index) => {
                            const dateStr = normalizeDate(item[0]);
                            dateIndexMap.set(dateStr, index);
                          });
                          
                          // 收集所有交易记录的索引
                          const tradeDateIndices: number[] = [];
                          tradeRecords.forEach(record => {
                            const dateStr = normalizeDate(record.date);
                            const index = dateIndexMap.get(dateStr);
                            if (index !== undefined) {
                              tradeDateIndices.push(index);
                            }
                          });
                          
                          console.log('找到的交易日期索引:', tradeDateIndices);
                          
                          if (tradeDateIndices.length > 0) {
                            // 找到最小和最大索引
                            const minIndex = Math.max(0, Math.min(...tradeDateIndices) - 10);
                            const maxIndex = Math.min(klineData.length - 1, Math.max(...tradeDateIndices) + 10);
                            
                            // 计算百分比位置
                            const start = (minIndex / klineData.length) * 100;
                            const end = (maxIndex / klineData.length) * 100;
                            
                            console.log(`设置缩放范围: ${start.toFixed(2)}% - ${end.toFixed(2)}%`);
                            
                            // 获取图表实例并设置缩放
                            const chartElement = document.querySelector('.kline-chart');
                            if (chartElement) {
                              const chartInstance = (chartElement as any).__echarts__;
                              if (chartInstance) {
                                chartInstance.dispatchAction({
                                  type: 'dataZoom',
                                  start: start,
                                  end: end
                                });
                                
                                // 使用函数组件包装，确保消息API调用在组件上下文中执行
                                const showFocusSuccessMessage = (count: number) => {
                                  message.success(`已聚焦到交易区域，共显示 ${count} 个交易点`);
                                };
                                showFocusSuccessMessage(tradeDateIndices.length);
                              }
                            }
                          } else {
                            // 使用函数组件包装，确保消息API调用在组件上下文中执行
                            const showNoSignalMessage = () => {
                              message.info('未找到交易信号对应的K线数据点');
                            };
                            showNoSignalMessage();
                          }
                        } else {
                          // 使用函数组件包装，确保消息API调用在组件上下文中执行
                          const showNoDataMessage = () => {
                            message.info('没有交易记录或K线数据');
                          };
                          showNoDataMessage();
                        }
                      }}
                    >
                      聚焦交易
                    </Button>
                    <Tooltip title="只显示有交易的区域">
                      <InfoCircleOutlined />
                    </Tooltip>
                  </Space>
                }
              >
                <OptimizedChart 
                  className="kline-chart"
                  option={getKlineOption()} 
                  style={{ height: 600 }} 
                  notMerge={true}
                  opts={{ renderer: 'canvas' }}
                  onEvents={{
                    click: (params: any) => {
                      // 点击交易标记时，弹出详细信息
                      if (params.componentType === 'markPoint') {
                        const pointName = params.name; // '买入' 或 '卖出'
                        const isBuy = pointName === '买入';
                        const xIndex = params.data.coord[0]; // X轴索引
                        
                        // 获取该索引对应的K线日期
                        const klineDate = klineData[xIndex][0];
                        
                        // 查找与该日期对应的交易记录
                        const directionType = isBuy ? '买入' : '卖出';
                        const matchedRecord = tradeRecords.find(record => 
                          record.direction === directionType && 
                          normalizeDate(record.date) === normalizeDate(klineDate)
                        );
                        
                        console.log(`点击了${directionType}标记，日期: ${klineDate}`, matchedRecord);
                        
                        if (matchedRecord) {
                          const record = matchedRecord;
                          const title = isBuy ? '买入详情' : '卖出详情';
                          const content = (
                            <div>
                              <p><strong>日期:</strong> {record.date}</p>
                              <p><strong>价格:</strong> {isBuy ? record.entryPrice : record.exitPrice}</p>
                              <p><strong>数量:</strong> {record.shares.toLocaleString()} 股</p>
                              <p><strong>金额:</strong> {record.value.toLocaleString('zh-CN', {minimumFractionDigits: 2})} 元</p>
                              {!isBuy && (
                                <>
                                  <p><strong>盈亏:</strong> {record.profitLoss >= 0 ? '+' : ''}{record.profitLoss.toLocaleString('zh-CN', {minimumFractionDigits: 2})} 元</p>
                                  <p><strong>收益率:</strong> {record.returnPct >= 0 ? '+' : ''}{record.returnPct.toFixed(2)}%</p>
                                  <p><strong>持仓天数:</strong> {record.duration} 天</p>
                                </>
                              )}
                              <p><strong>交易前资金:</strong> {record.beforeCash.toLocaleString('zh-CN', {minimumFractionDigits: 2})} 元</p>
                              <p><strong>交易后资金:</strong> {record.afterCash.toLocaleString('zh-CN', {minimumFractionDigits: 2})} 元</p>
                              <p><strong>触发原因:</strong> {record.trigger_reason || '未记录原因'}</p>
                            </div>
                          );
                          
                          Modal.info({
                            title,
                            content,
                            width: 400
                          });
                        } else {
                          // 使用函数组件包装，确保消息API调用在组件上下文中执行
                          const showNoMatchMessage = (type: string, date: string) => {
                            message.info(`未找到匹配的${type}交易记录，日期: ${date}`);
                          };
                          showNoMatchMessage(directionType, klineDate);
                        }
                      }
                    }
                  }}
                />
              </Card>
            </Col>
          </Row>
        )
      },
      {
        key: "2",
        label: (
          <span>
            <InfoCircleOutlined />
            交易明细
          </span>
        ),
        children: (
          <OptimizedTable
            dataSource={tradeRecords}
            columns={columns}
            pagination={{ pageSize: 10 }}
            scroll={{ x: true }}
          />
        )
      }
    ];
  };

  return (
    <div>
      <Title level={2}>回测分析</Title>
      <Paragraph>回测您的交易策略，分析策略表现并优化参数。</Paragraph>
      
      <Card>
        <Spin spinning={loading}>
          <Form layout="vertical">
            <Row gutter={24}>
              <Col span={8}>
                <Form.Item label="策略选择" required>
                  <Input.Group compact>
                    <Select
                      value={selectedStrategyName}
                      onChange={(value, option: any) => {
                        handleStrategyChange(Number(option.key));
                      }}
                      placeholder="选择策略"
                      style={{ width: 'calc(100% - 80px)' }}
                      size="middle"
                    >
                      {strategiesList.map(strategy => (
                        <Option 
                          key={strategy.id} 
                          value={strategy.name}
                        >
                          {strategy.name}
                        </Option>
                      ))}
                    </Select>
                    <Button 
                      type="primary" 
                      ghost
                      onClick={handleParametersModal}
                      style={{ width: '80px' }}
                      icon={<SettingOutlined />}
                      size="middle"
                    >
                      参数
                    </Button>
                  </Input.Group>
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item label="交易品种" required>
                  <Select
                    value={selectedStock?.symbol}
                    onChange={async (value) => {
                      const stock = stockList.find(s => s.symbol === value);
                      if (stock) {
                        await handleStockSelection(stock);
                      }
                    }}
                    placeholder="选择交易品种"
                  >
                    {stockList.map(stock => (
                      <Option key={stock.id} value={stock.symbol}>
                        {stock.name} ({stock.symbol}) - {
                          dataSources.find(ds => ds.id === stock.source_id)?.name || '未知数据源'
                        }
                      </Option>
                    ))}
                  </Select>
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item label="回测周期" required>
                  <DatePicker.RangePicker
                    value={dateRange}
                    onChange={(dates) => {
                      if (dates && dates[0] && dates[1]) {
                        setDateRange([
                          dates[0].startOf('day'),
                          dates[1].endOf('day')
                        ]);
                      }
                    }}
                    style={{ width: '100%' }}
                    placeholder={['开始日期', '结束日期']}
                    format="YYYY-MM-DD"
                    allowClear={false}
                    disabledDate={(current) => {
                      return current && current > dayjs().endOf('day');
                    }}
                    presets={[
                      {
                        label: 'Last 7 days',
                        value: [dayjs().subtract(7, 'day'), dayjs()]
                      },
                      {
                        label: 'Last 30 days',
                        value: [dayjs().subtract(30, 'day'), dayjs()]
                      },
                      {
                        label: 'Last 3 months',
                        value: [dayjs().subtract(3, 'month'), dayjs()]
                      },
                      {
                        label: 'Last 6 months',
                        value: [dayjs().subtract(6, 'month'), dayjs()]
                      },
                      {
                        label: 'Last 1 year',
                        value: [dayjs().subtract(1, 'year'), dayjs()]
                      },
                      {
                        label: 'Last 3 years',
                        value: [dayjs().subtract(3, 'year'), dayjs()]
                      },
                      {
                        label: 'Last 5 years',
                        value: [dayjs().subtract(5, 'year'), dayjs()]
                      },
                      {
                        label: 'Last 7 years',
                        value: [dayjs().subtract(7, 'year'), dayjs()]
                      },
                      {
                        label: 'Last 10 years',
                        value: [dayjs().subtract(10, 'year'), dayjs()]
                      }
                    ]}
                  />
                </Form.Item>
              </Col>
            </Row>
            
            <Row gutter={24}>
              <Col span={6}>
                <Form.Item label="初始资金">
                  <InputNumber
                    value={initialCapital}
                    onChange={value => setInitialCapital(Number(value) || 100000)}
                    formatter={value => `¥ ${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
                    parser={value => {
                      if (value) {
                        const parsed = parseFloat(value.replace(/\¥\s?|(,*)/g, ''));
                        return isNaN(parsed) ? initialCapital : parsed;
                      }
                      return initialCapital;
                    }}
                    style={{ width: '100%' }}
                  />
                </Form.Item>
              </Col>
              <Col span={6}>
                <Form.Item label="手续费率(%)">
                  <InputNumber 
                    value={commissionRate} 
                    onChange={value => setCommissionRate(Number(value) || 0.15)} 
                    min={0} 
                    max={10} 
                    step={0.01} 
                    style={{ width: '100%' }} 
                  />
                </Form.Item>
              </Col>
              <Col span={6}>
                <Form.Item label="滑点(%)">
                  <InputNumber 
                    value={slippage} 
                    onChange={value => setSlippage(Number(value) || 0.1)} 
                    min={0} 
                    max={10} 
                    step={0.01} 
                    style={{ width: '100%' }} 
                  />
                </Form.Item>
              </Col>
              <Col span={6}>
                <Form.Item label="基准">
                  <Select defaultValue="SPY" placeholder="选择基准">
                    <Option value="SPY">标普500ETF</Option>
                    <Option value="QQQ">纳斯达克ETF</Option>
                    <Option value="DIA">道琼斯ETF</Option>
                  </Select>
                </Form.Item>
              </Col>
            </Row>
            
            {selectedStock && (
              <Alert
                message={`已选择数据源: ${dataSources.find(ds => ds.id === selectedStock.source_id)?.name || '未知'}`}
                description={`回测将使用与数据管理中相同的数据源获取 ${selectedStock.symbol} 的历史数据`}
                type="info"
                showIcon
                style={{ marginBottom: 16 }}
              />
            )}
            
            <Form.Item label="执行模式">
              <Space>
                <Switch
                  checked={asyncMode}
                  onChange={setAsyncMode}
                  checkedChildren="异步"
                  unCheckedChildren="同步"
                />
                <Tooltip title={asyncMode ? "异步模式：任务在后台执行，可以处理大数据量回测" : "同步模式：立即返回结果，适合快速回测"}>
                  <InfoCircleOutlined style={{ color: '#aaa' }} />
                </Tooltip>
                {asyncMode && currentTaskId && (
                  <Tag color={taskStatus === 'completed' ? 'green' : taskStatus === 'failed' ? 'red' : 'blue'}>
                    任务状态: {taskStatus === 'pending' ? '等待中' : 
                             taskStatus === 'running' ? '执行中' : 
                             taskStatus === 'completed' ? '已完成' : 
                             taskStatus === 'failed' ? '失败' : taskStatus}
                    {taskStatus === 'running' && ` (${taskProgress}%)`}
                  </Tag>
                )}
              </Space>
            </Form.Item>
            
            <Form.Item>
              <Space>
                <Button 
                  type="primary" 
                  icon={<PlayCircleOutlined />} 
                  loading={running} 
                  onClick={handleRunBacktest}
                >
                  {asyncMode ? '提交异步回测' : '运行回测'}
                </Button>
                <Button 
                  type="default" 
                  icon={<PlayCircleOutlined />} 
                  loading={running} 
                  onClick={handleForceRefreshBacktest}
                  title="强制刷新：清除缓存并重新运行回测"
                  disabled={asyncMode} // 异步模式下禁用强制刷新
                >
                  强制刷新
                </Button>
              </Space>
            </Form.Item>
          </Form>
        </Spin>
      </Card>
      
      {hasResults && (
        <>
          <Divider />
          <Card>
            <Row gutter={16}>
              <Col span={6}>
                <Statistic
                  title={<span>总收益率 <Tooltip title="总收益率=最终资金/初始资金-1，反映策略总体收益情况"><InfoCircleOutlined style={{ fontSize: 14, color: '#aaa' }} /></Tooltip></span>}
                  value={performanceData.totalReturn}
                  precision={2}
                  valueStyle={{ color: performanceData.totalReturn >= 0 ? '#f5222d' : '#52c41a' }}
                  suffix="%"
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title={<span>年化收益率 <Tooltip title="年化收益率=（总收益率+1）^(365/天数)-1，反映策略年化增长速度"><InfoCircleOutlined style={{ fontSize: 14, color: '#aaa' }} /></Tooltip></span>}
                  value={performanceData.annualReturn}
                  precision={2}
                  valueStyle={{ color: performanceData.annualReturn >= 0 ? '#f5222d' : '#52c41a' }}
                  suffix="%"
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title={<span>最大回撤 <Tooltip title="最大回撤=历史最高点到最低点的最大跌幅，衡量风险"><InfoCircleOutlined style={{ fontSize: 14, color: '#aaa' }} /></Tooltip></span>}
                  value={Math.abs(performanceData.maxDrawdown)}
                  precision={2}
                  valueStyle={{ color: '#52c41a' }}
                  suffix="%"
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title={<span>夏普比率 <Tooltip title="夏普比率=（年化收益率-无风险利率）/年化波动率，衡量单位风险收益"><InfoCircleOutlined style={{ fontSize: 14, color: '#aaa' }} /></Tooltip></span>}
                  value={performanceData.sharpeRatio}
                  precision={2}
                />
              </Col>
            </Row>
            <Row gutter={16} style={{ marginTop: 16 }}>
              <Col span={6}>
                <Statistic
                  title={<span>胜率 <Tooltip title="胜率=盈利交易次数/总交易次数"><InfoCircleOutlined style={{ fontSize: 14, color: '#aaa' }} /></Tooltip></span>}
                  value={performanceData.winRate}
                  precision={2}
                  suffix="%"
                />
              </Col>
            </Row>
            
            <Row gutter={16} style={{ marginTop: 24 }}>
              <Col span={6}>
                <Statistic
                  title={<span>盈亏比 <Tooltip title="盈亏比=所有盈利交易收益总和/所有亏损交易亏损总和"><InfoCircleOutlined style={{ fontSize: 14, color: '#aaa' }} /></Tooltip></span>}
                  value={performanceData.profitFactor || 0}
                  precision={2}
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title={<span>Alpha <Tooltip title="Alpha=策略超越基准的年化收益，反映主动收益"><InfoCircleOutlined style={{ fontSize: 14, color: '#aaa' }} /></Tooltip></span>}
                  value={performanceData.alpha || 0}
                  precision={2}
                  suffix="%"
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title={<span>Beta <Tooltip title="Beta=策略与基准的相关性，衡量系统性风险"><InfoCircleOutlined style={{ fontSize: 14, color: '#aaa' }} /></Tooltip></span>}
                  value={performanceData.beta || 0}
                  precision={2}
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title={<span>交易次数 <Tooltip title="策略在回测期间的总交易次数"><InfoCircleOutlined style={{ fontSize: 14, color: '#aaa' }} /></Tooltip></span>}
                  value={tradeRecords.length}
                />
              </Col>
            </Row>
            
            <Divider />
            
            <Tabs defaultActiveKey="1" items={renderTabsItems()} />
            
            <div style={{ textAlign: 'right', marginTop: 16 }}>
              <Button icon={<DownloadOutlined />} style={{ marginRight: 8 }}>
                导出报告
              </Button>
              <Button 
                icon={<SaveOutlined />} 
                type="primary"
                onClick={() => {
                  // 生成默认回测名称：股票代码_v日期_时分
                  const now = new Date();
                  const dateStr = now.toISOString().slice(0, 10).replace(/-/g, ''); // YYYYMMDD
                  const timeStr = now.toTimeString().slice(0, 5).replace(':', ''); // HHMM
                  const defaultName = `${selectedStock?.symbol || 'UNKNOWN'}_v${dateStr}_${timeStr}`;
                  setBacktestName(defaultName);
                  setSaveModalVisible(true);
                }}
                disabled={!hasResults}
              >
                保存回测
              </Button>
            </div>
            
          </Card>
        </>
      )}

      {/* 保存回测模态框 */}
      <Modal
        title="保存回测"
        open={saveModalVisible}
        onOk={handleSaveBacktest}
        onCancel={() => {
          setSaveModalVisible(false);
          setBacktestName('');
          setBacktestDescription('');
        }}
        confirmLoading={saveLoading}
        okText="保存"
        cancelText="取消"
      >
        <Form layout="vertical">
          <Form.Item
            label="回测名称"
            required
            help="请输入一个描述性的回测名称"
          >
            <Input
              placeholder="例如：MA交叉策略_AAPL_2024年回测"
              value={backtestName}
              onChange={(e) => setBacktestName(e.target.value)}
            />
          </Form.Item>
          
          <Form.Item
            label="回测描述"
            help="可选：添加回测的详细描述"
          >
            <Input.TextArea
              placeholder="例如：使用移动平均线交叉策略对AAPL进行回测，包含仓位控制..."
              value={backtestDescription}
              onChange={(e) => setBacktestDescription(e.target.value)}
              rows={3}
            />
          </Form.Item>
          
          <Alert
            message="保存信息"
            description={
              <div>
                <p><strong>策略：</strong>{selectedStrategyName}</p>
                <p><strong>股票：</strong>{selectedStock?.symbol} ({selectedStock?.name})</p>
                <p><strong>回测期间：</strong>{dateRange[0].format('YYYY-MM-DD')} 至 {dateRange[1].format('YYYY-MM-DD')}</p>
                <p><strong>初始资金：</strong>${initialCapital.toLocaleString()}</p>
                {Object.keys(strategyParameters).length > 0 && (
                  <p><strong>策略参数：</strong>
                    短期均线 {strategyParameters.short_window || 5}天, 
                    长期均线 {strategyParameters.long_window || 20}天
                  </p>
                )}
              </div>
            }
            type="info"
            showIcon
          />
        </Form>
      </Modal>

      {/* 策略参数设置模态框 */}
      <Modal
        title="策略参数设置"
        open={showParametersModal}
        onOk={handleSaveParameters}
        onCancel={() => setShowParametersModal(false)}
        width={800}
      >
        <Alert
          message={`当前策略: ${currentStrategyInfo?.name || selectedStrategyName}`}
          description={currentStrategyInfo?.description || "策略参数配置"}
          type="info"
          showIcon
          style={{ marginBottom: '16px' }}
        />
        
        <Form layout="vertical">
          {parameterSpaces.length > 0 ? (
            <Row gutter={16}>
              {parameterSpaces.map((param, index) => (
                <Col span={12} key={param.parameter_name}>
                  <Form.Item 
                    label={`${param.parameter_name}${param.description ? ` (${param.description})` : ''}`}
                    help={param.description}
                  >
                    {param.parameter_type === 'int' ? (
                      <InputNumber
                        value={strategyParameters[param.parameter_name] || param.min_value}
                        onChange={(value) => setStrategyParameters(prev => ({ 
                          ...prev, 
                          [param.parameter_name]: value 
                        }))}
                        min={param.min_value}
                        max={param.max_value}
                        step={param.step_size}
                        style={{ width: '100%' }}
                      />
                    ) : param.parameter_type === 'float' ? (
                      <InputNumber
                        value={strategyParameters[param.parameter_name] || param.min_value}
                        onChange={(value) => setStrategyParameters(prev => ({ 
                          ...prev, 
                          [param.parameter_name]: value 
                        }))}
                        min={param.min_value}
                        max={param.max_value}
                        step={param.step_size}
                        precision={2}
                        style={{ width: '100%' }}
                      />
                    ) : param.parameter_type === 'choice' ? (
                      <Select
                        value={
                          strategyParameters[param.parameter_name] !== undefined
                            ? strategyParameters[param.parameter_name]
                            : (param.choices && param.choices.length > 0 ? param.choices[0] : undefined)
                        }
                        onChange={(value) => setStrategyParameters(prev => ({
                          ...prev,
                          [param.parameter_name]: value
                        }))}
                        style={{ width: '100%' }}
                      >
                        {(param.choices || []).map((c: boolean | number | string, i: number) => (
                          <Option key={i} value={c as any}>
                            {typeof c === 'boolean' ? (c ? 'true' : 'false') : String(c)}
                          </Option>
                        ))}
                      </Select>
                    ) : (
                      <Input
                        value={strategyParameters[param.parameter_name] || ''}
                        onChange={(e) => setStrategyParameters(prev => ({ 
                          ...prev, 
                          [param.parameter_name]: e.target.value 
                        }))}
                        placeholder={`请输入${param.parameter_name}`}
                      />
                    )}
                  </Form.Item>
                </Col>
              ))}
            </Row>
          ) : (
            <Alert
              message="暂无参数配置"
              description="该策略暂未配置参数空间，将使用默认参数进行回测"
              type="warning"
              showIcon
            />
          )}
          
          {parameterSpaces.length > 0 && (
            <Alert
              message="参数说明"
              description={
                <div>
                  {parameterSpaces.map((param, index) => (
                    <p key={index}>
                      <strong>{param.parameter_name}：</strong>
                      {param.description}
                      {param.parameter_type === 'int' || param.parameter_type === 'float' ? 
                        ` (范围: ${param.min_value} - ${param.max_value}, 步长: ${param.step_size})` :
                        (param.parameter_type === 'choice' ? ` (选项: ${(param.choices || []).map((c: boolean | number | string) => (typeof c === 'boolean' ? (c ? 'true' : 'false') : String(c))).join(', ')})` : '')
                      }
                    </p>
                  ))}
                </div>
              }
              type="info"
              showIcon
              style={{ marginBottom: '16px' }}
            />
          )}
          
          <Space>
            <Button onClick={handleResetParameters}>
              重置默认值
            </Button>
            <Button type="dashed" onClick={handleImportFromOptimization}>
              从优化导入
            </Button>
          </Space>
        </Form>
      </Modal>

      {/* 优化结果选择模态框 */}
      <Modal
        title="选择优化结果"
        open={showOptimizationResultsModal}
        onCancel={() => setShowOptimizationResultsModal(false)}
        width={800}
        footer={null}
      >
        <Alert
          message="选择要导入的优化结果"
          description="以下是从参数优化中获得的最佳参数配置，按优化得分排序"
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
        />
        
        <div style={{ maxHeight: 400, overflowY: 'auto' }}>
          {optimizationResults.map((result, index) => (
            <Card 
              key={result.job_id} 
              size="small" 
              style={{ marginBottom: 8 }}
              hoverable
              onClick={() => handleSelectOptimizationResult(result)}
            >
              <Row gutter={16} align="middle">
                <Col span={16}>
                  <div>
                    <strong>{result.job_name}</strong>
                    <div style={{ fontSize: '12px', color: '#666', marginTop: 4 }}>
                      {result.description && `${result.description} • `}
                      完成时间: {result.completed_at ? new Date(result.completed_at).toLocaleString() : '未知'}
                    </div>
                  </div>
                </Col>
                <Col span={4}>
                  <div style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: '14px', fontWeight: 'bold', color: '#1890ff' }}>
                      {result.best_score?.toFixed(4)}
                    </div>
                    <div style={{ fontSize: '12px', color: '#666' }}>
                      {result.objective_function}
                    </div>
                  </div>
                </Col>
                <Col span={4}>
                  <div style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: '12px', color: '#666' }}>
                      试验次数: {result.total_trials}
                    </div>
                  </div>
                </Col>
              </Row>
              
              {/* 显示关键参数 */}
              <div style={{ marginTop: 8, fontSize: '12px' }}>
                <strong>关键参数:</strong>
                <div style={{ marginTop: 4, maxHeight: '40px', overflow: 'hidden' }}>
                  {Object.entries(result.best_parameters || {}).slice(0, 3).map(([key, value]) => (
                    <Tag 
                      key={key} 
                      style={{ 
                        margin: '1px 2px 1px 0', 
                        fontSize: '10px',
                        padding: '1px 4px',
                        lineHeight: '16px'
                      }}
                    >
                      {key === 'short_window' ? '短期' : 
                       key === 'long_window' ? '长期' : 
                       key === 'min_reversal_points' ? '反转点' :
                       key === 'lookback_period' ? '回望期' :
                       key === 'signal_strength_threshold' ? '信号阈值' :
                       key === 'batch_count' ? '批次数' :
                       key === 'stop_loss_ratio' ? '止损' :
                       key === 'take_profit_ratio' ? '止盈' :
                       key}: {typeof value === 'number' ? value.toFixed(1) : String(value)}
                    </Tag>
                  ))}
                  {Object.keys(result.best_parameters || {}).length > 3 && (
                    <Tag 
                      style={{ 
                        margin: '1px 2px 1px 0', 
                        fontSize: '10px',
                        padding: '1px 4px',
                        lineHeight: '16px'
                      }}
                    >
                      +{Object.keys(result.best_parameters || {}).length - 3}个
                    </Tag>
                  )}
                </div>
              </div>
            </Card>
          ))}
        </div>
        
        {optimizationResults.length === 0 && (
          <div style={{ textAlign: 'center', padding: '40px 0', color: '#999' }}>
            暂无优化结果
          </div>
        )}
      </Modal>
    </div>
  );
};

export default memo(Backtest);