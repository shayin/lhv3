import React, { useState, useEffect, memo, useMemo, useCallback, useRef } from 'react';
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
import { fetchStockList, fetchDataSources, fetchChartData, updateAllStocksData, Stock, DataSource } from '../services/apiService';
import { PaginationCookie } from '../utils/cookie';
import { useDebounce } from '../hooks/useDebounce';
import OptimizedTable from '../components/OptimizedTable';
import OptimizedChart from '../components/OptimizedChart';
import ReactECharts from 'echarts-for-react';
import dayjs from 'dayjs';

const { Title, Text } = Typography;
const { Option } = Select;

// 使用memo优化日期范围组件
interface PresetType {
  label: string;
  days?: number;
  type?: string;
}

const DateRangePresets = memo(({ onSelect }: { onSelect: (startDate: string, endDate: string) => void }) => {
  const presets = useMemo((): PresetType[] => [
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
  ], []);

  const handlePresetClick = useCallback((preset: PresetType) => {
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
      startDate = now.subtract(preset.days!, 'day').format('YYYY-MM-DD');
      endDate = now.format('YYYY-MM-DD');
    }

    onSelect(startDate, endDate);
  }, [onSelect]);

  return (
    <Space wrap>
      {presets.map((preset: PresetType, index: number) => (
        <Button 
          key={index} 
          size="small" 
          onClick={() => handlePresetClick(preset)}
        >
          {preset.label}
        </Button>
      ))}
    </Space>
  );
});

DateRangePresets.displayName = 'DateRangePresets';

// 计算移动平均线的函数 - 移到组件外部
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

