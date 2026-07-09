import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      component: () => import('@/layouts/MainLayout.vue'),
      children: [
        {
          path: '',
          name: 'home',
          component: () => import('@/views/HomeView.vue'),
          meta: { title: '首页' },
        },
        {
          path: 'data-download',
          name: 'data-download',
          component: () => import('@/views/DataDownloadView.vue'),
          meta: { title: '股票数据更新' },
        },
        {
          path: 'stock-overview',
          name: 'stock-overview',
          component: () => import('@/views/StockOverviewView.vue'),
          meta: { title: '股票走势概览' },
        },
        {
          path: 'strategy-config',
          name: 'strategy-config',
          component: () => import('@/views/StrategyConfigView.vue'),
          meta: { title: '选股策略配置' },
        },
        {
          path: 'selection-result',
          name: 'selection-result',
          component: () => import('@/views/SelectionResultView.vue'),
          meta: { title: '选股生成结果' },
        },
        {
          path: 'backtest',
          name: 'backtest',
          component: () => import('@/views/BacktestView.vue'),
          meta: { title: '回测分析展示' },
        },
      ],
    },
  ],
})

export default router
