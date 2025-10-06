import React, { useState, useEffect, memo, useCallback, useMemo } from 'react';
import { Table, Button, Space, Card, message, Modal, Popconfirm, Typography, Tag } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, ExclamationCircleOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { fetchStrategies, Strategy, deleteStrategy } from '../services/apiService';
import OptimizedTable from '../components/OptimizedTable';

const { Title } = Typography;

const StrategyManagement: React.FC = () => {
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const navigate = useNavigate();

  // 加载策略列表
  const loadStrategies = async () => {
    setLoading(true);
    try {
      const data = await fetchStrategies();
      setStrategies(data);
    } catch (error) {
      console.error('获取策略列表失败:', error);
      message.error('获取策略列表失败');
    } finally {
      setLoading(false);
    }
  };

  // 初始加载
  useEffect(() => {
    loadStrategies();
  }, []);

  // 创建新策略
  const handleCreateStrategy = () => {
    navigate('/strategy-builder');
  };

  // 编辑策略
  const handleEditStrategy = (strategyId: string) => {
    navigate(`/strategy-builder?id=${strategyId}`);
  };

  // 删除策略确认
  const confirmDelete = (strategyId: string) => {
    Modal.confirm({
      title: '确认删除',
      icon: <ExclamationCircleOutlined />,
      content: '确定要删除这个策略吗？此操作不可恢复。',
      okText: '确认',
      cancelText: '取消',
      onOk: () => handleDeleteStrategy(strategyId),
    });
  };

  // 删除策略
  const handleDeleteStrategy = async (strategyId: string) => {
    try {
      // 调用删除API
      await deleteStrategy(strategyId);
      message.success('策略删除成功');
      // 重新加载列表
      loadStrategies();
    } catch (error) {
      console.error('删除策略失败:', error);
      message.error('删除策略失败');
    }
  };

  // 表格列定义
  const columns = [
    {
      title: '策略名称',
      dataIndex: 'name',
      key: 'name',
      render: (text: string, record: Strategy) => (
        <Space>
          {text}
          {record.is_custom ? <Tag color="blue">自定义</Tag> : <Tag color="green">系统</Tag>}
        </Space>
      ),
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (text: string) => text ? new Date(text).toLocaleString() : '—',
    },
    {
      title: '更新时间',
      dataIndex: 'updated_at',
      key: 'updated_at',
      render: (text: string) => text ? new Date(text).toLocaleString() : '—',
    },
    {
      title: '操作',
      key: 'action',
      render: (_: any, record: Strategy) => (
        <Space size="middle">
          <Button
            icon={<EditOutlined />}
            onClick={() => handleEditStrategy(record.id || '')}
            disabled={!record.is_custom}
          >
            编辑
          </Button>
          <Button 
            icon={<DeleteOutlined />} 
            danger
            onClick={() => confirmDelete(record.id || '')}
            disabled={!record.is_custom}
          >
            删除
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Title level={2}>策略管理</Title>
      
      <Card
        title="我的策略"
        extra={
          <Button 
            type="primary" 
            icon={<PlusOutlined />}
            onClick={handleCreateStrategy}
          >
            创建策略
          </Button>
        }
      >
        <OptimizedTable
          columns={columns}
          dataSource={strategies}
          rowKey="id"
          loading={loading}
          pagination={{ pageSize: 10 }}
        />
      </Card>
    </div>
  );
};

export default memo(StrategyManagement);