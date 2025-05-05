import axios from 'axios';
import { message } from 'antd';

// 直接硬编码API URL，避免process未定义错误
const API_URL = 'http://localhost:8000/api';

interface Strategy {
  id: number;
  name: string;
  description?: string;
  code?: string;
  parameters?: any;
  created_at?: string;
  updated_at?: string;
  is_template?: boolean;
  template?: string;
}

// 获取所有策略
export const getStrategies = async (name?: string): Promise<Strategy[]> => {
  try {
    const params: any = {};
    if (name) {
      params.name = name;
    }
    
    const response = await axios.get(`${API_URL}/strategies`, { params });
    
    if (response.data && response.data.status === 'success') {
      return response.data.data || [];
    }
    
    throw new Error(response.data?.message || '获取策略列表失败');
  } catch (error: any) {
    message.error(`获取策略列表错误: ${error.message}`);
    return [];
  }
};

// 获取单个策略详情
export const getStrategy = async (id: number): Promise<Strategy | null> => {
  try {
    const response = await axios.get(`${API_URL}/strategies/${id}`);
    
    if (response.data && response.data.status === 'success') {
      return response.data.data;
    }
    
    throw new Error(response.data?.message || '获取策略详情失败');
  } catch (error: any) {
    message.error(`获取策略详情错误: ${error.message}`);
    return null;
  }
};

// 创建新策略
export const createStrategy = async (strategy: Partial<Strategy>): Promise<Strategy | null> => {
  try {
    const response = await axios.post(`${API_URL}/strategies`, strategy);
    
    if (response.data && response.data.status === 'success') {
      message.success('策略创建成功');
      return response.data.data;
    }
    
    throw new Error(response.data?.message || '创建策略失败');
  } catch (error: any) {
    message.error(`创建策略错误: ${error.message}`);
    return null;
  }
};

// 更新策略
export const updateStrategy = async (id: number, strategy: Partial<Strategy>): Promise<Strategy | null> => {
  try {
    const response = await axios.put(`${API_URL}/strategies/${id}`, strategy);
    
    if (response.data && response.data.status === 'success') {
      message.success('策略更新成功');
      return response.data.data;
    }
    
    throw new Error(response.data?.message || '更新策略失败');
  } catch (error: any) {
    message.error(`更新策略错误: ${error.message}`);
    return null;
  }
};

// 删除策略
export const deleteStrategy = async (id: number): Promise<boolean> => {
  try {
    const response = await axios.delete(`${API_URL}/strategies/${id}`);
    
    if (response.data && response.data.status === 'success') {
      message.success('策略删除成功');
      return true;
    }
    
    throw new Error(response.data?.message || '删除策略失败');
  } catch (error: any) {
    message.error(`删除策略错误: ${error.message}`);
    return false;
  }
};

// 测试策略代码
export const testStrategy = async (code: string, data?: any[], parameters?: any): Promise<any> => {
  try {
    const payload = {
      code,
      data: data || [],
      parameters: parameters || {}
    };
    
    const response = await axios.post(`${API_URL}/strategies/test`, payload);
    
    if (response.data && response.data.status === 'success') {
      return response.data.data;
    }
    
    throw new Error(response.data?.message || '测试策略失败');
  } catch (error: any) {
    message.error(`测试策略错误: ${error.message}`);
    return { error: error.message };
  }
};

// 通过ID测试策略
export const testStrategyById = async (strategyId: string | number, data?: any[], parameters?: any): Promise<any> => {
  try {
    const payload = {
      strategy_id: strategyId,
      data: data || [],
      parameters: parameters || {}
    };
    
    const response = await axios.post(`${API_URL}/strategies/test`, payload);
    
    if (response.data && response.data.status === 'success') {
      return response.data.data;
    }
    
    throw new Error(response.data?.message || '测试策略失败');
  } catch (error: any) {
    message.error(`测试策略错误: ${error.message}`);
    return { error: error.message };
  }
};

// 对策略执行历史数据回测
export const backtestStrategy = async (
  strategyId: number,
  symbol: string,
  startDate: string,
  endDate: string,
  initialCapital: number = 100000,
  parameters: any = {},
  commissionRate: number = 0.0015,
  slippageRate: number = 0.001,
  dataSource: string = 'database',
  features: string[] = []
): Promise<any> => {
  try {
    const payload = {
      strategy_id: strategyId,
      symbol,
      start_date: startDate,
      end_date: endDate,
      initial_capital: initialCapital,
      parameters,
      commission_rate: commissionRate,
      slippage_rate: slippageRate,
      data_source: dataSource,
      features
    };
    
    const response = await axios.post(`${API_URL}/strategies/backtest`, payload);
    
    if (response.data && response.data.status === 'success') {
      return response.data.data;
    }
    
    throw new Error(response.data?.message || '策略回测失败');
  } catch (error: any) {
    message.error(`策略回测错误: ${error.message}`);
    return { error: error.message };
  }
}; 