import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Card, Form, Button, DatePicker, Select, InputNumber, Row, Col, Divider, Typography, Tabs, Table, Statistic, Spin, Alert, Space, Tooltip, Modal, Tag, App, Input } from 'antd';
import { useNavigate } from 'react-router-dom';
import { LineChartOutlined, PlayCircleOutlined, DownloadOutlined, SaveOutlined, InfoCircleOutlined, SettingOutlined } from '@ant-design/icons';
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
  cumulative_position_ratio?: number; // 累计仓位比例
  total_shares?: number; // 累计持股数量
  available_capital?: number; // 交易后的可用资金
  allocated_capital?: number; // 已分配的资金
}

const Backtest: React.FC = () => {
  const navigate = useNavigate();
  const { message } = App.useApp();
  
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
          onOk() {
            navigate('/backtest-history');
          },
        });
      }
    } catch (error) {
      console.error('保存回测失败:', error);
      message.error('保存回测失败');
    } finally {
      setSaveLoading(false);
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
        message.success(`已自动设置回测周期：${dateRange.first_date} 至 ${dateRange.last_date}`);
      }
    } catch (error) {
      console.error('获取股票日期范围失败:', error);
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

  // 初始化数据
  useEffect(() => {
    const initializeData = async () => {
      if (initializedRef.current) return;
      initializedRef.current = true;
      
      try {
        // 获取策略列表
        const strategies = await getStrategies();
        setStrategiesList(strategies);
        
        // 获取数据源列表
        const sources = await fetchDataSourcesAPI();
        setDataSources(sources);
        
        // 获取股票列表
        await fetchStocks();
        
        // 加载默认策略的参数空间
        if (strategies.length > 0) {
          const defaultStrategy = strategies.find(s => s.id === selectedStrategy) || strategies[0];
          setSelectedStrategy(defaultStrategy.id);
          setSelectedStrategyName(defaultStrategy.name);
          setCurrentStrategyInfo(defaultStrategy);
          await loadParameterSpaces(defaultStrategy.id);
        }
      } catch (error) {
        console.error('初始化数据失败:', error);
        message.error('初始化数据失败，请刷新页面重试');
      }
    };

    initializeData();
  }, []);

  // 监听策略变化，重新加载参数空间
  useEffect(() => {
    if (strategiesList.length > 0 && selectedStrategy) {
      loadParameterSpaces(selectedStrategy);
    }
  }, [strategiesList, selectedStrategy]);

  // 运行回测
  const handleRunBacktest = useCallback(async () => {
    if (!selectedStrategy || !selectedStock || !dateRange[0] || !dateRange[1]) {
      message.error('请选择策略、交易品种和回测周期');
      return;
    }

    setLoading(true);
    setBacktestResults(null);
    setHasResults(false); // 重置结果状态
    
    try {
      const startDate = dateRange[0].format('YYYY-MM-DD');
      const endDate = dateRange[1].format('YYYY-MM-DD');
      
      // 使用新的backtestStrategy方法进行回测，确保传入数字类型的策略ID
      const result = await backtestStrategy(
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
        message.error(`回测失败: ${result.error}`);
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
        console.warn('回测结果中没有trades数据');
        result.trades = [];
      }
      
      // 确保equity_curve数组存在
      if (!result.equity_curve) {
        console.warn('回测结果中没有equity_curve数据');
        result.equity_curve = [];
      }
      
      // 确保drawdowns数组存在
      if (!result.drawdowns) {
        console.warn('回测结果中没有drawdowns数据');
        result.drawdowns = [];
      }
      
      // 保存回测结果
      setBacktestResults(result);
      setHasResults(true);
      
      // 处理交易记录
      const processedTrades = result.trades.map((trade: any, index: number) => ({
        key: `${trade.date}-${index}`,
        date: trade.date,
        symbol: trade.symbol,
        direction: trade.direction,
        entryPrice: trade.entry_price,
        exitPrice: trade.exit_price,
        shares: trade.shares,
        value: trade.value,
        profitLoss: trade.profit_loss || 0,
        returnPct: trade.return_pct || 0,
        duration: trade.duration || 0,
        beforeCash: trade.before_cash || 0,
        afterCash: trade.after_cash || 0,
        beforeEquity: trade.before_equity || 0,
        afterEquity: trade.after_equity || 0,
        trigger_reason: trade.trigger_reason || '',
        position_size: trade.position_size || 100,
        cumulative_position_ratio: trade.cumulative_position_ratio || 0,
        total_shares: trade.total_shares || 0,
        available_capital: trade.available_capital || 0,
        allocated_capital: trade.allocated_capital || 0
      }));
      
      setTradeRecords(processedTrades);
      
      // 处理资产曲线数据
      const processedEquity = result.equity_curve.map((point: any) => ({
        date: point.date,
        value: point.value,
        benchmark: point.benchmark || point.value // 如果没有基准，使用策略值
      }));
      
      setEquityCurveData(processedEquity);
      
      // 处理回撤数据
      const processedDrawdowns = result.drawdowns.map((point: any) => ({
        date: point.date,
        drawdown: point.drawdown
      }));
      
      setDrawdownData(processedDrawdowns);
      
      // 处理性能指标
      setPerformanceData({
        totalReturn: result.total_return || 0,
        annualReturn: result.annual_return || 0,
        sharpeRatio: result.sharpe_ratio || 0,
        maxDrawdown: result.max_drawdown || 0,
        winRate: result.win_rate || 0,
        profitFactor: result.profit_factor || 0,
        alpha: result.alpha || 0,
        beta: result.beta || 0
      });
      
      // 滚动到结果区域
      setTimeout(() => {
        if (resultsRef.current) {
          resultsRef.current.scrollIntoView({ behavior: 'smooth' });
        }
      }, 100);
      
    } catch (error) {
      console.error('回测失败:', error);
      message.error('回测失败，请检查参数设置');
    } finally {
      setLoading(false);
    }
  }, [selectedStrategy, selectedStock, dateRange, initialCapital, commissionRate, slippage, strategyParameters]);

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
                  <Space.Compact style={{ width: '100%' }}>
                    <Select
                      value={selectedStrategyName}
                      onChange={(value, option: any) => {
                        handleStrategyChange(Number(option.key));
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
                  </Space.Compact>
                </Form.Item>
              </Col>
              
              <Col span={8}>
                <Form.Item label="交易品种" required>
                  <Select
                    value={selectedStock?.symbol}
                    onChange={(symbol) => {
                      const stock = stockList.find(s => s.symbol === symbol);
                      if (stock) {
                        handleStockSelection(stock);
                      }
                    }}
                    placeholder="选择交易品种"
                    showSearch
                    filterOption={(input, option) =>
                      (option?.children as unknown as string)?.toLowerCase().includes(input.toLowerCase())
                    }
                  >
                    {stockList.map(stock => (
                      <Option key={stock.symbol} value={stock.symbol}>
                        {stock.symbol} - {stock.name}
                      </Option>
                    ))}
                  </Select>
                </Form.Item>
              </Col>
              
              <Col span={8}>
                <Form.Item label="回测周期" required>
                  <RangePicker
                    value={dateRange}
                    onChange={(dates) => {
                      if (dates && dates[0] && dates[1]) {
                        setDateRange([dates[0], dates[1]]);
                      }
                    }}
                    format="YYYY-MM-DD"
                    style={{ width: '100%' }}
                  />
                </Form.Item>
              </Col>
            </Row>
            
            <Row gutter={24}>
              <Col span={6}>
                <Form.Item label="初始资金($)">
                  <InputNumber 
                    value={initialCapital} 
                    onChange={value => setInitialCapital(Number(value) || 100000)} 
                    min={1000} 
                    max={10000000} 
                    step={1000} 
                    style={{ width: '100%' }} 
                  />
                </Form.Item>
              </Col>
              <Col span={6}>
                <Form.Item label="手续费(%)">
                  <InputNumber 
                    value={commissionRate} 
                    onChange={value => setCommissionRate(Number(value) || 0.15)} 
                    min={0} 
                    max={5} 
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
          <div ref={resultsRef}>
            <Divider />
            <Title level={3}>回测结果</Title>
            
            <Row gutter={16} style={{ marginBottom: 24 }}>
              <Col span={6}>
                <Statistic
                  title={<span>总收益率 <Tooltip title="策略在回测期间的总收益率"><InfoCircleOutlined style={{ fontSize: 14, color: '#aaa' }} /></Tooltip></span>}
                  value={performanceData.totalReturn}
                  precision={2}
                  suffix="%"
                  valueStyle={{ color: performanceData.totalReturn >= 0 ? '#3f8600' : '#cf1322' }}
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title={<span>年化收益率 <Tooltip title="策略的年化收益率"><InfoCircleOutlined style={{ fontSize: 14, color: '#aaa' }} /></Tooltip></span>}
                  value={performanceData.annualReturn}
                  precision={2}
                  suffix="%"
                  valueStyle={{ color: performanceData.annualReturn >= 0 ? '#3f8600' : '#cf1322' }}
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title={<span>夏普比率 <Tooltip title="衡量策略风险调整后收益的指标，越高越好"><InfoCircleOutlined style={{ fontSize: 14, color: '#aaa' }} /></Tooltip></span>}
                  value={performanceData.sharpeRatio}
                  precision={2}
                  valueStyle={{ color: performanceData.sharpeRatio >= 1 ? '#3f8600' : performanceData.sharpeRatio >= 0 ? '#faad14' : '#cf1322' }}
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title={<span>最大回撤 <Tooltip title="策略在回测期间的最大回撤幅度"><InfoCircleOutlined style={{ fontSize: 14, color: '#aaa' }} /></Tooltip></span>}
                  value={Math.abs(performanceData.maxDrawdown)}
                  precision={2}
                  suffix="%"
                  valueStyle={{ color: '#cf1322' }}
                />
              </Col>
            </Row>
            
            <Row gutter={16} style={{ marginBottom: 24 }}>
              <Col span={6}>
                <Statistic
                  title={<span>胜率 <Tooltip title="盈利交易占总交易次数的比例"><InfoCircleOutlined style={{ fontSize: 14, color: '#aaa' }} /></Tooltip></span>}
                  value={performanceData.winRate}
                  precision={2}
                  suffix="%"
                  valueStyle={{ color: performanceData.winRate >= 50 ? '#3f8600' : '#cf1322' }}
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title={<span>盈亏比 <Tooltip title="平均盈利与平均亏损的比值"><InfoCircleOutlined style={{ fontSize: 14, color: '#aaa' }} /></Tooltip></span>}
                  value={performanceData.profitFactor}
                  precision={2}
                  valueStyle={{ color: performanceData.profitFactor >= 1 ? '#3f8600' : '#cf1322' }}
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title={<span>Alpha <Tooltip title="策略相对于基准的超额收益"><InfoCircleOutlined style={{ fontSize: 14, color: '#aaa' }} /></Tooltip></span>}
                  value={performanceData.alpha}
                  precision={2}
                  suffix="%"
                  valueStyle={{ color: performanceData.alpha >= 0 ? '#3f8600' : '#cf1322' }}
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title={<span>交易次数 <Tooltip title="策略在回测期间的总交易次数"><InfoCircleOutlined style={{ fontSize: 14, color: '#aaa' }} /></Tooltip></span>}
                  value={tradeRecords.length}
                />
              </Col>
            </Row>
            
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
          </div>
        </>
      )}

      {/* 保存回测模态框 */}
      <Modal
        title="保存回测结果"
        open={saveModalVisible}
        onOk={handleSaveBacktest}
        onCancel={() => setSaveModalVisible(false)}
        confirmLoading={saveLoading}
        width={600}
      >
        <Form layout="vertical">
          <Form.Item label="回测名称" required>
            <Input
              value={backtestName}
              onChange={(e) => setBacktestName(e.target.value)}
              placeholder="请输入回测名称"
            />
          </Form.Item>
          <Form.Item label="回测描述">
            <Input.TextArea
              value={backtestDescription}
              onChange={(e) => setBacktestDescription(e.target.value)}
              placeholder="请输入回测描述（可选）"
              rows={3}
            />
          </Form.Item>
          <Alert
            message="回测信息预览"
            description={
              <div>
                <p><strong>策略：</strong>{selectedStrategyName}</p>
                <p><strong>交易品种：</strong>{selectedStock?.symbol}</p>
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
    </div>
  );
};

export default Backtest;