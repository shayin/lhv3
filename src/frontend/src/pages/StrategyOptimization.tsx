import React, { useState, useEffect, memo, useCallback, useMemo, useRef } from 'react';
import { Card, Form, Button, Select, InputNumber, Row, Col, Typography, message, Table, Space, Modal, Input, Progress, Tag, Alert, Tabs, Statistic, Popconfirm, DatePicker, Tooltip } from 'antd';
import { PlayCircleOutlined, PlusOutlined, DeleteOutlined, SettingOutlined, EyeOutlined, ReloadOutlined, CalendarOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import axios from 'axios';
import dayjs from 'dayjs';
import { PaginationCookie } from '../utils/cookie';
import OptimizedTable from '../components/OptimizedTable';
import { useDebounce } from '../hooks/useDebounce';

const { Title, Text } = Typography;
const { Option } = Select;
const { TabPane } = Tabs;

interface Strategy {
  id: number;
  name: string;
  description?: string;
}

interface ParameterSpace {
  id?: number;
  parameter_name: string;
  parameter_type: 'int' | 'float' | 'choice';
  min_value?: number;
  max_value?: number;
  step_size?: number;
  choices?: any[];
  description?: string;
}

interface OptimizationJob {
  id: number;
  strategy_id: number;
  name: string;
  status: string;
  progress: number;
  best_score?: number;
  best_parameters?: Record<string, any>;
  optimization_config?: {
    backtest_config: {
      symbol: string;
      start_date: string;
      end_date: string;
      initial_capital: number;
    };
    parameter_spaces: any[];
    objective_function: string;
    n_trials: number;
  };
  total_trials: number;
  completed_trials: number;
  created_at: string;
  objective_function?: string;
}

const StrategyOptimization: React.FC = () => {
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [selectedStrategy, setSelectedStrategy] = useState<number | null>(null);
  const [parameterSpaces, setParameterSpaces] = useState<ParameterSpace[]>([]);
  const [optimizationJobs, setOptimizationJobs] = useState<OptimizationJob[]>([]);
  const [loading, setLoading] = useState(false);
  const initializedRef = useRef<boolean>(false);
  
  // 表单和模态框状态
  const [optimizationForm] = Form.useForm();
  const [parameterSpaceModalVisible, setParameterSpaceModalVisible] = useState(false);
  const [optimizationModalVisible, setOptimizationModalVisible] = useState(false);
  const [jobDetailModalVisible, setJobDetailModalVisible] = useState(false);
  const [selectedJob, setSelectedJob] = useState<OptimizationJob | null>(null);
  const [jobBacktestResult, setJobBacktestResult] = useState<any>(null);
  const [trialsModalVisible, setTrialsModalVisible] = useState(false);
  const [optimizationTrials, setOptimizationTrials] = useState<any[]>([]);
  
  // 股票数据范围状态
  const [stockDateRange, setStockDateRange] = useState<{min_date?: string, max_date?: string}>({});
  const [availableStocks, setAvailableStocks] = useState<{symbol: string, name: string}[]>([]);

  // 加载策略列表
  const loadStrategies = async () => {
    try {
      const response = await axios.get('/api/strategies');
      if (response.data && response.data.data) {
        setStrategies(response.data.data);
      }
    } catch (error) {
      console.error('加载策略列表失败:', error);
      message.error('加载策略列表失败');
    }
  };

  // 加载股票列表
  const loadStocks = async () => {
    try {
      const response = await axios.get('/api/data/stocks');
      if (response.data && Array.isArray(response.data)) {
        const stocks = response.data.map((stock: any) => ({
          symbol: stock.symbol,
          name: stock.name
        }));
        setAvailableStocks(stocks);
      }
    } catch (error) {
      console.error('加载股票列表失败:', error);
      // 不显示错误消息，使用默认选项
      setAvailableStocks([
        { symbol: 'AAPL', name: 'Apple Inc.' },
        { symbol: 'TSLA', name: 'Tesla Inc.' },
        { symbol: 'MSFT', name: 'Microsoft Corporation' },
        { symbol: 'GOOGL', name: 'Alphabet Inc.' },
        { symbol: 'AMZN', name: 'Amazon.com Inc.' }
      ]);
    }
  };

  // 获取股票数据范围
  const fetchStockDateRange = async (symbol: string) => {
    try {
      const response = await axios.get(`/api/data/stock/symbol/${symbol}/date-range`);
      if (response.data && response.data.status === 'success') {
        const { min_date, max_date } = response.data.data;
        setStockDateRange({ min_date, max_date });
        
        // 自动设置表单的开始和结束日期
        if (min_date && max_date) {
          optimizationForm.setFieldsValue({
            start_date: dayjs(min_date),
            end_date: dayjs(max_date)
          });
        }
      }
    } catch (error) {
      console.error('获取股票数据范围失败:', error);
      // 不显示错误消息，因为可能是新股票代码
    }
  };

  // 设置快捷时间范围
  const setQuickTimeRange = (type: 'recent1y' | 'recent3y' | 'recent5y' | 'recent6y' | 'recent7y' | 'recent8y' | 'recent9y' | 'recent10y' | 'full') => {
    const now = dayjs();
    let startDate: dayjs.Dayjs;
    let endDate: dayjs.Dayjs = now;

    switch (type) {
      case 'recent1y':
        startDate = now.subtract(1, 'year');
        break;
      case 'recent3y':
        startDate = now.subtract(3, 'year');
        break;
      case 'recent5y':
        startDate = now.subtract(5, 'year');
        break;
      case 'recent6y':
        startDate = now.subtract(6, 'year');
        break;
      case 'recent7y':
        startDate = now.subtract(7, 'year');
        break;
      case 'recent8y':
        startDate = now.subtract(8, 'year');
        break;
      case 'recent9y':
        startDate = now.subtract(9, 'year');
        break;
      case 'recent10y':
        startDate = now.subtract(10, 'year');
        break;
      case 'full':
        if (stockDateRange.min_date && stockDateRange.max_date) {
          startDate = dayjs(stockDateRange.min_date);
          endDate = dayjs(stockDateRange.max_date);
        } else {
          startDate = now.subtract(5, 'year');
        }
        break;
      default:
        startDate = now.subtract(1, 'year');
    }

    optimizationForm.setFieldsValue({
      start_date: startDate,
      end_date: endDate
    });
  };

  // 加载参数空间
  const loadParameterSpaces = async (strategyId: number) => {
    try {
      const response = await axios.get(`/api/optimization/strategies/${strategyId}/parameter-spaces`);
      if (response.data && response.data.status === 'success') {
        setParameterSpaces(response.data.data);
      }
    } catch (error) {
      console.error('加载参数空间失败:', error);
    }
  };

  // 加载优化任务
  const loadOptimizationJobs = async (strategyId?: number) => {
    try {
      const params = strategyId ? { strategy_id: strategyId } : {};
      const response = await axios.get('/api/optimization/jobs', { params });
      if (response.data && response.data.status === 'success') {
        // 数据在 response.data.data.jobs 中
        const jobs = Array.isArray(response.data.data?.jobs) ? response.data.data.jobs : [];
        setOptimizationJobs(jobs);
      } else {
        // 如果响应格式不正确，设置为空数组
        setOptimizationJobs([]);
      }
    } catch (error) {
      console.error('加载优化任务失败:', error);
      // 出错时设置为空数组，避免Table组件报错
      setOptimizationJobs([]);
    }
  };

  // 策略选择变化
  const handleStrategyChange = (strategyId: number) => {
    setSelectedStrategy(strategyId);
    loadParameterSpaces(strategyId);
    loadOptimizationJobs(strategyId);
  };

  // 添加参数空间
  const addParameterSpace = () => {
    setParameterSpaces([...parameterSpaces, {
      parameter_name: '',
      parameter_type: 'float',
      min_value: 0,
      max_value: 1,
      step_size: 0.1,
      description: ''
    }]);
  };

  // 删除参数空间
  const removeParameterSpace = (index: number) => {
    setParameterSpaces(parameterSpaces.filter((_, i) => i !== index));
  };

  // 更新参数空间
  const updateParameterSpace = (index: number, field: string, value: any) => {
    const newSpaces = [...parameterSpaces];
    newSpaces[index] = { ...newSpaces[index], [field]: value };
    setParameterSpaces(newSpaces);
  };

  // 保存参数空间
  const handleSaveParameterSpaces = async () => {
    if (!selectedStrategy) {
      message.error('请先选择策略');
      return;
    }

    try {
      setLoading(true);
      await axios.post(`/api/optimization/strategies/${selectedStrategy}/parameter-spaces`, parameterSpaces);
      message.success('参数空间保存成功');
      setParameterSpaceModalVisible(false);
    } catch (error) {
      console.error('保存参数空间失败:', error);
      message.error('保存参数空间失败');
    } finally {
      setLoading(false);
    }
  };

  // 查看其他回测试验
  const handleViewTrials = async (job: OptimizationJob) => {
    try {
      setLoading(true);
      setSelectedJob(job);
      
      console.log('🔍 开始获取试验列表:', job.name);
      const startTime = performance.now();
      
      // 优先使用轻量级摘要API
      try {
        console.log('📊 尝试获取轻量级试验摘要...');
        const response = await axios.get(`/api/optimization/jobs/${job.id}/trials-summary`);
        const endTime = performance.now();
        console.log(`✅ 轻量级试验摘要耗时: ${(endTime - startTime).toFixed(0)}ms`);
        
        if (response.data && response.data.status === 'success') {
          console.log(`📊 获取到 ${response.data.data.length} 个试验摘要`);
          setOptimizationTrials(response.data.data);
          setTrialsModalVisible(true);
          return;
        }
      } catch (summaryError) {
        console.warn('⚠️ 轻量级摘要API失败，使用完整数据:', summaryError);
      }
      
      // 如果轻量级API失败，fallback到完整数据
      console.log('📋 获取完整试验数据...');
      const fallbackStartTime = performance.now();
      const response = await axios.get(`/api/optimization/jobs/${job.id}/trials`);
      const endTime = performance.now();
      console.log(`📊 完整试验数据耗时: ${(endTime - fallbackStartTime).toFixed(0)}ms`);
      
      if (response.data && response.data.status === 'success') {
        console.log(`📊 获取到 ${response.data.data.length} 个完整试验结果`);
        setOptimizationTrials(response.data.data);
        setTrialsModalVisible(true);
      } else {
        message.error('获取试验数据失败');
      }
    } catch (error) {
      console.error('获取试验数据失败:', error);
      message.error('获取试验数据失败');
    } finally {
      setLoading(false);
    }
  };

  // 删除优化任务
  const handleDeleteJob = async (job: OptimizationJob, force: boolean = false) => {
    try {
      // 检查任务状态（非强制删除时）
      if (job.status === 'running' && !force) {
        message.error('运行中的任务不能删除，请先停止任务');
        return;
      }

      // 构建删除URL，如果是强制删除则添加force参数
      const deleteUrl = force 
        ? `/api/optimization/jobs/${job.id}?force=true`
        : `/api/optimization/jobs/${job.id}`;

      const response = await axios.delete(deleteUrl);
      
      if (response.data && response.data.status === 'success') {
        message.success(response.data.message || '删除成功');
        // 刷新任务列表
        await loadOptimizationJobs();
      } else {
        message.error('删除失败');
      }
    } catch (error: any) {
      console.error('删除优化任务失败:', error);
      const errorMessage = error.response?.data?.detail || error.message || '删除失败';
      message.error(errorMessage);
    }
  };

  // 查看任务详情
  const handleViewJobDetail = async (job: OptimizationJob) => {
    try {
    setLoading(true);
      setSelectedJob(job);
      
      console.log('🚀 开始获取任务详情:', job.name);
      const startTime = performance.now();
      
      // 如果有最佳参数和优化配置，获取对应的回测结果
      if (job.best_parameters && job.status === 'completed' && job.optimization_config) {
        // 先尝试使用轻量级API获取性能指标
        try {
          console.log('📊 尝试获取轻量级性能指标...');
          const performanceResponse = await axios.get(`/api/optimization/jobs/${job.id}/best-performance`);
          if (performanceResponse.data && performanceResponse.data.status === 'success') {
            const cacheTime = performance.now();
            console.log(`✅ 使用轻量级API，耗时: ${(cacheTime - startTime).toFixed(0)}ms`);
            
            // 构造简化的回测结果对象
            const performanceData = performanceResponse.data.data;
            const backtestResult = {
              total_return: performanceData.total_return,
              annual_return: performanceData.annual_return,
              sharpe_ratio: performanceData.sharpe_ratio,
              max_drawdown: performanceData.max_drawdown,
              win_rate: performanceData.win_rate,
              profit_factor: performanceData.profit_factor,
              alpha: performanceData.alpha,
              beta: performanceData.beta,
              total_trades: performanceData.total_trades,
              parameters: performanceData.parameters,
              // 添加标识，表明这是从优化结果获取的轻量级数据
              fromOptimization: true,
              isLightweight: true
            };
            
            setJobBacktestResult(backtestResult);
            setJobDetailModalVisible(true);
            setLoading(false);
            return;
          }
        } catch (performanceError) {
          console.warn('⚠️ 轻量级API失败，尝试完整数据:', performanceError);
        }
        
        // 如果轻量级API失败，尝试获取完整的回测数据
        try {
          console.log('📊 尝试获取完整回测结果...');
          const trialsResponse = await axios.get(`/api/optimization/jobs/${job.id}/trials`);
          if (trialsResponse.data && trialsResponse.data.status === 'success' && trialsResponse.data.data.length > 0) {
            // 获取最佳试验结果（已按得分降序排列）
            const bestTrial = trialsResponse.data.data[0];
            
            // 如果有完整的回测结果，直接使用
            if (bestTrial.backtest_results) {
              const cacheTime = performance.now();
              console.log(`✅ 使用完整缓存结果，耗时: ${(cacheTime - startTime).toFixed(0)}ms`);
              
              const backtestResult = {
                ...bestTrial.backtest_results,
                // 添加标识，表明这是从优化结果获取的
                fromOptimization: true
              };
              
              setJobBacktestResult(backtestResult);
              setJobDetailModalVisible(true);
              setLoading(false);
              return;
            } else {
              console.warn('⚠️ 最佳试验没有缓存的回测结果');
            }
          }
        } catch (trialsError) {
          console.warn('❌ 无法获取优化试验数据，将重新运行回测:', trialsError);
        }
        
        // 如果无法获取优化试验数据，则重新运行回测
        console.log('🔄 缓存未命中，重新运行回测...');
        const backtestStartTime = performance.now();
        
        const backtestConfig = job.optimization_config.backtest_config;
        
        // 使用保存的配置和最佳参数运行回测
        const backtestRequest = {
          strategy_id: job.strategy_id,
          parameters: job.best_parameters,
          symbol: backtestConfig.symbol,
          start_date: backtestConfig.start_date,
          end_date: backtestConfig.end_date,
          initial_capital: backtestConfig.initial_capital
        };
        
        console.log('📋 回测请求参数:', backtestRequest);
        
        const response = await axios.post('/api/strategies/backtest', backtestRequest);
        const backtestEndTime = performance.now();
        console.log(`⏱️ 重新回测耗时: ${(backtestEndTime - backtestStartTime).toFixed(0)}ms`);
        if (response.data && response.data.status === 'success') {
          setJobBacktestResult(response.data.data);
        } else {
          console.error('回测失败:', response.data);
          message.error('回测失败，无法获取详细结果');
        }
      } else if (job.status === 'completed') {
        message.warning('优化配置信息不完整，无法重现回测结果');
      }
      
      setJobDetailModalVisible(true);
    } catch (error) {
      console.error('获取任务详情失败:', error);
      message.error('获取任务详情失败');
    } finally {
      setLoading(false);
    }
  };

  // 启动优化任务
  const handleStartOptimization = async (values: any) => {
    if (!selectedStrategy) {
      message.error('请先选择策略');
      return;
    }

    if (parameterSpaces.length === 0) {
      message.error('请先配置参数空间');
      return;
    }

    try {
      setLoading(true);
      const request = {
        strategy_id: selectedStrategy,
        name: values.name,
        description: values.description,
        parameter_spaces: parameterSpaces,
        objective_function: values.objective_function,
        n_trials: values.n_trials,
        timeout: values.timeout,
        backtest_config: {
          symbol: values.symbol,
          start_date: values.start_date.format('YYYY-MM-DD'),
          end_date: values.end_date.format('YYYY-MM-DD'),
          initial_capital: values.initial_capital
        }
      };

      await axios.post('/api/optimization/optimize', request);
      message.success('优化任务已启动');
      setOptimizationModalVisible(false);
      optimizationForm.resetFields();
      loadOptimizationJobs(selectedStrategy);
    } catch (error) {
      console.error('启动优化任务失败:', error);
      message.error('启动优化任务失败');
    } finally {
      setLoading(false);
    }
  };

  // 优化任务表格列
  const jobColumns: ColumnsType<OptimizationJob> = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 60,
      align: 'center',
    },
    {
      title: '任务名称',
      dataIndex: 'name',
      key: 'name',
      width: 180,
      ellipsis: true,
    },
    {
      title: '策略',
      dataIndex: 'strategy_id',
      key: 'strategy',
      width: 140,
      ellipsis: {
        showTitle: false,
      },
      render: (strategyId: number) => {
        const strategy = strategies.find(s => s.id === strategyId);
        return strategy ? (
          <Tooltip title={strategy.name} placement="topLeft">
            <Tag 
              color="blue" 
              style={{ 
                margin: 0, 
                maxWidth: '120px',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
                display: 'inline-block',
                cursor: 'pointer'
              }}
            >
              {strategy.name}
            </Tag>
          </Tooltip>
        ) : (
          <Text type="secondary" style={{ fontSize: '12px' }}>未知策略</Text>
        );
      }
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 80,
      align: 'center',
      render: (status: string) => {
        const statusMap = {
          'running': { color: 'processing', text: '运行中' },
          'completed': { color: 'success', text: '已完成' },
          'failed': { color: 'error', text: '失败' },
          'cancelled': { color: 'default', text: '已取消' }
        };
        const config = statusMap[status as keyof typeof statusMap] || { color: 'default', text: status };
        return <Tag color={config.color}>{config.text}</Tag>;
      }
    },
    {
      title: '进度',
      dataIndex: 'progress',
      key: 'progress',
      width: 120,
      render: (progress: number, record: OptimizationJob) => (
        <div>
          <Progress percent={progress} size="small" />
          <Text type="secondary" style={{ fontSize: '11px' }}>
            {record.completed_trials}/{record.total_trials}
          </Text>
            </div>
      )
    },
    {
      title: '最佳得分',
      dataIndex: 'best_score',
      key: 'best_score',
      width: 100,
      align: 'center',
      render: (score: number, record: OptimizationJob) => {
        if (!score) return '-';
        const objectiveMap = {
          'sharpe_ratio': '夏普比率',
          'total_return': '总收益率',
          'annual_return': '年化收益率'
        };
        const objectiveName = objectiveMap[record.objective_function as keyof typeof objectiveMap] || '得分';
        return (
          <div>
            <div style={{ fontWeight: 'bold', color: '#1890ff' }}>{score.toFixed(4)}</div>
            <Text type="secondary" style={{ fontSize: '11px' }}>{objectiveName}</Text>
          </div>
        );
      }
    },
    {
      title: '交易配置',
      dataIndex: 'optimization_config',
      key: 'trading_config',
      width: 110,
      align: 'center',
      render: (config: any) => {
        if (!config || !config.backtest_config) return '-';
        const { symbol, initial_capital } = config.backtest_config;
        return (
          <div>
            <Tag color="green" style={{ marginBottom: '2px' }}>{symbol}</Tag>
            <div style={{ fontSize: '11px', color: '#666' }}>
              ¥{initial_capital?.toLocaleString() || 'N/A'}
            </div>
          </div>
        );
      }
    },
    {
      title: '回测时间段',
      dataIndex: 'optimization_config',
      key: 'date_range',
      width: 140,
      render: (config: any) => {
        if (!config || !config.backtest_config) return '-';
        const { start_date, end_date } = config.backtest_config;
        return (
          <div style={{ lineHeight: '1.2' }}>
            <div style={{ fontSize: '11px', color: '#666' }}>
              {start_date}
            </div>
            <div style={{ fontSize: '10px', color: '#999', margin: '2px 0' }}>至</div>
            <div style={{ fontSize: '11px', color: '#666' }}>
              {end_date}
            </div>
          </div>
        );
      }
    },
    {
      title: '最佳参数',
      dataIndex: 'best_parameters',
      key: 'best_parameters',
      width: 200,
      render: (params: Record<string, any>) => {
        if (!params) return '-';
        
        const paramEntries = Object.entries(params);
        const maxDisplay = 3; // 最多显示3个参数
        const displayParams = paramEntries.slice(0, maxDisplay);
        const remainingCount = paramEntries.length - maxDisplay;
        
        return (
          <div style={{ maxHeight: '60px', overflow: 'hidden' }}>
            {displayParams.map(([key, value]) => (
              <Tag 
                key={key} 
                color="blue" 
                style={{ 
                  marginBottom: '2px', 
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
                 key}: {typeof value === 'number' ? value.toFixed(2) : value}
              </Tag>
            ))}
            {remainingCount > 0 && (
              <Tag 
                color="default" 
                style={{ 
                  marginBottom: '2px', 
                  fontSize: '10px',
                  padding: '1px 4px',
                  lineHeight: '16px'
                }}
              >
                +{remainingCount}个
              </Tag>
            )}
          </div>
        );
      }
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 140,
      render: (time: string) => (
        <div style={{ lineHeight: '1.2' }}>
          <div style={{ fontSize: '11px' }}>{dayjs(time).format('YYYY-MM-DD')}</div>
          <div style={{ fontSize: '11px', color: '#666' }}>{dayjs(time).format('HH:mm:ss')}</div>
        </div>
      )
    },
    {
      title: '操作',
      key: 'action',
      width: 100,
      align: 'center',
      render: (_, record: OptimizationJob) => {
        // 判断是否为异常状态：运行中但创建时间超过1小时
        const isAbnormal = record.status === 'running' && 
          dayjs().diff(dayjs(record.created_at), 'hour') >= 1;
        
        return (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            <Button
              type="link"
              icon={<EyeOutlined />}
              onClick={() => handleViewJobDetail(record)}
              size="small"
              disabled={record.status !== 'completed'}
              style={{ padding: '2px 8px', height: 'auto', fontSize: '12px' }}
            >
              查看回测
            </Button>
            <Button
              type="link"
              onClick={() => handleViewTrials(record)}
              size="small"
              disabled={record.status !== 'completed'}
              style={{ color: '#1890ff', padding: '2px 8px', height: 'auto', fontSize: '12px' }}
            >
              其他回测
            </Button>
            <Popconfirm
              title="确认删除"
              description={
                isAbnormal 
                  ? `检测到异常状态，确定要删除优化任务 "${record.name}" 吗？此操作不可恢复。`
                  : `确定要删除优化任务 "${record.name}" 吗？此操作不可恢复。`
              }
              onConfirm={() => handleDeleteJob(record, isAbnormal)}
              okText="确定"
              cancelText="取消"
              disabled={record.status === 'running' && !isAbnormal}
              placement="top"
            >
              <Button 
                danger
                size="small"
                disabled={record.status === 'running' && !isAbnormal}
                icon={<DeleteOutlined />}
                style={{ 
                  padding: '2px 8px', 
                  height: 'auto', 
                  fontSize: '12px',
                  ...(isAbnormal && { borderColor: '#ff7875', color: '#ff7875' })
                }}
              >
                {isAbnormal ? '强制删除' : '删除'}
              </Button>
            </Popconfirm>
          </div>
        );
      }
    }
  ];

  useEffect(() => {
    if (!initializedRef.current) {
      initializedRef.current = true;
      loadStrategies();
      loadOptimizationJobs();
      loadStocks();
      // 自动获取默认股票AAPL的数据范围
      fetchStockDateRange('AAPL');
    }
  }, []);

  return (
    <div style={{ padding: '16px', height: '100vh', display: 'flex', flexDirection: 'column' }}>
      <Card style={{ marginBottom: '16px', flexShrink: 0 }}>
        <Title level={3} style={{ margin: '0 0 16px 0' }}>策略参数优化</Title>
        
        <Row gutter={[16, 16]} style={{ marginBottom: '24px' }}>
              <Col span={8}>
            <Select
              placeholder="选择策略"
              style={{ width: '100%' }}
              value={selectedStrategy}
              onChange={handleStrategyChange}
            >
              {strategies.map(strategy => (
                <Option key={strategy.id} value={strategy.id}>
                  {strategy.name}
                      </Option>
                    ))}
                  </Select>
              </Col>
          <Col span={16}>
            <Space>
              <Button
                icon={<SettingOutlined />}
                onClick={() => setParameterSpaceModalVisible(true)}
                disabled={!selectedStrategy}
              >
                配置参数空间
              </Button>
              <Button
                type="primary"
                icon={<PlayCircleOutlined />}
                onClick={() => setOptimizationModalVisible(true)}
                disabled={!selectedStrategy || parameterSpaces.length === 0}
              >
                启动优化
              </Button>
              <Button
                icon={<ReloadOutlined />}
                onClick={() => {
                  if (selectedStrategy) {
                    loadOptimizationJobs(selectedStrategy);
                  }
                }}
              >
                刷新
              </Button>
            </Space>
              </Col>
            </Row>
      </Card>

      <Card 
        title="优化任务列表" 
        style={{ 
          flex: 1,
          display: 'flex', 
          flexDirection: 'column',
          minHeight: 0
        }}
        styles={{ 
          body: {
            flex: 1, 
            padding: '16px', 
            display: 'flex',
            flexDirection: 'column',
            minHeight: 0
          }
        }}
      >
            <OptimizedTable
          columns={jobColumns}
          dataSource={optimizationJobs}
          rowKey="id"
          loading={loading}
          size="middle"
          scroll={{ 
            x: 1200,
            y: 'calc(100vh - 320px)'
          }}
          pagination={{
            pageSize: PaginationCookie.getPageSize(20),
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total) => `共 ${total} 条记录`,
            size: 'small',
            onChange: (page, pageSize) => {
              PaginationCookie.setCurrentPage(page);
              PaginationCookie.setPageSize(pageSize || 20);
            },
            onShowSizeChange: (current, size) => {
              PaginationCookie.setPageSize(size);
            }
          }}
          style={{ flex: 1 }}
        />
      </Card>

      {/* 参数空间配置模态框 */}
      <Modal
        title="配置参数空间"
        open={parameterSpaceModalVisible}
        onOk={handleSaveParameterSpaces}
        onCancel={() => setParameterSpaceModalVisible(false)}
        width={900}
        confirmLoading={loading}
      >
        <Alert
          message="MA交叉策略参数优化指南"
          description={
            <div>
              <p><strong>short_window</strong>: 短期移动平均线周期，建议范围 3-15天</p>
              <p><strong>long_window</strong>: 长期移动平均线周期，建议范围 10-60天</p>
              <p>注意：短期周期必须小于长期周期</p>
            </div>
          }
          type="info"
          showIcon
          style={{ marginBottom: '16px' }}
        />
        
        <div style={{ marginBottom: '16px' }}>
          <Button type="dashed" onClick={addParameterSpace} icon={<PlusOutlined />} block>
            添加参数
              </Button>
            </div>
        
        <div style={{ marginBottom: '16px' }}>
          <Space>
            <Button 
              type="link" 
              onClick={() => {
                setParameterSpaces([
                  {
                    parameter_name: 'short_window',
                    parameter_type: 'int',
                    min_value: 3,
                    max_value: 15,
                    step_size: 1,
                    description: '短期移动平均线周期'
                  },
                  {
                    parameter_name: 'long_window',
                    parameter_type: 'int',
                    min_value: 10,
                    max_value: 60,
                    step_size: 5,
                    description: '长期移动平均线周期'
                  }
                ]);
              }}
            >
              📊 使用MA策略推荐配置
            </Button>
          </Space>
        </div>
        
        {parameterSpaces.map((space, index) => (
          <Card key={index} size="small" style={{ marginBottom: '8px' }}>
            <Row gutter={[8, 8]}>
              <Col span={4}>
                <Input
                  placeholder="参数名"
                  value={space.parameter_name}
                  onChange={(e) => updateParameterSpace(index, 'parameter_name', e.target.value)}
                />
              </Col>
              <Col span={3}>
                <Select
                  value={space.parameter_type}
                  onChange={(value) => updateParameterSpace(index, 'parameter_type', value)}
                  style={{ width: '100%' }}
                >
                  <Option value="int">整数</Option>
                  <Option value="float">小数</Option>
                  <Option value="choice">选择</Option>
                  </Select>
              </Col>
              {space.parameter_type !== 'choice' && (
                <>
                  <Col span={3}>
                      <InputNumber 
                      placeholder="最小值"
                      value={space.min_value}
                      onChange={(value) => updateParameterSpace(index, 'min_value', value)}
                        style={{ width: '100%' }} 
                      />
                    </Col>
                  <Col span={3}>
                      <InputNumber 
                      placeholder="最大值"
                      value={space.max_value}
                      onChange={(value) => updateParameterSpace(index, 'max_value', value)}
                        style={{ width: '100%' }} 
                      />
                    </Col>
                </>
              )}
              <Col span={4}>
                <Input
                  placeholder="描述"
                  value={space.description}
                  onChange={(e) => updateParameterSpace(index, 'description', e.target.value)}
                />
              </Col>
              <Col span={2}>
                <Button
                  type="text"
                  danger
                  icon={<DeleteOutlined />}
                  onClick={() => removeParameterSpace(index)}
                      />
                    </Col>
                  </Row>
          </Card>
        ))}
      </Modal>

      {/* 启动优化模态框 */}
      <Modal
        title="启动参数优化"
        open={optimizationModalVisible}
        onOk={() => optimizationForm.submit()}
        onCancel={() => setOptimizationModalVisible(false)}
        width={700}
        confirmLoading={loading}
      >
        <Alert
          message="优化说明"
          description="系统将自动测试不同参数组合，找到最优的策略参数。建议先用较少试验次数快速测试。"
          type="info"
          showIcon
          style={{ marginBottom: '16px' }}
        />
        
        <Form form={optimizationForm} onFinish={handleStartOptimization} layout="vertical">
          <Form.Item name="name" label="任务名称" rules={[{ required: true, message: '请输入任务名称' }]}>
            <Input placeholder="如: MA策略优化_AAPL_20240101" />
          </Form.Item>
          
          <Form.Item name="description" label="任务描述">
            <Input.TextArea placeholder="描述此次优化的目的和预期..." rows={2} />
          </Form.Item>
          
          <Row gutter={[16, 16]}>
              <Col span={12}>
              <Form.Item name="objective_function" label="优化目标" initialValue="sharpe_ratio">
                <Select>
                  <Option value="sharpe_ratio">夏普比率 (推荐)</Option>
                  <Option value="total_return">总收益率</Option>
                  <Option value="annual_return">年化收益率</Option>
                </Select>
                </Form.Item>
              </Col>
              <Col span={12}>
              <Form.Item 
                name="n_trials" 
                label="试验次数" 
                initialValue={50}
                extra="建议: 快速测试50次，详细优化100-200次"
              >
                <InputNumber min={10} max={1000} style={{ width: '100%' }} />
                </Form.Item>
              </Col>
            </Row>
            
          <Row gutter={[16, 16]}>
              <Col span={12}>
              <Form.Item 
                name="symbol" 
                label="交易品种" 
                rules={[{ required: true, message: '请选择交易品种' }]}
                initialValue="AAPL"
              >
                <Select 
                  placeholder="选择股票代码" 
                  showSearch
                  filterOption={(input, option) =>
                    (option?.label ?? '').toLowerCase().includes(input.toLowerCase()) ||
                    (option?.value ?? '').toLowerCase().includes(input.toLowerCase())
                  }
                  onChange={(value) => {
                    if (value) {
                      fetchStockDateRange(value);
                    }
                  }}
                  options={availableStocks.map(stock => ({
                    value: stock.symbol,
                    label: `${stock.symbol} - ${stock.name}`
                  }))}
                />
                </Form.Item>
                    </Col>
              <Col span={12}>
              <Form.Item name="initial_capital" label="初始资金" initialValue={100000}>
                      <InputNumber 
                  min={1000} 
                        style={{ width: '100%' }} 
                  formatter={value => `¥ ${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
                  parser={value => value?.replace(/¥\s?|(,*)/g, '') as any}
                      />
              </Form.Item>
                    </Col>
                  </Row>
            
          {/* 快捷时间选择 */}
          <Form.Item label="快捷时间选择">
            <Space wrap>
              <Button 
                size="small" 
                icon={<CalendarOutlined />}
                onClick={() => setQuickTimeRange('recent1y')}
              >
                最近1年
              </Button>
              <Button 
                size="small" 
                icon={<CalendarOutlined />}
                onClick={() => setQuickTimeRange('recent3y')}
              >
                最近3年
              </Button>
              <Button 
                size="small" 
                icon={<CalendarOutlined />}
                onClick={() => setQuickTimeRange('recent5y')}
              >
                最近5年
              </Button>
              <Button 
                size="small" 
                icon={<CalendarOutlined />}
                onClick={() => setQuickTimeRange('recent6y')}
              >
                最近6年
              </Button>
              <Button 
                size="small" 
                icon={<CalendarOutlined />}
                onClick={() => setQuickTimeRange('recent7y')}
              >
                最近7年
              </Button>
              <Button 
                size="small" 
                icon={<CalendarOutlined />}
                onClick={() => setQuickTimeRange('recent8y')}
              >
                最近8年
              </Button>
              <Button 
                size="small" 
                icon={<CalendarOutlined />}
                onClick={() => setQuickTimeRange('recent9y')}
              >
                最近9年
              </Button>
              <Button 
                size="small" 
                icon={<CalendarOutlined />}
                onClick={() => setQuickTimeRange('recent10y')}
              >
                最近10年
              </Button>
              {stockDateRange.min_date && stockDateRange.max_date && (
                <Button 
                  size="small" 
                  icon={<CalendarOutlined />}
                  onClick={() => setQuickTimeRange('full')}
                  type="primary"
                >
                  全部数据 ({stockDateRange.min_date} ~ {stockDateRange.max_date})
                </Button>
              )}
            </Space>
          </Form.Item>

          <Row gutter={[16, 16]}>
            <Col span={12}>
              <Form.Item 
                name="start_date" 
                label="开始日期" 
                rules={[{ required: true, message: '请选择开始日期' }]}
                initialValue={dayjs('2023-01-01')}
              >
                <DatePicker 
                  style={{ width: '100%' }}
                  format="YYYY-MM-DD"
                  placeholder="选择开始日期"
                />
                </Form.Item>
              </Col>
              <Col span={12}>
              <Form.Item 
                name="end_date" 
                label="结束日期" 
                rules={[{ required: true, message: '请选择结束日期' }]}
                initialValue={dayjs('2024-12-31')}
              >
                <DatePicker 
                    style={{ width: '100%' }} 
                  format="YYYY-MM-DD"
                  placeholder="选择结束日期"
                  />
                </Form.Item>
              </Col>
            </Row>
            
          <Alert
            message="注意事项"
            description={
              <ul style={{ margin: 0, paddingLeft: '20px' }}>
                <li>确保已配置参数空间</li>
                <li>优化过程可能需要几分钟到几小时</li>
                <li>可以在任务列表中查看进度</li>
              </ul>
            }
            type="warning"
            showIcon
          />
        </Form>
      </Modal>

      {/* 任务详情模态框 */}
      <Modal
        title="优化任务详情"
        open={jobDetailModalVisible}
        onCancel={() => {
          setJobDetailModalVisible(false);
          setSelectedJob(null);
          setJobBacktestResult(null);
        }}
        footer={null}
        width={1000}
      >
        {selectedJob && (
          <div>
            <Alert
              message={`任务状态: ${selectedJob.status === 'completed' ? '已完成' : selectedJob.status}`}
              type={selectedJob.status === 'completed' ? 'success' : 'info'}
              showIcon
              style={{ marginBottom: '16px' }}
            />
            
            <Tabs defaultActiveKey="1">
              <TabPane tab="基本信息" key="1">
                <Row gutter={[16, 16]}>
                  <Col span={12}>
                    <Text strong>任务名称: </Text>
                    <Text>{selectedJob.name}</Text>
              </Col>
                  <Col span={12}>
                    <Text strong>优化目标: </Text>
                    <Text>{selectedJob.objective_function === 'sharpe_ratio' ? '夏普比率' : 
                          selectedJob.objective_function === 'total_return' ? '总收益率' : 
                          selectedJob.objective_function === 'annual_return' ? '年化收益率' : '未知'}</Text>
                  </Col>
                  <Col span={12}>
                    <Text strong>试验次数: </Text>
                    <Text>{selectedJob.completed_trials}/{selectedJob.total_trials}</Text>
                  </Col>
                  <Col span={12}>
                    <Text strong>最佳得分: </Text>
                    <Text>{selectedJob.best_score ? selectedJob.best_score.toFixed(4) : '-'}</Text>
              </Col>
            </Row>
            
                {selectedJob.optimization_config && (
                  <div style={{ marginTop: '16px' }}>
                    <Text strong>回测配置:</Text>
                    <Row gutter={[16, 8]} style={{ marginTop: '8px' }}>
                      <Col span={12}>
                        <Text type="secondary">交易品种: </Text>
                        <Tag color="green">{selectedJob.optimization_config.backtest_config.symbol}</Tag>
                      </Col>
                      <Col span={12}>
                        <Text type="secondary">初始资金: </Text>
                        <Tag color="blue">¥{selectedJob.optimization_config.backtest_config.initial_capital.toLocaleString()}</Tag>
                      </Col>
                      <Col span={12}>
                        <Text type="secondary">开始日期: </Text>
                        <Tag>{selectedJob.optimization_config.backtest_config.start_date}</Tag>
                      </Col>
                      <Col span={12}>
                        <Text type="secondary">结束日期: </Text>
                        <Tag>{selectedJob.optimization_config.backtest_config.end_date}</Tag>
                      </Col>
                    </Row>
                  </div>
                )}
                
                {selectedJob.best_parameters && (
                  <div style={{ marginTop: '16px' }}>
                    <Text strong>最优参数组合:</Text>
                    <div style={{ marginTop: '8px', maxHeight: '120px', overflowY: 'auto' }}>
                      {Object.entries(selectedJob.best_parameters).map(([key, value]) => (
                        <Tag 
                          key={key} 
                          color="blue" 
                          style={{ 
                            marginBottom: '4px', 
                            marginRight: '4px',
                            fontSize: '11px',
                            padding: '2px 6px'
                          }}
                        >
                          {key === 'short_window' ? '短期均线' : 
                           key === 'long_window' ? '长期均线' : 
                           key === 'min_reversal_points' ? '反转点数' :
                           key === 'lookback_period' ? '回望周期' :
                           key === 'min_price_change' ? '最小价格变化' :
                           key === 'signal_strength_threshold' ? '信号强度阈值' :
                           key === 'max_trading_range' ? '最大交易范围' :
                           key === 'batch_count' ? '分批次数' :
                           key === 'batch_interval' ? '分批间隔' :
                           key === 'position_size_per_batch' ? '分批仓位' :
                           key === 'stop_loss_ratio' ? '止损比例' :
                           key === 'take_profit_ratio' ? '止盈比例' :
                           key === 'rsi_oversold' ? 'RSI超卖' :
                           key === 'rsi_overbought' ? 'RSI超买' :
                           key === 'volume_threshold' ? '成交量阈值' :
                           key === 'max_extremums' ? '最大极值点' :
                           key === 'min_extremum_distance' ? '极值点距离' :
                           key}: {typeof value === 'number' ? value.toFixed(2) : value}
                        </Tag>
                      ))}
                    </div>
                  </div>
                )}
              </TabPane>
              
              <TabPane tab="回测结果" key="2">
                {jobBacktestResult ? (
                  <div>
                    <Row gutter={[16, 16]}>
                      <Col span={6}>
                        <Card size="small">
                          <Statistic
                            title="总收益率"
                            value={jobBacktestResult.total_return * 100}
                            precision={2}
                            suffix="%"
                            valueStyle={{ color: jobBacktestResult.total_return >= 0 ? '#3f8600' : '#cf1322' }}
                          />
      </Card>
                      </Col>
                      <Col span={6}>
                        <Card size="small">
                          <Statistic
                            title="年化收益率"
                            value={jobBacktestResult.annual_return * 100}
                            precision={2}
                            suffix="%"
                            valueStyle={{ color: '#3f8600' }}
                          />
                        </Card>
                      </Col>
                      <Col span={6}>
                        <Card size="small">
                          <Statistic
                            title="最大回撤"
                            value={jobBacktestResult.max_drawdown * 100}
                            precision={2}
                            suffix="%"
                            valueStyle={{ color: '#3f8600' }}
                          />
                        </Card>
                      </Col>
                      <Col span={6}>
                        <Card size="small">
                          <Statistic
                            title="夏普比率"
                            value={jobBacktestResult.sharpe_ratio}
                            precision={3}
                            valueStyle={{ color: jobBacktestResult.sharpe_ratio >= 1 ? '#3f8600' : '#cf1322' }}
                          />
      </Card>
                      </Col>
                    </Row>
                    
                    <Row gutter={[16, 16]} style={{ marginTop: '16px' }}>
                      <Col span={6}>
                        <Card size="small">
                          <Statistic
                            title="胜率"
                            value={jobBacktestResult.win_rate * 100}
                            precision={2}
                            suffix="%"
                            valueStyle={{ color: jobBacktestResult.win_rate >= 0.5 ? '#3f8600' : '#cf1322' }}
                          />
          </Card>
                      </Col>
                      <Col span={6}>
                        <Card size="small">
                          <Statistic
                            title="盈亏比"
                            value={jobBacktestResult.profit_factor}
                            precision={2}
                            valueStyle={{ color: jobBacktestResult.profit_factor >= 1 ? '#3f8600' : '#cf1322' }}
                          />
                        </Card>
                      </Col>
                      <Col span={6}>
                        <Card size="small">
                          <Statistic
                            title="交易次数"
                            value={jobBacktestResult.trades ? jobBacktestResult.trades.length : 0}
                            valueStyle={{ color: '#1890ff' }}
                          />
                        </Card>
                      </Col>
                      <Col span={6}>
                        <Card size="small">
                          <Statistic
                            title="Alpha"
                            value={jobBacktestResult.alpha}
                            precision={4}
                            valueStyle={{ color: jobBacktestResult.alpha >= 0 ? '#3f8600' : '#cf1322' }}
                          />
          </Card>
                      </Col>
                    </Row>
                    
                    <Alert
                      message="参数说明"
                      description={
                        <div>
                          <p><strong>夏普比率</strong>: 风险调整后收益，{'>'} 1.0为优秀，{'>'} 2.0为卓越</p>
                          <p><strong>胜率</strong>: 盈利交易占总交易的比例，{'>'} 50%为良好</p>
                          <p><strong>盈亏比</strong>: 平均盈利/平均亏损，{'>'} 1.0表示盈利大于亏损</p>
                          <p><strong>Alpha</strong>: 相对于市场的超额收益，{'>'} 0表示跑赢市场</p>
                        </div>
                      }
                      type="info"
                      showIcon
                      style={{ marginTop: '16px' }}
                    />
                  </div>
                ) : (
                  <div style={{ textAlign: 'center', padding: '40px' }}>
                    <Text type="secondary">加载回测结果中...</Text>
                  </div>
                )}
              </TabPane>
            </Tabs>
          </div>
        )}
      </Modal>

      {/* 试验列表模态框 */}
      <Modal
        title="所有回测试验结果"
        open={trialsModalVisible}
        onCancel={() => {
          setTrialsModalVisible(false);
          setOptimizationTrials([]);
          setSelectedJob(null);
        }}
        footer={null}
        width={1000}
      >
        {selectedJob && (
          <div>
            <Alert
              message={`任务: ${selectedJob.name} - 共${optimizationTrials.length}个试验，按得分降序排列`}
              type="info"
              showIcon
              style={{ marginBottom: '16px' }}
            />
            
            <OptimizedTable
              dataSource={optimizationTrials}
              rowKey={(record) => record.id || record.trial_number || Math.random()}
              pagination={false}
              size="small"
              scroll={{ y: 400 }}
              columns={[
                {
                  title: '排名',
                  key: 'rank',
                  width: 60,
                  render: (_, record, index) => {
                    // 如果有rank字段（轻量级API），使用它；否则使用index+1（完整API）
                    const rank = record.rank || (index + 1);
                    return (
                      <Tag color={rank === 1 ? 'gold' : rank === 2 ? 'silver' : rank === 3 ? 'orange' : 'default'}>
                        {rank}
                      </Tag>
                    );
                  }
                },
                {
                  title: '得分',
                  dataIndex: 'objective_value',
                  key: 'objective_value',
                  width: 100,
                  render: (value: number) => (
                    <Text strong style={{ color: '#1890ff' }}>
                      {value ? value.toFixed(4) : '-'}
                    </Text>
                  ),
                  sorter: (a, b) => (a.objective_value || 0) - (b.objective_value || 0),
                  defaultSortOrder: 'descend'
                },
                {
                  title: '参数组合',
                  dataIndex: 'parameters',
                  key: 'parameters',
                  width: 200,
                  render: (params: Record<string, any>) => (
                    <div>
                      {Object.entries(params || {}).map(([key, value]) => (
                        <Tag key={key} color="blue" style={{ marginBottom: '2px' }}>
                          {key === 'short_window' ? '短期' : 
                           key === 'long_window' ? '长期' : key}: {value}
                        </Tag>
                      ))}
                    </div>
                  )
                },
                {
                  title: '年化收益',
                  dataIndex: 'annual_return',
                  key: 'annual_return',
                  width: 90,
                  render: (value: number) => {
                    if (value === undefined || value === null) return '-';
                    const color = value >= 0 ? '#3f8600' : '#cf1322';
                    return (
                      <Text style={{ color, fontWeight: 'bold' }}>
                        {(value * 100).toFixed(1)}%
                      </Text>
                    );
                  }
                },
                {
                  title: '最大回撤',
                  dataIndex: 'max_drawdown',
                  key: 'max_drawdown',
                  width: 90,
                  render: (value: number) => {
                    if (value === undefined || value === null) return '-';
                    return (
                      <Text style={{ color: '#3f8600', fontWeight: 'bold' }}>
                        {(Math.abs(value) * 100).toFixed(1)}%
                      </Text>
                    );
                  }
                },
                {
                  title: '交易次数',
                  dataIndex: 'total_trades',
                  key: 'total_trades',
                  width: 80,
                  render: (value: number) => (
                    <Text type="secondary">
                      {value || 0}
                    </Text>
                  )
                },
                {
                  title: '执行时间',
                  dataIndex: 'execution_time',
                  key: 'execution_time',
                  width: 80,
                  render: (time: number) => (
                    <Text type="secondary">
                      {time ? `${(time * 1000).toFixed(0)}ms` : '-'}
                    </Text>
                  )
                },
                {
                  title: '完成时间',
                  dataIndex: 'completed_at',
                  key: 'completed_at',
                  width: 150,
                  render: (time: string) => time ? dayjs(time).format('HH:mm:ss') : '-'
                }
              ]}
            />
            
            <Alert
              message="说明"
              description={
                <div>
                  <p><strong>排名</strong>: 按优化目标得分排序，金牌为最佳结果</p>
                  <p><strong>得分</strong>: {selectedJob.objective_function === 'sharpe_ratio' ? '夏普比率' : 
                                        selectedJob.objective_function === 'total_return' ? '总收益率' : 
                                        selectedJob.objective_function === 'annual_return' ? '年化收益率' : '优化目标'}得分</p>
                  <p><strong>参数组合</strong>: 该试验使用的策略参数</p>
                </div>
              }
              type="info"
              showIcon
              style={{ marginTop: '16px' }}
            />
          </div>
        )}
      </Modal>
    </div>
  );
};

export default memo(StrategyOptimization);