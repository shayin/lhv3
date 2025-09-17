import React, { useState, useEffect, useMemo, useRef } from 'react';
import { Card, Table, Button, Space, Modal, message, Tag, Typography, Descriptions, Statistic, Row, Col, Alert, Form, Input, DatePicker, Tabs, Tooltip } from 'antd';
import { EyeOutlined, DeleteOutlined, ReloadOutlined, HistoryOutlined, SyncOutlined, LineChartOutlined, InfoCircleOutlined, ConsoleSqlOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import type { ColumnsType } from 'antd/es/table';
import axios from 'axios';
import dayjs from 'dayjs';
import ReactECharts from 'echarts-for-react';
import * as echarts from 'echarts/core';
import { LineChart } from 'echarts/charts';
import {
  TitleComponent, TooltipComponent, GridComponent, DataZoomComponent,
  ToolboxComponent, LegendComponent
} from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';

// 注册 ECharts 必要的组件
echarts.use([
  TitleComponent, TooltipComponent, GridComponent, DataZoomComponent,
  ToolboxComponent, LegendComponent, LineChart, CanvasRenderer
]);


const { Title, Text } = Typography;

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
  
  return dateStr;
};

interface BacktestRecord {
  id: number;
  name: string;
  description?: string;
  strategy_name?: string;
  start_date: string;
  end_date: string;
  initial_capital: number;
  instruments: string[];
  status: string;
  created_at: string;
  completed_at?: string;
  trade_records?: any[];  // 添加交易记录字段
  logs?: any[];  // 添加日志字段
  parameters?: any;  // 添加参数配置字段
  performance_metrics?: {
    total_return?: number;
    annual_return?: number;  // 添加年化收益率字段
    max_drawdown?: number;
    sharpe_ratio?: number;
    volatility?: number;
    win_rate?: number;
    profit_factor?: number;
  };
}

interface BacktestDetail {
  id: number;
  name: string;
  description?: string;
  strategy_info?: {
    id: number;
    name: string;
    description?: string;
    code: string;
    parameters: string;
    template?: string;
    created_at: string;
  };
  start_date: string;
  end_date: string;
  initial_capital: number;
  instruments: string[];
  parameters?: any;
  position_config?: any;
  results?: any;
  equity_curve?: any[];
  trade_records?: any[];
  performance_metrics?: any;
  status: string;
  created_at: string;
  completed_at?: string;
}

