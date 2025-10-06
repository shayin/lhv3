import { useCallback, useRef } from 'react';

/**
 * 记忆化回调Hook，避免不必要的函数重新创建
 * @param callback 回调函数
 * @param deps 依赖数组
 * @returns 记忆化的回调函数
 */
export function useMemoizedCallback<T extends (...args: any[]) => any>(
  callback: T,
  deps: React.DependencyList
): T {
  return useCallback(callback, deps);
}

/**
 * 稳定的回调Hook，函数引用永远不变
 * @param callback 回调函数
 * @returns 稳定的回调函数
 */
export function useStableCallback<T extends (...args: any[]) => any>(
  callback: T
): T {
  const callbackRef = useRef(callback);
  callbackRef.current = callback;

  return useCallback((...args: Parameters<T>) => {
    return callbackRef.current(...args);
  }, []) as T;
}

/**
 * 事件处理器Hook，优化事件处理函数
 * @param handler 事件处理函数
 * @param deps 依赖数组
 * @returns 优化的事件处理函数
 */
export function useEventHandler<T extends (...args: any[]) => any>(
  handler: T,
  deps: React.DependencyList = []
): T {
  return useCallback(handler, deps);
}