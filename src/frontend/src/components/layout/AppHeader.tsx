import React from 'react';
import { Layout, Menu, Button, theme } from 'antd';
import { Link } from 'react-router-dom';
import {
  DashboardOutlined,
  DatabaseOutlined,
  CodeOutlined,
  LineChartOutlined,
  SettingOutlined,
  GithubOutlined,
} from '@ant-design/icons';

const { Header } = Layout;
const { useToken } = theme;

const AppHeader: React.FC = () => {
  const { token } = useToken();
  
  // 定义菜单数据项
  const menuItems = [
    {
      key: '/',
      icon: <DashboardOutlined />,
      label: <Link to="/">首页</Link>,
    },
    {
      key: '/data',
      icon: <DatabaseOutlined />,
      label: <Link to="/data">数据管理</Link>,
    },
    {
      key: '/strategy',
      icon: <CodeOutlined />,
      label: <Link to="/strategy">策略编辑</Link>,
    },
    {
      key: '/backtest',
      icon: <LineChartOutlined />,
      label: <Link to="/backtest">回测分析</Link>,
    },
    {
      key: '/optimization',
      icon: <SettingOutlined />,
      label: <Link to="/optimization">参数优化</Link>,
    },
  ];

  return (
    <Header style={{ background: token.colorBgContainer, padding: '0 24px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
      <div className="header-nav-logo">
        <Link to="/" style={{ color: token.colorPrimary, fontSize: '18px', fontWeight: 'bold', display: 'flex', alignItems: 'center' }}>
          <LineChartOutlined style={{ marginRight: '8px', fontSize: '24px' }} />
          量化交易系统
        </Link>
      </div>
      
      <Menu
        className="header-nav-menu"
        mode="horizontal"
        selectedKeys={[window.location.pathname]}
        style={{ flex: 1, marginLeft: '40px', borderBottom: 'none' }}
        items={menuItems}
      />
      
      <div>
        <Button
          icon={<GithubOutlined />}
          type="text"
          href="https://github.com/yourusername/quant-trading-system"
          target="_blank"
          rel="noopener noreferrer"
        >
          GitHub
        </Button>
      </div>
    </Header>
  );
};

export default AppHeader; 