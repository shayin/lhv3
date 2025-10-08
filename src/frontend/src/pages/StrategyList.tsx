import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Card, 
  List, 
  Button, 
  Space, 
  Divider, 
  Typography, 
  Tag,
  Empty,
  Spin,
  message 
} from 'antd';
import { 
  PlusOutlined, 
  EditOutlined, 
  DeleteOutlined, 
  ExperimentOutlined 
} from '@ant-design/icons';
import { fetchStrategies, deleteStrategy, Strategy as ApiStrategy } from '../services/apiService';

const { Title, Text } = Typography;

// 使用与apiService一致的Strategy类型
type Strategy = ApiStrategy;

const StrategyList: React.FC = () => {
  const navigate = useNavigate();
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const initializedRef = useRef<boolean>(false);

  // 获取策略列表
  const fetchStrategyList = async () => {
    setLoading(true);
    try {
      const data = await fetchStrategies();
      console.log('获取到的策略数据:', data); // 调试输出
      setStrategies(data);
    } catch (error) {
      message.error('获取策略列表失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!initializedRef.current) {
      initializedRef.current = true;
      fetchStrategyList();
    }
  }, []);

  // 创建新策略
  const handleCreate = () => {
    navigate('/strategy/edit');
  };

  // 编辑策略
  const handleEdit = (id: string | undefined) => {
    if (id) {
      navigate(`/strategy/edit/${id}`);
    }
  };

  // 删除策略
  const handleDelete = async (id: string | undefined) => {
    if (id) {
      try {
        await deleteStrategy(id);
        message.success('策略删除成功');
        fetchStrategyList();
      } catch (error) {
        message.error('删除策略失败');
      }
    }
  };

  // 回测策略
  const handleBacktest = (id: string | undefined) => {
    if (id) {
      navigate(`/backtest?strategy=${id}`);
    }
  };

  const getStrategyListContent = () => {
    if (loading) {
      return <Spin tip="加载中..." />;
    }

    if (strategies.length === 0) {
      return (
        <Empty 
          description="暂无策略" 
          image={Empty.PRESENTED_IMAGE_SIMPLE} 
        />
      );
    }

    return (
      <List
        className="strategy-list"
        itemLayout="horizontal"
        dataSource={strategies}
        renderItem={item => (
          <List.Item 
            key={item.id}
            className="strategy-list-item"
            style={{ 
              padding: '16px', 
              borderRadius: '8px', 
              backgroundColor: '#f9f9f9', 
              marginBottom: '12px',
              display: 'flex',
              justifyContent: 'space-between'
            }}
          >
            <div style={{ flex: 1, overflow: 'hidden' }}>
              <div style={{ display: 'flex', alignItems: 'center', marginBottom: '8px' }}>
                <Text strong style={{ fontSize: '16px', marginRight: '8px' }}>
                  {item.name}
                </Text>
              </div>
              <Text type="secondary" style={{ display: 'block', marginBottom: '8px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {item.description || '无描述'}
              </Text>
              {item.updated_at && (
                <Text type="secondary" style={{ fontSize: '12px' }}>
                  最后更新: {new Date(item.updated_at).toLocaleString()}
                </Text>
              )}
            </div>
            <div style={{ display: 'flex', alignItems: 'center' }}>
              <Space>
                <Button 
                  type="primary"
                  icon={<ExperimentOutlined />}
                  onClick={() => handleBacktest(item.id)}
                >
                  回测
                </Button>
                <Button 
                  icon={<EditOutlined />}
                  onClick={() => handleEdit(item.id)}
                >
                  编辑
                </Button>
                <Button 
                  danger
                  icon={<DeleteOutlined />}
                  onClick={() => handleDelete(item.id)}
                >
                  删除
                </Button>
              </Space>
            </div>
          </List.Item>
        )}
      />
    );
  };

  return (
    <div style={{ padding: '20px' }}>
      <Card>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <Title level={4} style={{ margin: 0 }}>策略构建器</Title>
          <Button 
            type="primary" 
            icon={<PlusOutlined />} 
            onClick={handleCreate}
          >
            创建新策略
          </Button>
        </div>
        
        <Divider />
        
        {getStrategyListContent()}
      </Card>
    </div>
  );
};

export default StrategyList;