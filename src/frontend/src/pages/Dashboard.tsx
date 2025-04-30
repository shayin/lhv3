import React from 'react';
import { Row, Col, Card, Statistic, Button, List, Typography } from 'antd';
import { LineChartOutlined, RiseOutlined, AreaChartOutlined, ArrowUpOutlined, ArrowDownOutlined } from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';

const { Title, Paragraph } = Typography;

const Dashboard: React.FC = () => {
  // 示例数据：市场概况
  const marketOverview = [
    { name: '上证指数', value: 3536.24, change: 0.84, color: '#f5222d' },
    { name: '深证成指', value: 14672.16, change: 1.26, color: '#f5222d' },
    { name: '创业板指', value: 3213.84, change: 1.78, color: '#f5222d' },
    { name: '恒生指数', value: 26386.25, change: -0.13, color: '#52c41a' },
  ];

  // 示例数据：最近的回测结果
  const recentBacktests = [
    { id: 1, name: '移动平均交叉策略', symbol: 'AAPL', return: 12.5, date: '2023-09-15' },
    { id: 2, name: 'RSI策略', symbol: 'MSFT', return: 8.3, date: '2023-09-14' },
    { id: 3, name: 'MACD策略', symbol: 'GOOGL', return: -2.1, date: '2023-09-13' },
    { id: 4, name: '布林带策略', symbol: 'AMZN', return: 5.7, date: '2023-09-12' },
  ];
  
  // 图表选项：示例权益曲线
  const equityChartOption = {
    title: {
      text: '策略绩效比较',
      left: 'center'
    },
    tooltip: {
      trigger: 'axis',
      formatter: '{a} <br/>{b}: {c} ({d}%)'
    },
    legend: {
      data: ['移动平均交叉', 'RSI策略', 'MACD策略', '布林带策略', '沪深300'],
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
      data: ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月']
    },
    yAxis: {
      type: 'value',
      name: '累计收益率(%)',
      axisLabel: {
        formatter: '{value}%'
      }
    },
    series: [
      {
        name: '移动平均交叉',
        type: 'line',
        data: [0, 2.3, 5.8, 9.2, 12.5, 15.1, 18.6, 22.4, 25.2]
      },
      {
        name: 'RSI策略',
        type: 'line',
        data: [0, 1.5, 3.8, 6.2, 8.5, 10.1, 12.6, 14.4, 16.2]
      },
      {
        name: 'MACD策略',
        type: 'line',
        data: [0, -1.3, 1.8, 3.2, 5.5, 8.1, 10.6, 13.4, 15.2]
      },
      {
        name: '布林带策略',
        type: 'line',
        data: [0, 3.3, 2.8, 5.2, 8.5, 12.1, 15.6, 18.4, 21.2]
      },
      {
        name: '沪深300',
        type: 'line',
        data: [0, 1.3, 2.8, 3.2, 2.5, 4.1, 5.6, 4.4, 6.2],
        lineStyle: {
          type: 'dashed'
        }
      }
    ]
  };

  // 图表选项：资产分布
  const assetAllocationOption = {
    title: {
      text: '最优资产配置',
      left: 'center'
    },
    tooltip: {
      trigger: 'item',
      formatter: '{a} <br/>{b}: {c} ({d}%)'
    },
    legend: {
      orient: 'vertical',
      left: 10,
      data: ['股票', '债券', '商品', '外汇', '现金']
    },
    series: [
      {
        name: '资产配置',
        type: 'pie',
        radius: ['50%', '70%'],
        avoidLabelOverlap: false,
        label: {
          show: false,
          position: 'center'
        },
        emphasis: {
          label: {
            show: true,
            fontSize: '18',
            fontWeight: 'bold'
          }
        },
        labelLine: {
          show: false
        },
        data: [
          { value: 45, name: '股票' },
          { value: 25, name: '债券' },
          { value: 15, name: '商品' },
          { value: 10, name: '外汇' },
          { value: 5, name: '现金' }
        ]
      }
    ]
  };

  return (
    <div>
      <Title level={2}>仪表盘</Title>
      <Paragraph>欢迎使用量化交易系统，您可以在这里查看市场概况和您的策略表现。</Paragraph>
      
      <Row gutter={16}>
        <Col span={6}>
          <Card>
            <Statistic
              title="本月最佳策略"
              value="移动平均交叉"
              prefix={<RiseOutlined />}
              valueStyle={{ color: '#3f8600' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="最佳策略收益"
              value={25.2}
              precision={2}
              valueStyle={{ color: '#3f8600' }}
              prefix={<ArrowUpOutlined />}
              suffix="%"
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="最差策略收益"
              value={-2.1}
              precision={2}
              valueStyle={{ color: '#cf1322' }}
              prefix={<ArrowDownOutlined />}
              suffix="%"
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="策略总数"
              value={8}
              prefix={<AreaChartOutlined />}
            />
          </Card>
        </Col>
      </Row>
      
      <Row gutter={16} style={{ marginTop: '16px' }}>
        <Col span={12}>
          <Card title="主要市场指数" extra={<Button type="link">查看更多</Button>}>
            <List
              dataSource={marketOverview}
              renderItem={item => (
                <List.Item>
                  <List.Item.Meta
                    title={item.name}
                  />
                  <div>{item.value}</div>
                  <div style={{ color: item.color, marginLeft: '16px' }}>
                    {item.change > 0 ? '+' : ''}{item.change}%
                  </div>
                </List.Item>
              )}
            />
          </Card>
        </Col>
        <Col span={12}>
          <Card title="最近的回测" extra={<Button type="link">查看全部</Button>}>
            <List
              dataSource={recentBacktests}
              renderItem={item => (
                <List.Item>
                  <List.Item.Meta
                    title={item.name}
                    description={`${item.symbol} | ${item.date}`}
                  />
                  <div style={{ color: item.return > 0 ? '#3f8600' : '#cf1322', fontWeight: 'bold' }}>
                    {item.return > 0 ? '+' : ''}{item.return}%
                  </div>
                </List.Item>
              )}
            />
          </Card>
        </Col>
      </Row>
      
      <Row gutter={16} style={{ marginTop: '16px' }}>
        <Col span={16}>
          <Card title="策略绩效比较" extra={<Button type="link" icon={<LineChartOutlined />}>详细分析</Button>}>
            <div className="chart-container">
              <ReactECharts option={equityChartOption} style={{ height: '100%' }} />
            </div>
          </Card>
        </Col>
        <Col span={8}>
          <Card title="最优资产配置">
            <div className="chart-container">
              <ReactECharts option={assetAllocationOption} style={{ height: '100%' }} />
            </div>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default Dashboard; 