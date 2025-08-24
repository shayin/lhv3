import axios from 'axios';

// 定义交易品种接口
export interface Stock {
  id: string;
  symbol: string;
  name: string;
  type: string;
  exchange?: string;
  source_id?: number;
  data_count?: number;
  last_updated?: string;
  first_date?: string;
  last_date?: string;
}

// 定义数据源接口
export interface DataSource {
  id: number;
  name: string;
  description?: string;
}

// 定义策略接口
export interface Strategy {
  id?: string;
  name: string;
  description?: string;
  template?: string;
  parameters?: Record<string, any>;
  code?: string;
  created_at?: string;
  updated_at?: string;
  is_custom?: boolean;
  is_template?: boolean;
}

// 获取所有交易品种列表
export const fetchStockList = async (): Promise<Stock[]> => {
  try {
    const response = await axios.get('/api/data/stocks');
    if (response.data && Array.isArray(response.data)) {
      return response.data.map((item: any) => ({
        id: item.id.toString(),
        symbol: item.symbol,
        name: item.name,
        type: item.type || '未知',
        exchange: item.exchange,
        source_id: item.source_id,
        data_count: item.data_count || 0,
        last_updated: item.last_updated,
        first_date: item.first_date,
        last_date: item.last_date
      }));
    }
    return [];
  } catch (error) {
    console.error('获取交易品种列表失败:', error);
    throw error;
  }
};

// 获取所有数据源列表
export const fetchDataSources = async (): Promise<DataSource[]> => {
  try {
    const response = await axios.get('/api/data/list');
    if (response.data && Array.isArray(response.data)) {
      return response.data;
    }
    return [];
  } catch (error) {
    console.error('获取数据源列表失败:', error);
    throw error;
  }
};

// 从后端获取K线图数据
export const fetchChartData = async (stockId: string) => {
  try {
    const response = await axios.get(`/api/data/chart/${stockId}`);
    if (response.data && response.data.data) {
      return response.data;
    }
    return { data: [] };
  } catch (error) {
    console.error('获取图表数据失败:', error);
    throw error;
  }
};

// 保存策略
export async function saveStrategy(strategyData: Strategy): Promise<Strategy> {
  try {
    console.log('保存策略数据:', JSON.stringify(strategyData, null, 2));
    
    let response;
    if (strategyData.id) {
      // 更新现有策略
      response = await axios.put(`/api/strategies/${strategyData.id}`, strategyData);
    } else {
      // 创建新策略
      response = await axios.post('/api/strategies', strategyData);
    }
    
    console.log('策略保存响应:', response.data);
    
    if (response.data && response.data.status === 'success') {
      return response.data.data;
    } else if (response.data) {
      return response.data; // 兼容旧版API格式
    } else {
      throw new Error('保存策略失败，返回数据格式错误');
    }
  } catch (error) {
    console.error('保存策略时发生错误:', error);
    throw error;
  }
}

// 获取所有策略列表
export const fetchStrategies = async (): Promise<Strategy[]> => {
  try {
    const response = await axios.get('/api/strategies');
    if (response.data && response.data.data) {
      return response.data.data;
    }
    return [];
  } catch (error) {
    console.error('获取策略列表失败:', error);
    throw error;
  }
};

// 获取单个策略详情
export const fetchStrategyById = async (id: string): Promise<Strategy> => {
  try {
    const response = await axios.get(`/api/strategies/${id}`);
    if (response.data && response.data.data) {
      return response.data.data;
    }
    throw new Error('未找到策略数据');
  } catch (error) {
    console.error(`获取策略(ID:${id})详情失败:`, error);
    throw error;
  }
};

// 删除策略
export const deleteStrategy = async (id: string): Promise<void> => {
  try {
    await axios.delete(`/api/strategies/${id}`);
  } catch (error) {
    console.error(`删除策略(ID:${id})失败:`, error);
    throw error;
  }
};

// 获取策略模板列表
export const fetchStrategyTemplates = async (): Promise<Strategy[]> => {
  try {
    const response = await axios.get('/api/strategies/templates');
    if (response.data && response.data.data) {
      return response.data.data;
    }
    return [];
  } catch (error) {
    console.error('获取策略模板列表失败:', error);
    throw error;
  }
};

// 获取单个策略模板详情
export const fetchStrategyTemplateById = async (id: string): Promise<Strategy> => {
  try {
    const response = await axios.get(`/api/strategies/templates/${id}`);
    if (response.data && response.data.data) {
      return response.data.data;
    }
    throw new Error('未找到策略模板数据');
  } catch (error) {
    console.error(`获取策略模板(ID:${id})详情失败:`, error);
    throw error;
  }
}; 