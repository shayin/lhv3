import React, { useMemo, memo } from 'react';
import { Table, TableProps } from 'antd';
import './OptimizedTable.css';

interface OptimizedTableProps extends TableProps<any> {
  virtualScroll?: boolean;
  itemHeight?: number;
  maxHeight?: number;
}

const OptimizedTable: React.FC<OptimizedTableProps> = memo(({
  virtualScroll = false,
  itemHeight = 54,
  maxHeight = 400,
  dataSource = [],
  columns = [],
  ...props
}) => {
  // 使用useMemo优化列配置
  const optimizedColumns = useMemo(() => {
    return columns.map((column: any) => ({
      ...column,
      // 为每列添加ellipsis属性以优化长文本显示
      ellipsis: column.ellipsis !== false,
    }));
  }, [columns]);

  // 使用useMemo优化数据源
  const optimizedDataSource = useMemo(() => {
    return dataSource || [];
  }, [dataSource]);

  // 优化的表格配置
  const tableConfig = useMemo(() => ({
    size: 'middle' as const,
    scroll: { x: 'max-content', y: maxHeight },
    pagination: {
      showSizeChanger: true,
      showQuickJumper: true,
      showTotal: (total: number, range: [number, number]) => 
        `第 ${range[0]}-${range[1]} 条，共 ${total} 条`,
      ...props.pagination,
    },
    ...props,
  }), [maxHeight, props]);

  return (
    <div className="optimized-table-container">
      <Table
        {...tableConfig}
        columns={optimizedColumns}
        dataSource={optimizedDataSource}
        className={`optimized-table ${props.className || ''}`}
      />
    </div>
  );
});

OptimizedTable.displayName = 'OptimizedTable';

export default OptimizedTable;