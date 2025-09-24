/**
 * Cookie 工具函数
 */

/**
 * 设置cookie
 * @param name cookie名称
 * @param value cookie值
 * @param days 过期天数，默认30天
 */
export const setCookie = (name: string, value: string, days: number = 30): void => {
  const expires = new Date();
  expires.setTime(expires.getTime() + (days * 24 * 60 * 60 * 1000));
  document.cookie = `${name}=${value};expires=${expires.toUTCString()};path=/`;
};

/**
 * 获取cookie
 * @param name cookie名称
 * @returns cookie值，如果不存在返回null
 */
export const getCookie = (name: string): string | null => {
  const nameEQ = name + "=";
  const ca = document.cookie.split(';');
  for (let i = 0; i < ca.length; i++) {
    let c = ca[i];
    while (c.charAt(0) === ' ') c = c.substring(1, c.length);
    if (c.indexOf(nameEQ) === 0) return c.substring(nameEQ.length, c.length);
  }
  return null;
};

/**
 * 删除cookie
 * @param name cookie名称
 */
export const deleteCookie = (name: string): void => {
  document.cookie = `${name}=;expires=Thu, 01 Jan 1970 00:00:00 UTC;path=/;`;
};

/**
 * 分页设置相关的cookie操作
 */
export const PaginationCookie = {
  /**
   * 保存每页条数设置
   * @param pageSize 每页条数
   */
  setPageSize: (pageSize: number): void => {
    setCookie('data_management_page_size', pageSize.toString());
  },

  /**
   * 获取每页条数设置
   * @param defaultValue 默认值
   * @returns 每页条数
   */
  getPageSize: (defaultValue: number = 15): number => {
    const saved = getCookie('data_management_page_size');
    return saved ? parseInt(saved, 10) : defaultValue;
  },

  /**
   * 保存当前页码
   * @param current 当前页码
   */
  setCurrentPage: (current: number): void => {
    setCookie('data_management_current_page', current.toString());
  },

  /**
   * 获取当前页码
   * @param defaultValue 默认值
   * @returns 当前页码
   */
  getCurrentPage: (defaultValue: number = 1): number => {
    const saved = getCookie('data_management_current_page');
    return saved ? parseInt(saved, 10) : defaultValue;
  }
};
