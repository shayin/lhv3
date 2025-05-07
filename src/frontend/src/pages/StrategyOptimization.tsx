import React, { useState, useEffect } from 'react';
import { Card, Form, Button, DatePicker, Select, InputNumber, Row, Col, Divider, Typography, Tabs, Table, Slider, Space, Tag, Spin } from 'antd';
import { SettingOutlined, PlayCircleOutlined, LineChartOutlined, SyncOutlined, SaveOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import ReactECharts from 'echarts-for-react';
import { fetchStockList, Stock } from '../services/apiService';

const { Title, Paragraph } = Typography;
const { Option } = Select;

interface OptimizationResult {
  key: string;
  shortPeriod: number;
  longPeriod: number;
  annualReturn: number;
  maxDrawdown: number;
  sharpeRatio: number;
  winRate: number;
  tradeCount: number;
}

const StrategyOptimization: React.FC = () => {
  const [running, setRunning] = useState(false);
  const [hasResults, setHasResults] = useState(false);
  const [stockList, setStockList] = useState<Stock[]>([]);
  const [loading, setLoading] = useState(false);
  
  const handleRunOptimization = () => {
    setRunning(true);
    // 模拟优化过程
    setTimeout(() => {
      setRunning(false);
      setHasResults(true);
    }, 3000);
  };
  
  // 示例优化结果
  const optimizationResults: OptimizationResult[] = [
    {
      key: '1',
      shortPeriod: 10,
      longPeriod: 30,
      annualReturn: 15.6,
      maxDrawdown: 13.2,
      sharpeRatio: 1.52,
      winRate: 62.5,
      tradeCount: 48
    },
    {
      key: '2',
      shortPeriod: 15,
      longPeriod: 45,
      annualReturn: 18.3,
      maxDrawdown: 12.8,
      sharpeRatio: 1.76,
      winRate: 64.8,
      tradeCount: 42
    },
    {
      key: '3',
      shortPeriod: 20,
      longPeriod: 60,
      annualReturn: 21.2,
      maxDrawdown: 11.5,
      sharpeRatio: 2.03,
      winRate: 68.2,
      tradeCount: 36
    },
    {
      key: '4',
      shortPeriod: 25,
      longPeriod: 75,
      annualReturn: 17.8,
      maxDrawdown: 13.1,
      sharpeRatio: 1.62,
      winRate: 63.1,
      tradeCount: 32
    },
    {
      key: '5',
      shortPeriod: 12,
      longPeriod: 36,
      annualReturn: 16.9,
      maxDrawdown: 12.4,
      sharpeRatio: 1.64,
      winRate: 63.8,
      tradeCount: 45
    },
    {
      key: '6',
      shortPeriod: 18,
      longPeriod: 54,
      annualReturn: 19.5,
      maxDrawdown: 11.9,
      sharpeRatio: 1.88,
      winRate: 66.5,
      tradeCount: 38
    },
    {
      key: '7',
      shortPeriod: 22,
      longPeriod: 66,
      annualReturn: 20.1,
      maxDrawdown: 11.7,
      sharpeRatio: 1.94,
      winRate: 67.2,
      tradeCount: 34
    },
  ];
  
  const columns: ColumnsType<OptimizationResult> = [
    {
      title: 'Short Period',
      dataIndex: 'shortPeriod',
      key: 'shortPeriod',
      sorter: (a, b) => a.shortPeriod - b.shortPeriod,
    },
    {
      title: 'Long Period',
      dataIndex: 'longPeriod',
      key: 'longPeriod',
      sorter: (a, b) => a.longPeriod - b.longPeriod,
    },
    {
      title: 'Annual Return (%)',
      dataIndex: 'annualReturn',
      key: 'annualReturn',
      sorter: (a, b) => a.annualReturn - b.annualReturn,
      render: (text) => <span style={{ color: '#f5222d' }}>{text.toFixed(2)}%</span>,
      defaultSortOrder: 'descend',
    },
    {
      title: 'Max Drawdown (%)',
      dataIndex: 'maxDrawdown',
      key: 'maxDrawdown',
      sorter: (a, b) => a.maxDrawdown - b.maxDrawdown,
      render: (text) => <span style={{ color: '#52c41a' }}>{text.toFixed(2)}%</span>,
    },
    {
      title: 'Sharpe Ratio',
      dataIndex: 'sharpeRatio',
      key: 'sharpeRatio',
      sorter: (a, b) => a.sharpeRatio - b.sharpeRatio,
    },
    {
      title: 'Win Rate (%)',
      dataIndex: 'winRate',
      key: 'winRate',
      sorter: (a, b) => a.winRate - b.winRate,
    },
    {
      title: 'Trade Count',
      dataIndex: 'tradeCount',
      key: 'tradeCount',
      sorter: (a, b) => a.tradeCount - b.tradeCount,
    },
    {
      title: 'Action',
      key: 'action',
      render: (_, _record) => (
        <Space size="small">
          <Button size="small" type="link">Apply</Button>
          <Button size="small" type="link">Details</Button>
        </Space>
      ),
    },
  ];
  
  // 热力图
  const heatmapOption = {
    title: {
      text: 'Parameter Optimization Heatmap - Annual Return (%)',
      left: 'center'
    },
    tooltip: {
      position: 'top',
      formatter: function (params: any) {
        return 'Short Period: ' + params.data[0] + '<br>Long Period: ' + params.data[1] + '<br>Return: ' + params.data[2].toFixed(2) + '%';
      }
    },
    grid: {
      top: '15%',
      bottom: '10%',
      left: '10%',
      right: '5%'
    },
    xAxis: {
      type: 'category',
      name: 'Short Period',
      data: [5, 10, 15, 20, 25, 30],
      splitArea: {
        show: true
      }
    },
    yAxis: {
      type: 'category',
      name: 'Long Period',
      data: [20, 30, 40, 50, 60, 70, 80, 90],
      splitArea: {
        show: true
      }
    },
    visualMap: {
      min: 10,
      max: 25,
      calculable: true,
      orient: 'horizontal',
      left: 'center',
      bottom: '0%',
      inRange: {
        color: ['#52c41a', '#yellow', '#f5222d']
      }
    },
    series: [{
      name: 'Annual Return',
      type: 'heatmap',
      data: [
        [0, 0, 12.5], [0, 1, 13.2], [0, 2, 14.8], [0, 3, 15.9], [0, 4, 16.7], [0, 5, 15.5], [0, 6, 14.2], [0, 7, 13.8],
        [1, 0, 13.8], [1, 1, 14.6], [1, 2, 16.2], [1, 3, 17.8], [1, 4, 18.5], [1, 5, 17.2], [1, 6, 16.3], [1, 7, 15.5],
        [2, 0, 15.2], [2, 1, 16.5], [2, 2, 18.3], [2, 3, 19.8], [2, 4, 20.6], [2, 5, 19.5], [2, 6, 18.4], [2, 7, 17.2],
        [3, 0, 16.4], [3, 1, 17.8], [3, 2, 19.6], [3, 3, 21.2], [3, 4, 22.5], [3, 5, 21.3], [3, 6, 20.1], [3, 7, 18.9],
        [4, 0, 15.6], [4, 1, 16.9], [4, 2, 18.7], [4, 3, 20.1], [4, 4, 21.3], [4, 5, 20.2], [4, 6, 19.2], [4, 7, 18.0],
        [5, 0, 14.3], [5, 1, 15.5], [5, 2, 17.2], [5, 3, 18.5], [5, 4, 19.6], [5, 5, 18.8], [5, 6, 17.5], [5, 7, 16.3]
      ],
      emphasis: {
        itemStyle: {
          shadowBlur: 10,
          shadowColor: 'rgba(0, 0, 0, 0.5)'
        }
      }
    }]
  };
  
  // 3D散点图
  const scatter3DOption = {
    title: {
      text: 'Parameter Space Exploration',
      left: 'center'
    },
    grid3D: {
      viewControl: {
        projection: 'orthographic',
        autoRotate: true
      },
      axisLabel: {
        formatter: '{value}'
      }
    },
    xAxis3D: {
      name: 'Short Period',
      type: 'value',
      min: 5,
      max: 30
    },
    yAxis3D: {
      name: 'Long Period',
      type: 'value',
      min: 20,
      max: 90
    },
    zAxis3D: {
      name: 'Annual Return (%)',
      type: 'value',
      min: 10,
      max: 25
    },
    visualMap: {
      dimension: 2,
      min: 10,
      max: 25,
      inRange: {
        color: ['#52c41a', '#yellow', '#f5222d']
      }
    },
    dataset: {
      source: [
        [10, 30, 12.5], [10, 40, 13.2], [10, 50, 14.8], [10, 60, 15.9], [10, 70, 16.7], [10, 80, 15.5], [10, 90, 14.2],
        [15, 30, 13.8], [15, 40, 14.6], [15, 50, 16.2], [15, 60, 17.8], [15, 70, 18.5], [15, 80, 17.2], [15, 90, 16.3],
        [20, 30, 15.2], [20, 40, 16.5], [20, 50, 18.3], [20, 60, 19.8], [20, 70, 20.6], [20, 80, 19.5], [20, 90, 18.4],
        [25, 30, 16.4], [25, 40, 17.8], [25, 50, 19.6], [25, 60, 21.2], [25, 70, 22.5], [25, 80, 21.3], [25, 90, 20.1],
        [30, 30, 15.6], [30, 40, 16.9], [30, 50, 18.7], [30, 60, 20.1], [30, 70, 21.3], [30, 80, 20.2], [30, 90, 19.2]
      ]
    },
    series: [{
      type: 'scatter3D',
      symbolSize: 8,
      encode: {
        x: 0,
        y: 1,
        z: 2
      }
    }]
  };

  // 加载数据
  useEffect(() => {
    fetchStocks();
  }, []);
  
  // 获取股票列表
  const fetchStocks = async () => {
    setLoading(true);
    try {
      const stocks = await fetchStockList();
      setStockList(stocks);
    } catch (error) {
      console.error('获取股票列表失败:', error);
    } finally {
      setLoading(false);
    }
  };

  // 创建Tabs的items配置
  const getResultTabItems = () => {
    return [
      {
        key: "1",
        label: (
          <span>
            <LineChartOutlined />
            Optimization Results
          </span>
        ),
        children: (
          <>
            <Table
              dataSource={optimizationResults}
              columns={columns}
              pagination={false}
              scroll={{ x: true }}
            />
            
            <div style={{ marginTop: 16, marginBottom: 16 }}>
              <Tag color="blue">Best Parameter Combination: Short MA=20, Long MA=60</Tag>
              <Tag color="green">Best Sharpe Ratio: 2.03</Tag>
              <Tag color="red">Max Annual Return: 21.2%</Tag>
            </div>
            
            <div style={{ textAlign: 'right', marginTop: 16 }}>
              <Button icon={<SaveOutlined />} type="primary">
                Apply Best Parameters
              </Button>
            </div>
          </>
        )
      },
      {
        key: "2",
        label: (
          <span>
            <SyncOutlined />
            Parameter Analysis
          </span>
        ),
        children: (
          <Row gutter={16}>
            <Col span={12} style={{ height: 500 }}>
              <ReactECharts option={heatmapOption} style={{ height: '100%' }} />
            </Col>
            <Col span={12} style={{ height: 500 }}>
              <ReactECharts option={scatter3DOption} style={{ height: '100%' }} />
            </Col>
          </Row>
        )
      }
    ];
  };

  return (
    <div>
      <Title level={2}>Strategy Optimization</Title>
      <Paragraph>Optimize your trading strategy parameters to find the best parameter combination.</Paragraph>
      
      <Card>
        <Spin spinning={loading}>
          <Form layout="vertical">
            <Row gutter={24}>
              <Col span={8}>
                <Form.Item label="Strategy Selection" required>
                  <Select defaultValue="ma_cross" placeholder="Select Strategy">
                    <Option value="ma_cross">Moving Average Cross Strategy</Option>
                    <Option value="rsi">RSI Strategy</Option>
                    <Option value="macd">MACD Strategy</Option>
                    <Option value="bbands">Bollinger Bands Strategy</Option>
                  </Select>
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item label="Trading Instrument" required>
                  <Select defaultValue={stockList[0]?.symbol} placeholder="Select Trading Instrument">
                    {stockList.map(stock => (
                      <Option key={stock.id} value={stock.symbol}>
                        {stock.name} ({stock.symbol})
                      </Option>
                    ))}
                  </Select>
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item label="Optimization Target">
                  <Select defaultValue="sharpe" placeholder="Select Optimization Target">
                    <Option value="return">Max Annual Return</Option>
                    <Option value="sharpe">Max Sharpe Ratio</Option>
                    <Option value="calmar">Max Calmar Ratio</Option>
                    <Option value="custom">Custom Target</Option>
                  </Select>
                </Form.Item>
              </Col>
            </Row>
            
            <Divider orientation="left">Parameter Range Settings</Divider>
            
            <Row gutter={24}>
              <Col span={12}>
                <Form.Item label="Short Period Range">
                  <Row gutter={12}>
                    <Col span={10}>
                      <InputNumber 
                        min={5} 
                        max={50} 
                        defaultValue={5} 
                        style={{ width: '100%' }} 
                      />
                    </Col>
                    <Col span={4} style={{ textAlign: 'center' }}>
                      <span>To</span>
                    </Col>
                    <Col span={10}>
                      <InputNumber 
                        min={5} 
                        max={50} 
                        defaultValue={30} 
                        style={{ width: '100%' }} 
                      />
                    </Col>
                  </Row>
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item label="Step">
                  <InputNumber 
                    min={1} 
                    max={10} 
                    defaultValue={5} 
                    style={{ width: '100%' }} 
                  />
                </Form.Item>
              </Col>
            </Row>
            
            <Row gutter={24}>
              <Col span={12}>
                <Form.Item label="Long Period Range">
                  <Row gutter={12}>
                    <Col span={10}>
                      <InputNumber 
                        min={20} 
                        max={200} 
                        defaultValue={20} 
                        style={{ width: '100%' }} 
                      />
                    </Col>
                    <Col span={4} style={{ textAlign: 'center' }}>
                      <span>To</span>
                    </Col>
                    <Col span={10}>
                      <InputNumber 
                        min={20} 
                        max={200} 
                        defaultValue={100} 
                        style={{ width: '100%' }} 
                      />
                    </Col>
                  </Row>
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item label="Step">
                  <InputNumber 
                    min={1} 
                    max={20} 
                    defaultValue={10} 
                    style={{ width: '100%' }} 
                  />
                </Form.Item>
              </Col>
            </Row>
            
            <Divider orientation="left">Advanced Settings</Divider>
            
            <Row gutter={24}>
              <Col span={8}>
                <Form.Item label="Optimization Method">
                  <Select defaultValue="grid" placeholder="Select Optimization Method">
                    <Option value="grid">Grid Search</Option>
                    <Option value="random">Random Search</Option>
                    <Option value="bayesian">Bayesian Optimization</Option>
                    <Option value="genetic">Genetic Algorithm</Option>
                  </Select>
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item label="Parallel Processes">
                  <Slider
                    min={1}
                    max={8}
                    defaultValue={4}
                    marks={{
                      1: '1',
                      4: '4',
                      8: '8',
                    }}
                  />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item label="Cross Validation">
                  <Select defaultValue="none" placeholder="Select Cross Validation Method">
                    <Option value="none">No Use</Option>
                    <Option value="time">Time Series Split</Option>
                    <Option value="walk">Rolling Window</Option>
                  </Select>
                </Form.Item>
              </Col>
            </Row>
            
            <Form.Item>
              <Space>
                <Button 
                  type="primary" 
                  icon={<PlayCircleOutlined />} 
                  loading={running} 
                  onClick={handleRunOptimization}
                >
                  Start Optimization
                </Button>
                <Button icon={<SettingOutlined />}>Advanced Parameters</Button>
              </Space>
            </Form.Item>
          </Form>
        </Spin>
      </Card>
      
      {hasResults && (
        <>
          <Divider />
          <Card>
            <Tabs defaultActiveKey="1" items={getResultTabItems()} />
          </Card>
        </>
      )}
    </div>
  );
};

export default StrategyOptimization; 