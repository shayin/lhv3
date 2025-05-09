import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { ConfigProvider, Layout } from 'antd';
import enUS from 'antd/locale/en_US';
import { theme } from './theme';

import AppHeader from './components/layout/AppHeader';
import AppSider from './components/layout/AppSider';
import Dashboard from './pages/Dashboard';
import DataManagement from './pages/DataManagement';
import StrategyBuilder from './pages/StrategyBuilder';
import Backtest from './pages/Backtest';
import StrategyOptimization from './pages/StrategyOptimization';
import StrategyList from './pages/StrategyList';
import StrategyEditor from './pages/StrategyEditor';

import './App.css';

const { Content } = Layout;

const App: React.FC = () => {
  return (
    <ConfigProvider locale={enUS} theme={theme}>
      <Router>
        <Layout style={{ minHeight: '100vh' }}>
          <AppHeader />
          <Layout>
            <AppSider />
            <Layout style={{ padding: '24px' }}>
              <Content
                style={{
                  padding: 24,
                  margin: 0,
                  minHeight: 280,
                  background: '#fff',
                  borderRadius: '8px',
                }}
              >
                <Routes>
                  <Route path="/" element={<Navigate to="/dashboard" replace />} />
                  <Route path="/dashboard" element={<Dashboard />} />
                  <Route path="/data" element={<DataManagement />} />
                  <Route path="/strategy" element={<StrategyList />} />
                  <Route path="/strategy/edit" element={<StrategyEditor />} />
                  <Route path="/strategy/edit/:id" element={<StrategyEditor />} />
                  <Route path="/strategy/builder" element={<StrategyBuilder />} />
                  <Route path="/backtest" element={<Backtest />} />
                  <Route path="/optimization" element={<StrategyOptimization />} />
                </Routes>
              </Content>
            </Layout>
          </Layout>
        </Layout>
      </Router>
    </ConfigProvider>
  );
};

export default App; 