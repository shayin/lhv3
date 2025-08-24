import React, { useState, useEffect } from 'react';
import {
  Table, Button, Upload, message, Modal, Input, Select, Form, 
  Card, Space, Typography, Spin, Tag, Tooltip, Row, Col, Checkbox,
  Radio, DatePicker, Divider
} from 'antd';
import {
  UploadOutlined, DownloadOutlined, DeleteOutlined, 
  SyncOutlined, QuestionCircleOutlined, FilePdfOutlined,
  LineChartOutlined
} from '@ant-design/icons';
import type { UploadProps } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import axios from 'axios';
import ReactECharts from 'echarts-for-react';
import { fetchStockList, fetchDataSources, fetchChartData, Stock, DataSource } from '../services/apiService';
import dayjs from 'dayjs';

const { Title, Text } = Typography;
const { Option } = Select;

// 日期范围快捷选项
const DateRangePresets = ({ onSelect }: { onSelect: (startDate: string, endDate: string) => void }) => {
  const presets = [
    { label: '最近7天', days: 7 },
    { label: '最近30天', days: 30 },
    { label: '最近90天', days: 90 },
    { label: '最近180天', days: 180 },
    { label: '最近1年', days: 365 },
    { label: '最近2年', days: 730 },
    { label: '最近3年', days: 1095 },
    { label: '最近4年', days: 1460 },
    { label: '最近5年', days: 1825 },
    { label: '最近10年', days: 3650 },
    { label: '今年', type: 'year' },
    { label: '去年', type: 'lastYear' },
    { label: '本月', type: 'month' },
    { label: '上月', type: 'lastMonth' },
  ];

  const handlePresetClick = (preset: any) => {
    const now = dayjs();
    let startDate: string, endDate: string;

    if (preset.type === 'year') {
      startDate = now.startOf('year').format('YYYY-MM-DD');
      endDate = now.format('YYYY-MM-DD');
    } else if (preset.type === 'lastYear') {
      startDate = now.subtract(1, 'year').startOf('year').format('YYYY-MM-DD');
      endDate = now.subtract(1, 'year').endOf('year').format('YYYY-MM-DD');
    } else if (preset.type === 'month') {
      startDate = now.startOf('month').format('YYYY-MM-DD');
      endDate = now.format('YYYY-MM-DD');
    } else if (preset.type === 'lastMonth') {
      startDate = now.subtract(1, 'month').startOf('month').format('YYYY-MM-DD');
      endDate = now.subtract(1, 'month').endOf('month').format('YYYY-MM-DD');
    } else {
      startDate = now.subtract(preset.days, 'day').format('YYYY-MM-DD');
      endDate = now.format('YYYY-MM-DD');
    }

    onSelect(startDate, endDate);
  };

  return (
    <div style={{ marginBottom: 16 }}>
      <Text strong style={{ marginBottom: 8, display: 'block' }}>快捷选择：</Text>
      <Space wrap>
        {presets.map((preset, index) => (
          <Button
            key={index}
            size="small"
            type="link"
            onClick={() => handlePresetClick(preset)}
            style={{ padding: '4px 8px', fontSize: '12px' }}
          >
            {preset.label}
          </Button>
        ))}
      </Space>
    </div>
  );
};

// 计算移动平均线的函数
const calculateMA = (dayCount: number, data: any[]) => {
  const result = [];
  for (let i = 0, len = data.length; i < len; i++) {
    if (i < dayCount - 1) {
      result.push('-');
      continue;
    }
    let sum = 0;
    for (let j = 0; j < dayCount; j++) {
      sum += data[i - j].close;
    }
    result.push((sum / dayCount).toFixed(2));
  }
  return result;
};

// 定义数据类型
interface DataItem {
  id: string;
  symbol: string;
  name: string;
  type: string;
  exchange?: string;
  startDate?: string;
  endDate?: string;
  first_date?: string;
  last_date?: string;
  records: number;
  source: string;
  last_updated?: string;
}

