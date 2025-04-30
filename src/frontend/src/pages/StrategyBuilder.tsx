import React, { useState, useEffect } from 'react';
import { Card, Tabs, Form, Input, Select, Button, Collapse, Space, Switch, InputNumber, Row, Col, Typography, message, Spin } from 'antd';
import { SaveOutlined, PlayCircleOutlined, CodeOutlined, LineChartOutlined, SettingOutlined } from '@ant-design/icons';
import ReactCodeMirror from '@uiw/react-codemirror';
import { python } from '@codemirror/lang-python';
import { fetchStockList, Stock } from '../services/apiService';

const { Title, Paragraph } = Typography;
const { TabPane } = Tabs;
const { Panel } = Collapse;
const { Option } = Select;

const StrategyBuilder: React.FC = () => {
  const [activeKey, setActiveKey] = useState('visual');
  const [codeValue, setCodeValue] = useState(`# 策略示例：移动平均线交叉策略
import pandas as pd
import numpy as np
import talib

def initialize(context):
    """初始化策略参数"""
    context.params = {
        'symbol': '000300.SH',
        'short_period': 20,
        'long_period': 60
    }

def handle_data(context, data):
    """处理每个交易日的数据"""
    params = context.params
    df = data[params['symbol']]
    
    # 计算移动平均线
    df['short_ma'] = talib.SMA(df['close'], timeperiod=params['short_period'])
    df['long_ma'] = talib.SMA(df['close'], timeperiod=params['long_period'])
    
    # 生成交易信号
    df['signal'] = 0
    # 短均线上穿长均线，买入信号
    df.loc[(df['short_ma'] > df['long_ma']) & (df['short_ma'].shift(1) <= df['long_ma'].shift(1)), 'signal'] = 1
    # 短均线下穿长均线，卖出信号
    df.loc[(df['short_ma'] < df['long_ma']) & (df['short_ma'].shift(1) >= df['long_ma'].shift(1)), 'signal'] = -1
    
    return df['signal']
`);

  const [form] = Form.useForm();
  const [stockList, setStockList] = useState<Stock[]>([]);
  const [loading, setLoading] = useState(false);
  
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

  const handleSave = () => {
    message.success('策略保存成功');
  };

  const handleTest = () => {
    message.info('开始测试策略...');
  };

  const indicatorOptions = [
    { label: '移动平均线 (MA)', value: 'ma' },
    { label: '指数移动平均线 (EMA)', value: 'ema' },
    { label: '相对强弱指标 (RSI)', value: 'rsi' },
    { label: 'MACD', value: 'macd' },
    { label: '布林带 (BBANDS)', value: 'bbands' },
    { label: '随机指标 (KDJ)', value: 'kdj' },
  ];

  const strategyTemplates = [
    { label: '移动平均线交叉策略', value: 'ma_cross' },
    { label: '布林带策略', value: 'bbands' },
    { label: 'RSI策略', value: 'rsi' },
    { label: 'MACD策略', value: 'macd' },
    { label: '趋势跟踪策略', value: 'trend_following' },
    { label: '双均线策略', value: 'dual_ma' },
  ];

  return (
    <div>
      <Title level={2}>策略构建器</Title>
      <Paragraph>创建和编辑您的交易策略，可以选择使用可视化编辑器或直接编写代码。</Paragraph>
      
      <Card>
        <Tabs 
          activeKey={activeKey} 
          onChange={setActiveKey}
          tabBarExtraContent={
            <Space>
              <Button icon={<SaveOutlined />} type="primary" onClick={handleSave}>
                保存策略
              </Button>
              <Button icon={<PlayCircleOutlined />} onClick={handleTest}>
                测试策略
              </Button>
            </Space>
          }
        >
          <TabPane 
            tab={
              <span>
                <SettingOutlined />
                可视化编辑
              </span>
            } 
            key="visual"
          >
            <Spin spinning={loading}>
              <Form
                form={form}
                layout="vertical"
                initialValues={{
                  strategyName: '移动平均线交叉策略',
                  description: '基于短期和长期移动平均线交叉产生交易信号的策略',
                  template: 'ma_cross',
                  symbol: '000300.SH',
                  timeframe: 'D',
                  shortPeriod: 20,
                  longPeriod: 60,
                  positionSizing: 'all_in',
                }}
              >
                <Row gutter={24}>
                  <Col span={12}>
                    <Form.Item 
                      label="策略名称" 
                      name="strategyName"
                      rules={[{ required: true, message: '请输入策略名称' }]}
                    >
                      <Input placeholder="请输入策略名称" />
                    </Form.Item>
                  </Col>
                  <Col span={12}>
                    <Form.Item 
                      label="策略模板" 
                      name="template"
                    >
                      <Select placeholder="选择策略模板">
                        {strategyTemplates.map(item => (
                          <Option key={item.value} value={item.value}>{item.label}</Option>
                        ))}
                      </Select>
                    </Form.Item>
                  </Col>
                </Row>
                
                <Form.Item 
                  label="策略描述" 
                  name="description"
                >
                  <Input.TextArea rows={2} placeholder="请输入策略描述" />
                </Form.Item>
                
                <Collapse defaultActiveKey={['1', '2', '3']}>
                  <Panel header="数据设置" key="1">
                    <Row gutter={24}>
                      <Col span={8}>
                        <Form.Item 
                          label="交易品种" 
                          name="symbol"
                          rules={[{ required: true, message: '请选择交易品种' }]}
                        >
                          <Select placeholder="选择交易品种">
                            {stockList.map(stock => (
                              <Option key={stock.id} value={stock.symbol}>
                                {stock.name} ({stock.symbol})
                              </Option>
                            ))}
                          </Select>
                        </Form.Item>
                      </Col>
                      <Col span={8}>
                        <Form.Item 
                          label="时间周期" 
                          name="timeframe"
                          rules={[{ required: true, message: '请选择时间周期' }]}
                        >
                          <Select placeholder="选择时间周期">
                            <Option value="D">日线</Option>
                            <Option value="W">周线</Option>
                            <Option value="M">月线</Option>
                            <Option value="60M">60分钟</Option>
                            <Option value="15M">15分钟</Option>
                          </Select>
                        </Form.Item>
                      </Col>
                      <Col span={8}>
                        <Form.Item 
                          label="添加技术指标" 
                          name="indicators"
                        >
                          <Select 
                            mode="multiple" 
                            placeholder="添加技术指标"
                            options={indicatorOptions}
                          />
                        </Form.Item>
                      </Col>
                    </Row>
                  </Panel>
                  
                  <Panel header="策略参数" key="2">
                    <Row gutter={24}>
                      <Col span={8}>
                        <Form.Item 
                          label="短期周期" 
                          name="shortPeriod"
                          rules={[{ required: true, message: '请输入短期周期' }]}
                        >
                          <InputNumber min={1} max={100} style={{ width: '100%' }} />
                        </Form.Item>
                      </Col>
                      <Col span={8}>
                        <Form.Item 
                          label="长期周期" 
                          name="longPeriod"
                          rules={[{ required: true, message: '请输入长期周期' }]}
                        >
                          <InputNumber min={5} max={200} style={{ width: '100%' }} />
                        </Form.Item>
                      </Col>
                      <Col span={8}>
                        <Form.Item 
                          label="仓位管理" 
                          name="positionSizing"
                        >
                          <Select placeholder="选择仓位管理方式">
                            <Option value="all_in">全仓</Option>
                            <Option value="fixed">固定金额</Option>
                            <Option value="percentage">资金百分比</Option>
                            <Option value="kelly">凯利公式</Option>
                          </Select>
                        </Form.Item>
                      </Col>
                    </Row>
                    
                    <Row gutter={24}>
                      <Col span={12}>
                        <Form.Item 
                          label="启用止损" 
                          name="useStopLoss"
                          valuePropName="checked"
                        >
                          <Switch />
                        </Form.Item>
                      </Col>
                      <Col span={12}>
                        <Form.Item 
                          label="启用止盈" 
                          name="useTakeProfit"
                          valuePropName="checked"
                        >
                          <Switch />
                        </Form.Item>
                      </Col>
                    </Row>
                  </Panel>
                  
                  <Panel header="风险控制" key="3">
                    <Row gutter={24}>
                      <Col span={8}>
                        <Form.Item 
                          label="单笔风险(%)" 
                          name="singleRisk"
                        >
                          <InputNumber min={0} max={100} style={{ width: '100%' }} />
                        </Form.Item>
                      </Col>
                      <Col span={8}>
                        <Form.Item 
                          label="最大回撤限制(%)" 
                          name="maxDrawdown"
                        >
                          <InputNumber min={0} max={100} style={{ width: '100%' }} />
                        </Form.Item>
                      </Col>
                      <Col span={8}>
                        <Form.Item 
                          label="单日风险(%)" 
                          name="dailyRisk"
                        >
                          <InputNumber min={0} max={100} style={{ width: '100%' }} />
                        </Form.Item>
                      </Col>
                    </Row>
                  </Panel>
                </Collapse>
              </Form>
            </Spin>
          </TabPane>
          
          <TabPane 
            tab={
              <span>
                <CodeOutlined />
                代码编辑
              </span>
            } 
            key="code"
          >
            <ReactCodeMirror
              value={codeValue}
              height="600px"
              extensions={[python()]}
              onChange={(value) => setCodeValue(value)}
              theme="light"
            />
          </TabPane>
          
          <TabPane 
            tab={
              <span>
                <LineChartOutlined />
                性能分析
              </span>
            } 
            key="analysis"
          >
            <div style={{ padding: '20px 0', textAlign: 'center' }}>
              <Paragraph>请先测试策略以查看性能分析</Paragraph>
              <Button icon={<PlayCircleOutlined />} type="primary" onClick={handleTest}>
                测试策略
              </Button>
            </div>
          </TabPane>
        </Tabs>
      </Card>
    </div>
  );
};

export default StrategyBuilder; 