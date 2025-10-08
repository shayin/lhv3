import { ThemeConfig } from 'antd';

export const theme: ThemeConfig = {
  token: {
    colorPrimary: '#1890ff',
    borderRadius: 8,
    colorBgContainer: '#ffffff',
    fontSize: 12,  // 全局字体大小从默认14px减小到12px
    fontSizeSM: 11, // 小字体从默认12px减小到11px
    fontSizeLG: 14, // 大字体从默认16px减小到14px
    fontSizeXL: 16, // 超大字体从默认20px减小到16px
  },
  components: {
    Table: {
      colorBgContainer: '#ffffff',
      borderRadius: 8,
      fontSize: 12,  // 表格字体大小
    },
    Card: {
      colorBgContainer: '#ffffff',
      borderRadius: 8,
      fontSize: 12,  // 卡片字体大小
    },
    Button: {
      borderRadius: 6,
      fontSize: 12,  // 按钮字体大小
    },
    Typography: {
      fontSize: 12,  // 文本组件字体大小
    },
    Form: {
      fontSize: 12,  // 表单字体大小
    },
    Input: {
      fontSize: 12,  // 输入框字体大小
    },
    Select: {
      fontSize: 12,  // 选择器字体大小
    },
    Menu: {
      fontSize: 12,  // 菜单字体大小
    },
  },
};