const DataManagement: React.FC = memo(() => {
  // 状态定义
  const [dataList, setDataList] = useState<DataItem[]>([]);
  const [dataSources, setDataSources] = useState<DataSource[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [uploadVisible, setUploadVisible] = useState<boolean>(false);
  const [fileList, setFileList] = useState<any[]>([]);
  const [form] = Form.useForm();
  const [uploadMode, setUploadMode] = useState<'upload' | 'fetch'>('fetch');
  const [fetchLoading, setFetchLoading] = useState(false);
  const [updateAllLoading, setUpdateAllLoading] = useState(false);
  
  // 添加初始化标记，防止React StrictMode导致的重复初始化
  const initializedRef = useRef<boolean>(false);
  
  // 分页相关状态 - 从cookie读取设置
  const [pagination, setPagination] = useState({
    current: PaginationCookie.getCurrentPage(),
    pageSize: PaginationCookie.getPageSize(),
    total: 0,
    showSizeChanger: true,
    showQuickJumper: true,
    showTotal: (total: number, range: [number, number]) => 
      `第 ${range[0]}-${range[1]} 条，共 ${total} 条`,
    pageSizeOptions: ['10', '15', '20', '50', '100'],
  });
  
  // K线图相关状态
  const [chartVisible, setChartVisible] = useState<boolean>(false);
  const [currentStock, setCurrentStock] = useState<DataItem | null>(null);
  const [chartData, setChartData] = useState<any[]>([]);
  const [chartLoading, setChartLoading] = useState<boolean>(false);

  // 搜索相关状态
  const [searchText, setSearchText] = useState<string>('');
  const debouncedSearchText = useDebounce(searchText, 300);

  // 获取数据列表 - 使用useCallback优化
  const fetchList = useCallback(async (page: number = PaginationCookie.getCurrentPage(), pageSize: number = PaginationCookie.getPageSize()) => {
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
      
      // 更新分页状态
      setPagination(prev => ({
        ...prev,
        current: page,
        pageSize: pageSize,
        total: formattedData.length,
      }));
      
      setDataList(formattedData);
    } catch (error) {
      console.error('获取数据列表失败:', error);
      message.error('获取数据列表失败，请检查网络连接');
    } finally {
      setLoading(false);
    }
  }, []);

  // 获取数据源列表 - 使用useCallback优化
  const fetchSourcesList = useCallback(async () => {
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
  }, [uploadMode, form]);

  // 分页处理函数 - 使用useCallback优化
  const handleTableChange = useCallback((pagination: any) => {
    const { current, pageSize } = pagination;
    
    // 保存分页设置到cookie
    PaginationCookie.setCurrentPage(current);
    PaginationCookie.setPageSize(pageSize);
    
    fetchList(current, pageSize);
  }, [fetchList]);

  // 处理数据下载 - 使用useCallback优化
  const handleDownload = useCallback(async (id: string) => {
    setLoading(true);
    try {
      const response = await axios.get(`/api/data/download/${id}`, {
        responseType: 'blob',
      });
      
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      
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
  }, []);

  // 处理数据删除 - 使用useCallback优化
  const handleDelete = useCallback(async (id: string) => {
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
            fetchList();
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
  }, [fetchList]);

  // 查看K线图 - 使用useCallback优化
  const handleViewChart = useCallback(async (record: DataItem) => {
    setCurrentStock(record);
    setChartVisible(true);
    setChartLoading(true);
    
    try {
      const response = await fetchChartData(record.id);
      console.log('API响应数据:', response);
      
      // 检查数据结构并提取实际的K线数据
      const data = response.data || response || [];
      console.log('处理后的数据:', data);
      
      setChartData(data);
    } catch (error) {
      console.error('获取图表数据失败:', error);
      message.error('获取图表数据失败');
    } finally {
      setChartLoading(false);
    }
  }, []);

  // 使用useMemo优化表格列配置
  const columns: ColumnsType<DataItem> = useMemo(() => [
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
            </div>
          );
        }
        return <span style={{ color: '#999' }}>暂无数据</span>;
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
  ], [handleDownload, handleViewChart, handleDelete]);

  // 一键更新所有股票数据
  const handleUpdateAll = useCallback(() => {
    Modal.confirm({
      title: '一键更新确认',
      content: '确定要更新所有股票的最新数据吗？此操作可能需要较长时间。',
      okText: '确定更新',
      cancelText: '取消',
      onOk: async () => {
        setUpdateAllLoading(true);
        try {
          const result = await updateAllStocksData();
          
          if (result && result.status === 'success') {
            const { summary } = result;
            
            if (summary.error === 0) {
              message.success(`一键更新完成！成功更新 ${summary.success} 个股票数据`);
            } else {
              message.success(`一键更新完成！成功更新 ${summary.success} 个，失败 ${summary.error} 个`);
              
              // 获取失败的结果
              const errorResults = result.results.filter(r => r.status === 'error');
              console.warn('更新失败的股票:', errorResults);
              
              // 显示前几个错误信息
              const errorMessages = errorResults.slice(0, 3).map(r => `${r.symbol}: ${r.message}`).join('; ');
              if (errorResults.length > 3) {
                message.warning(`部分股票更新失败: ${errorMessages}... (共${errorResults.length}个失败)`);
              } else {
                message.warning(`部分股票更新失败: ${errorMessages}`);
              }
            }
            
            // 刷新列表
            fetchList();
          } else {
            message.error('一键更新失败');
          }
        } catch (error: any) {
          console.error('一键更新失败:', error);
          
          // 安全地处理错误信息
          const detail = error.response?.data?.detail;
          if (detail) {
            if (typeof detail === 'object') {
              message.error(JSON.stringify(detail));
            } else {
              message.error(detail);
            }
          } else {
            message.error('一键更新失败，请重试');
          }
        } finally {
          setUpdateAllLoading(false);
        }
      },
    });
  }, [fetchList]);

  // 初始化加载
  useEffect(() => {
    // 防止React StrictMode导致的重复初始化
    if (initializedRef.current) {
      return;
    }
    initializedRef.current = true;
    
    fetchList();
    fetchSourcesList();
  }, [fetchList, fetchSourcesList]);

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
                type="primary"
                icon={<SyncOutlined />} 
                loading={updateAllLoading}
                onClick={handleUpdateAll}
                style={{ backgroundColor: '#52c41a', borderColor: '#52c41a' }}
              >
                一键更新
              </Button>
              <Button 
                icon={<SyncOutlined />} 
                onClick={() => fetchList(pagination.current, pagination.pageSize)}
              >
                刷新列表
              </Button>
            </Space>
          </Col>
        </Row>

        <Spin spinning={loading}>
          <OptimizedTable 
            columns={columns} 
            dataSource={dataList} 
            rowKey="id" 
            bordered 
            size="middle"
            pagination={pagination}
            onChange={handleTableChange}
          />
        </Spin>
      </Card>

      {/* K线图模态框 */}
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
});

DataManagement.displayName = 'DataManagement';

export default DataManagement;