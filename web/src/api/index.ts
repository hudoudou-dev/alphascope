import axios from 'axios'
import { ElMessage } from 'element-plus'

const http = axios.create({
  baseURL: '/api',
  timeout: 120000,
})

http.interceptors.response.use(
  (response) => response,
  (error) => {
    const msg = error.response?.data?.detail || error.message || '请求失败'
    ElMessage.error(msg)
    return Promise.reject(error)
  }
)

export default http

// ==================== System ====================

export const systemApi = {
  health: () => http.get('/system/health'),
  info: () => http.get('/system/info'),
}

// ==================== Data ====================

export const dataApi = {
  listStocks: () => http.get('/data/stocks'),
  getStock: (code: string, limit = 100) => http.get(`/data/stocks/${code}`, { params: { limit } }),
  download: (data: {
    codes?: string[]
    start_date: string
    end_date: string
    adjust: string
    mode: string
  }) => http.post('/data/download', data),
  downloadStatus: (taskId: string) => http.get(`/data/download/${taskId}/status`),
  stopDownload: (taskId: string) => http.post(`/data/download/${taskId}/stop`),
  deleteStock: (code: string) => http.delete(`/data/stocks/${code}`),
  fullStockList: () => http.get('/data/stock-list'),
}

// ==================== Strategy ====================

export const strategyApi = {
  getConfig: () => http.get('/strategy/config'),
  updateConfig: (data: Record<string, any>) => http.put('/strategy/config', data),
  resetConfig: () => http.post('/strategy/config/reset'),
}

// ==================== Selection ====================

export const selectionApi = {
  run: () => http.post('/selection/run'),
}

// ==================== Backtest ====================

export const backtestApi = {
  run: (data: {
    start_date: string
    end_date: string
    initial_cash: number
    max_positions: number
    stop_loss_pct: number
    take_profit_pct: number
    max_drawdown_limit: number
  }) => http.post('/backtest/run', data),
}

// ==================== Calendar ====================

export const calendarApi = {
  check: (date: string) => http.get('/calendar/check', { params: { check_date: date } }),
  nav: (date: string) => http.get('/calendar/nav', { params: { check_date: date } }),
  days: (start: string, end: string) => http.get('/calendar/days', { params: { start_date: start, end_date: end } }),
  count: (start: string, end: string) => http.get('/calendar/count', { params: { start_date: start, end_date: end } }),
  download: (data: { start_date: string; end_date: string; source: string }) =>
    http.post('/calendar/download', data),
}
