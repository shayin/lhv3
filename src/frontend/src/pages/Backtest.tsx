import React, { useState, useEffect } from 'react';
import { Card, Form, Button, DatePicker, Select, InputNumber, Row, Col, Divider, Typography, Tabs, Table, Statistic, Spin, message, Alert } from 'antd';
import { LineChartOutlined, PlayCircleOutlined, DownloadOutlined, SaveOutlined, InfoCircleOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import ReactECharts from 'echarts-for-react';
import { fetchStockList, fetchDataSources as fetchDataSourcesAPI, Stock, DataSource } from '../services/apiService';
import axios from 'axios';
import moment from 'moment';
import type { Moment } from 'moment';
import 'moment/locale/zh-cn'; // 添加中文支持
import type { RangePickerProps } from 'antd/es/date-picker';
import dayjs from 'dayjs';
import type { Dayjs } from 'dayjs';

moment.locale('zh-cn'); // 设置为中文

const { RangePicker } = DatePicker;
const { Title, Paragraph } = Typography;
const { Option } = Select;
const { TabPane } = Tabs;

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
}

const Backtest: React.FC = () => {
  // 状态变量
  const [running, setRunning] = useState(false);
  const [hasResults, setHasResults] = useState(false);
  const [initialCapital, setInitialCapital] = useState(100000);
  const [commissionRate, setCommissionRate] = useState(0.15);
  const [slippage, setSlippage] = useState(0.1);
  const [stockList, setStockList] = useState<Stock[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedStrategy, setSelectedStrategy] = useState('ma_crossover');
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
  
  const handleRunBacktest = async () => {
    if (!selectedStock) {
      message.error('请选择交易品种');
      return;
    }
    
    setRunning(true);
    setHasResults(false); // 重置结果状态
    
    try {
      // 从选定的股票中获取数据源
      const stockDataSource = dataSources.find(ds => ds.id === selectedStock.source_id);
      // 默认使用 'yahoo' 如果没有找到匹配的数据源
      const dataSourceName = stockDataSource?.name || 'yahoo';
      
      // 检查是否为"用户上传"类型的数据源，这类数据源需要特殊处理
      const isUserUploadedData = dataSourceName === '用户上传' || dataSourceName.toLowerCase() === 'user_upload';
      
      // 获取表单值
      const formValues = {
        strategy_id: selectedStrategy, // 使用选定的策略
        symbol: selectedStock.symbol, // 使用选定的股票符号
        start_date: dateRange[0].format('YYYY-MM-DD'), // 开始日期
        end_date: dateRange[1].format('YYYY-MM-DD'), // 结束日期
        initial_capital: initialCapital,
        parameters: {
          short_window: 5, // 短期均线周期
          long_window: 10, // 长期均线周期
          commission_rate: commissionRate / 100, // 转换为小数
          slippage_rate: slippage / 100 // 转换为小数
        },
        data_source: isUserUploadedData ? 'local' : dataSourceName.toLowerCase() // 对于用户上传的数据，使用'local'作为数据源
      };
      
      console.log('回测参数:', formValues);
      
      // 首先获取K线数据
      const klineUrl = `/api/data/fetch?symbol=${selectedStock.symbol}&start_date=${formValues.start_date}&end_date=${formValues.end_date}&data_source=${formValues.data_source}`;
      console.log('获取K线数据URL:', klineUrl);
      
      try {
        const klineResponse = await axios.get(klineUrl);
        
        if (klineResponse.data && klineResponse.data.status === 'success') {
          const klineItems = klineResponse.data.data;
          // 如果没有K线数据，则不能进行回测
          if (!klineItems || klineItems.length === 0) {
            message.error('获取K线数据失败：数据为空');
            setRunning(false);
            return;
          }
          
          // 转换为图表需要的格式 [日期, 开盘价, 收盘价, 最低价, 最高价, 交易量]
          const formattedKlineData = klineItems.map((item: any) => [
            item.date,
            item.open,
            item.close,
            item.low,
            item.high,
            item.volume || 0
          ]);
          
          // 更新K线数据
          setKlineData(formattedKlineData);
          
          // 调用后端API执行回测
          const response = await axios.post('/api/strategies/test', formValues);
          
          if (response.data && response.data.status === 'success') {
            // 处理回测结果，更新界面
            console.log('回测成功:', response.data);
            
            // 更新回测结果数据
            const result = response.data.data;
            if (result) {
              // 更新图表数据和统计数据
              message.success('回测执行成功！');
              
              // 更新性能指标
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
              
              // 更新权益曲线
              if (result.equity_curve && result.equity_curve.length > 0) {
                const equityCurve = result.equity_curve.map((item: any) => ({
                  date: item.date,
                  equity: item.equity
                }));
                setEquityCurveData(equityCurve);
              } else {
                setEquityCurveData([]);
              }
              
              // 更新回撤数据
              if (result.drawdowns && result.drawdowns.length > 0) {
                const drawdowns = result.drawdowns.map((item: any) => ({
                  date: item.date,
                  drawdown: item.drawdown * 100 // 转换为百分比
                }));
                setDrawdownData(drawdowns);
              } else {
                setDrawdownData([]);
              }
              
              // 更新交易记录
              if (result.trades && result.trades.length > 0) {
                console.log('原始交易记录:', JSON.stringify(result.trades));
                
                // 处理交易记录
                const processedTrades: TradeRecord[] = result.trades.map((trade: any, index: number) => {
                  // 格式化交易数据
                  const isBuy = trade.action === 'BUY';
                  const price = parseFloat(trade.price) || 0;
                  const shares = parseInt(trade.shares) || 0;
                  const value = parseFloat(trade.value) || (price * shares);
                  const profit = isBuy ? 0 : (parseFloat(trade.profit) || 0);
                  
                  // 使用后端返回的收益率数据
                  // 卖出交易中，profit_percent 是以买入价为基准的百分比收益率
                  const returnPct = isBuy ? 0 : (
                    // 优先使用后端返回的收益率百分比
                    trade.profit_percent !== undefined ? parseFloat(trade.profit_percent) : 
                    // 如果没有，但有入场价，则计算
                    (trade.entry_price && parseFloat(trade.entry_price) > 0 ? 
                      (profit / (parseFloat(trade.entry_price) * shares) * 100) : 
                      // 最后尝试使用return_pct字段
                      (trade.return_pct !== undefined ? parseFloat(trade.return_pct) : 0)
                    )
                  );
                  
                  // 使用后端返回的持仓天数
                  const holdingDays = isBuy ? 0 : (parseInt(trade.holding_days) || 0);
                  
                  // 获取期初期末资金数据
                  const beforeCash = parseFloat(trade.before_cash) || 0;
                  const afterCash = parseFloat(trade.after_cash) || 0;
                  const beforeEquity = parseFloat(trade.before_equity) || 0;
                  const afterEquity = parseFloat(trade.after_equity) || 0;
                  
                  return {
                    key: `${trade.date}-${trade.action}-${index}`,
                    date: trade.date,
                    symbol: selectedStock.symbol,
                    direction: isBuy ? '买入' : '卖出',
                    entryPrice: isBuy ? price : parseFloat(trade.entry_price || '0'),
                    exitPrice: isBuy ? undefined : price,
                    shares: shares,
                    value: value,
                    profitLoss: profit,
                    returnPct: returnPct,
                    duration: holdingDays,  // 使用后端计算的持仓天数
                    beforeCash: beforeCash,  // 交易前现金
                    afterCash: afterCash,   // 交易后现金
                    beforeEquity: beforeEquity, // 交易前总资产
                    afterEquity: afterEquity   // 交易后总资产
                  };
                });
                
                console.log('处理后的交易记录:', processedTrades);
                setTradeRecords(processedTrades);
              } else {
                setTradeRecords([]);
              }
              
              setHasResults(true);
            }
          } else {
            message.error(response.data?.detail || '回测失败');
          }
        } else {
          message.error('获取K线数据失败：' + (klineResponse.data?.detail || '未知错误'));
        }
      } catch (klineError: any) {
        console.error('获取K线数据失败:', klineError);
        if (klineError.response) {
          message.error(`获取K线数据失败: ${klineError.response.data?.detail || JSON.stringify(klineError.response.data) || klineError.message}`);
        } else if (klineError.request) {
          message.error('网络错误: 获取K线数据时服务器未响应');
        } else {
          message.error(`获取K线数据错误: ${klineError.message}`);
        }
        setRunning(false);
        return;
      }
    } catch (error: any) {
      console.error('回测失败:', error);
      
      // 显示详细错误信息
      if (error.response) {
        // 服务器响应了错误
        message.error(`回测失败: ${error.response.data?.detail || JSON.stringify(error.response.data) || error.message}`);
      } else if (error.request) {
        // 请求已发送但未收到响应
        message.error(`网络错误: 服务器未响应`);
      } else {
        // 请求设置时出现问题
        message.error(`请求错误: ${error.message}`);
      }
    } finally {
      setRunning(false);
    }
  };
  
  // K线图配置
  const getKlineOption = () => {
    const title = selectedStock ? `${selectedStock.name} (${selectedStock.symbol}) K线图与交易信号` : 'K线图与交易信号';
    
    // 交易信号标记
    const buySignals: any[] = [];
    const sellSignals: any[] = [];
    
    // 从交易记录中提取买入和卖出信号
    if (tradeRecords.length > 0 && klineData.length > 0) {
      // 建立日期与索引的映射
      const dateIndexMap = new Map();
      klineData.forEach((item, index) => {
        dateIndexMap.set(item[0], index);
      });
      
      // 添加买入信号
      const buyRecords = tradeRecords.filter(record => record.direction === '买入');
      console.log('买入记录:', buyRecords);
      
      buyRecords.forEach(record => {
        const dateStr = record.date;
        const index = dateIndexMap.get(dateStr);
        console.log(`买入日期: ${dateStr}, 索引: ${index}, 价格: ${record.entryPrice}`);
        
        if (index !== undefined && record.entryPrice) {
          buySignals.push({
            name: '买入信号',
            coord: [index, record.entryPrice],
            value: record.entryPrice,
            itemStyle: {
              color: '#f5222d'
            }
          });
        }
      });
      
      // 添加卖出信号
      const sellRecords = tradeRecords.filter(record => record.direction === '卖出');
      console.log('卖出记录:', sellRecords);
      
      sellRecords.forEach(record => {
        const dateStr = record.date;
        const index = dateIndexMap.get(dateStr);
        console.log(`卖出日期: ${dateStr}, 索引: ${index}, 价格: ${record.exitPrice}`);
        
        if (index !== undefined && record.exitPrice) {
          sellSignals.push({
            name: '卖出信号',
            coord: [index, record.exitPrice],
            value: record.exitPrice,
            itemStyle: {
              color: '#52c41a'
            }
          });
        }
      });
      
      console.log('生成买入信号点:', buySignals);
      console.log('生成卖出信号点:', sellSignals);
    }
    
    return {
      title: {
        text: title,
        left: 'center'
      },
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'cross'
        },
        formatter: function(params: any) {
          // 自定义提示框内容
          let result = '';
          // 判断是否为数组
          if (Array.isArray(params)) {
            // 获取第一个项的日期作为标题
            const date = params[0].axisValue;
            result = `<div style="font-weight:bold;margin-bottom:3px;">${date}</div>`;
            
            // 遍历所有系列数据
            params.forEach((item: any) => {
              if (item.seriesName === '买入信号' || item.seriesName === '卖出信号') {
                const color = item.seriesName === '买入信号' ? '#f5222d' : '#52c41a';
                const actionName = item.seriesName === '买入信号' ? '买入' : '卖出';
                result += `<div style="color:${color};font-weight:bold;">${actionName}：${item.value[1]}</div>`;
              } else if (item.seriesName === 'K线') {
                const color = item.data[0] > item.data[1] ? '#52c41a' : '#f5222d';
                result += `<div style="color:${color};line-height:1.5;">
                  开盘：${item.data[0]}<br/>
                  收盘：${item.data[1]}<br/>
                  最低：${item.data[2]}<br/>
                  最高：${item.data[3]}<br/>
                </div>`;
              } else if (item.value !== '-') {
                result += `<div style="color:${item.color};font-weight:bold;">${item.seriesName}：${item.value}</div>`;
              }
            });
          }
          return result;
        }
      },
      legend: {
        data: ['K线', 'MA5', 'MA20', '买入信号', '卖出信号'],
        bottom: 10
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
        data: klineData.map(item => item[0]),
        scale: true,
        boundaryGap: false,
        axisLine: { onZero: false },
        splitLine: { show: false },
        splitNumber: 20,
        min: 'dataMin',
        max: 'dataMax'
      },
      yAxis: {
        scale: true,
        splitLine: { show: true },
        splitArea: { show: true }
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
          data: klineData.map(item => [item[1], item[2], item[3], item[4]]),
          itemStyle: {
            color: '#f5222d',
            color0: '#52c41a',
            borderColor: '#f5222d',
            borderColor0: '#52c41a'
          }
        },
        {
          name: 'MA5',
          type: 'line',
          data: calculateMA(5, klineData),
          smooth: true,
          lineStyle: {
            width: 1
          }
        },
        {
          name: 'MA20',
          type: 'line',
          data: calculateMA(20, klineData),
          smooth: true,
          lineStyle: {
            width: 1
          }
        },
        {
          name: '买入信号',
          type: 'effectScatter',
          coordinateSystem: 'cartesian2d',
          data: buySignals,
          symbolSize: 10,
          showEffectOn: 'render',
          rippleEffect: {
            brushType: 'stroke'
          },
          hoverAnimation: true,
          itemStyle: {
            color: '#f5222d'
          },
          zlevel: 1
        },
        {
          name: '卖出信号',
          type: 'effectScatter',
          coordinateSystem: 'cartesian2d',
          data: sellSignals,
          symbolSize: 10,
          showEffectOn: 'render',
          rippleEffect: {
            brushType: 'stroke'
          },
          hoverAnimation: true,
          itemStyle: {
            color: '#52c41a'
          },
          zlevel: 1
        },
        {
          name: '标记线',
          type: 'custom',
          renderItem: function(params: {dataIndex: number}, api: any) {
            if (params.dataIndex >= buySignals.length) return;
            
            // 绘制标记
            const point = api.coord(buySignals[params.dataIndex].coord);
            return {
              type: 'group',
              children: [{
                type: 'path',
                shape: {
                  pathData: 'M0,0 L0,-20 L5,-15 L0,-20 L-5,-15 Z',
                  x: point[0],
                  y: point[1]
                },
                style: {
                  fill: '#f5222d'
                }
              }]
            };
          },
          data: buySignals
        },
        {
          name: '标记线',
          type: 'custom',
          renderItem: function(params: {dataIndex: number}, api: any) {
            if (params.dataIndex >= sellSignals.length) return;
            
            // 绘制标记
            const point = api.coord(sellSignals[params.dataIndex].coord);
            return {
              type: 'group',
              children: [{
                type: 'path',
                shape: {
                  pathData: 'M0,0 L0,20 L5,15 L0,20 L-5,15 Z',
                  x: point[0],
                  y: point[1]
                },
                style: {
                  fill: '#52c41a'
                }
              }]
            };
          },
          data: sellSignals
        }
      ]
    };
  };

  // 计算移动平均线数据
  function calculateMA(dayCount: number, data: any[]) {
    const result = [];
    for (let i = 0; i < data.length; i++) {
      if (i < dayCount - 1) {
        result.push('-');
        continue;
      }
      let sum = 0;
      for (let j = 0; j < dayCount; j++) {
        sum += Number(data[i - j][2]); // 使用收盘价
      }
      result.push((sum / dayCount).toFixed(2));
    }
    return result;
  }
  
  const columns: ColumnsType<TradeRecord> = [
    {
      title: '日期',
      dataIndex: 'date',
      key: 'date',
      sorter: (a, b) => a.date.localeCompare(b.date),
    },
    {
      title: '品种',
      dataIndex: 'symbol',
      key: 'symbol',
    },
    {
      title: '方向',
      dataIndex: 'direction',
      key: 'direction',
      filters: [
        { text: '买入', value: '买入' },
        { text: '卖出', value: '卖出' },
      ],
      onFilter: (value, record) => record.direction.includes(value as string),
      render: (text) => {
        return text === '买入' ? 
          <span style={{ color: '#f5222d' }}>{text}</span> : 
          <span style={{ color: '#52c41a' }}>{text}</span>;
      }
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
  ];
  
  // 权益曲线图表配置
  const getEquityCurveOption = () => {
    return {
      title: {
        text: '策略收益曲线',
        left: 'center'
      },
      tooltip: {
        trigger: 'axis',
        formatter: function(params: any) {
          const date = params[0].axisValue;
          const value = params[0].data;
          return `${date}<br/>${params[0].seriesName}: ${parseFloat(value).toFixed(2)}`;
        }
      },
      legend: {
        data: ['策略收益'],
        bottom: 10
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
        data: equityCurveData.map(item => item.date)
      },
      yAxis: {
        type: 'value',
        name: '资金',
        axisLabel: {
          formatter: '¥{value}'
        }
      },
      series: [
        {
          name: '策略收益',
          type: 'line',
          data: equityCurveData.map(item => item.equity),
          smooth: true,
          showSymbol: false,
          lineStyle: {
            width: 2
          },
          areaStyle: {
            opacity: 0.2
          }
        }
      ]
    };
  };
  
  // 回撤图表配置
  const getDrawdownOption = () => {
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

  // 加载数据
  useEffect(() => {
    fetchStocks();
    fetchDataSources();
  }, []);
  
  // 获取股票列表
  const fetchStocks = async () => {
    setLoading(true);
    try {
      const stocks = await fetchStockList();
      setStockList(stocks);
      if (stocks.length > 0) {
        // 默认选择第一个股票
        setSelectedStock(stocks[0]);
      }
    } catch (error) {
      console.error('获取股票列表失败:', error);
    } finally {
      setLoading(false);
    }
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
                  <Select
                    value={selectedStrategy}
                    onChange={value => setSelectedStrategy(value)}
                    placeholder="选择策略"
                  >
                    <Option value="ma_crossover">移动平均线交叉策略</Option>
                    <Option value="rsi">RSI策略</Option>
                    <Option value="macd">MACD策略</Option>
                    <Option value="bollinger_bands">布林带策略</Option>
                  </Select>
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item label="交易品种" required>
                  <Select
                    value={selectedStock?.symbol}
                    onChange={value => {
                      const stock = stockList.find(s => s.symbol === value);
                      setSelectedStock(stock || null);
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
                  title="年化收益率"
                  value={performanceData.annualReturn}
                  precision={2}
                  valueStyle={{ color: performanceData.annualReturn >= 0 ? '#f5222d' : '#52c41a' }}
                  suffix="%"
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title="最大回撤"
                  value={Math.abs(performanceData.maxDrawdown)}
                  precision={2}
                  valueStyle={{ color: '#52c41a' }}
                  suffix="%"
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title="夏普比率"
                  value={performanceData.sharpeRatio}
                  precision={2}
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title="胜率"
                  value={performanceData.winRate}
                  precision={2}
                  suffix="%"
                />
              </Col>
            </Row>
            
            <Row gutter={16} style={{ marginTop: 24 }}>
              <Col span={6}>
                <Statistic
                  title="盈亏比"
                  value={performanceData.profitFactor || 0}
                  precision={2}
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title="Alpha"
                  value={performanceData.alpha || 0}
                  precision={2}
                  suffix="%"
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title="Beta"
                  value={performanceData.beta || 0}
                  precision={2}
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title="交易次数"
                  value={tradeRecords.length}
                />
              </Col>
            </Row>
            
            <Divider />
            
            <Tabs defaultActiveKey="1">
              <TabPane
                tab={
                  <span>
                    <LineChartOutlined />
                    绩效分析
                  </span>
                } 
                key="1"
              >
                <Row gutter={16}>
                  <Col span={24} style={{ marginBottom: 16 }}>
                    <ReactECharts option={getEquityCurveOption()} style={{ height: 350 }} />
                  </Col>
                </Row>
                <Row gutter={16}>
                  <Col span={12}>
                    <ReactECharts option={getDrawdownOption()} style={{ height: 350 }} />
                  </Col>
                </Row>
              </TabPane>
              
              <TabPane
                tab={
                  <span>
                    <LineChartOutlined />
                    K线与交易信号
                  </span>
                } 
                key="3"
              >
                <Row gutter={16}>
                  <Col span={24}>
                    <ReactECharts option={getKlineOption()} style={{ height: 600 }} />
                  </Col>
                </Row>
              </TabPane>
              
              <TabPane 
                tab={
                  <span>
                    <InfoCircleOutlined />
                    交易明细
                  </span>
                } 
                key="2"
              >
                <Table
                  dataSource={tradeRecords}
                  columns={columns}
                  pagination={{ pageSize: 10 }}
                  scroll={{ x: true }}
                />
              </TabPane>
            </Tabs>
            
            <div style={{ textAlign: 'right', marginTop: 16 }}>
              <Button icon={<DownloadOutlined />} style={{ marginRight: 8 }}>
                导出报告
              </Button>
              <Button icon={<SaveOutlined />} type="primary">
                保存回测
              </Button>
            </div>
          </Card>
        </>
      )}
    </div>
  );
};

export default Backtest; 