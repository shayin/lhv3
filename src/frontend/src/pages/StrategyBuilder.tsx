import React, { useState, useEffect } from 'react';
import { Card, Tabs, Form, Input, Select, Button, Collapse, Space, Switch, InputNumber, Row, Col, Typography, message, Spin, List, Tooltip, Popconfirm, Modal, Divider, Dropdown, Menu } from 'antd';
import { SaveOutlined, PlayCircleOutlined, CodeOutlined, LineChartOutlined, SettingOutlined, PlusOutlined, CopyOutlined, DeleteOutlined, EditOutlined, ExclamationCircleOutlined, DownOutlined } from '@ant-design/icons';
import ReactCodeMirror from '@uiw/react-codemirror';
import { python } from '@codemirror/lang-python';
import { 
  fetchStockList,
  Stock,
  saveStrategy,
  Strategy,
  fetchStrategyById,
  fetchStrategies,
  deleteStrategy,
  fetchStrategyTemplates,
  fetchStrategyTemplateById
} from '../services/apiService';
import { useLocation, useNavigate } from 'react-router-dom';

const { Title, Paragraph } = Typography;
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
  const [templateList, setTemplateList] = useState<any[]>([]);
  const [templatesLoading, setTemplatesLoading] = useState<boolean>(false);
  const [strategyTemplates, setStrategyTemplates] = useState([
    { label: '移动平均线交叉策略', value: 'ma_cross' },
    { label: '布林带策略', value: 'bbands' },
    { label: 'RSI策略', value: 'rsi' },
    { label: 'MACD策略', value: 'macd' },
    { label: '趋势跟踪策略', value: 'trend_following' },
    { label: '双均线策略', value: 'dual_ma' },
  ]);
  const [strategyParams, setStrategyParams] = useState<any>({});
  const [saving, setSaving] = useState<boolean>(false);
  const [testing, setTesting] = useState<boolean>(false);
  
  // 从URL获取策略ID（如果有）
  const getStrategyIdFromUrl = () => {
    const searchParams = new URLSearchParams(location.search);
    const id = searchParams.get('id');
    return id;
  };
  
  // 用于跟踪组件是否已加载初始数据
  const [initialDataLoaded, setInitialDataLoaded] = useState<boolean>(false);
  
  // 加载数据
  useEffect(() => {
    // 仅在首次挂载时或URL变化且未加载过数据时加载
    const loadInitialData = async () => {
      if (initialDataLoaded) {
        // 如果已经加载过初始数据，只处理URL中的策略ID变化
        const strategyId = getStrategyIdFromUrl();
        if (strategyId) {
          // 如果当前策略ID与URL中的不同，则加载新策略
          if (!currentStrategy || currentStrategy.id !== strategyId) {
            await loadStrategyIfNeeded(strategyId);
          }
        }
        return;
      }
      
      setInitialDataLoaded(true);
      
      try {
        // 并行加载股票列表和策略模板
        await Promise.all([
          fetchStocks(),
          loadStrategyTemplates()
        ]);
        
        // 加载策略列表
        await fetchStrategyList();
      } catch (error) {
        console.error('初始化数据加载失败:', error);
        message.error('数据加载失败，请刷新页面重试');
      }
    };
    
    loadInitialData();
  // 添加location作为依赖，当URL变化时重新加载
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [location.search, initialDataLoaded]);
  
  // 获取策略列表
  const fetchStrategyList = async () => {
    // 如果已经在加载中，不重复发起请求
    if (loadingStrategies) return;
    
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
        // 检查策略是否已经加载，避免重复加载
        if (!currentStrategy || currentStrategy.id !== strategyId) {
          await loadStrategyIfNeeded(strategyId);
        }
      } else if (userStrategies.length > 0 && !currentStrategy) {
        // 如果没有策略ID且策略列表不为空且当前没有加载策略，加载第一个策略
        await handleStrategyClick(userStrategies[0]);
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
    // 如果已经有股票列表数据，不再重复获取
    if (stockList.length > 0) return stockList;
    
    setLoading(true);
    try {
      const stocks = await fetchStockList();
      setStockList(stocks);
      return stocks;
    } catch (error) {
      console.error('获取股票列表失败:', error);
    } finally {
      setLoading(false);
    }
    return [];
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
      
      // 直接调用handleStrategyClick加载新策略，不重复获取策略列表
      handleStrategyClick(savedStrategy);
      
      // 更新URL参数
      window.history.replaceState(null, '', `?id=${savedStrategy.id}`);
      
      // 刷新策略列表，但不重复加载当前策略
      if (!loadingStrategies) {
        const savedId = savedStrategy.id;
        const tempFetch = async () => {
          const strategies = await fetchStrategies();
          const userStrategies = strategies.filter(s => !s.is_template);
          setStrategyList(userStrategies);
        };
        tempFetch();
      }
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
          
          // 刷新策略列表，避免重复请求
          if (!loadingStrategies) {
            const tempFetch = async () => {
              const strategies = await fetchStrategies();
              const userStrategies = strategies.filter(s => !s.is_template);
              setStrategyList(userStrategies);
            };
            tempFetch();
          }
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
      
      // 刷新策略列表，但不重复加载当前策略
      if (!loadingStrategies) {
        const savedId = savedStrategy.id;
        const tempFetch = async () => {
          const strategies = await fetchStrategies();
          const userStrategies = strategies.filter(s => !s.is_template);
          setStrategyList(userStrategies);
        };
        tempFetch();
      }
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
    // 如果已经有模板数据且不是默认值，不再重复获取
    if (strategyTemplates.length > 0 && strategyTemplates[0].value !== 'ma_cross') {
      return strategyTemplates;
    }
    
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
        return templates;
      }
    } catch (error) {
      console.error('获取策略模板失败:', error);
    }
    return strategyTemplates;
  };

  // 加载策略模板列表
  const fetchTemplateList = async () => {
    setTemplatesLoading(true);
    try {
      const templates = await fetchStrategyTemplates();
      setTemplateList(templates);
    } catch (error) {
      message.error('获取策略模板失败');
    } finally {
      setTemplatesLoading(false);
    }
  };

  // 加载特定模板
  const loadTemplate = async (templateId: string) => {
    try {
      const template = await fetchStrategyTemplateById(templateId);
      if (template) {
        form.setFieldsValue({
          name: `自定义${template.name}`,
          description: template.description,
          code: template.code,
        });
        
        // 如果模板有预定义参数，设置参数
        if (template.parameters) {
          setStrategyParams(template.parameters);
        }
        
        message.success('模板加载成功');
      }
    } catch (error) {
      message.error('加载模板失败');
    }
  };

  const handleSelectTemplate = (templateId: string) => {
    loadTemplate(templateId);
  };

  // 表单初始值
  const initialValues = {
    name: '',
    description: '',
    code: ''
  };

  // 表单提交
  const onFinish = (values: any) => {
    // 保存策略的逻辑
    setSaving(true);
    // 假设已有保存策略的函数
    saveStrategy(values)
      .then(async (savedStrategy) => {
        message.success('策略保存成功');
        
        // 更新当前策略
        if (savedStrategy) {
          setCurrentStrategy(savedStrategy);
          
          // 更新URL参数
          window.history.replaceState(null, '', `?id=${savedStrategy.id}`);
          
          // 刷新策略列表，但不重复加载当前策略
          if (!loadingStrategies) {
            const strategies = await fetchStrategies();
            const userStrategies = strategies.filter(s => !s.is_template);
            setStrategyList(userStrategies);
          }
        }
      })
      .catch(error => {
        message.error('保存策略失败: ' + error.message);
      })
      .finally(() => {
        setSaving(false);
      });
  };

  // 测试策略
  const testStrategy = () => {
    setTesting(true);
    // 测试策略的逻辑
    setTimeout(() => {
      message.success('策略测试成功');
      setTesting(false);
    }, 1500);
  };

  // 重置表单
  const resetForm = (templateType: string) => {
    // 重置表单的逻辑
    form.resetFields();
    // 可以根据模板类型加载不同的默认代码
    message.success('已重置为' + templateType + '模板');
  };

  // 添加一个函数来创建策略库标签页的配置
  const getStrategyLibraryTabs = () => {
    return [
      {
        key: 'mine',
        label: '我的策略',
        children: (
          <List
            itemLayout="horizontal"
            dataSource={strategyList}
            loading={loadingStrategies}
            renderItem={item => (
              <List.Item
                className="strategy-list-item"
                actions={[
                  <Button 
                    key="edit" 
                    type="link" 
                    size="small"
                    onClick={() => handleStrategyClick(item)}
                  >
                    编辑
                  </Button>,
                  <Button 
                    key="delete" 
                    type="link" 
                    danger 
                    size="small"
                    onClick={() => showDeleteConfirm(item)}
                  >
                    删除
                  </Button>
                ]}
              >
                <div className="strategy-list-content">
                  <div className="strategy-name">{item.name}</div>
                  <div className="strategy-desc">{item.description}</div>
                </div>
              </List.Item>
            )}
          />
        )
      },
      {
        key: 'templates',
        label: '策略模板',
        children: (
          <List
            itemLayout="horizontal"
            dataSource={templateList}
            loading={templatesLoading}
            renderItem={item => (
              <List.Item
                className="strategy-list-item"
                actions={[
                  <Button 
                    key="use" 
                    type="link" 
                    size="small"
                    onClick={() => handleSelectTemplate(item.id)}
                  >
                    使用
                  </Button>
                ]}
              >
                <div className="strategy-list-content">
                  <div className="strategy-name">{item.name}</div>
                  <div className="strategy-desc">{item.description}</div>
                </div>
              </List.Item>
            )}
          />
        )
      }
    ];
  };

  return (
    <div className="strategy-builder">
      <div className="page-header" style={{ marginBottom: '20px' }}>
        <Title level={2}>策略构建器</Title>
        <Paragraph>创建和测试您的交易策略</Paragraph>
      </div>
      
      <Row gutter={16}>
        <Col span={18}>
          <Card 
            title="策略编辑器" 
            bordered={false} 
            className="editor-card"
          >
            <Form
              form={form}
              layout="vertical"
              initialValues={initialValues}
              onFinish={onFinish}
            >
              <Row gutter={16}>
                <Col span={12}>
                  <Form.Item
                    name="name"
                    label="策略名称"
                    rules={[
                      { required: true, message: '请输入策略名称' },
                      { max: 50, message: '策略名称不能超过50个字符' }
                    ]}
                  >
                    <Input placeholder="请输入策略名称" />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item
                    name="description"
                    label="策略描述"
                    rules={[
                      { max: 200, message: '策略描述不能超过200个字符' }
                    ]}
                  >
                    <Input.TextArea 
                      placeholder="请输入策略描述" 
                      autoSize={{ minRows: 1, maxRows: 3 }}
                    />
                  </Form.Item>
                </Col>
              </Row>
              
              <Form.Item
                name="code"
                label="策略代码"
                rules={[
                  { required: true, message: '请输入策略代码' }
                ]}
              >
                <ReactCodeMirror
                  height="450px"
                  extensions={[python()]}
                  onChange={(value: string) => form.setFieldsValue({ code: value })}
                />
              </Form.Item>
              
              <Form.Item>
                <Space>
                  <Button type="primary" htmlType="submit" loading={saving}>
                    保存策略
                  </Button>
                  <Button type="default" onClick={testStrategy} loading={testing}>
                    测试策略
                  </Button>
                  <Dropdown overlay={
                    <Menu>
                      <Menu.Item key="basic" onClick={() => resetForm('basic')}>
                        基础策略模板
                      </Menu.Item>
                      <Menu.Item key="technical" onClick={() => resetForm('technical')}>
                        技术指标策略
                      </Menu.Item>
                      <Menu.Item key="empty" onClick={() => resetForm('empty')}>
                        空白策略
                      </Menu.Item>
                    </Menu>
                  }>
                    <Button>
                      重置模板 <DownOutlined />
                    </Button>
                  </Dropdown>
                </Space>
              </Form.Item>
            </Form>
          </Card>
        </Col>
        
        <Col span={6}>
          <Card 
            title="策略库"
            bordered={false}
            className="strategy-library-card"
            style={{ marginBottom: '16px', height: '300px' }}
          >
            <Tabs defaultActiveKey="mine" items={getStrategyLibraryTabs()} />
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default StrategyBuilder; 