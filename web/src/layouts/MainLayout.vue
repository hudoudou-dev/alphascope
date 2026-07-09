<script setup lang="ts">
import { useRoute } from 'vue-router'
import {
  HomeFilled,
  Download,
  TrendCharts,
  Setting,
  Aim,
  DataAnalysis,
} from '@element-plus/icons-vue'

const route = useRoute()

const menuItems = [
  { index: '/', title: '首页', icon: HomeFilled },
  { index: '/data-download', title: '股票数据更新', icon: Download },
  { index: '/stock-overview', title: '股票走势概览', icon: TrendCharts },
  { index: '/strategy-config', title: '选股策略配置', icon: Setting },
  { index: '/selection-result', title: '选股生成结果', icon: Aim },
  { index: '/backtest', title: '回测分析展示', icon: DataAnalysis },
]
</script>

<template>
  <el-container class="layout-container">
    <el-aside width="220px" class="layout-aside">
      <div class="logo">
        <el-icon size="24" color="#409eff"><TrendCharts /></el-icon>
        <span class="logo-text">AlphaScope</span>
      </div>
      <el-menu
        :default-active="route.path"
        router
        class="layout-menu"
      >
        <el-menu-item
          v-for="item in menuItems"
          :key="item.index"
          :index="item.index"
        >
          <el-icon><component :is="item.icon" /></el-icon>
          <span>{{ item.title }}</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="layout-header">
        <span class="header-title">{{ route.meta.title || 'AlphaScope' }}</span>
        <el-tag size="small" type="info">v3.1.0</el-tag>
      </el-header>

      <el-main class="layout-main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<style scoped lang="scss">
.layout-container {
  height: 100vh;
}

.layout-aside {
  background-color: #1a1d29;
  border-right: 1px solid #2a2d3a;
  overflow: hidden;
}

.logo {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 20px 16px;
  border-bottom: 1px solid #2a2d3a;

  .logo-text {
    font-size: 18px;
    font-weight: 700;
    color: #e5eaf3;
  }
}

.layout-menu {
  background-color: transparent;
  border-right: none;

  :deep(.el-menu-item) {
    color: #cfd3dc;

    &:hover {
      background-color: #2a2d3a;
    }

    &.is-active {
      background-color: var(--el-color-primary);
      color: #fff;
    }
  }
}

.layout-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background-color: #1a1d29;
  border-bottom: 1px solid #2a2d3a;

  .header-title {
    font-size: 18px;
    font-weight: 600;
    color: #e5eaf3;
  }
}

.layout-main {
  background-color: #0e1117;
  padding: 0;
  overflow-y: auto;
}
</style>
