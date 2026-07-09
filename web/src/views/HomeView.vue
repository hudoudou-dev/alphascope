<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { dataApi } from '@/api'

const router = useRouter()
const totalStocks = ref(0)
const totalRows = ref(0)
const totalSize = ref(0)

const features = [
  {
    title: '数据管理',
    desc: '支持多数据源自动切换、增量更新、K线可视化验真',
    icon: 'Download',
    color: '#409eff',
    route: '/data-download',
  },
  {
    title: '选股策略',
    desc: '灵活的超参配置界面、自定义评分权重、Top-N 候选股票',
    icon: 'Aim',
    color: '#67c23a',
    route: '/strategy-config',
  },
  {
    title: '回测分析',
    desc: '支持真实数据和合成数据、交易记录、资产变化曲线',
    icon: 'DataAnalysis',
    color: '#e6a23c',
    route: '/backtest',
  },
]

const steps = [
  '股票数据更新：下载或更新股票数据',
  '股票走势概览：查看已下载的股票数据和K线图',
  '选股策略配置：配置选股策略的超参',
  '选股生成结果：运行选股策略，查看候选股票',
  '回测分析展示：对候选股票进行回测分析',
]

onMounted(async () => {
  try {
    const res = await dataApi.listStocks()
    totalStocks.value = res.data.total
    totalRows.value = res.data.total_rows
    totalSize.value = res.data.total_size_mb
  } catch {
    // ignored
  }
})
</script>

<template>
  <div class="page-container">
    <h1 class="page-title">AlphaScope - A股量化选股与回测平台</h1>
    <el-divider />

    <el-row :gutter="20">
      <el-col :span="8">
        <el-card shadow="hover" class="metric-card">
          <div class="metric-value">{{ totalStocks }}</div>
          <div class="metric-label">已下载股票数</div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover" class="metric-card">
          <div class="metric-value">{{ totalRows.toLocaleString() }}</div>
          <div class="metric-label">总数据行数</div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover" class="metric-card">
          <div class="metric-value">{{ totalSize.toFixed(2) }} MB</div>
          <div class="metric-label">总文件大小</div>
        </el-card>
      </el-col>
    </el-row>

    <h2 class="section-title">核心功能</h2>
    <el-row :gutter="20">
      <el-col v-for="f in features" :key="f.title" :span="8">
        <el-card shadow="hover" class="feature-card" @click="router.push(f.route)">
          <div class="feature-icon" :style="{ color: f.color }">
            <el-icon size="32"><component :is="f.icon" /></el-icon>
          </div>
          <h3>{{ f.title }}</h3>
          <p>{{ f.desc }}</p>
        </el-card>
      </el-col>
    </el-row>

    <h2 class="section-title">使用指南</h2>
    <el-card shadow="never">
      <el-steps direction="vertical" :active="0">
        <el-step v-for="(step, i) in steps" :key="i" :title="step" />
      </el-steps>
    </el-card>

    <h2 class="section-title">技术规范</h2>
    <el-card shadow="never">
      <el-descriptions :column="2" border>
        <el-descriptions-item label="数据契约">统一 Schema，保证数据质量</el-descriptions-item>
        <el-descriptions-item label="策略隔离">所有策略继承 BaseStrategy，完全隔离</el-descriptions-item>
        <el-descriptions-item label="严禁未来函数">回测系统严格禁止未来数据泄露</el-descriptions-item>
        <el-descriptions-item label="配置优先">所有可变运行行为必须配置化</el-descriptions-item>
      </el-descriptions>
    </el-card>
  </div>
</template>

<style scoped lang="scss">
.feature-card {
  cursor: pointer;
  transition: transform 0.2s;
  text-align: center;
  padding: 10px 0;

  &:hover {
    transform: translateY(-4px);
  }

  .feature-icon {
    margin-bottom: 12px;
  }

  h3 {
    margin: 8px 0;
    font-size: 16px;
  }

  p {
    color: var(--el-text-color-secondary);
    font-size: 13px;
    line-height: 1.6;
    margin: 0;
  }
}
</style>
