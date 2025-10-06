import React from 'react';
import ReactDOM from 'react-dom/client';
import { ConfigProvider } from 'antd';
import enUS from 'antd/locale/en_US';
import axios from 'axios';
import moment from 'moment';
import 'moment/locale/en-gb';
import App from './App.tsx';
import './App.css';

// 设置moment为英文
moment.locale('en-gb');

// 设置Axios默认配置
axios.defaults.baseURL = 'http://localhost:8001';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ConfigProvider locale={enUS}>
      <App />
    </ConfigProvider>
  </React.StrictMode>
);