const BacktestHistory: React.FC = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [backtestList, setBacktestList] = useState<BacktestRecord[]>([]);
  const [detailModalVisible, setDetailModalVisible] = useState(false);
  const [selectedBacktest, setSelectedBacktest] = useState<BacktestDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('performance');
  const [chartKey, setChartKey] = useState(0);
  const equityChartRef = useRef<any>(null);
  const klineChartRef = useRef<any>(null);

  // 交易记录列定义 - 直接复用单次回测分析的代码
  const tradeColumns: ColumnsType<any> = [
    {
      title: '日期',
      dataIndex: 'date',
      key: 'date',
      sorter: (a, b) => {
        const dateA = new Date(a.date);
        const dateB = new Date(b.date);
        return dateA.getTime() - dateB.getTime();
      }
    },
    {
      title: '方向',
      dataIndex: 'action',
      key: 'action',
      filters: [
        { text: '买入', value: 'BUY' },
        { text: '卖出', value: 'SELL' },
      ],
      onFilter: (value, record) => record.action === value,
      render: (text) => {
        const displayText = text === 'BUY' ? '买入' : text === 'SELL' ? '卖出' : text;
        return (
          <Tag color={text === 'BUY' ? 'red' : 'green'}>
            {displayText}
          </Tag>
        );
      }
    },
    {
      title: '触发原因',
      dataIndex: 'trigger_reason',
      key: 'trigger_reason',
      width: 120,
      ellipsis: true,
      render: (text) => (
        <Tooltip title={text || '未记录'} placement="topLeft">
          <span style={{ maxWidth: 100, display: 'inline-block', overflow: 'hidden', textOverflow: 'ellipsis', verticalAlign: 'middle', whiteSpace: 'nowrap' }}>{text || '未记录'}</span>
        </Tooltip>
      )
    },
    {
      title: '期初资金',
      dataIndex: 'before_cash',
      key: 'before_cash',
      sorter: (a, b) => a.before_cash - b.before_cash,
      render: (text) => {
        const value = parseFloat(text) || 0;
        return value.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
      }
    },
    {
      title: '期末资金',
      dataIndex: 'after_cash',
      key: 'after_cash',
      sorter: (a, b) => a.after_cash - b.after_cash,
      render: (text) => {
        const value = parseFloat(text) || 0;
        return value.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
      }
    },
    {
      title: '价格',
      dataIndex: 'price',
      key: 'price',
      sorter: (a, b) => {
        const priceA = a.price || 0;
        const priceB = b.price || 0;
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
        const value = parseFloat(text) || 0;
        return value.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
      }
    },
    {
      title: '手续费',
      dataIndex: 'commission',
      key: 'commission',
      sorter: (a, b) => a.commission - b.commission,
      render: (text) => {
        const value = parseFloat(text) || 0;
        return value.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
      }
    },
    {
      title: '仓位大小',
      dataIndex: 'position_size',
      key: 'position_size',
      sorter: (a, b) => a.position_size - b.position_size,
      render: (text) => {
        const value = parseFloat(text) || 0;
        return `${(value * 100).toFixed(1)}%`;
      }
    }
  ];
  
  // 更新回测相关状态
  const [updateModalVisible, setUpdateModalVisible] = useState(false);
  const [selectedBacktestForUpdate, setSelectedBacktestForUpdate] = useState<BacktestRecord | null>(null);
  const [updateLoading, setUpdateLoading] = useState(false);
  const [updateForm] = Form.useForm();
  const [logsModalVisible, setLogsModalVisible] = useState(false);
  const [selectedLogs, setSelectedLogs] = useState<any[]>([]);

  // 获取回测列表
  const fetchBacktestList = async () => {
    setLoading(true);
    try {
      // 使用新的回测状态API
      const response = await axios.get('/api/backtest-status/list');
      setBacktestList(response.data);
    } catch (error: any) {
      console.error('获取回测列表失败:', error);
      message.error('获取回测列表失败');
    } finally {
      setLoading(false);
    }
  };

  // 获取回测详情
  const fetchBacktestDetail = async (id: number) => {
    setDetailLoading(true);
    try {
      const response = await axios.get(`/api/backtest-status/${id}`);
      if (response.data.status === 'success') {
        const backtestData = response.data.data;
        
        // 对交易记录按时间倒序排序（最新的在前面）
        if (backtestData.results && backtestData.results.trades) {
          backtestData.results.trades = backtestData.results.trades.sort((a: any, b: any) => {
            return new Date(b.date).getTime() - new Date(a.date).getTime();
          });
        }
        
        if (backtestData.trade_records) {
          backtestData.trade_records = backtestData.trade_records.sort((a: any, b: any) => {
            return new Date(b.date).getTime() - new Date(a.date).getTime();
          });
        }
        
        setSelectedBacktest(backtestData);
        setDetailModalVisible(true);
      } else {
        message.error('获取回测详情失败');
      }
    } catch (error: any) {
      console.error('获取回测详情失败:', error);
      message.error('获取回测详情失败');
    } finally {
      setDetailLoading(false);
    }
  };

  // 删除回测
  const handleDeleteBacktest = async (id: number) => {
    Modal.confirm({
      title: '确认删除',
      content: '此操作将永久删除该回测记录，是否继续？',
      okText: '确认',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        try {
          const response = await axios.delete(`/api/backtest-status/${id}`);
          if (response.data.status === 'success') {
            message.success('删除成功');
            fetchBacktestList(); // 刷新列表
          } else {
            message.error(response.data.message || '删除失败');
          }
        } catch (error: any) {
          console.error('删除回测失败:', error);
          message.error('删除失败，请重试');
        }
      },
    });
  };

  // 打开更新回测对话框
  const handleOpenUpdateModal = (record: BacktestRecord) => {
    setSelectedBacktestForUpdate(record);
    updateForm.setFieldsValue({
      new_name: record.name,
      new_description: record.description || '', // 预填充原有描述
      update_to_date: null
    });
    setUpdateModalVisible(true);
  };

  // 查看日志
  const handleViewLogs = (record: BacktestRecord) => {
    const logs = record.logs || [];
    setSelectedLogs(logs);
    setLogsModalVisible(true);
  };

  // 更新回测
  const handleUpdateBacktest = async () => {
    if (!selectedBacktestForUpdate) return;

    try {
      const values = await updateForm.validateFields();
      setUpdateLoading(true);

      const updateData = {
        new_name: values.new_name,
        new_description: values.new_description || '', // 包含描述字段
        update_to_date: values.update_to_date ? values.update_to_date.format('YYYY-MM-DD') : undefined
      };

      const response = await axios.post(`/api/backtest-status/${selectedBacktestForUpdate.id}/update`, updateData);
      
      if (response.data.status === 'success') {
        message.success('回测更新成功！');
        setUpdateModalVisible(false);
        updateForm.resetFields();
        fetchBacktestList(); // 刷新列表
        
        // 显示更新结果
        const result = response.data.data;
        Modal.success({
          title: '更新成功',
          content: (
            <div>
              <p><strong>新回测名称:</strong> {result.new_backtest_name}</p>
              <p><strong>更新日期范围:</strong> {result.update_range.start_date} 至 {result.update_range.end_date}</p>
              {result.performance_metrics && (
                <div>
                  <p><strong>性能指标:</strong></p>
                  <ul>
                    <li>总收益率: {(result.performance_metrics.total_return * 100).toFixed(2)}%</li>
                    <li>最大回撤: {(result.performance_metrics.max_drawdown * 100).toFixed(2)}%</li>
                    <li>夏普比率: {result.performance_metrics.sharpe_ratio?.toFixed(2) || 'N/A'}</li>
                  </ul>
                </div>
              )}
            </div>
          ),
          okText: '确定'
        });
      } else {
        message.error(response.data.message || '更新失败');
      }
    } catch (error: any) {
      console.error('更新回测失败:', error);
      message.error(error.response?.data?.detail || '更新失败，请重试');
    } finally {
      setUpdateLoading(false);
    }
  };

  // 表格列定义 - 优化后的版本
  const columns: ColumnsType<BacktestRecord> = [ 
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 60,
      fixed: 'left',
      align: 'center',
    },
    {
      title: '回测名称',
      dataIndex: 'name',
      key: 'name',
      width: 180,
      fixed: 'left',
      ellipsis: true,
      render: (text: string) => (
        <Tooltip title={text} placement="topLeft">
          <Text strong style={{ color: '#1890ff' }}>{text}</Text>
        </Tooltip>
      ),
    },
    {
      title: '策略',
      dataIndex: 'strategy_name',
      key: 'strategy_name',
      width: 120,
      ellipsis: true,
      render: (text: string) => (
        <Tooltip title={text || '未知策略'} placement="topLeft">
          <Tag color="blue">{text || '未知'}</Tag>
        </Tooltip>
      ),
    },
    {
      title: '自定义参数',
      key: 'parameters',
      width: 150,
      ellipsis: true,
      render: (_, record) => {
        const parameters = record.parameters;
        if (!parameters || Object.keys(parameters).length === 0) {
          return <Text style={{ color: '#999' }}>-</Text>;
        }
        
        // 提取策略参数
        const strategyParams = parameters.parameters || {};
        const paramCount = Object.keys(strategyParams).length;
        
        if (paramCount === 0) {
          return <Text style={{ color: '#999' }}>-</Text>;
        }
        
        // 显示前2个参数，超过的用省略号
        const paramEntries = Object.entries(strategyParams).slice(0, 2);
        const paramText = paramEntries.map(([key, value]) => `${key}:${value}`).join(', ');
        const displayText = paramCount > 2 ? `${paramText}...` : paramText;
        
        return (
          <Tooltip 
            title={
              <div>
                <div style={{ fontWeight: 'bold', marginBottom: '8px' }}>策略参数:</div>
                {Object.entries(strategyParams).map(([key, value]) => (
                  <div key={key} style={{ marginBottom: '4px' }}>
                    <span style={{ color: '#1890ff' }}>{key}:</span> {String(value)}
                  </div>
                ))}
                {parameters.positionConfig && (
                  <div>
                    <div style={{ fontWeight: 'bold', marginTop: '8px', marginBottom: '4px' }}>仓位配置:</div>
                    <div style={{ fontSize: '12px' }}>
                      模式: {parameters.positionConfig.mode || 'fixed'}
                    </div>
                  </div>
                )}
              </div>
            } 
            placement="topLeft"
          >
            <Text style={{ color: '#722ed1', fontSize: '12px' }}>
              {displayText}
            </Text>
          </Tooltip>
        );
      },
    },
    {
      title: '股票',
      dataIndex: 'instruments',
      key: 'instruments',
      width: 80,
      align: 'center',
      render: (instruments: string[]) => (
        <Tag color="green">{instruments.join(', ')}</Tag>
      ),
    },
    {
      title: '回测期间',
      key: 'date_range',
      width: 160,
      align: 'center',
      render: (_, record) => (
        <div style={{ fontSize: '12px', lineHeight: '1.4' }}>
          <div style={{ fontWeight: 'bold' }}>{dayjs(record.start_date).format('MM-DD')}</div>
          <div style={{ color: '#999' }}>至 {dayjs(record.end_date).format('MM-DD')}</div>
        </div>
      ),
    },
    {
      title: '初始资金',
      dataIndex: 'initial_capital',
      key: 'initial_capital',
      width: 100,
      align: 'right',
      render: (value: number) => (
        <Text style={{ fontWeight: 'bold', color: '#52c41a' }}>
          ${(value / 1000).toFixed(0)}K
        </Text>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 80,
      align: 'center',
      render: (status: string) => {
        const statusMap = {
          'running': { text: '运行中', color: 'processing' },
          'completed': { text: '已完成', color: 'success' },
          'failed': { text: '失败', color: 'error' },
        };
        const config = statusMap[status as keyof typeof statusMap] || { text: status, color: 'default' };
        return <Tag color={config.color}>{config.text}</Tag>;
      },
    },
    {
      title: '年化收益率',
      key: 'annual_return',
      width: 100,
      align: 'right',
      render: (_, record) => {
        const returnValue = record.performance_metrics?.annual_return;
        if (returnValue !== undefined) {
          const color = returnValue >= 0 ? '#52c41a' : '#ff4d4f';
          const displayValue = returnValue * 100;
          return (
            <Text style={{ color, fontWeight: 'bold' }}>
              {displayValue >= 0 ? '+' : ''}{displayValue.toFixed(1)}%
            </Text>
          );
        }
        return <Text style={{ color: '#999' }}>-</Text>;
      },
    },
    {
      title: '最大回撤',
      key: 'max_drawdown',
      width: 100,
      align: 'right',
      render: (_, record) => {
        const drawdown = record.performance_metrics?.max_drawdown;
        if (drawdown !== undefined) {
          const value = Math.floor((drawdown * 100) * 100) / 100;
          return (
            <Text style={{ color: '#ff4d4f', fontWeight: 'bold' }}>
              {value.toFixed(1)}%
            </Text>
          );
        }
        return <Text style={{ color: '#999' }}>-</Text>;
      },
    },
    {
      title: '交易次数',
      key: 'trade_count',
      width: 80,
      align: 'center',
      render: (_, record) => {
        const tradeCount = record.trade_records?.length || 0;
        return (
          <Tag color={tradeCount > 0 ? 'blue' : 'default'}>
            {tradeCount}
          </Tag>
        );
      },
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 120,
      align: 'center',
      render: (date: string) => (
        <div style={{ fontSize: '12px', lineHeight: '1.4' }}>
          <div>{dayjs(date).format('MM-DD')}</div>
          <div style={{ color: '#999' }}>{dayjs(date).format('HH:mm')}</div>
        </div>
      ),
    },
    {
      title: '操作',
      key: 'actions',
      width: 180,
      fixed: 'right',
      render: (_, record) => (
        <Space size="small">
          <Tooltip title="查看详情">
            <Button
              type="text"
              icon={<EyeOutlined />}
              onClick={() => fetchBacktestDetail(record.id)}
              size="small"
              style={{ color: '#1890ff' }}
            />
          </Tooltip>
          <Tooltip title="历史记录">
            <Button
              type="text"
              icon={<HistoryOutlined />}
              onClick={() => navigate(`/backtest-history/${record.id}`)}
              size="small"
              style={{ color: '#52c41a' }}
            />
          </Tooltip>
          <Tooltip title="更新数据">
            <Button
              type="text"
              icon={<SyncOutlined />}
              onClick={() => handleOpenUpdateModal(record)}
              size="small"
              style={{ color: '#faad14' }}
            />
          </Tooltip>
          <Tooltip title="查看日志">
            <Button
              type="text"
              icon={<ConsoleSqlOutlined />}
              onClick={() => handleViewLogs(record)}
              size="small"
              style={{ color: '#722ed1' }}
            />
          </Tooltip>
          <Tooltip title="删除">
            <Button
              type="text"
              danger
              icon={<DeleteOutlined />}
              onClick={() => handleDeleteBacktest(record.id)}
              size="small"
            />
          </Tooltip>
        </Space>
      ),
    },
  ];

  // 权益曲线图表配置
  const getEquityCurveOption = (equityCurve: any[], tradeRecords: any[], initialCapital: number) => {
    // 检查数据，确保不为空
    if (!equityCurve || equityCurve.length === 0) {
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
    const validData = equityCurve.filter(item => 
      item && item.date && item.equity !== undefined && !isNaN(Number(item.equity))
    );
    
    if (validData.length === 0) {
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
    if (tradeRecords && tradeRecords.length > 0) {
      // 遍历所有交易记录
      tradeRecords.forEach(record => {
        const dateStr = normalizeDate(record.date);
        const index = dateIndexMap.get(dateStr);
        
        if (index !== undefined) {
          // 创建交易点标记
          const point = {
            name: record.action === 'BUY' ? '买入点' : '卖出点',
            value: validData[index].equity,
            xAxis: index,
            yAxis: validData[index].equity,
            itemStyle: {
              color: record.action === 'BUY' ? '#f64034' : '#00b46a'
            }
          };
          
          if (record.action === 'BUY') {
            buyPoints.push(point);
          } else {
            sellPoints.push(point);
          }
        }
      });
    }
    
    // 计算最大回撤区间
    let maxDrawdownStartIndex = -1;
    let maxDrawdownEndIndex = -1;
    let maxDrawdownValue = 0;
    let maxDrawdownStartDate = '';
    let maxDrawdownEndDate = '';
    let maxDrawdownPeak = 0;
    let maxDrawdownBottom = 0;
    
    if (validData.length > 0) {
      // 查找最大回撤对应的区间
      let maxValue = validData[0].equity;
      let currentDrawdown = 0;
      let tempStartIndex = 0;
      
      for (let i = 1; i < validData.length; i++) {
        // 如果当前值创新高，更新最大值和起始点
        if (validData[i].equity > maxValue) {
          maxValue = validData[i].equity;
          tempStartIndex = i;
        } 
        // 计算当前回撤
        else {
          currentDrawdown = (maxValue - validData[i].equity) / maxValue * 100;
          
          // 如果找到更大的回撤，更新记录
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
      
      console.log(`最大回撤区间索引: ${maxDrawdownStartIndex} - ${maxDrawdownEndIndex}`);
      console.log(`最大回撤: ${maxDrawdownValue.toFixed(2)}%, 从 ${maxDrawdownStartDate} 到 ${maxDrawdownEndDate}`);
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
            
            // 检查是否为markArea类型，显示最大回撤信息
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
                  ((param.seriesName === '买入点' && record.action === 'BUY') || 
                   (param.seriesName === '卖出点' && record.action === 'SELL'))
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
          // 添加最大回撤区间标记
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

  // 计算移动平均线数据
  const calculateMA = (dayCount: number, data: any[]) => {
    // 检查数据有效性
    if (!data || !Array.isArray(data) || data.length === 0) {
      console.warn(`计算MA${dayCount}失败: 数据无效`);
      return [];
    }
    
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
    
    return result;
  };

  // K线图表配置 - 使用权益曲线数据中的OHLC数据
  const getKlineOption = (equityCurve: any[], tradeRecords: any[]) => {
    const title = `${selectedBacktest?.instruments?.[0] || '股票'} K线图与交易信号`;
    
    // 检查数据有效性
    if (!equityCurve || equityCurve.length === 0) {
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
          name: '价格',
          axisLabel: {
            formatter: '¥{value}'
          }
        }
      };
    }

    // 从权益曲线数据中提取K线数据
    const klineData = equityCurve.map(item => [
      item.date,
      item.open,
      item.close,
      item.low,
      item.high,
      item.volume
    ]);

    // 交易信号标记数组
    let buySignals: any[] = [];
    let sellSignals: any[] = [];
    
    // 从交易记录中提取买入和卖出信号
    if (tradeRecords && tradeRecords.length > 0) {
      // 建立日期与索引的映射
      const dateIndexMap = new Map<string, number>();
      
      // 处理K线数据的日期，创建映射
      klineData.forEach((item, index) => {
        const dateStr = normalizeDate(item[0]);
        dateIndexMap.set(dateStr, index);
      });
      
      // 过滤并处理买入信号
      const buyRecords = tradeRecords.filter(record => record.action === 'BUY');
      
      // 构建买入标记
      buySignals = buyRecords
        .map(record => {
          const dateStr = normalizeDate(record.date);
          const index = dateIndexMap.get(dateStr);
          const price = record.price || 0;
          
          if (index === undefined || price <= 0) {
            return null;
          }
          
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
      const sellRecords = tradeRecords.filter(record => record.action === 'SELL');
      
      // 构建卖出标记
      sellSignals = sellRecords
        .map(record => {
          const dateStr = normalizeDate(record.date);
          const index = dateIndexMap.get(dateStr);
          const price = record.price || 0;
          
          if (index === undefined || price <= 0) {
            return null;
          }
          
          return {
            name: '卖出',
            value: [index, price],
            xAxis: index,
            yAxis: price,
            itemStyle: {
              color: '#00b46a'
            }
          };
        })
        .filter(item => item !== null);
    }
    
    // 构建x轴数据
    const xAxisData = klineData.map(item => item[0]);
    
    // 构建交易标记系列
    let markPointData: any[] = [
      // 价格位置的小圆点标记
      ...buySignals.map(signal => ({
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
      })),
      ...sellSignals.map(signal => ({
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
      })),
      
      // K线顶部的买入标签
      ...buySignals.map(signal => {
        const xIndex = signal.value[0];
        const highPrice = klineData[xIndex][4]; // K线的第4个元素是最高价
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
        const highPrice = klineData[xIndex][4]; // K线的第4个元素是最高价
        const labelY = highPrice * 1.20; // 最高价上方20%的位置
        
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
          let result = '';
          if (Array.isArray(params)) {
            const date = params[0].axisValue;
            result = `<div style="font-weight:bold;margin-bottom:5px;color:#333;font-size:14px;">${date}</div>`;
            
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
              record.action === 'BUY' && 
              normalizeDate(record.date) === dateStr
            );
            
            // 查找卖出信号
            const sellRecord = tradeRecords.find(record => 
              record.action === 'SELL' && 
              normalizeDate(record.date) === dateStr
            );
            
            // 显示买卖信号
            if (buyRecord || sellRecord) {
              result += `<div style="margin-top:5px;border-top:1px dashed #ddd;padding-top:5px;"></div>`;
            }
            
            // 显示买入信号
            if (buyRecord) {
              const price = buyRecord.price || 0;
              const reason = buyRecord.trigger_reason || '未记录原因';
              result += `<div style="color:#f64034;font-weight:bold;margin-top:3px;">
                买入(B)：¥${price.toFixed(2)}<br/>
                原因：${reason}
              </div>`;
            }
            
            // 显示卖出信号
            if (sellRecord) {
              const price = sellRecord.price || 0;
              const reason = sellRecord.trigger_reason || '未记录原因';
              result += `<div style="color:#00b46a;font-weight:bold;margin-top:3px;">
                卖出(S)：¥${price.toFixed(2)}<br/>
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
        name: '价格',
        axisLabel: {
          formatter: '¥{value}'
        },
        scale: true,
        splitArea: {
          show: true
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

  // 渲染标签页内容 - 直接复用单次回测分析的代码
  const renderTabsItems = useMemo(() => {
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
              <ReactECharts 
                ref={equityChartRef}
                key={`equity-chart-${chartKey}`}
                option={getEquityCurveOption(
                  selectedBacktest?.equity_curve || [],
                  selectedBacktest?.results?.trades || selectedBacktest?.trade_records || [],
                  selectedBacktest?.initial_capital || 100000
                )} 
                style={{ height: 500 }} 
                notMerge={true}
                lazyUpdate={true}
                opts={{ renderer: 'canvas' }}
              />
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
                title={`${selectedBacktest?.instruments?.[0] || '股票'}交易图表`} 
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
                        const tradeRecords = selectedBacktest?.results?.trades || selectedBacktest?.trade_records || [];
                        const equityCurve = selectedBacktest?.equity_curve || [];
                        
                        if (tradeRecords.length > 0 && equityCurve.length > 0) {
                          // 创建日期映射
                          const dateIndexMap = new Map();
                          equityCurve.forEach((item, index) => {
                            const dateStr = normalizeDate(item.date);
                            dateIndexMap.set(dateStr, index);
                          });
                          
                          // 收集所有交易记录的索引
                          const tradeDateIndices: number[] = [];
                          tradeRecords.forEach((record: any) => {
                            const dateStr = normalizeDate(record.date);
                            const index = dateIndexMap.get(dateStr);
                            if (index !== undefined) {
                              tradeDateIndices.push(index);
                            }
                          });
                          
                          if (tradeDateIndices.length > 0) {
                            // 找到最小和最大索引
                            const minIndex = Math.max(0, Math.min(...tradeDateIndices) - 10);
                            const maxIndex = Math.min(equityCurve.length - 1, Math.max(...tradeDateIndices) + 10);
                            
                            // 计算百分比位置
                            const start = (minIndex / equityCurve.length) * 100;
                            const end = (maxIndex / equityCurve.length) * 100;
                            
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
                                
                                message.success(`已聚焦到交易区域，共显示 ${tradeDateIndices.length} 个交易点`);
                              }
                            }
                          } else {
                            message.info('未找到交易信号对应的K线数据点');
                          }
                        } else {
                          message.info('没有交易记录或K线数据');
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
              ref={klineChartRef}
              key={`kline-chart-${chartKey}`}
              className="kline-chart"
              option={getKlineOption(
                selectedBacktest?.equity_curve || [],
                selectedBacktest?.results?.trades || selectedBacktest?.trade_records || []
              )}
              style={{ height: 600 }}
              notMerge={true}
              lazyUpdate={true}
              opts={{ renderer: 'canvas' }}
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
            dataSource={selectedBacktest?.results?.trades || selectedBacktest?.trade_records || []}
            columns={tradeColumns}
            rowKey={(record) => `trade-${record.date}-${record.action}-${record.price}`}
            pagination={{ pageSize: 10 }}
            scroll={{ x: true }}
          />
        )
      }
    ];
  }, [selectedBacktest]);

  useEffect(() => {
    fetchBacktestList();
  }, []);

  // 处理Modal打开后的图表重新渲染
  useEffect(() => {
    if (detailModalVisible && selectedBacktest) {
      // 延迟重新渲染图表，确保Modal完全打开
      const timer = setTimeout(() => {
        // 直接调用ECharts的resize方法
        if (equityChartRef.current) {
          equityChartRef.current.getEchartsInstance().resize();
        }
        if (klineChartRef.current) {
          klineChartRef.current.getEchartsInstance().resize();
        }
        setChartKey(prev => prev + 1);
      }, 500);
      
      // 添加resize事件监听器
      const handleResize = () => {
        if (equityChartRef.current) {
          equityChartRef.current.getEchartsInstance().resize();
        }
        if (klineChartRef.current) {
          klineChartRef.current.getEchartsInstance().resize();
        }
      };
      
      window.addEventListener('resize', handleResize);
      
      return () => {
        clearTimeout(timer);
        window.removeEventListener('resize', handleResize);
      };
    }
  }, [detailModalVisible, selectedBacktest]);


  return (
    <div style={{ padding: '24px' }}>
      <style>{`
        .table-row-light {
          background-color: #fafafa;
        }
        .table-row-dark {
          background-color: #ffffff;
        }
        .ant-table-thead > tr > th {
          background-color: #f5f5f5 !important;
          font-weight: 600 !important;
          text-align: center !important;
          white-space: nowrap !important;
        }
        .ant-table-tbody > tr:hover > td {
          background-color: #e6f7ff !important;
        }
        .ant-table-tbody > tr > td {
          padding: 8px 12px !important;
          border-bottom: 1px solid #f0f0f0 !important;
        }
        .ant-table-fixed-left .ant-table-thead > tr > th,
        .ant-table-fixed-right .ant-table-thead > tr > th {
          background-color: #f5f5f5 !important;
        }
        .ant-table-fixed-left .ant-table-tbody > tr > td,
        .ant-table-fixed-right .ant-table-tbody > tr > td {
          background-color: inherit !important;
        }
      `}</style>
      <Card
        title={
          <Space>
            <HistoryOutlined />
            <span>回测历史</span>
          </Space>
        }
        extra={
          <Button
            icon={<ReloadOutlined />}
            onClick={fetchBacktestList}
            loading={loading}
          >
            刷新
          </Button>
        }
      >
        <Table
          columns={columns}
          dataSource={backtestList}
          rowKey="id"
          loading={loading}
          size="small"
          bordered
          pagination={{
            pageSize: 15,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total, range) => `第 ${range[0]}-${range[1]} 条，共 ${total} 条`,
            pageSizeOptions: ['10', '15', '20', '50'],
            size: 'small',
          }}
          scroll={{ 
            x: 1550,
            y: 'calc(100vh - 300px)'
          }}
          rowClassName={(record, index) => 
            index % 2 === 0 ? 'table-row-light' : 'table-row-dark'
          }
        />
      </Card>

      {/* 回测详情模态框 */}
      <Modal
        title="回测详情"
        open={detailModalVisible}
        onCancel={() => {
          setDetailModalVisible(false);
          setActiveTab('performance');
        }}
        footer={null}
        width={1200}
        destroyOnClose
        afterOpenChange={(open) => {
          if (open) {
            // Modal完全打开后，强制重新渲染图表
            setTimeout(() => {
              if (equityChartRef.current) {
                equityChartRef.current.getEchartsInstance().resize();
              }
              if (klineChartRef.current) {
                klineChartRef.current.getEchartsInstance().resize();
              }
            }, 100);
          }
        }}
      >
        {selectedBacktest && (
          <div>
            {/* 基本信息 */}
            <Descriptions title="基本信息" bordered column={2} style={{ marginBottom: 24 }}>
              <Descriptions.Item label="回测名称">{selectedBacktest.name}</Descriptions.Item>
              <Descriptions.Item label="策略名称">{selectedBacktest.strategy_info?.name || '-'}</Descriptions.Item>
              <Descriptions.Item label="回测期间">
                {dayjs(selectedBacktest.start_date).format('YYYY-MM-DD')} 至 {dayjs(selectedBacktest.end_date).format('YYYY-MM-DD')}
              </Descriptions.Item>
              <Descriptions.Item label="初始资金">${selectedBacktest.initial_capital.toLocaleString()}</Descriptions.Item>
              <Descriptions.Item label="交易标的">{selectedBacktest.instruments.join(', ')}</Descriptions.Item>
              <Descriptions.Item label="状态">
                <Tag color={selectedBacktest.status === 'completed' ? 'success' : 'processing'}>
                  {selectedBacktest.status === 'completed' ? '已完成' : '运行中'}
                </Tag>
              </Descriptions.Item>
            </Descriptions>

            {/* 性能指标 */}
            {selectedBacktest.performance_metrics && (
              <Card title="性能指标" style={{ marginBottom: 24 }}>
                <Row gutter={16}>
                  <Col span={6}>
                    <Statistic
                      title={<span>年化收益率 <Tooltip title="策略的年化收益率"><InfoCircleOutlined style={{ fontSize: 14, color: '#aaa' }} /></Tooltip></span>}
                      value={(selectedBacktest.performance_metrics.annual_return || 0) * 100}
                      precision={2}
                      valueStyle={{ color: '#3f8600' }}  // 年化收益率统一显示为绿色
                      suffix="%"
                    />
                  </Col>
                  <Col span={6}>
                    <Statistic
                      title={<span>最大回撤 <Tooltip title="策略的最大回撤幅度"><InfoCircleOutlined style={{ fontSize: 14, color: '#aaa' }} /></Tooltip></span>}
                      value={selectedBacktest.performance_metrics.max_drawdown * 100}
                      precision={2}
                      valueStyle={{ color: '#3f8600' }}  // 修改为绿色
                      suffix="%"
                    />
                  </Col>
                  <Col span={6}>
                    <Statistic
                      title={<span>夏普比率 <Tooltip title="风险调整后的收益指标"><InfoCircleOutlined style={{ fontSize: 14, color: '#aaa' }} /></Tooltip></span>}
                      value={selectedBacktest.performance_metrics.sharpe_ratio}
                      precision={2}
                    />
                  </Col>
                  <Col span={6}>
                    <Statistic
                      title={<span>胜率 <Tooltip title="盈利交易占总交易的比例"><InfoCircleOutlined style={{ fontSize: 14, color: '#aaa' }} /></Tooltip></span>}
                      value={selectedBacktest.performance_metrics.win_rate * 100}
                      precision={2}
                      suffix="%"
                    />
                  </Col>
                </Row>
                
                <Row gutter={16} style={{ marginTop: 24 }}>
                  <Col span={6}>
                    <Statistic
                      title={<span>盈亏比 <Tooltip title="盈亏比=所有盈利交易收益总和/所有亏损交易亏损总和"><InfoCircleOutlined style={{ fontSize: 14, color: '#aaa' }} /></Tooltip></span>}
                      value={selectedBacktest.performance_metrics.profit_factor || 0}
                      precision={2}
                    />
                  </Col>
                  <Col span={6}>
                    <Statistic
                      title={<span>Alpha <Tooltip title="Alpha=策略超越基准的年化收益，反映主动收益"><InfoCircleOutlined style={{ fontSize: 14, color: '#aaa' }} /></Tooltip></span>}
                      value={0}
                      precision={2}
                      suffix="%"
                    />
                  </Col>
                  <Col span={6}>
                    <Statistic
                      title={<span>Beta <Tooltip title="Beta=策略与基准的相关性，衡量系统性风险"><InfoCircleOutlined style={{ fontSize: 14, color: '#aaa' }} /></Tooltip></span>}
                      value={0}
                      precision={2}
                    />
                  </Col>
                  <Col span={6}>
                    <Statistic
                      title={<span>交易次数 <Tooltip title="策略在回测期间的总交易次数"><InfoCircleOutlined style={{ fontSize: 14, color: '#aaa' }} /></Tooltip></span>}
                      value={selectedBacktest.trade_records?.length || 0}
                    />
                  </Col>
                </Row>
              </Card>
            )}

            {/* 标签页内容 - 直接复用单次回测分析的代码 */}
            <Tabs defaultActiveKey="1" items={renderTabsItems} />
          </div>
        )}
      </Modal>

      {/* 更新回测对话框 */}
      <Modal
        title="更新回测数据"
        open={updateModalVisible}
        onOk={handleUpdateBacktest}
        onCancel={() => {
          setUpdateModalVisible(false);
          updateForm.resetFields();
        }}
        confirmLoading={updateLoading}
        okText="更新"
        cancelText="取消"
        width={600}
      >
        <Form
          form={updateForm}
          layout="vertical"
          style={{ marginTop: 16 }}
        >
          <Form.Item
            label="新回测名称"
            name="new_name"
            rules={[{ required: true, message: '请输入新回测名称' }]}
          >
            <Input placeholder="请输入新回测名称" />
          </Form.Item>
          
          <Form.Item
            label="更新到日期"
            name="update_to_date"
            extra="留空则自动更新到最新可用数据（通常是昨天）"
          >
            <DatePicker 
              style={{ width: '100%' }} 
              placeholder="选择更新截止日期（可选）"
              format="YYYY-MM-DD"
            />
          </Form.Item>

          <Form.Item
            label="回测描述"
            name="new_description"
            extra="可选：更新回测的描述信息"
          >
            <Input.TextArea
              placeholder="请输入回测描述（可选）"
              rows={3}
            />
          </Form.Item>

          {selectedBacktestForUpdate && (
            <Alert
              message="更新说明"
              description={
                <div>
                  <p>• 将基于原回测的配置（策略、参数、仓位配置等）重新运行回测</p>
                  <p>• 起始日期保持原回测的起始日期：{selectedBacktestForUpdate.start_date}</p>
                  <p>• 结束日期将更新到您选择的日期，如不选择则自动更新到最新可用数据</p>
                  <p>• 将创建新的回测记录，原回测记录保持不变</p>
                </div>
              }
              type="info"
              showIcon
              style={{ marginBottom: 16 }}
            />
          )}
        </Form>
      </Modal>

      {/* 日志查看模态框 */}
      <Modal
        title="策略执行日志"
        open={logsModalVisible}
        onCancel={() => setLogsModalVisible(false)}
        footer={[
          <Button key="close" onClick={() => setLogsModalVisible(false)}>
            关闭
          </Button>
        ]}
        width={800}
      >
        <div style={{ maxHeight: '500px', overflowY: 'auto' }}>
          {selectedLogs.length > 0 ? (
            <div style={{ fontFamily: 'monospace', fontSize: '12px' }}>
              {selectedLogs.map((log, index) => (
                <div
                  key={index}
                  style={{
                    marginBottom: '8px',
                    padding: '8px 12px',
                    backgroundColor: log.level === 'ERROR' ? '#fff2f0' : 
                                   log.level === 'WARNING' ? '#fffbe6' : 
                                   log.level === 'DEBUG' ? '#f6ffed' : '#fafafa',
                    border: `1px solid ${log.level === 'ERROR' ? '#ffccc7' : 
                                         log.level === 'WARNING' ? '#ffe58f' : 
                                         log.level === 'DEBUG' ? '#d9f7be' : '#d9d9d9'}`,
                    borderRadius: '4px'
                  }}
                >
                  <div style={{ 
                    color: log.level === 'ERROR' ? '#cf1322' : 
                           log.level === 'WARNING' ? '#d46b08' : 
                           log.level === 'DEBUG' ? '#52c41a' : '#595959',
                    fontWeight: 'bold',
                    marginBottom: '4px'
                  }}>
                    [{log.timestamp}] {log.level}
                  </div>
                  <div style={{ color: '#262626', whiteSpace: 'pre-wrap' }}>
                    {log.message}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div style={{ textAlign: 'center', color: '#999', padding: '40px 0' }}>
              <ConsoleSqlOutlined style={{ fontSize: '48px', marginBottom: '16px' }} />
              <div>暂无策略执行日志</div>
              <div style={{ fontSize: '12px', marginTop: '8px' }}>
                策略中可以使用 log() 函数记录执行过程
              </div>
            </div>
          )}
        </div>
      </Modal>
    </div>
  );
};

export default BacktestHistory;
