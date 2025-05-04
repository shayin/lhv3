import React, { useState, useEffect } from 'react';
import { Card, Tabs, Form, Input, Select, Button, Collapse, Space, Switch, InputNumber, Row, Col, Typography, message, Spin, List, Tooltip, Popconfirm, Modal, Divider } from 'antd';
import { SaveOutlined, PlayCircleOutlined, CodeOutlined, LineChartOutlined, SettingOutlined, PlusOutlined, CopyOutlined, DeleteOutlined, EditOutlined, ExclamationCircleOutlined } from '@ant-design/icons';
import ReactCodeMirror from '@uiw/react-codemirror';
import { python } from '@codemirror/lang-python';
import { fetchStockList, Stock, saveStrategy, Strategy, fetchStrategyById, fetchStrategies, deleteStrategy } from '../services/apiService';
import { useLocation, useNavigate } from 'react-router-dom';

const { Title, Paragraph, Text } = Typography;
const { TabPane } = Tabs;
const { Panel } = Collapse;
const { Option } = Select;
const { confirm } = Modal;

const StrategyBuilder: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
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
  const [currentStrategy, setCurrentStrategy] = useState<Strategy | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [strategyList, setStrategyList] = useState<Strategy[]>([]);
  const [loadingStrategies, setLoadingStrategies] = useState(false);
  const [searchText, setSearchText] = useState('');
  const [strategyTemplates, setStrategyTemplates] = useState([
    { label: '移动平均线交叉策略', value: 'ma_cross' },
    { label: '布林带策略', value: 'bbands' },
    { label: 'RSI策略', value: 'rsi' },
    { label: 'MACD策略', value: 'macd' },
    { label: '趋势跟踪策略', value: 'trend_following' },
    { label: '双均线策略', value: 'dual_ma' },
  ]);
  
  // 从URL获取策略ID（如果有）
  const getStrategyIdFromUrl = () => {
    const searchParams = new URLSearchParams(location.search);
    const id = searchParams.get('id');
    return id;
  };
  
  // 加载数据
  useEffect(() => {
    // 仅在首次挂载时获取股票列表和策略模板列表
    const loadInitialData = async () => {
      await Promise.all([
        fetchStocks(),
        loadStrategyTemplates()
      ]);
      
      // 加载策略列表
      await fetchStrategyList();
    };
    
    loadInitialData();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  
  // 获取策略列表
  const fetchStrategyList = async () => {
    setLoadingStrategies(true);
    try {
      const strategies = await fetchStrategies();
      // 过滤掉模板策略，只显示用户创建的策略
      const userStrategies = strategies.filter(s => !s.is_template);
      setStrategyList(userStrategies);
      console.log('加载到策略列表:', userStrategies.length, '个策略');
      
      // 获取URL中的策略ID
      const strategyId = getStrategyIdFromUrl();
      
      // 如果URL中有策略ID，加载该策略
      if (strategyId) {
        loadStrategyIfNeeded(strategyId);
      } else if (userStrategies.length > 0) {
        // 如果没有策略ID且策略列表不为空，加载第一个策略
        handleStrategyClick(userStrategies[0]);
      }
    } catch (error) {
      console.error('获取策略列表失败:', error);
      message.error('获取策略列表失败');
    } finally {
      setLoadingStrategies(false);
    }
  };
  
  // 如果URL中有策略ID，加载该策略
  const loadStrategyIfNeeded = async (strategyId?: string) => {
    // 初始默认值
    const defaultValues = {
      strategyName: '新策略',
      description: '请输入策略描述',
      template: 'ma_cross',
      symbol: '000300.SH',
      timeframe: 'D',
      shortPeriod: 20,
      longPeriod: 60,
      positionSizing: 'all_in',
    };
    
    if (strategyId) {
      try {
        setLoading(true);
        // 使用封装好的API函数加载策略详情
        const strategy = await fetchStrategyById(strategyId);
        
        setCurrentStrategy(strategy);
        
        // 设置表单值
        if (strategy.code) {
          // 如果有代码，切换到代码编辑模式
          setActiveKey('code');
          setCodeValue(strategy.code);
        }
        
        // 创建包含所有参数的对象，用于设置表单
        const formValues = {
          strategyName: strategy.name,
          description: strategy.description,
          template: strategy.template || 'ma_cross',
        };
        
        // 合并参数详情
        if (strategy.parameters) {
          console.log("加载策略参数:", strategy.parameters);
          
          // 将parameters中的值直接展开到formValues中
          Object.assign(formValues, strategy.parameters);
        }
        
        console.log("设置表单值:", formValues);
        
        // 设置所有表单字段值
        form.setFieldsValue(formValues);
      } catch (error) {
        console.error('加载策略详情失败:', error);
        message.error('加载策略详情失败');
        // 设置表单默认值
        form.setFieldsValue(defaultValues);
      } finally {
        setLoading(false);
      }
    } else {
      // 没有策略ID时，设置表单默认值
      form.setFieldsValue(defaultValues);
    }
  };
  
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

  // 处理策略点击
  const handleStrategyClick = async (strategy: Strategy) => {
    if (strategy.id) {
      try {
        setLoading(true);
        
        // 直接调用API获取完整的策略详情
        const strategyDetail = await fetchStrategyById(strategy.id as string);
        
        // 更新当前策略
        setCurrentStrategy(strategyDetail);
        
        // 设置表单值
        if (strategyDetail.code) {
          // 如果有代码，切换到代码编辑模式
          setActiveKey('code');
          setCodeValue(strategyDetail.code);
        } else {
          // 否则切换到可视化编辑模式
          setActiveKey('visual');
        }
        
        // 创建包含所有参数的对象，用于设置表单
        const formValues = {
          strategyName: strategyDetail.name,
          description: strategyDetail.description,
          template: strategyDetail.template || 'ma_cross',
        };
        
        // 合并参数详情
        if (strategyDetail.parameters) {
          console.log("加载策略参数:", strategyDetail.parameters);
          
          // 将parameters中的值直接展开到formValues中
          Object.assign(formValues, strategyDetail.parameters);
        }
        
        console.log("设置表单值:", formValues);
        
        // 设置所有表单字段值
        form.setFieldsValue(formValues);
        
        // 更新URL参数
        window.history.replaceState(null, '', `?id=${strategy.id}`);
        
      } catch (error) {
        console.error('加载策略详情失败:', error);
        message.error('加载策略详情失败');
      } finally {
        setLoading(false);
      }
    }
  };

  // 处理新建策略
  const handleCreateStrategy = () => {
    // 清除当前策略
    setCurrentStrategy(null);
    
    // 重置为默认值
    form.setFieldsValue({
      strategyName: '新策略',
      description: '请输入策略描述',
      template: 'ma_cross',
      symbol: '000300.SH',
      timeframe: 'D',
      shortPeriod: 20,
      longPeriod: 60,
      positionSizing: 'all_in',
    });
    
    // 默认切换到可视化编辑模式
    setActiveKey('visual');
    
    // 清除URL参数
    window.history.replaceState(null, '', window.location.pathname);
  };

  // 处理复制策略
  const handleCopyStrategy = async (strategy: Strategy) => {
    try {
      if (!strategy) return;
      
      // 获取完整策略详情
      const fullStrategy = await fetchStrategyById(strategy.id as string);
      
      // 创建新策略对象
      const newStrategy: Strategy = {
        name: `${fullStrategy.name} (副本)`,
        description: fullStrategy.description,
        template: fullStrategy.template,
        parameters: fullStrategy.parameters,
        code: fullStrategy.code
      };
      
      // 保存新策略
      const savedStrategy = await saveStrategy(newStrategy);
      message.success('策略复制成功');
      
      // 刷新策略列表并加载新策略
      await fetchStrategyList();
      
      // 直接调用handleStrategyClick加载新策略，但不更新URL
      handleStrategyClick(savedStrategy);
      
      // 更新URL参数
      window.history.replaceState(null, '', `?id=${savedStrategy.id}`);
    } catch (error) {
      console.error('复制策略失败:', error);
      message.error('复制策略失败');
    }
  };

  // 处理删除策略
  const showDeleteConfirm = (strategy: Strategy) => {
    confirm({
      title: '确定要删除这个策略吗?',
      icon: <ExclamationCircleOutlined />,
      content: '此操作不可撤销，删除后数据将无法恢复。',
      okText: '是的，删除',
      okType: 'danger',
      cancelText: '取消',
      async onOk() {
        try {
          await deleteStrategy(strategy.id as string);
          message.success('策略删除成功');
          
          // 如果当前正在编辑被删除的策略，则清空表单和当前策略
          if (currentStrategy && currentStrategy.id === strategy.id) {
            setCurrentStrategy(null);
            form.resetFields();
            
            // 设置默认值
            form.setFieldsValue({
              strategyName: '新策略',
              description: '请输入策略描述',
              template: 'ma_cross',
              symbol: '000300.SH',
              timeframe: 'D',
              shortPeriod: 20,
              longPeriod: 60,
              positionSizing: 'all_in',
            });
            
            // 清除URL参数
            window.history.replaceState(null, '', window.location.pathname);
          }
          
          // 刷新策略列表
          fetchStrategyList();
        } catch (error) {
          console.error('删除策略失败:', error);
          message.error('删除策略失败');
        }
      }
    });
  };

  const handleSave = async () => {
    try {
      // 根据activeKey获取不同的策略数据
      let strategyData: Strategy;
      
      if (activeKey === 'visual') {
        // 从表单获取可视化编辑器的数据
        const formValues = form.getFieldsValue();
        
        // 获取表单中的template值，确保这是从后端获取的真实模板ID
        const templateId = formValues.template;
        
        strategyData = {
          name: formValues.strategyName,
          description: formValues.description,
          template: templateId, // 使用正确的模板ID
          parameters: {
            // 移除与策略本身无关的字段
            symbol: formValues.symbol,
            timeframe: formValues.timeframe,
            shortPeriod: formValues.shortPeriod,
            longPeriod: formValues.longPeriod,
            positionSizing: formValues.positionSizing,
            useStopLoss: formValues.useStopLoss,
            useTakeProfit: formValues.useTakeProfit,
            singleRisk: formValues.singleRisk,
            maxDrawdown: formValues.maxDrawdown,
            dailyRisk: formValues.dailyRisk,
            indicators: formValues.indicators
          }
        };
      } else {
        // 使用代码编辑器的数据
        const formValues = form.getFieldsValue();
        strategyData = {
          name: formValues.strategyName || '自定义策略',
          description: formValues.description || '通过代码编辑器创建的自定义策略',
          template: formValues.template, // 确保传递模板ID
          code: codeValue
        };
      }
      
      // 添加日志，确认策略数据格式正确
      console.log('准备保存的策略数据:', JSON.stringify(strategyData, null, 2));
      
      // 如果是更新已有策略，添加ID
      if (currentStrategy && currentStrategy.id) {
        strategyData.id = currentStrategy.id;
        console.log('更新现有策略，ID:', currentStrategy.id);
      } else {
        console.log('创建新策略');
      }
      
      setIsSaving(true);
      
      // 调用API保存策略
      const savedStrategy = await saveStrategy(strategyData);
      
      message.success('策略保存成功');
      console.log('保存的策略数据:', savedStrategy);
      
      // 更新当前策略
      setCurrentStrategy(savedStrategy);
      
      // 更新URL参数
      window.history.replaceState(null, '', `?id=${savedStrategy.id}`);
      
      // 刷新策略列表
      fetchStrategyList();
    } catch (error) {
      console.error('保存策略失败:', error);
      message.error('保存策略失败，请重试');
    } finally {
      setIsSaving(false);
    }
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

  // 过滤策略列表
  const filteredStrategies = strategyList.filter(strategy => 
    strategy.name?.toLowerCase().includes(searchText.toLowerCase()) ||
    strategy.description?.toLowerCase().includes(searchText.toLowerCase())
  );

  // 处理模板选择变更
  const handleTemplateChange = async (value: string) => {
    try {
      // 从模板策略列表中查找对应模板
      const templates = await fetchStrategies();
      const templateStrategy = templates.find(t => t.is_template && t.id === value);
      
      if (templateStrategy && templateStrategy.parameters) {
        // 合并模板参数与当前表单值
        const currentValues = form.getFieldsValue();
        const newValues = {
          ...currentValues,
          template: value,
          // 保留策略名称和描述，合并其他参数
          ...templateStrategy.parameters
        };
        
        // 更新表单值
        form.setFieldsValue(newValues);
        message.success(`已应用${templateStrategy.name}模板参数`);
      }
    } catch (error) {
      console.error('应用模板参数失败:', error);
      message.error('应用模板参数失败');
    }
  };

  // 加载策略模板
  const loadStrategyTemplates = async () => {
    try {
      const strategies = await fetchStrategies();
      // 过滤出模板策略
      const templates = strategies
        .filter(s => s.is_template)
        .map(s => ({ 
          label: s.name, 
          value: s.id as string 
        }));

      if (templates.length > 0) {
        setStrategyTemplates(templates);
      }
    } catch (error) {
      console.error('获取策略模板失败:', error);
    }
  };

  return (
    <div>
      <Title level={2}>策略构建器</Title>
      <Paragraph>创建和编辑您的交易策略，可以选择使用可视化编辑器或直接编写代码。</Paragraph>
      
      <Row gutter={24}>
        {/* 左侧策略列表 */}
        <Col span={6}>
          <Card 
            title="策略列表" 
            extra={
              <Button 
                type="primary" 
                icon={<PlusOutlined />}
                onClick={handleCreateStrategy}
              >
                新建
              </Button>
            }
            style={{ height: '100%', display: 'flex', flexDirection: 'column' }}
            bodyStyle={{ flex: 1, padding: '12px', overflowY: 'hidden', display: 'flex', flexDirection: 'column' }}
          >
            <Input.Search 
              placeholder="搜索策略" 
              style={{ marginBottom: 16 }} 
              onChange={(e) => setSearchText(e.target.value)}
              allowClear
            />
            
            <div style={{ flex: 1, overflow: 'hidden' }}>
              <List
                loading={loadingStrategies}
                dataSource={filteredStrategies}
                renderItem={strategy => (
                  <List.Item
                    key={strategy.id as string}
                    actions={[
                      <div style={{ display: 'flex', flexShrink: 0 }}>
                        <Button.Group size="small">
                          <Tooltip title="编辑">
                            <Button 
                              icon={<EditOutlined />} 
                              type="text" 
                              onClick={() => handleStrategyClick(strategy)}
                            />
                          </Tooltip>
                          <Tooltip title="复制">
                            <Button 
                              icon={<CopyOutlined />} 
                              type="text" 
                              onClick={() => handleCopyStrategy(strategy)}
                            />
                          </Tooltip>
                          <Tooltip title="删除">
                            <Button 
                              icon={<DeleteOutlined />} 
                              type="text" 
                              danger
                              onClick={() => showDeleteConfirm(strategy)}
                            />
                          </Tooltip>
                        </Button.Group>
                      </div>
                    ]}
                    className={currentStrategy?.id === strategy.id ? 'ant-list-item-selected' : ''}
                    style={{
                      ...(currentStrategy?.id === strategy.id ? { background: '#e6f7ff' } : {}),
                      padding: '8px 12px',
                      borderRadius: '4px',
                      marginBottom: '8px',
                      display: 'flex',
                      justifyContent: 'space-between'
                    }}
                  >
                    <List.Item.Meta
                      title={
                        <div style={{ 
                          overflow: 'hidden', 
                          textOverflow: 'ellipsis', 
                          whiteSpace: 'nowrap',
                          maxWidth: '100%',
                          fontSize: '14px',
                          fontWeight: 500
                        }}>
                          <a onClick={() => handleStrategyClick(strategy)}>{strategy.name}</a>
                        </div>
                      }
                      description={
                        <div style={{ 
                          overflow: 'hidden', 
                          textOverflow: 'ellipsis', 
                          whiteSpace: 'nowrap',
                          maxWidth: '100%',
                          fontSize: '12px',
                          color: 'rgba(0, 0, 0, 0.45)'
                        }}>
                          {strategy.description || '无描述'}
                        </div>
                      }
                    />
                  </List.Item>
                )}
                locale={{ 
                  emptyText: '暂无策略，点击"新建"创建第一个策略' 
                }}
                style={{ 
                  height: '100%', 
                  overflow: 'auto',
                  padding: '0 4px'
                }}
                itemLayout="horizontal"
              />
            </div>
          </Card>
        </Col>
        
        {/* 右侧策略编辑 */}
        <Col span={18}>
          <Card>
            <Tabs 
              activeKey={activeKey} 
              onChange={setActiveKey}
              tabBarExtraContent={
                <Space>
                  <Button 
                    icon={<SaveOutlined />} 
                    type="primary" 
                    onClick={handleSave}
                    loading={isSaving}
                  >
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
                          <Select placeholder="选择策略模板" onChange={handleTemplateChange}>
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
                <Spin spinning={loading}>
                  <Form
                    form={form}
                    layout="vertical"
                    style={{ marginBottom: 16 }}
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
                          label="策略描述" 
                          name="description"
                        >
                          <Input placeholder="请输入策略描述" />
                        </Form.Item>
                      </Col>
                    </Row>
                  </Form>
                  <ReactCodeMirror
                    value={codeValue}
                    height="500px"
                    extensions={[python()]}
                    onChange={(value) => setCodeValue(value)}
                    theme="light"
                  />
                </Spin>
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
        </Col>
      </Row>
    </div>
  );
};

export default StrategyBuilder; 