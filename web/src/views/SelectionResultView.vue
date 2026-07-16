<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { selectionApi, strategyApi } from '@/api'

const loading = ref(false)
const config = ref<any>(null)
const results = ref<any[]>([])
const summary = ref({ total_scanned: 0, total_selected: 0, avg_score: 0, tradable_count: 0 })

onMounted(async () => {
  try {
    const res = await strategyApi.getConfig()
    config.value = res.data
  } catch {
    // ignored
  }
})

const runSelection = async () => {
  loading.value = true
  results.value = []
  try {
    const res = await selectionApi.run()
    summary.value = {
      total_scanned: res.data.total_scanned,
      total_selected: res.data.total_selected,
      avg_score: res.data.avg_score,
      tradable_count: res.data.tradable_count,
    }
    results.value = res.data.results
    ElMessage.success(`选股完成：扫描 ${summary.value.total_scanned} 只，选出 ${summary.value.total_selected} 只`)
  } catch {
    // ignored
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="page-container">
    <h1 class="page-title">选股生成结果</h1>

    <!-- 当前配置概览 -->
    <el-card shadow="hover" style="margin-bottom: 16px" v-if="config">
      <template #header><strong>当前选股策略配置</strong></template>
      <el-descriptions :column="4" border size="small">
        <el-descriptions-item label="初始资金">{{ config.initial_cash?.toLocaleString() }} 元</el-descriptions-item>
        <el-descriptions-item label="最大持仓数">{{ config.max_positions }} 只</el-descriptions-item>
        <el-descriptions-item label="Top-N">{{ config.top_n }} 只</el-descriptions-item>
        <el-descriptions-item label="最小评分阈值">{{ config.min_score_threshold }}</el-descriptions-item>
        <el-descriptions-item label="市值区间">{{ config.market_cap_min }} - {{ config.market_cap_max }} 亿元</el-descriptions-item>
        <el-descriptions-item label="股价区间">{{ config.price_min }} - {{ config.price_max }} 元</el-descriptions-item>
        <el-descriptions-item label="涨跌停统计周期">{{ config.limit_stat_period }} 天</el-descriptions-item>
        <el-descriptions-item label="最大涨幅阈值">{{ config.max_up_threshold }}%</el-descriptions-item>
      </el-descriptions>
    </el-card>

    <!-- 运行按钮 -->
    <div style="text-align: center; margin-bottom: 20px">
      <el-button type="primary" size="large" :loading="loading" @click="runSelection">
        运行选股策略
      </el-button>
    </div>

    <!-- 统计 -->
    <el-row :gutter="16" style="margin-bottom: 16px" v-if="results.length > 0">
      <el-col :span="6">
        <el-card shadow="hover" class="metric-card">
          <div class="metric-value">{{ summary.total_scanned }}</div>
          <div class="metric-label">扫描股票数</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="metric-card">
          <div class="metric-value">{{ summary.total_selected }}</div>
          <div class="metric-label">选出股票数</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="metric-card">
          <div class="metric-value">{{ summary.avg_score }}</div>
          <div class="metric-label">平均评分</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="metric-card">
          <div class="metric-value">{{ summary.tradable_count }}</div>
          <div class="metric-label">可交易数</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 选股结果表格 -->
    <el-card shadow="hover" v-if="results.length > 0">
      <template #header><strong>候选股票清单</strong>（按评分倒序）</template>
      <el-table :data="results" stripe size="default">
        <el-table-column type="index" label="排名" width="70" />
        <el-table-column prop="code" label="股票代码" min-width="120" />
        <el-table-column prop="name" label="股票名称" width="90" />
        <el-table-column prop="score" label="综合评分" width="110" sortable>
          <template #default="{ row }">
            <el-progress :percentage="row.score" :color="row.score >= 75 ? '#67c23a' : row.score >= 60 ? '#e6a23c' : '#f56c6c'" :show-text="false" :stroke-width="8" style="display: inline-block; width: 60px; vertical-align: middle" />
            <span style="margin-left: 8px">{{ row.score }}</span>
          </template>
        </el-table-column>
        <el-table-column label="子策略分项得分" min-width="340">
          <template #default="{ row }">
            <div style="display: flex; gap: 8px; flex-wrap: wrap; align-items: center">
              <el-tag size="small" type="primary" effect="plain">
                趋势 {{ row.sub_scores?.TrendStrategy ?? '-' }}
              </el-tag>
              <el-tag size="small" type="success" effect="plain">
                动量 {{ row.sub_scores?.MomentumStrategy ?? '-' }}
              </el-tag>
              <el-tag size="small" type="warning" effect="plain">
                量价 {{ row.sub_scores?.VolumePriceStrategy ?? '-' }}
              </el-tag>
              <el-tag size="small" type="info" effect="plain">
                质量 {{ row.sub_scores?.QualityStrategy ?? '-' }}
              </el-tag>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="close_price" label="股价（元）" width="100" />
        <el-table-column prop="pct_chg" label="涨跌幅" width="100">
          <template #default="{ row }">
            <el-text :type="row.pct_chg > 0 ? 'danger' : 'success'">{{ row.pct_chg.toFixed(2) }}%</el-text>
          </template>
        </el-table-column>
        <el-table-column prop="tradable" label="可交易" width="80">
          <template #default="{ row }">
            <el-tag :type="row.tradable ? 'success' : 'danger'" size="small">{{ row.tradable ? '是' : '否' }}</el-tag>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-empty v-else-if="!loading" description="点击上方按钮运行选股策略" />
  </div>
</template>
