import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { 
  Card, 
  Form, 
  Input, 
  Button, 
  message, 
  Space, 
  Divider, 
  Modal,
  Spin,
  Typography,
  Row,
  Col,
  Alert
} from 'antd';
import { CodeOutlined, SaveOutlined, PlayCircleOutlined, ArrowLeftOutlined } from '@ant-design/icons';
import MonacoEditor from 'react-monaco-editor';
import { getStrategy, createStrategy, updateStrategy, testStrategy } from '../services/strategyService';

const { Title, Text } = Typography;
const { TextArea } = Input;

interface StrategyEditorParams {
  id?: string;
  [key: string]: string | undefined;
}

const StrategyEditor: React.FC = () => {
  const { id } = useParams<StrategyEditorParams>();
  const navigate = useNavigate();
  const [form] = Form.useForm();
  
  const [strategyCode, setStrategyCode] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [testLoading, setTestLoading] = useState<boolean>(false);
  const [isNew, setIsNew] = useState<boolean>(true);
  const [strategyTemplate, setStrategyTemplate] = useState<string>('');
  
  // 加载策略默认代码模板
  const defaultStrategyCode = `from .strategy_template import StrategyTemplate
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)

class MyStrategy(StrategyTemplate):
    """
    我的自定义策略
    """
    
    def __init__(self, parameters=None):
        """初始化策略"""
        default_params = {
            # 在这里定义策略参数和默认值
        }
        
        # 合并用户参数与默认参数
        if parameters:
            default_params.update(parameters)
            
        super().__init__("我的策略", default_params)
        
    def generate_signals(self) -> pd.DataFrame:
        """
        生成交易信号
        
        Returns:
            包含信号的DataFrame，包括:
            - signal: 交易信号 (1: 买入, -1: 卖出, 0: 不操作)
            - trigger_reason: 信号触发原因
        """
        if self.data is None or self.data.empty:
            logger.warning("未设置数据或数据为空，无法生成信号")
            return pd.DataFrame()
        
        # 获取数据
        df = self.data.copy()
        
        # 添加交易信号
        df['signal'] = 0
        df['trigger_reason'] = ''
        
        # TODO: 实现您的交易逻辑
        
        # 使用log函数记录策略执行过程（可选）
        self.log("开始生成交易信号", "INFO")
        self.log(f"数据行数: {len(df)}", "DEBUG")
        
        # 示例: 当价格上涨超过2%时买入
        price_change = df['close'].pct_change() * 100
        buy_signal = price_change > 2
        df.loc[buy_signal, 'signal'] = 1
        df.loc[buy_signal, 'trigger_reason'] = "价格上涨超过2%"
        
        # 记录买入信号数量
        buy_count = buy_signal.sum()
        if buy_count > 0:
            self.log(f"生成买入信号 {buy_count} 个", "INFO")
        
        # 示例: 当价格下跌超过2%时卖出
        sell_signal = price_change < -2
        df.loc[sell_signal, 'signal'] = -1
        df.loc[sell_signal, 'trigger_reason'] = "价格下跌超过2%"
        
        # 记录卖出信号数量
        sell_count = sell_signal.sum()
        if sell_count > 0:
            self.log(f"生成卖出信号 {sell_count} 个", "INFO")
        
        self.log("交易信号生成完成", "INFO")
        
        return df
`;

  // 初始化
  useEffect(() => {
    if (id) {
      setIsNew(false);
      fetchStrategyDetails(parseInt(id));
    } else {
      setStrategyCode(defaultStrategyCode);
    }
  }, [id]);

  // 获取策略详情
  const fetchStrategyDetails = async (strategyId: number) => {
    setLoading(true);
    try {
      const data = await getStrategy(strategyId);
      if (data) {
        form.setFieldsValue({
          name: data.name,
          description: data.description,
        });
        setStrategyCode(data.code || defaultStrategyCode);
        setStrategyTemplate(data.template || '');
      }
    } catch (error) {
      message.error('获取策略详情失败');
    } finally {
      setLoading(false);
    }
  };

  // 保存策略
  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      
      setLoading(true);
      const strategyData = {
        name: values.name,
        description: values.description,
        code: strategyCode,
        parameters: {},
        template: strategyTemplate,
      };
      
      let result;
      if (isNew) {
        result = await createStrategy(strategyData);
      } else if (id) {
        result = await updateStrategy(parseInt(id), strategyData);
      }
      
      if (result) {
        message.success(`策略${isNew ? '创建' : '更新'}成功`);
        if (isNew && result.id) {
          navigate(`/strategy/edit/${result.id}`);
          setIsNew(false);
        }
      }
    } catch (error: any) {
      if (error.message) {
        message.error(error.message);
      } else {
        message.error(`策略${isNew ? '创建' : '更新'}失败`);
      }
    } finally {
      setLoading(false);
    }
  };

  // 测试策略代码
  const handleTest = async () => {
    setTestLoading(true);
    try {
      const result = await testStrategy(strategyCode);
      
      if (result && !result.error) {
        Modal.success({
          title: '策略代码验证通过',
          content: (
            <div>
              <p>策略代码语法正确，可以正常运行。</p>
              {result.signals && (
                <p>测试生成了 {result.signals.length} 条数据记录。</p>
              )}
            </div>
          ),
        });
      } else {
        Modal.error({
          title: '策略代码验证失败',
          content: (
            <div>
              <p>策略代码存在问题，详细错误信息：</p>
              <pre style={{ maxHeight: '300px', overflow: 'auto' }}>
                {result.error || '未知错误'}
              </pre>
            </div>
          ),
        });
      }
    } catch (error) {
      message.error('测试策略代码失败');
    } finally {
      setTestLoading(false);
    }
  };

  // 返回列表页
  const handleBack = () => {
    navigate('/strategy');
  };

  return (
    <div style={{ padding: '20px' }}>
      <Spin spinning={loading} tip="加载中...">
        <Card>
          <Row gutter={[16, 16]}>
            <Col span={24}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
                <Space>
                  <Button icon={<ArrowLeftOutlined />} onClick={handleBack}>
                    返回
                  </Button>
                  <Title level={4} style={{ margin: 0 }}>
                    {isNew ? '创建新策略' : '编辑策略'}
                  </Title>
                </Space>
                <Space>
                  <Button 
                    type="primary" 
                    icon={<SaveOutlined />} 
                    onClick={handleSave}
                    loading={loading}
                  >
                    保存
                  </Button>
                  <Button 
                    icon={<PlayCircleOutlined />} 
                    onClick={handleTest}
                    loading={testLoading}
                  >
                    测试
                  </Button>
                </Space>
              </div>
            </Col>
            
            <Col span={24}>
              <Form
                form={form}
                layout="vertical"
              >
                <Row gutter={16}>
                  <Col span={12}>
                    <Form.Item
                      label="策略名称"
                      name="name"
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
                      <TextArea rows={1} placeholder="请输入策略描述" />
                    </Form.Item>
                  </Col>
                </Row>
              </Form>
            </Col>
            
            <Col span={24}>
              <Divider orientation="left">
                <Space>
                  <CodeOutlined />
                  <Text strong>策略代码</Text>
                </Space>
              </Divider>
              
              {/* Log函数使用说明 */}
              <div style={{ marginBottom: '16px' }}>
                <Alert
                  message="💡 策略日志功能"
                  description={
                    <div>
                      <p>您可以在策略中使用 <code>self.log(message, level)</code> 函数记录执行过程：</p>
                      <ul style={{ marginBottom: 0 }}>
                        <li><code>self.log("信息内容", "INFO")</code> - 记录一般信息</li>
                        <li><code>self.log("调试信息", "DEBUG")</code> - 记录调试信息</li>
                        <li><code>self.log("警告信息", "WARNING")</code> - 记录警告信息</li>
                        <li><code>self.log("错误信息", "ERROR")</code> - 记录错误信息</li>
                      </ul>
                      <p style={{ marginTop: '8px', marginBottom: 0 }}>
                        <Text type="secondary">日志将在回测历史的"控制台"按钮中查看，帮助您调试和监控策略执行过程。</Text>
                      </p>
                    </div>
                  }
                  type="info"
                  showIcon
                  style={{ marginBottom: '16px' }}
                />
              </div>
              
              <div style={{ border: '1px solid #d9d9d9', borderRadius: '2px' }}>
                <MonacoEditor
                  width="100%"
                  height="600"
                  language="python"
                  theme="vs-dark"
                  value={strategyCode}
                  onChange={setStrategyCode}
                  options={{
                    selectOnLineNumbers: true,
                    roundedSelection: false,
                    readOnly: false,
                    cursorStyle: 'line',
                    automaticLayout: true,
                    folding: true,
                    lineNumbers: 'on',
                    rulers: [80, 120],
                    minimap: { enabled: true },
                  }}
                />
              </div>
              
              <div style={{ marginTop: '8px' }}>
                <Text type="secondary">
                  注意：策略代码必须继承自StrategyTemplate基类，并实现generate_signals方法。
                </Text>
              </div>
            </Col>
          </Row>
        </Card>
      </Spin>
    </div>
  );
};

export default StrategyEditor; 