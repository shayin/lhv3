import { useState, useMemo, useCallback } from 'react';

interface UseVirtualListOptions {
  itemHeight: number;
  containerHeight: number;
  overscan?: number;
}

interface VirtualListItem {
  index: number;
  style: React.CSSProperties;
}

/**
 * 虚拟列表Hook
 * @param data 数据数组
 * @param options 配置选项
 * @returns 虚拟列表相关状态和方法
 */
export function useVirtualList<T>(
  data: T[],
  options: UseVirtualListOptions
) {
  const { itemHeight, containerHeight, overscan = 5 } = options;
  const [scrollTop, setScrollTop] = useState(0);

  // 计算可见项目
  const visibleItems = useMemo(() => {
    const visibleCount = Math.ceil(containerHeight / itemHeight);
    const startIndex = Math.floor(scrollTop / itemHeight);
    const endIndex = Math.min(startIndex + visibleCount + overscan, data.length - 1);
    
    const items: VirtualListItem[] = [];
    for (let i = Math.max(0, startIndex - overscan); i <= endIndex; i++) {
      items.push({
        index: i,
        style: {
          position: 'absolute',
          top: i * itemHeight,
          left: 0,
          right: 0,
          height: itemHeight,
        },
      });
    }
    
    return items;
  }, [data.length, itemHeight, containerHeight, scrollTop, overscan]);

  // 总高度
  const totalHeight = useMemo(() => data.length * itemHeight, [data.length, itemHeight]);

  // 滚动处理
  const handleScroll = useCallback((event: React.UIEvent<HTMLDivElement>) => {
    setScrollTop(event.currentTarget.scrollTop);
  }, []);

  return {
    visibleItems,
    totalHeight,
    handleScroll,
    containerProps: {
      style: {
        height: containerHeight,
        overflow: 'auto',
        position: 'relative' as const,
      },
      onScroll: handleScroll,
    },
    wrapperProps: {
      style: {
        height: totalHeight,
        position: 'relative' as const,
      },
    },
  };
}