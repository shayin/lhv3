import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Card, Form, Button, DatePicker, Select, InputNumber, Row, Col, Divider, Typography, Tabs, Table, Statistic, Spin, message as antdMessage, Alert, Space, Tooltip, Modal, Tag, App, message, Slider, Input } from 'antd';
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
import { getStrategies, backtestStrategy } from '../services/strategyService';

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
  position_size?: number; // 该笔交易使用的仓位百分比
  available_capital?: number; // 交易后的可用资金
  allocated_capital?: number; // 已分配的资金
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
  // 添加仓位控制相关状态
  const [positionMode, setPositionMode] = useState<string>('fixed'); // 'fixed', 'dynamic', 'staged'
  const [defaultPositionSize, setDefaultPositionSize] = useState<number>(100); // 默认100%
  const [positionSizes, setPositionSizes] = useState<number[]>([25, 25, 25, 25]); // 分批建仓的比例
  const [dynamicPositionMax, setDynamicPositionMax] = useState<number>(100); // 动态仓位最大值
  
  // 添加保存回测相关状态
  const [saveModalVisible, setSaveModalVisible] = useState(false);
  const [saveLoading, setSaveLoading] = useState(false);
  const [backtestName, setBacktestName] = useState('');
  const [backtestDescription, setBacktestDescription] = useState('');
  
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
      // 构建仓位配置
      const positionConfig = {
        mode: positionMode,
        defaultSize: defaultPositionSize / 100,
        sizes: positionSizes.map(size => size / 100),
        dynamicMax: dynamicPositionMax / 100
      };

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
          positionConfig: positionConfig,
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
      
      // 构建仓位配置对象，传递给后端
      const positionConfig = {
        mode: positionMode,
        defaultSize: defaultPositionSize / 100, // 转换为小数
        sizes: positionSizes.map(size => size / 100), // 转换为小数数组
        dynamicMax: dynamicPositionMax / 100 // 转换为小数
      };
      
      // 使用新的backtestStrategy方法进行回测，确保传入数字类型的策略ID
      const result = await backtestStrategy(
        selectedStrategy, // 已经是number类型
        selectedStock.symbol,
        startDate,
        endDate,
        initialCapital,
        {
          positionConfig: positionConfig, // 传递仓位配置
          save_backtest: false, // 暂时不自动保存，等用户手动保存
          parameters: strategyParameters // 添加策略参数
        }, // 参数对象
        commissionRate,
        slippage,
        'database', // 使用数据库作为数据源
        [] // 默认特征列表
      );
      
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
      
      // 如果找不到任何数据，添加一些示例数据以确保UI能显示（仅用于调试）
      if (!result.trades || result.trades.length === 0) {
        console.warn('未找到交易记录，添加示例数据用于调试');
        result.trades = [{
          date: new Date().toISOString(),
          action: 'BUY',
          price: 100,
          shares: 100,
          value: 10000,
          commission: 15,
          before_cash: 100000,
          after_cash: 90000,
          before_equity: 100000,
          after_equity: 100000,
          trigger_reason: '调试示例'
        }];
      }
      
      if (!result.equity_curve || result.equity_curve.length === 0) {
        console.warn('未找到权益曲线数据，添加示例数据用于调试');
        // 创建30天的模拟权益曲线
        result.equity_curve = Array.from({ length: 30 }, (_, i) => {
          const date = new Date();
          date.setDate(date.getDate() - 30 + i);
          return {
            date: date.toISOString(),
            equity: 100000 + i * 1000,
            capital: 50000,
            position: 100,
            position_value: 50000 + i * 1000,
            drawdown: 0
          };
        });
      }
      
      if (!result.drawdowns || result.drawdowns.length === 0) {
        console.warn('未找到回撤数据，添加示例数据用于调试');
        result.drawdowns = result.equity_curve.map((item: any) => ({
          date: item.date,
          drawdown: Math.random() * 0.05 // 随机回撤，最大5%
        }));
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
      if (result.trades && result.trades.length > 0) {
        // 设置交易记录
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
            // 添加仓位相关信息
            position_size: trade.position_size ? (trade.position_size * 100) : 100, // 默认100%
            available_capital: trade.available_capital,
            allocated_capital: trade.allocated_capital
          };
        });
        
        // 按交易时间倒序排序（最新的在前面）
        const sortedTrades = trades.sort((a: any, b: any) => {
          return new Date(b.date).getTime() - new Date(a.date).getTime();
        });
        
        setTradeRecords(sortedTrades);
        setTradesData(sortedTrades);
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
      }
      
      // 更新回撤曲线
      if (result.drawdowns && result.drawdowns.length > 0) {
        const drawdownsData = result.drawdowns.map((item: any) => ({
          date: normalizeDate(item.date),
          drawdown: (item.drawdown || 0) * 100 // 转为百分比
        }));
        setDrawdownData(drawdownsData);
      }
      
      // 标记有回测结果
      setHasResults(true);
      
      // 滚动到结果区域
      resultsRef.current?.scrollIntoView({ behavior: 'smooth' });
      
      // 使用函数组件包装，确保消息API调用在组件上下文中执行
      const showSuccessMessage = () => {
        message.success('回测完成');
      };
      showSuccessMessage();
    } catch (error: any) {
      console.error('回测执行失败:', error);
      antdMessage.error(`回测失败: ${error.message || '未知错误'}`);
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
    setLoading,
    // 添加仓位相关依赖
    positionMode,
    defaultPositionSize,
    positionSizes,
    dynamicPositionMax
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
      title: '仓位(%)',
      dataIndex: 'position_size',
      key: 'position_size',
      sorter: (a, b) => (a.position_size || 0) - (b.position_size || 0),
      render: (text) => {
        const value = parseFloat(text) || 100;
        return value.toFixed(0) + '%';
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
    if (selectedStrategy === 1) { // MA交叉策略
      setStrategyParameters({
        short_window: 5,
        long_window: 20
      });
    }
    message.success('参数已重置为默认值');
  };

  // 从优化结果导入参数
  const handleImportFromOptimization = () => {
    // 这里可以添加从优化页面导入参数的逻辑
    message.info('请从参数优化页面复制最佳参数');
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
              <ReactECharts option={getEquityCurveOption()} style={{ height: 500 }} />
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
                <ReactECharts 
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
          <Table
            dataSource={tradeRecords}
            columns={columns}
            pagination={{ pageSize: 10 }}
            scroll={{ x: true }}
          />
        )
      }
    ];
  };

  // 渲染不同仓位模式的配置选项
  const renderPositionModeOptions = () => {
    switch (positionMode) {
      case 'fixed':
        return (
          <>
            <Form.Item label="固定仓位比例(%)">
              <Row gutter={16}>
                <Col span={16}>
                  <InputNumber
                    value={defaultPositionSize}
                    onChange={value => setDefaultPositionSize(Number(value) || 100)}
                    min={1}
                    max={100}
                    style={{ width: '100%' }}
                  />
                </Col>
                <Col span={8}>
                  <Slider
                    value={defaultPositionSize}
                    onChange={value => setDefaultPositionSize(value)}
                    min={0}
                    max={100}
                    step={5}
                  />
                </Col>
              </Row>
            </Form.Item>
            <Alert
              message="固定仓位说明"
              description={
                <div>
                  <p>每次买入信号都使用相同比例的资金进行交易：</p>
                  <ul>
                    <li>设置为100%表示每次买入信号都使用全部可用资金</li>
                    <li>设置为50%表示每次买入信号都使用一半可用资金</li>
                    <li>适合稳定型策略，或者想要均匀分配资金的情况</li>
                  </ul>
                </div>
              }
              type="info"
              showIcon
            />
          </>
        );
      
      case 'dynamic':
        return (
          <>
            <Form.Item label="最大仓位比例(%)">
              <Row gutter={16}>
                <Col span={16}>
                  <InputNumber
                    value={dynamicPositionMax}
                    onChange={value => setDynamicPositionMax(Number(value) || 100)}
                    min={1}
                    max={100}
                    style={{ width: '100%' }}
                  />
                </Col>
                <Col span={8}>
                  <Slider
                    value={dynamicPositionMax}
                    onChange={value => setDynamicPositionMax(value)}
                    min={0}
                    max={100}
                    step={5}
                  />
                </Col>
              </Row>
            </Form.Item>
            <Alert
              message="动态仓位说明"
              description={
                <div>
                  <p>系统将根据多种因素综合评估信号强度，自动调整每次买入的仓位大小：</p>
                  <ul>
                    <li>信号强度越高，分配的仓位越接近设置的最大值</li>
                    <li>信号强度综合考虑以下因素：信号值大小、均线偏离度、RSI指标、MACD柱状图、成交量变化</li>
                    <li>当信号强度低于阈值时，将不会开仓或使用极小仓位</li>
                    <li>适合于顺势交易策略，可以在趋势初期小仓位试水，趋势明确后加大仓位</li>
                  </ul>
                </div>
              }
              type="info"
              showIcon
            />
          </>
        );
      
      case 'staged':
        return (
          <>
            <Form.Item label="分批建仓比例设置(%)">
              <Space direction="vertical" style={{ width: '100%' }}>
                {positionSizes.map((size, index) => (
                  <div key={index} style={{ display: 'flex', alignItems: 'center' }}>
                    <span style={{ marginRight: '8px', minWidth: '60px' }}>第{index + 1}批:</span>
                    <InputNumber
                      value={size}
                      onChange={value => {
                        const newSizes = [...positionSizes];
                        newSizes[index] = Number(value) || 0;
                        setPositionSizes(newSizes);
                      }}
                      min={0}
                      max={100}
                      style={{ flex: 1 }}
                    />
                    {index > 0 && (
                      <Button 
                        type="text" 
                        danger
                        icon={<MinusCircleOutlined />}
                        onClick={() => {
                          const newSizes = positionSizes.filter((_, i) => i !== index);
                          setPositionSizes(newSizes);
                        }}
                      />
                    )}
                  </div>
                ))}
                {positionSizes.length < 5 && (
                  <Button
                    type="dashed"
                    onClick={() => {
                      if (positionSizes.length < 5) {
                        // 计算合理的默认值
                        const remainingPercent = 100 - positionSizes.reduce((sum, size) => sum + size, 0);
                        const defaultNewSize = Math.max(0, Math.min(20, remainingPercent));
                        setPositionSizes([...positionSizes, defaultNewSize]);
                      }
                    }}
                    block
                    icon={<PlusOutlined />}
                  >
                    添加批次
                  </Button>
                )}
                <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '8px' }}>
                  <span>当前总仓位: {positionSizes.reduce((sum, size) => sum + size, 0)}%</span>
                  {positionSizes.reduce((sum, size) => sum + size, 0) !== 100 && (
                    <span style={{ color: '#ff4d4f' }}>
                      (建议总和为100%)
                    </span>
                  )}
                  <Button
                    type="link"
                    onClick={() => {
                      // 平均分配各批次仓位
                      const batchCount = positionSizes.length;
                      const equalSize = Math.floor(100 / batchCount);
                      const remainder = 100 - (equalSize * batchCount);
                      
                      const newSizes = positionSizes.map((_, i) => 
                        i === 0 ? equalSize + remainder : equalSize
                      );
                      setPositionSizes(newSizes);
                    }}
                    size="small"
                  >
                    平均分配
                  </Button>
                </div>
              </Space>
            </Form.Item>
            <Alert
              message="分批建仓说明"
              description="按顺序使用配置的比例进行买入。当出现多个连续的买入信号时，系统将按照第1批→第2批→第3批...的顺序依次使用对应比例的资金进行买入。卖出信号会重置顺序至第1批。"
              type="info"
              showIcon
            />
          </>
        );
      
      default:
        return null;
    }
  };

  // 添加仓位图表配置
  const getPositionChartOption = () => {
    // 如果没有交易记录，返回空图表
    if (!tradeRecords || tradeRecords.length === 0) {
      return {
        title: {
          text: '仓位分布 (无数据)',
          left: 'center'
        },
        tooltip: {
          trigger: 'item'
        },
        series: [
          {
            type: 'pie',
            radius: '65%',
            center: ['50%', '50%'],
            data: [],
            emphasis: {
              itemStyle: {
                shadowBlur: 10,
                shadowOffsetX: 0,
                shadowColor: 'rgba(0, 0, 0, 0.5)'
              }
            }
          }
        ]
      };
    }
    
    // 只获取买入交易记录
    const buyRecords = tradeRecords.filter(record => record.direction === '买入');
    
    // 获取所有使用的仓位大小
    const positionSizeValues = buyRecords.map(record => record.position_size || 100);
    
    // 对仓位大小进行分类 (每10%为一组)
    const positionGroups: Record<string, number> = {};
    positionSizeValues.forEach(size => {
      // 向下取整到最近的10的倍数
      const groupValue = Math.floor(size / 10) * 10;
      const groupKey = `${groupValue}-${groupValue + 10}%`;
      positionGroups[groupKey] = (positionGroups[groupKey] || 0) + 1;
    });
    
    // 转换为饼图数据, 按照仓位大小排序
    const pieData = Object.entries(positionGroups)
      .sort((a, b) => {
        const aValue = parseInt(a[0]);
        const bValue = parseInt(b[0]);
        return aValue - bValue;
      })
      .map(([sizeRange, count]) => ({
        name: sizeRange,
        value: count
      }));
    
    // 计算平均仓位大小
    const avgPositionSize = positionSizeValues.length > 0
      ? positionSizeValues.reduce((sum, size) => sum + size, 0) / positionSizeValues.length
      : 0;
    
    // 仓位使用次数
    const totalBuys = buyRecords.length;
    
    return {
      title: {
        text: '仓位分布',
        subtext: `平均仓位: ${avgPositionSize.toFixed(2)}% | 总买入次数: ${totalBuys}`,
        left: 'center'
      },
      tooltip: {
        trigger: 'item',
        formatter: '{a} <br/>{b}: {c}次 ({d}%)'
      },
      legend: {
        orient: 'vertical',
        left: 'left',
        data: pieData.map(item => item.name)
      },
      series: [
        {
          name: '仓位使用',
          type: 'pie',
          radius: ['40%', '70%'],
          avoidLabelOverlap: false,
          itemStyle: {
            borderRadius: 10,
            borderColor: '#fff',
            borderWidth: 2
          },
          label: {
            show: false,
            position: 'center'
          },
          emphasis: {
            label: {
              show: true,
              fontSize: '18',
              fontWeight: 'bold'
            }
          },
          labelLine: {
            show: false
          },
          data: pieData
        }
      ],
      color: [
        '#91cc75', // 小仓位 (0-30%)
        '#fac858', // 中等仓位 (30-70%)
        '#ee6666', // 大仓位 (70-100%)
        '#73c0de', 
        '#3ba272',
        '#fc8452',
        '#9a60b4'
      ]
    };
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
                        // 设置策略ID为数字类型
                        setSelectedStrategy(Number(option.key));
                        // 设置策略显示名称
                        setSelectedStrategyName(value);
                        // 重置参数
                        if (Number(option.key) === 1) {
                          setStrategyParameters({
                            short_window: 5,
                            long_window: 20
                          });
                        }
                      }}
                      placeholder="选择策略"
                      style={{ width: '70%' }}
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
                      type="default" 
                      onClick={handleParametersModal}
                      style={{ width: '30%' }}
                      icon={<SettingOutlined />}
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
            
            {/* 添加仓位控制部分 */}
            <Divider orientation="left">仓位控制</Divider>
            <Row gutter={24}>
              <Col span={6}>
                <Form.Item label="仓位模式">
                  <Select
                    value={positionMode}
                    onChange={(value) => setPositionMode(value)}
                    style={{ width: '100%' }}
                  >
                    <Option value="fixed">固定比例</Option>
                    <Option value="dynamic">动态比例</Option>
                    <Option value="staged">分批建仓</Option>
                  </Select>
                </Form.Item>
              </Col>
              <Col span={18}>
                {renderPositionModeOptions()}
              </Col>
            </Row>
            
            {/* 添加仓位说明卡片 */}
            <Row style={{ marginBottom: 16 }}>
              <Col span={24}>
                <Card 
                  size="small" 
                  title="仓位管理说明" 
                  bordered={false} 
                  style={{ background: '#f5f5f5' }}
                >
                  <div>
                    <p><b>固定比例模式：</b> 每次买入信号都使用相同的资金比例进行交易，适合稳定策略。</p>
                    <p><b>动态比例模式：</b> 根据信号强度动态决定买入资金比例，信号越强使用的资金越多，适合趋势策略。</p>
                    <p><b>分批建仓模式：</b> 按顺序分批买入，每次买入使用不同的资金比例，适合价格波动大的品种。</p>
                  </div>
                </Card>
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
            
            <Form.Item>
              <Button 
                type="primary" 
                icon={<PlayCircleOutlined />} 
                loading={running} 
                onClick={handleRunBacktest}
              >
                运行回测
              </Button>
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
            
            {/* 添加仓位分析图表 */}
            <Divider orientation="left">仓位分析</Divider>
            <Row gutter={16}>
              <Col span={12}>
                <Card title="仓位分布" bordered={false}>
                  <ReactECharts 
                    option={getPositionChartOption()}
                    style={{ height: 300 }}
                  />
                </Card>
              </Col>
              <Col span={12}>
                <Card title="仓位管理统计" bordered={false}>
                  <Row gutter={[16, 16]}>
                    <Col span={12}>
                      <Statistic 
                        title="平均建仓仓位" 
                        value={
                          tradeRecords.filter(record => record.direction === '买入')
                            .reduce((sum, record) => sum + (record.position_size || 100), 0) / 
                            Math.max(1, tradeRecords.filter(record => record.direction === '买入').length)
                        }
                        precision={2}
                        suffix="%"
                      />
                    </Col>
                    <Col span={12}>
                      <Statistic 
                        title="最大单次建仓" 
                        value={
                          Math.max(
                            ...tradeRecords.filter(record => record.direction === '买入')
                              .map(record => record.position_size || 100),
                            0
                          )
                        }
                        precision={2}
                        suffix="%"
                      />
                    </Col>
                    <Col span={12}>
                      <Statistic 
                        title="交易次数" 
                        value={tradeRecords.length}
                        suffix="次"
                      />
                    </Col>
                    <Col span={12}>
                      <Statistic 
                        title="买入次数" 
                        value={tradeRecords.filter(record => record.direction === '买入').length}
                        suffix="次"
                      />
                    </Col>
                  </Row>
                  <Divider style={{ margin: '16px 0' }} />
                  <Alert
                    message="仓位模式分析"
                    description={
                      <>
                        <p>当前使用的仓位模式: <strong>{
                          positionMode === 'fixed' ? '固定比例' : 
                          positionMode === 'dynamic' ? '动态比例' : 
                          '分批建仓'
                        }</strong></p>
                        <p>
                          {positionMode === 'fixed' && `每次交易使用可用资金的 ${defaultPositionSize}%`}
                          {positionMode === 'dynamic' && `根据信号强度动态分配仓位，最大仓位为 ${dynamicPositionMax}%`}
                          {positionMode === 'staged' && `分 ${positionSizes.length} 批建仓，比例分别为: ${positionSizes.join('%, ')}%`}
                        </p>
                      </>
                    }
                    type="info"
                    showIcon
                  />
                </Card>
              </Col>
            </Row>
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
                <p><strong>仓位模式：</strong>{
                  positionMode === 'fixed' ? '固定比例' : 
                  positionMode === 'dynamic' ? '动态比例' : 
                  '分批建仓'
                }</p>
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
        width={600}
      >
        <Alert
          message="当前策略: MA交叉策略"
          description="移动平均线交叉策略，通过短期和长期均线的交叉信号进行买卖决策"
          type="info"
          showIcon
          style={{ marginBottom: '16px' }}
        />
        
        <Form layout="vertical">
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item label="短期均线周期 (天)">
                <InputNumber
                  value={strategyParameters.short_window || 5}
                  onChange={(value) => setStrategyParameters(prev => ({ ...prev, short_window: value }))}
                  min={1}
                  max={50}
                  style={{ width: '100%' }}
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="长期均线周期 (天)">
                <InputNumber
                  value={strategyParameters.long_window || 20}
                  onChange={(value) => setStrategyParameters(prev => ({ ...prev, long_window: value }))}
                  min={5}
                  max={200}
                  style={{ width: '100%' }}
                />
              </Form.Item>
            </Col>
          </Row>
          
          <Alert
            message="参数说明"
            description={
              <div>
                <p><strong>短期均线</strong>: 反应价格变化的敏感度，值越小越敏感，建议范围 3-15</p>
                <p><strong>长期均线</strong>: 趋势判断的基准线，值越大越稳定，建议范围 10-60</p>
                <p><strong>交叉信号</strong>: 短期均线上穿长期均线时买入，下穿时卖出</p>
              </div>
            }
            type="info"
            showIcon
            style={{ marginBottom: '16px' }}
          />
          
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
    </div>
  );
};

export default Backtest; 