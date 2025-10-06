import React, { memo, useMemo, useState, useEffect, useRef } from 'react';
import { Spin } from 'antd';
import ReactECharts from 'echarts-for-react';

interface OptimizedChartProps {
  option?: any;
  loading?: boolean;
  height?: number | string;
  lazyLoad?: boolean;
  threshold?: number;
  style?: React.CSSProperties;
  onChartReady?: (chart: any) => void;
  data?: any[];
  symbol?: string;
  className?: string;
  notMerge?: boolean;
  opts?: any;
  onEvents?: any;
}

// 懒加载图表组件
const OptimizedChart: React.FC<OptimizedChartProps> = memo(({
  option,
  loading = false,
  height = 400,
  lazyLoad = true,
  threshold = 0.1,
  style,
  onChartReady,
  data,
  symbol,
  className,
  notMerge = false,
  opts = { renderer: 'canvas' },
  onEvents
}) => {
  const [isVisible, setIsVisible] = useState(!lazyLoad);
  const [chartInstance, setChartInstance] = useState<any>(null);
  const chartRef = useRef<HTMLDivElement>(null);
  const observerRef = useRef<IntersectionObserver | null>(null);

  // 计算移动平均线的函数
  const calculateMA = useMemo(() => (dayCount: number, chartData: any[]) => {
    const result = [];
    for (let i = 0, len = chartData.length; i < len; i++) {
      if (i < dayCount - 1) {
        result.push('-');
        continue;
      }
      let sum = 0;
      for (let j = 0; j < dayCount; j++) {
        sum += chartData[i - j].close;
      }
      result.push((sum / dayCount).toFixed(2));
    }
    return result;
  }, []);

  // 生成K线图配置
  const generateKLineOption = useMemo(() => {
    if (!data || data.length === 0) return {};

    return {
      backgroundColor: '#fff',
      title: {
        text: symbol,
        left: 'center',
        top: 10,
        textStyle: {
          fontSize: 16,
          fontWeight: 'bold'
        },
        subtextStyle: {
          color: '#888'
        }
      },
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'cross',
          label: {
            backgroundColor: '#555'
          }
        },
        backgroundColor: 'rgba(255, 255, 255, 0.8)',
        borderWidth: 1,
        borderColor: '#ccc',
        padding: 10,
        textStyle: {
          color: '#333'
        }
      },
      legend: {
        data: ['K线', 'MA5', 'MA10'],
        top: 35,
        selected: {
          'K线': true,
          'MA5': true,
          'MA10': true
        }
      },
      toolbox: {
        feature: {
          dataZoom: {
            yAxisIndex: [0, 1]
          },
          brush: {
            type: ['lineX', 'clear']
          },
          restore: {},
          saveAsImage: {}
        }
      },
      brush: {
        xAxisIndex: 'all',
        brushLink: 'all',
        outOfBrush: {
          colorAlpha: 0.1
        }
      },
      grid: [
        {
          left: '10%',
          right: '10%',
          top: 80,
          height: '60%'
        },
        {
          left: '10%',
          right: '10%',
          top: '75%',
          height: '15%'
        }
      ],
      xAxis: [
        {
          type: 'category',
          data: data.map(item => item.time),
          scale: true,
          boundaryGap: false,
          axisLine: { onZero: false },
          splitLine: { show: false },
          splitNumber: 20,
          min: 'dataMin',
          max: 'dataMax',
          axisPointer: {
            z: 100
          }
        },
        {
          type: 'category',
          gridIndex: 1,
          data: data.map(item => item.time),
          scale: true,
          boundaryGap: false,
          axisLine: { onZero: false },
          axisTick: { show: false },
          splitLine: { show: false },
          axisLabel: { show: false },
          splitNumber: 20,
          min: 'dataMin',
          max: 'dataMax'
        }
      ],
      yAxis: [
        {
          scale: true,
          splitArea: {
            show: true
          },
          splitLine: {
            show: true
          }
        },
        {
          scale: true,
          gridIndex: 1,
          splitNumber: 2,
          axisLabel: { show: false },
          axisLine: { show: false },
          axisTick: { show: false },
          splitLine: { show: false }
        }
      ],
      dataZoom: [
        {
          type: 'inside',
          xAxisIndex: [0, 1],
          start: 50,
          end: 100
        },
        {
          show: true,
          xAxisIndex: [0, 1],
          type: 'slider',
          bottom: 10,
          start: 50,
          end: 100
        }
      ],
      visualMap: {
        show: false,
        seriesIndex: 3,
        dimension: 2,
        pieces: [
          {
            value: 1,
            color: '#ef232a'
          },
          {
            value: -1,
            color: '#14b143'
          }
        ]
      },
      series: [
        {
          name: 'K线',
          type: 'candlestick',
          data: data.map(item => [
            item.open,  // 开盘价
            item.close,  // 收盘价
            item.low,   // 最低价
            item.high,  // 最高价
          ]),
          itemStyle: {
            color: '#ef232a',
            color0: '#14b143',
            borderColor: '#ef232a',
            borderColor0: '#14b143'
          }
        },
        {
          name: 'MA5',
          type: 'line',
          data: calculateMA(5, data),
          smooth: true,
          lineStyle: {
            width: 1,
            opacity: 0.7
          }
        },
        {
          name: 'MA10',
          type: 'line',
          data: calculateMA(10, data),
          smooth: true,
          lineStyle: {
            width: 1,
            opacity: 0.7
          }
        },
        {
          name: '成交量',
          type: 'bar',
          xAxisIndex: 1,
          yAxisIndex: 1,
          data: data.map((item, i) => {
            return [
              i,
              item.volume,
              item.close > item.open ? 1 : -1 // 1表示涨，-1表示跌
            ];
          })
        }
      ]
    };
  }, [data, symbol, calculateMA]);

  // 使用 useMemo 缓存图表配置
  const memoizedOption = useMemo(() => {
    // 如果传入了option，使用传入的option，否则使用生成的K线图配置
    const finalOption = option || generateKLineOption;
    
    if (!finalOption || Object.keys(finalOption).length === 0) return {};
    
    // 优化图表配置
    return {
      ...finalOption,
      animation: false, // 禁用动画以提高性能
      progressive: 1000, // 渐进式渲染
      progressiveThreshold: 3000, // 渐进式渲染阈值
      useUTC: true, // 使用UTC时间
    };
  }, [option, generateKLineOption]);

  // 懒加载逻辑
  useEffect(() => {
    if (!lazyLoad || isVisible) return;

    const currentRef = chartRef.current;
    if (!currentRef) return;

    observerRef.current = new IntersectionObserver(
      (entries) => {
        const [entry] = entries;
        if (entry.isIntersecting) {
          setIsVisible(true);
          observerRef.current?.disconnect();
        }
      },
      { threshold }
    );

    observerRef.current.observe(currentRef);

    return () => {
      observerRef.current?.disconnect();
    };
  }, [lazyLoad, isVisible, threshold]);

  // 图表实例化回调
  const handleChartReady = (chart: any) => {
    setChartInstance(chart);
    onChartReady?.(chart);
  };

  // 如果启用懒加载但图表不可见，显示占位符
  if (lazyLoad && !isVisible) {
    return (
      <div
        ref={chartRef}
        style={{
          height,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          backgroundColor: '#fafafa',
          border: '1px dashed #d9d9d9',
          ...style
        }}
      >
        <div style={{ textAlign: 'center', color: '#999' }}>
          <div>图表懒加载中...</div>
          <div style={{ fontSize: '12px', marginTop: '4px' }}>滚动到此处将自动加载</div>
        </div>
      </div>
    );
  }

  return (
    <div ref={chartRef} style={style}>
      <Spin spinning={loading} tip="图表加载中...">
        <ReactECharts
          className={className}
          option={memoizedOption}
          style={{ height }}
          onChartReady={handleChartReady}
          notMerge={notMerge}
          opts={opts}
          onEvents={onEvents}
        />
      </Spin>
    </div>
  );
});

OptimizedChart.displayName = 'OptimizedChart';

export default OptimizedChart;