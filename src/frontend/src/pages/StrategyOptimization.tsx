import React, { useState, useEffect } from 'react';
import { Card, Form, Button, Select, InputNumber, Row, Col, Typography, message, Table, Space, Modal, Input, Progress, Tag, Alert, Tabs, Statistic } from 'antd';
import { PlayCircleOutlined, PlusOutlined, DeleteOutlined, SettingOutlined, EyeOutlined, ReloadOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import axios from 'axios';
import dayjs from 'dayjs';

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
  
  // 表单和模态框状态
  const [optimizationForm] = Form.useForm();
  const [parameterSpaceModalVisible, setParameterSpaceModalVisible] = useState(false);
  const [optimizationModalVisible, setOptimizationModalVisible] = useState(false);
  const [jobDetailModalVisible, setJobDetailModalVisible] = useState(false);
  const [selectedJob, setSelectedJob] = useState<OptimizationJob | null>(null);
  const [jobBacktestResult, setJobBacktestResult] = useState<any>(null);

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
        setOptimizationJobs(response.data.data);
      }
    } catch (error) {
      console.error('加载优化任务失败:', error);
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

  // 查看任务详情
  const handleViewJobDetail = async (job: OptimizationJob) => {
    try {
      setLoading(true);
      setSelectedJob(job);
      
      // 如果有最佳参数和优化配置，获取对应的回测结果
      if (job.best_parameters && job.status === 'completed' && job.optimization_config) {
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
        
        console.log('使用优化配置进行回测:', backtestRequest);
        
        const response = await axios.post('/api/strategies/backtest', backtestRequest);
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
          start_date: values.start_date,
          end_date: values.end_date,
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
      width: 80,
    },
    {
      title: '任务名称',
      dataIndex: 'name',
      key: 'name',
      width: 200,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
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
      width: 150,
      render: (progress: number, record: OptimizationJob) => (
        <div>
          <Progress percent={progress} size="small" />
          <Text type="secondary" style={{ fontSize: '12px' }}>
            {record.completed_trials}/{record.total_trials}
          </Text>
        </div>
      )
    },
    {
      title: '最佳得分',
      dataIndex: 'best_score',
      key: 'best_score',
      width: 120,
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
            <div>{score.toFixed(4)}</div>
            <Text type="secondary" style={{ fontSize: '12px' }}>{objectiveName}</Text>
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
        return (
          <div>
            {Object.entries(params).map(([key, value]) => (
              <Tag key={key} color="blue" style={{ marginBottom: '2px' }}>
                {key}: {value}
              </Tag>
            ))}
          </div>
        );
      }
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (time: string) => dayjs(time).format('YYYY-MM-DD HH:mm:ss')
    },
    {
      title: '操作',
      key: 'action',
      width: 120,
      render: (_, record: OptimizationJob) => (
        <Space>
          <Button
            type="link"
            icon={<EyeOutlined />}
            onClick={() => handleViewJobDetail(record)}
            size="small"
            disabled={record.status !== 'completed'}
          >
            查看回测
          </Button>
        </Space>
      )
    }
  ];

  useEffect(() => {
    loadStrategies();
    loadOptimizationJobs();
  }, []);
  
  return (
    <div style={{ padding: '24px' }}>
      <Card>
        <Title level={3}>策略参数优化</Title>
        
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

            <Table
          columns={jobColumns}
          dataSource={optimizationJobs}
          rowKey="id"
          pagination={{ pageSize: 10 }}
          loading={loading}
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
                rules={[{ required: true, message: '请输入交易品种' }]}
                initialValue="AAPL"
              >
                <Input placeholder="如: AAPL, TSLA" />
                </Form.Item>
              </Col>
              <Col span={12}>
              <Form.Item name="initial_capital" label="初始资金" initialValue={100000}>
                  <InputNumber 
                  min={1000} 
                    style={{ width: '100%' }} 
                  formatter={value => `¥ ${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
                  parser={value => value ? value.replace(/¥\s?|(,*)/g, '') : ''}
                  />
                </Form.Item>
              </Col>
            </Row>
            
          <Row gutter={[16, 16]}>
            <Col span={12}>
              <Form.Item 
                name="start_date" 
                label="开始日期" 
                rules={[{ required: true, message: '请输入开始日期' }]}
                initialValue="2023-01-01"
              >
                <Input placeholder="YYYY-MM-DD" />
                </Form.Item>
              </Col>
            <Col span={12}>
              <Form.Item 
                name="end_date" 
                label="结束日期" 
                rules={[{ required: true, message: '请输入结束日期' }]}
                initialValue="2024-12-31"
              >
                <Input placeholder="YYYY-MM-DD" />
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
                    <div style={{ marginTop: '8px' }}>
                      {Object.entries(selectedJob.best_parameters).map(([key, value]) => (
                        <Tag key={key} color="blue" style={{ marginBottom: '4px' }}>
                          {key === 'short_window' ? '短期均线' : 
                           key === 'long_window' ? '长期均线' : key}: {value}
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
    </div>
  );
};

export default StrategyOptimization; 