const DataManagement: React.FC = () => {
  // 状态定义
  const [dataList, setDataList] = useState<DataItem[]>([]);
  const [dataSources, setDataSources] = useState<DataSource[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [uploadVisible, setUploadVisible] = useState<boolean>(false);
  const [fileList, setFileList] = useState<any[]>([]);
  const [form] = Form.useForm();
  const [uploadMode, setUploadMode] = useState<'upload' | 'fetch'>('fetch'); // 新增：上传模式
  const [fetchLoading, setFetchLoading] = useState(false); // 新增：抓取加载状态
  
  // K线图相关状态
  const [chartVisible, setChartVisible] = useState<boolean>(false);
  const [currentStock, setCurrentStock] = useState<DataItem | null>(null);
  const [chartData, setChartData] = useState<any[]>([]);
  const [chartLoading, setChartLoading] = useState<boolean>(false);

  // 初始化加载
  useEffect(() => {
    fetchList();
    fetchSourcesList();
  }, []);

  // 获取数据列表
  const fetchList = async () => {
    setLoading(true);
    try {
      const stocks = await fetchStockList();
      
      // 转换为DataItem格式，直接使用stocks表的统计信息
      const formattedData = stocks.map(stock => ({
        id: stock.id.toString(),
        symbol: stock.symbol,
        name: stock.name,
        type: stock.type || '未知',
        exchange: stock.exchange,
        records: stock.data_count || 0,
        source: stock.source_id?.toString() || '未知',
        last_updated: stock.last_updated ? new Date(stock.last_updated).toLocaleString() : '未知',
        first_date: stock.first_date || undefined,
        last_date: stock.last_date || undefined
      }));
      
      setDataList(formattedData);
    } catch (error) {
      console.error('获取数据列表失败:', error);
      message.error('获取数据列表失败，请检查网络连接');
    } finally {
      setLoading(false);
    }
  };

  // 获取数据源列表
  const fetchSourcesList = async () => {
    try {
      const sources = await fetchDataSources();
      setDataSources(sources);
      
      // 设置默认数据源
      if (uploadMode === 'fetch') {
        const akShareSource = sources.find(source => source.name === 'AkShare抓取');
        if (akShareSource) {
          form.setFieldsValue({ source_id: akShareSource.id });
        }
      } else if (uploadMode === 'upload') {
        const userUploadSource = sources.find(source => source.name === '用户上传');
        if (userUploadSource) {
          form.setFieldsValue({ source_id: userUploadSource.id });
        }
      }
    } catch (error) {
      console.error('获取数据源列表失败:', error);
      message.error('获取数据源列表失败');
    }
  };

  // 处理数据下载
  const handleDownload = async (id: string) => {
    setLoading(true);
    try {
      // 使用axios直接下载文件
      const response = await axios.get(`/api/data/download/${id}`, {
        responseType: 'blob', // 指定响应类型为blob
      });
      
      // 创建下载链接
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      
      // 从响应头获取文件名，如果没有则使用默认文件名
      const contentDisposition = response.headers['content-disposition'];
      let filename = 'stock_data.csv';
      
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename="?(.+)"?/);
        if (filenameMatch && filenameMatch.length === 2) {
          filename = filenameMatch[1];
        }
      }
      
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      
      message.success('数据下载成功');
    } catch (error) {
      console.error('下载失败:', error);
      message.error('下载失败，请重试');
    } finally {
      setLoading(false);
    }
  };

  // 处理数据删除
  const handleDelete = async (id: string) => {
    Modal.confirm({
      title: '确认删除',
      content: '此操作将永久删除该数据，是否继续？',
      okText: '确认',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        setLoading(true);
        try {
          const response = await axios.delete(`/api/data/delete/${id}`);
          if (response.data && response.data.status === 'success') {
            message.success(response.data.message || '删除成功');
            fetchList(); // 刷新列表
          } else {
            message.error(response.data?.message || '删除失败');
          }
        } catch (error) {
          console.error('删除失败:', error);
          message.error('删除失败，请重试');
        } finally {
          setLoading(false);
        }
      },
    });
  };

  // 处理上传前检查
  const beforeUpload = (file: any) => {
    const isCsv = file.type === 'text/csv' || file.name.endsWith('.csv');
    if (!isCsv) {
      message.error('只能上传CSV文件!');
    }
    return isCsv;
  };

  // 处理文件上传
  const handleUpload = async (values: any) => {
    if (fileList.length === 0) {
      message.error('请选择要上传的文件');
      return;
    }

    // 只在formData中放文件
    const formData = new FormData();
    formData.append('file', fileList[0]);
    
    // 构建URL查询参数
    const params = new URLSearchParams({
      symbol: values.symbol,
      name: values.name,
      type: values.type,
      source_id: values.source_id.toString()
    });
    
    // 可选字段
    if (values.exchange) {
      params.append('exchange', values.exchange);
    }
    
    // 拼接完整URL
    const url = `/api/data/upload?${params.toString()}`;

    setLoading(true);
    try {
      const response = await axios.post(url, formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });
      
      if (response.data && response.data.status === 'success') {
        message.success(response.data.message || '上传成功');
        setUploadVisible(false);
        form.resetFields();
        setFileList([]);
        fetchList(); // 刷新列表
      } else {
        message.error(response.data?.message || '上传失败');
      }
    } catch (error: any) {
      console.error('上传失败:', error);
      
      // 安全地处理错误信息，确保不会渲染对象
      const detail = error.response?.data?.detail;
      if (detail) {
        // 如果detail是对象，将其转为字符串
        if (typeof detail === 'object') {
          message.error(JSON.stringify(detail));
        } else {
          message.error(detail);
        }
      } else {
        message.error('上传失败，请重试');
      }
    } finally {
      setLoading(false);
    }
  };

  // 处理自动抓取数据
  const handleFetch = async (values: any) => {
    setFetchLoading(true);
    try {
      // 构建请求体
      const payload = {
        symbol: values.symbol,
        name: values.name,
        type: values.type,
        source_id: values.source_id,
        start_date: values.start_date ? values.start_date.format('YYYY-MM-DD') : undefined,
        end_date: values.end_date ? values.end_date.format('YYYY-MM-DD') : undefined,
      };

      const response = await axios.post('/api/data/fetch', payload, {
        headers: {
          'Content-Type': 'application/json'
        }
      });
      
      if (response.data && response.data.status === 'success') {
        message.success(response.data.message || '数据抓取成功');
        setUploadVisible(false);
        form.resetFields();
        fetchList(); // 刷新列表
      } else {
        message.error(response.data?.message || '数据抓取失败');
      }
    } catch (error: any) {
      console.error('数据抓取失败:', error);
      
      // 安全地处理错误信息
      const detail = error.response?.data?.detail;
      if (detail) {
        if (typeof detail === 'object') {
          message.error(JSON.stringify(detail));
        } else {
          message.error(detail);
        }
      } else {
        message.error('数据抓取失败，请重试');
      }
    } finally {
      setFetchLoading(false);
    }
  };

  // 处理刷新数据
  const handleRefreshData = async (record: DataItem) => {
    Modal.confirm({
      title: '更新数据',
      content: `确定要更新 ${record.name}(${record.symbol}) 的数据吗？将从最后一天K线抓取到今天的最新数据。`,
      onOk: async () => {
        setLoading(true);
        try {
          // 查找对应的数据源ID
          const sourceId = dataSources.find(s => s.id.toString() === record.source)?.id;
          if (!sourceId) {
            message.error('找不到对应的数据源');
            return;
          }
          
          // 使用update接口更新数据
          const response = await axios.post(`/api/data/update/${record.id}`);
          
          if (response.data && response.data.status === 'success') {
            message.success(response.data.message || '数据更新成功');
            fetchList(); // 刷新列表
          } else {
            message.error(response.data?.message || '数据更新失败');
          }
        } catch (error: any) {
          console.error('更新数据失败:', error);
          
          // 安全地处理错误信息
          const detail = error.response?.data?.detail;
          if (detail) {
            if (typeof detail === 'object') {
              message.error(JSON.stringify(detail));
            } else {
              message.error(detail);
            }
          } else {
            message.error('更新数据失败，请重试');
          }
        } finally {
          setLoading(false);
        }
      },
    });
  };

  // 处理查看K线图
  const handleViewChart = async (record: DataItem) => {
    setCurrentStock(record);
    setChartVisible(true);
    setChartLoading(true);
    
    try {
      const chartResult = await fetchChartData(record.id);
      if (chartResult && chartResult.data) {
        setChartData(chartResult.data);
      } else {
        setChartData([]);
        message.warning('未获取到图表数据');
      }
    } catch (error: any) {
      console.error('获取图表数据失败:', error);
      
      // 安全地处理错误信息
      const detail = error.response?.data?.detail;
      if (detail) {
        if (typeof detail === 'object') {
          message.error(JSON.stringify(detail));
        } else {
          message.error(detail);
        }
      } else {
        message.error('获取图表数据失败，请重试');
      }
      setChartData([]);
    } finally {
      setChartLoading(false);
    }
  };

  // 表格列定义
  const columns: ColumnsType<DataItem> = [
    {
      title: '代码',
      dataIndex: 'symbol',
      key: 'symbol',
      width: 100,
    },
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
      width: 120,
    },
    {
      title: '类型',
      dataIndex: 'type',
      key: 'type',
      width: 80,
      render: (text) => <Tag color="blue">{text}</Tag>
    },
    {
      title: '交易所',
      dataIndex: 'exchange',
      key: 'exchange',
      width: 80,
    },
    {
      title: '记录数',
      dataIndex: 'records',
      key: 'records',
      width: 80,
      sorter: (a, b) => a.records - b.records,
    },
    {
      title: '数据时间范围',
      key: 'date_range',
      width: 200,
      render: (_, record) => {
        if (record.first_date && record.last_date) {
          return (
            <div>
              <div style={{ fontSize: '12px', color: '#666' }}>
                {record.first_date} 至 {record.last_date}
              </div>
              <div style={{ fontSize: '11px', color: '#999' }}>
                {record.records} 条记录
              </div>
            </div>
          );
        } else if (record.records > 0) {
          return <span style={{ color: '#999' }}>时间范围未知</span>;
        } else {
          return <span style={{ color: '#ccc' }}>无数据</span>;
        }
      }
    },
    {
      title: '数据源',
      dataIndex: 'source',
      key: 'source',
      width: 100,
    },
    {
      title: '最后更新',
      dataIndex: 'last_updated',
      key: 'last_updated',
      width: 150,
    },
    {
      title: '操作',
      key: 'action',
      width: 280,
      render: (_, record) => (
        <Space size="small">
          <Button 
            type="primary" 
            icon={<DownloadOutlined />} 
            size="small" 
            onClick={() => handleDownload(record.id)}
          >
            下载
          </Button>
          <Button 
            icon={<LineChartOutlined />} 
            size="small"
            onClick={() => handleViewChart(record)}
          >
            K线图
          </Button>
          <Button 
            icon={<SyncOutlined />} 
            size="small" 
            onClick={() => handleRefreshData(record)}
          >
            更新
          </Button>
          <Button 
            danger 
            icon={<DeleteOutlined />} 
            size="small" 
            onClick={() => handleDelete(record.id)}
          >
            删除
          </Button>
        </Space>
      ),
    },
  ];

  // 上传组件属性
  const uploadProps: UploadProps = {
    onRemove: () => {
      setFileList([]);
    },
    beforeUpload: (file) => {
      if (beforeUpload(file)) {
        setFileList([file]);
      }
      return false; // 阻止自动上传
    },
    fileList,
  };

  return (
    <div className="data-management">
      <Card>
        <Row justify="space-between" align="middle" style={{ marginBottom: 16 }}>
          <Col>
            <Title level={4}>市场数据管理</Title>
          </Col>
          <Col>
            <Space>
              <Button 
                type="primary" 
                icon={<UploadOutlined />} 
                onClick={() => setUploadVisible(true)}
              >
                添加数据
              </Button>
              <Button 
                icon={<SyncOutlined />} 
                onClick={fetchList}
              >
                刷新列表
              </Button>
              <Tooltip title="CSV格式说明">
                <Button 
                  icon={<FilePdfOutlined />} 
                  href="/docs/data_format.pdf" 
                  target="_blank"
                >
                  数据格式
                </Button>
              </Tooltip>
            </Space>
          </Col>
        </Row>

        <Spin spinning={loading}>
          <Table 
            columns={columns} 
            dataSource={dataList} 
            rowKey="id" 
            bordered 
            size="middle"
            pagination={{ pageSize: 10 }}
          />
        </Spin>
      </Card>

      {/* 上传数据弹窗 */}
      <Modal
        title="市场数据管理"
        open={uploadVisible}
        onCancel={() => setUploadVisible(false)}
        footer={null}
        width={600}
      >
        {/* 模式切换 */}
        <div style={{ marginBottom: 20, textAlign: 'center' }}>
                    <Radio.Group
            value={uploadMode}
            onChange={(e) => {
              setUploadMode(e.target.value);
              form.resetFields();
              
              // 根据模式设置默认数据源
              if (e.target.value === 'fetch') {
                // 自动抓取模式：默认选择AkShare抓取
                const akShareSource = dataSources.find(source => source.name === 'AkShare抓取');
                if (akShareSource) {
                  form.setFieldsValue({ source_id: akShareSource.id });
                }
              } else if (e.target.value === 'upload') {
                // 手动上传模式：默认选择用户上传
                const userUploadSource = dataSources.find(source => source.name === '用户上传');
                if (userUploadSource) {
                  form.setFieldsValue({ source_id: userUploadSource.id });
                }
              }
            }}
            buttonStyle="solid"
          >
            <Radio.Button value="fetch">自动抓取</Radio.Button>
            <Radio.Button value="upload">手动上传</Radio.Button>
          </Radio.Group>
        </div>

        <Form
          form={form}
          layout="vertical"
          onFinish={uploadMode === 'fetch' ? handleFetch : handleUpload}
        >
          {/* 自动抓取模式 */}
          {uploadMode === 'fetch' && (
            <>
              <Form.Item
                name="symbol"
                label="股票代码"
                rules={[{ required: true, message: '请输入股票代码' }]}
              >
                <Input placeholder="例如: AAPL, 600519, TSLA" />
              </Form.Item>
              
              <Form.Item
                name="name"
                label="股票名称"
                rules={[{ required: true, message: '请输入股票名称' }]}
              >
                <Input placeholder="例如: 苹果公司, 贵州茅台, 特斯拉" />
              </Form.Item>
              
              <Form.Item
                name="type"
                label="股票类型"
                rules={[{ required: true, message: '请选择股票类型' }]}
              >
                <Select placeholder="选择股票类型">
                  <Option value="A股">A股</Option>
                  <Option value="港股">港股</Option>
                  <Option value="美股">美股</Option>
                  <Option value="期货">期货</Option>
                  <Option value="指数">指数</Option>
                  <Option value="加密货币">加密货币</Option>
                </Select>
              </Form.Item>
              
              <Form.Item
                name="source_id"
                label="数据源"
                rules={[{ required: true, message: '请选择数据源' }]}
              >
                <Select placeholder="选择数据源" disabled>
                  {dataSources.filter(source => source.name === 'AkShare抓取').map(source => (
                    <Option key={source.id} value={source.id}>{source.name}</Option>
                  ))}
                </Select>
              </Form.Item>
              
              <Form.Item label="日期范围">
                <DateRangePresets 
                  onSelect={(startDate, endDate) => {
                    form.setFieldsValue({
                      start_date: dayjs(startDate),
                      end_date: dayjs(endDate)
                    });
                  }}
                />
                <Row gutter={8}>
                  <Col span={12}>
                    <Form.Item
                      name="start_date"
                      noStyle
                    >
                      <DatePicker 
                        placeholder="选择开始日期" 
                        style={{ width: '100%' }}
                        format="YYYY-MM-DD"
                      />
                    </Form.Item>
                  </Col>
                  <Col span={12}>
                    <Form.Item
                      name="end_date"
                      noStyle
                    >
                      <DatePicker 
                        placeholder="选择结束日期" 
                        style={{ width: '100%' }}
                        format="YYYY-MM-DD"
                      />
                    </Form.Item>
                  </Col>
                </Row>
              </Form.Item>
              
              <Form.Item>
                <Space>
                  <Button 
                    type="primary" 
                    htmlType="submit" 
                    loading={fetchLoading}
                    icon={<SyncOutlined />}
                  >
                    开始抓取
                  </Button>
                  <Button onClick={() => setUploadVisible(false)}>
                    取消
                  </Button>
                </Space>
              </Form.Item>
            </>
          )}

          {/* 手动上传模式 */}
          {uploadMode === 'upload' && (
            <>
              <Form.Item
                name="file"
                label="数据文件"
                rules={[{ required: true, message: '请选择要上传的CSV文件' }]}
              >
                <Upload {...uploadProps}>
                  <Button icon={<UploadOutlined />}>选择CSV文件</Button>
                  <Text type="secondary" style={{ marginLeft: 8 }}>
                    仅支持CSV格式的数据文件
                  </Text>
                </Upload>
              </Form.Item>
              
              <Form.Item
                name="symbol"
                label="股票代码"
                rules={[{ required: true, message: '请输入股票代码' }]}
              >
                <Input placeholder="例如: AAPL, 600000.SH" />
              </Form.Item>
              
              <Form.Item
                name="name"
                label="股票名称"
                rules={[{ required: true, message: '请输入股票名称' }]}
              >
                <Input placeholder="例如: 苹果公司, 浦发银行" />
              </Form.Item>
              
              <Form.Item
                name="type"
                label="股票类型"
                rules={[{ required: true, message: '请选择股票类型' }]}
              >
                <Select placeholder="选择股票类型">
                  <Option value="A股">A股</Option>
                  <Option value="港股">港股</Option>
                  <Option value="美股">美股</Option>
                  <Option value="期货">期货</Option>
                  <Option value="指数">指数</Option>
                  <Option value="加密货币">加密货币</Option>
                </Select>
              </Form.Item>
              
              <Form.Item
                name="exchange"
                label="交易所"
              >
                <Input placeholder="例如: NYSE, SSE" />
              </Form.Item>
              
              <Form.Item
                name="source_id"
                label="数据源"
                rules={[{ required: true, message: '请选择数据源' }]}
              >
                <Select placeholder="选择数据源" disabled>
                  {dataSources.filter(source => source.name === '用户上传').map(source => (
                    <Option key={source.id} value={source.id}>{source.name}</Option>
                  ))}
                </Select>
              </Form.Item>
              
              <Form.Item>
                <Space>
                  <Button type="primary" htmlType="submit" loading={loading}>
                    上传数据
                  </Button>
                  <Button onClick={() => setUploadVisible(false)}>
                    取消
                  </Button>
                </Space>
              </Form.Item>
            </>
          )}
        </Form>
      </Modal>

      {/* K线图对话框 */}
      <Modal
        title={currentStock ? `${currentStock.name}(${currentStock.symbol}) K线图` : 'K线图'}
        open={chartVisible}
        onCancel={() => setChartVisible(false)}
        footer={null}
        width={800}
      >
        <Spin spinning={chartLoading}>
          {chartData.length > 0 ? (
            <div style={{ height: '500px', width: '100%' }}>
              <ReactECharts
                option={{
                  backgroundColor: '#fff',
                  title: {
                    text: currentStock?.symbol,
                    left: 'center',
                    top: 10,
                    textStyle: {
                      fontSize: 16,
                      fontWeight: 'bold'
                    },
                    // subtext: '股票历史K线',
                    subtextStyle: {
                      color: '#888'
                    }
                  },
                  tooltip: {
                    trigger: 'axis',
                    axisPointer: {
                      type: 'cross',
                      label: {
                        backgroundColor: '#555'
                      }
                    },
                    backgroundColor: 'rgba(255, 255, 255, 0.8)',
                    borderWidth: 1,
                    borderColor: '#ccc',
                    padding: 10,
                    textStyle: {
                      color: '#333'
                    }
                  },
                  legend: {
                    data: ['K线', 'MA5', 'MA10'],
                    top: 35,
                    selected: {
                      'K线': true,
                      'MA5': true,
                      'MA10': true
                    }
                  },
                  toolbox: {
                    feature: {
                      dataZoom: {
                        yAxisIndex: [0, 1]
                      },
                      brush: {
                        type: ['lineX', 'clear']
                      },
                      restore: {},
                      saveAsImage: {}
                    }
                  },
                  brush: {
                    xAxisIndex: 'all',
                    brushLink: 'all',
                    outOfBrush: {
                      colorAlpha: 0.1
                    }
                  },
                  grid: [
                    {
                      left: '10%',
                      right: '10%',
                      top: 80,
                      height: '60%'
                    },
                    {
                      left: '10%',
                      right: '10%',
                      top: '75%',
                      height: '15%'
                    }
                  ],
                  xAxis: [
                    {
                      type: 'category',
                      data: chartData.map(item => item.time),
                      scale: true,
                      boundaryGap: false,
                      axisLine: { onZero: false },
                      splitLine: { show: false },
                      splitNumber: 20,
                      min: 'dataMin',
                      max: 'dataMax',
                      axisPointer: {
                        z: 100
                      }
                    },
                    {
                      type: 'category',
                      gridIndex: 1,
                      data: chartData.map(item => item.time),
                      scale: true,
                      boundaryGap: false,
                      axisLine: { onZero: false },
                      axisTick: { show: false },
                      splitLine: { show: false },
                      axisLabel: { show: false },
                      splitNumber: 20,
                      min: 'dataMin',
                      max: 'dataMax'
                    }
                  ],
                  yAxis: [
                    {
                      scale: true,
                      splitArea: {
                        show: true
                      },
                      splitLine: {
                        show: true
                      }
                    },
                    {
                      scale: true,
                      gridIndex: 1,
                      splitNumber: 2,
                      axisLabel: { show: false },
                      axisLine: { show: false },
                      axisTick: { show: false },
                      splitLine: { show: false }
                    }
                  ],
                  dataZoom: [
                    {
                      type: 'inside',
                      xAxisIndex: [0, 1],
                      start: 50,
                      end: 100
                    },
                    {
                      show: true,
                      xAxisIndex: [0, 1],
                      type: 'slider',
                      bottom: 10,
                      start: 50,
                      end: 100
                    }
                  ],
                  visualMap: {
                    show: false,
                    seriesIndex: 3,
                    dimension: 2,
                    pieces: [
                      {
                        value: 1,
                        color: '#ef232a'
                      },
                      {
                        value: -1,
                        color: '#14b143'
                      }
                    ]
                  },
                  series: [
                    {
                      name: 'K线',
                      type: 'candlestick',
                      data: chartData.map(item => [
                        item.open,  // 开盘价
                        item.close,  // 收盘价
                        item.low,   // 最低价
                        item.high,  // 最高价
                      ]),
                      itemStyle: {
                        color: '#ef232a',
                        color0: '#14b143',
                        borderColor: '#ef232a',
                        borderColor0: '#14b143'
                      }
                    },
                    {
                      name: 'MA5',
                      type: 'line',
                      data: calculateMA(5, chartData),
                      smooth: true,
                      lineStyle: {
                        width: 1,
                        opacity: 0.7
                      }
                    },
                    {
                      name: 'MA10',
                      type: 'line',
                      data: calculateMA(10, chartData),
                      smooth: true,
                      lineStyle: {
                        width: 1,
                        opacity: 0.7
                      }
                    },
                    {
                      name: '成交量',
                      type: 'bar',
                      xAxisIndex: 1,
                      yAxisIndex: 1,
                      data: chartData.map((item, i) => {
                        return [
                          i,
                          item.volume,
                          item.close > item.open ? 1 : -1 // 1表示涨，-1表示跌
                        ];
                      })
                    }
                  ]
                }}
                style={{ height: '100%', width: '100%' }}
                opts={{ renderer: 'canvas' }}
              />
            </div>
          ) : (
            <div style={{ textAlign: 'center', padding: '40px 0' }}>
              <p>暂无数据可供显示</p>
            </div>
          )}
        </Spin>
      </Modal>
    </div>
  );
};

export default DataManagement; 