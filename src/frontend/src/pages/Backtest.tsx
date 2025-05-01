import React, { useState, useEffect } from 'react';
import { Card, Form, Button, DatePicker, Select, InputNumber, Row, Col, Divider, Typography, Tabs, Table, Statistic, Spin, message, Alert, Space, Tooltip, Modal, Tag } from 'antd';
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
  trigger_reason?: string; // 交易触发原因
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
      
      // 获取K线数据
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
            item.date, // 保留原始日期格式
            item.open,
            item.close,
            item.low,
            item.high,
            item.volume || 0
          ]);
          
          // 输出K线数据示例，用于调试
          console.log('K线数据样本:', formattedKlineData.slice(0, 3));
          
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
              if (result.equity_curve) {
                console.log('原始权益曲线数据:', JSON.stringify(result.equity_curve).substring(0, 200) + '...');
                
                // 检查数据结构，确保能处理不同格式
                let equityCurve = [];
                
                // 如果是数组格式
                if (Array.isArray(result.equity_curve)) {
                  equityCurve = result.equity_curve.map((item: any) => ({
                    date: item.date,
                    equity: parseFloat(item.equity) // 确保是数字
                  }));
                  console.log(`处理权益曲线数组，共${equityCurve.length}条数据`);
                } 
                // 如果是包含date和equity数组的对象
                else if (result.equity_curve.date && result.equity_curve.equity && 
                         Array.isArray(result.equity_curve.date) && 
                         Array.isArray(result.equity_curve.equity)) {
                  const dates = result.equity_curve.date;
                  const equities = result.equity_curve.equity;
                  const length = Math.min(dates.length, equities.length);
                  
                  for (let i = 0; i < length; i++) {
                    equityCurve.push({
                      date: dates[i],
                      equity: parseFloat(equities[i]) // 确保是数字
                    });
                  }
                  console.log(`处理权益曲线对象，共${equityCurve.length}条数据`);
                }
                
                // 数据样本展示
                if (equityCurve.length > 0) {
                  console.log('处理后的权益曲线数据样本:',
                    equityCurve.length <= 5 ? equityCurve : 
                    [equityCurve[0], '...', equityCurve[equityCurve.length-1]]);
                }
                
                setEquityCurveData(equityCurve);
              } else {
                console.log('未找到权益曲线数据');
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
                    afterEquity: afterEquity,   // 交易后总资产
                    trigger_reason: trade.trigger_reason || '未记录'  // 添加触发原因字段
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
    
    // 交易信号标记数组
    let buySignals: any[] = [];
    let sellSignals: any[] = [];
    
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
                  const [open, close, low, high] = item.value;
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
              else if (item.seriesName.startsWith('MA') && item.value !== '-') {
                const colors: {[key: string]: string} = {
                  'MA5': '#f7b500',
                  'MA10': '#2196F3',
                  'MA20': '#8067dc', 
                  'MA30': '#00b46a',
                  'MA60': '#7cb305',
                  'MA120': '#eb2f96'
                };
                const color = colors[item.seriesName] || item.color;
                const value = parseFloat(item.value).toFixed(3);
                result += `<div style="color:${color};font-weight:bold;display:inline-block;margin-right:15px;">${item.seriesName}：${value}</div>`;
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
          data: klineData.map(item => [item[1], item[2], item[3], item[4]]),
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
          data: calculateMA(5, klineData),
          smooth: true,
          lineStyle: {
            width: 1,
            color: '#f7b500'  // 参考富途的颜色
          }
        },
        {
          name: 'MA10',
          type: 'line',
          data: calculateMA(10, klineData),
          smooth: true,
          lineStyle: {
            width: 1,
            color: '#2196F3'  // 参考富途的颜色
          }
        },
        {
          name: 'MA20',
          type: 'line',
          data: calculateMA(20, klineData),
          smooth: true,
          lineStyle: {
            width: 1,
            color: '#8067dc'  // 参考富途的颜色
          }
        },
        {
          name: 'MA30',
          type: 'line',
          data: calculateMA(30, klineData),
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
      width: 200,
      ellipsis: true, // 超出部分显示省略号
      render: (text) => (
        <Tooltip title={text || '未记录'}>
          <span>{text || '未记录'}</span>
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
    console.log('生成权益曲线图表, 数据长度:', equityCurveData.length);
    
    // 检查数据，确保不为空
    if (equityCurveData.length === 0) {
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
    
    return {
      title: {
        text: '策略收益曲线',
        left: 'center'
      },
      tooltip: {
        trigger: 'axis',
        formatter: function(params: any) {
          // 处理数组类型的参数
          if (Array.isArray(params) && params.length > 0) {
            const date = params[0].axisValue;
            const value = params[0].data;
            
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
        }
      },
      legend: {
        data: ['初始资金', '策略收益', '买入点', '卖出点'],
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
          name: '初始资金',
          type: 'line',
          data: validData.map(() => initialCapital), 
          symbol: 'none',
          lineStyle: {
            width: 2,
            type: 'dashed',
            color: '#5470c6'  // 更醒目的蓝色
          },
          markArea: {
            silent: true,
            itemStyle: {
              opacity: 0.1,
              color: '#5470c6'
            },
            data: [[{
              yAxis: 0
            }, {
              yAxis: initialCapital
            }]]
          },
          markLine: {
            silent: true,
            lineStyle: {
              color: '#5470c6',
              width: 2,
              type: 'solid'
            },
            data: [{
              yAxis: initialCapital,
              label: {
                formatter: '初始资金: ¥' + initialCapital.toLocaleString(),
                position: 'start',
                distance: [0, -20], // 水平和垂直偏移
                color: '#5470c6',
                fontSize: 12,
                fontWeight: 'bold',
                backgroundColor: 'rgba(255,255,255,0.8)',
                padding: [4, 8]
              }
            }]
          },
          tooltip: {
            formatter: function(params: any) {
              return `初始资金: ¥${initialCapital.toLocaleString('zh-CN', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
            }
          }
        },
        {
          name: '策略收益',
          type: 'line',
          data: validData.map(item => item.equity),
          smooth: true,
          showSymbol: false,
          lineStyle: {
            width: 2
          },
          areaStyle: {
            opacity: 0.2
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
                symbolSize: 30,
                label: {
                  formatter: function(dataIndex: number, params: any): string {
                    return 'B';
                  },
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
                symbolSize: 30,
                label: {
                  formatter: function(dataIndex: number, params: any): string {
                    return 'S';
                  },
                  color: '#fff',
                  position: 'inside'
                }
              }))
            ],
            symbolSize: function(value: any, params: any): number {
              return 30;
            }
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
                    <ReactECharts option={getEquityCurveOption()} style={{ height: 500 }} />
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
                                    <p><strong>触发原因:</strong> {record.trigger_reason || '未记录'}</p>
                                  </div>
                                );
                                
                                Modal.info({
                                  title,
                                  content,
                                  width: 400
                                });
                              } else {
                                message.info(`未找到匹配的${directionType}交易记录，日期: ${klineDate}`);
                              }
                            }
                          }
                        }}
                      />
                    </Card>
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