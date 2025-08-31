import React, { useState, useEffect } from 'react';
import { Card, Table, Button, Space, Modal, message, Tag, Typography, Descriptions, Statistic, Row, Col, Alert } from 'antd';
import { EyeOutlined, DeleteOutlined, ReloadOutlined, HistoryOutlined } from '@ant-design/icons';
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
  performance_metrics?: {
    total_return?: number;
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
  const [loading, setLoading] = useState(false);
  const [backtestList, setBacktestList] = useState<BacktestRecord[]>([]);
  const [detailModalVisible, setDetailModalVisible] = useState(false);
  const [selectedBacktest, setSelectedBacktest] = useState<BacktestDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  // 获取回测列表
  const fetchBacktestList = async () => {
    setLoading(true);
    try {
      const response = await axios.get('/api/backtest/list');
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
      const response = await axios.get(`/api/backtest/${id}`);
      if (response.data.status === 'success') {
        setSelectedBacktest(response.data.data);
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
          const response = await axios.delete(`/api/backtest/${id}`);
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

  // 表格列定义
  const columns: ColumnsType<BacktestRecord> = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 80,
    },
    {
      title: '回测名称',
      dataIndex: 'name',
      key: 'name',
      width: 200,
      render: (text: string) => <Text strong>{text}</Text>,
    },
    {
      title: '策略',
      dataIndex: 'strategy_name',
      key: 'strategy_name',
      width: 150,
      render: (text: string) => text || '-',
    },
    {
      title: '股票',
      dataIndex: 'instruments',
      key: 'instruments',
      width: 120,
      render: (instruments: string[]) => instruments.join(', '),
    },
    {
      title: '回测期间',
      key: 'date_range',
      width: 200,
      render: (_, record) => (
        <div>
          <div>{dayjs(record.start_date).format('YYYY-MM-DD')}</div>
          <div style={{ fontSize: '12px', color: '#999' }}>
            至 {dayjs(record.end_date).format('YYYY-MM-DD')}
          </div>
        </div>
      ),
    },
    {
      title: '初始资金',
      dataIndex: 'initial_capital',
      key: 'initial_capital',
      width: 120,
      render: (value: number) => `$${value.toLocaleString()}`,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
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
      title: '收益率',
      key: 'total_return',
      width: 120,
      render: (_, record) => {
        const returnValue = record.performance_metrics?.total_return;
        if (returnValue !== undefined) {
          const color = returnValue >= 0 ? '#52c41a' : '#ff4d4f';
          return <Text style={{ color }}>{returnValue >= 0 ? '+' : ''}{(returnValue * 100).toFixed(2)}%</Text>;
        }
        return '-';
      },
    },
    {
      title: '最大回撤',
      key: 'max_drawdown',
      width: 120,
      render: (_, record) => {
        const drawdown = record.performance_metrics?.max_drawdown;
        if (drawdown !== undefined) {
          return <Text type="danger">-{(drawdown * 100).toFixed(2)}%</Text>;
        }
        return '-';
      },
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (date: string) => dayjs(date).format('YYYY-MM-DD HH:mm'),
    },
    {
      title: '操作',
      key: 'actions',
      width: 150,
      render: (_, record) => (
        <Space>
          <Button
            type="link"
            icon={<EyeOutlined />}
            onClick={() => fetchBacktestDetail(record.id)}
            size="small"
          >
            查看
          </Button>
          <Button
            type="link"
            danger
            icon={<DeleteOutlined />}
            onClick={() => handleDeleteBacktest(record.id)}
            size="small"
          >
            删除
          </Button>
        </Space>
      ),
    },
  ];

  // 权益曲线图表配置
  const getEquityCurveOption = (equityCurve: any[]) => {
    if (!equityCurve || equityCurve.length === 0) {
      return {
        title: { text: '权益曲线', left: 'center' },
        xAxis: { type: 'category', data: [] },
        yAxis: { type: 'value' },
        series: [{ type: 'line', data: [] }],
      };
    }

    const dates = equityCurve.map(item => dayjs(item.date).format('MM-DD'));
    const values = equityCurve.map(item => item.equity);

    return {
      title: { text: '权益曲线', left: 'center' },
      tooltip: {
        trigger: 'axis',
        formatter: function (params: any) {
          const data = params[0];
          return `${data.name}<br/>权益: $${data.value.toLocaleString()}`;
        },
      },
      xAxis: {
        type: 'category',
        data: dates,
        axisLabel: { rotate: 45 },
      },
      yAxis: {
        type: 'value',
        axisLabel: {
          formatter: '${value}',
        },
      },
      series: [
        {
          type: 'line',
          data: values,
          smooth: true,
          lineStyle: { color: '#1890ff' },
          areaStyle: {
            color: {
              type: 'linear',
              x: 0,
              y: 0,
              x2: 0,
              y2: 1,
              colorStops: [
                { offset: 0, color: 'rgba(24, 144, 255, 0.3)' },
                { offset: 1, color: 'rgba(24, 144, 255, 0.1)' },
              ],
            },
          },
        },
      ],
    };
  };

  useEffect(() => {
    fetchBacktestList();
  }, []);

  return (
    <div style={{ padding: '24px' }}>
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
          pagination={{
            pageSize: 20,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total, range) => `第 ${range[0]}-${range[1]} 条，共 ${total} 条`,
          }}
          scroll={{ x: 1200 }}
        />
      </Card>

      {/* 回测详情模态框 */}
      <Modal
        title="回测详情"
        open={detailModalVisible}
        onCancel={() => setDetailModalVisible(false)}
        footer={null}
        width={1000}
        destroyOnClose
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
                      title="总收益率"
                      value={selectedBacktest.performance_metrics.total_return}
                      precision={4}
                      valueStyle={{ color: selectedBacktest.performance_metrics.total_return >= 0 ? '#3f8600' : '#cf1322' }}
                      suffix="%"
                    />
                  </Col>
                  <Col span={6}>
                    <Statistic
                      title="最大回撤"
                      value={selectedBacktest.performance_metrics.max_drawdown}
                      precision={4}
                      valueStyle={{ color: '#cf1322' }}
                      suffix="%"
                    />
                  </Col>
                  <Col span={6}>
                    <Statistic
                      title="夏普比率"
                      value={selectedBacktest.performance_metrics.sharpe_ratio}
                      precision={2}
                    />
                  </Col>
                  <Col span={6}>
                    <Statistic
                      title="胜率"
                      value={selectedBacktest.performance_metrics.win_rate}
                      precision={2}
                      suffix="%"
                    />
                  </Col>
                </Row>
              </Card>
            )}

            {/* 权益曲线 */}
            {selectedBacktest.equity_curve && selectedBacktest.equity_curve.length > 0 ? (
              <Card title="权益曲线" style={{ marginBottom: 24 }}>
                <ReactECharts
                  option={getEquityCurveOption(selectedBacktest.equity_curve)}
                  style={{ height: 400 }}
                />
              </Card>
            ) : (
              <Alert
                message="暂无权益曲线数据"
                description="该回测记录没有保存权益曲线数据"
                type="info"
                showIcon
                style={{ marginBottom: 24 }}
              />
            )}

            {/* 策略信息 */}
            {selectedBacktest.strategy_info && (
              <Card title="策略信息" style={{ marginBottom: 24 }}>
                <Descriptions bordered column={1}>
                  <Descriptions.Item label="策略描述">
                    {selectedBacktest.strategy_info.description || '-'}
                  </Descriptions.Item>
                  <Descriptions.Item label="策略代码">
                    <pre style={{ maxHeight: 200, overflow: 'auto', fontSize: '12px' }}>
                      {selectedBacktest.strategy_info.code}
                    </pre>
                  </Descriptions.Item>
                  <Descriptions.Item label="策略参数">
                    {selectedBacktest.strategy_info.parameters || '{}'}
                  </Descriptions.Item>
                </Descriptions>
              </Card>
            )}

            {/* 仓位配置 */}
            {selectedBacktest.position_config && (
              <Card title="仓位配置">
                <pre style={{ maxHeight: 200, overflow: 'auto' }}>
                  {JSON.stringify(selectedBacktest.position_config, null, 2)}
                </pre>
              </Card>
            )}
          </div>
        )}
      </Modal>
    </div>
  );
};

export default BacktestHistory;
