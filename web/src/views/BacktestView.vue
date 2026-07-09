<script setup lang="ts">
import { ref, nextTick, watch } from 'vue'
import * as echarts from 'echarts'
import { ElMessage } from 'element-plus'
import { backtestApi } from '@/api'

const loading = ref(false)
const result = ref<any>(null)

const form = ref({
  start_date: '2024-01-01',
  end_date: '2024-06-30',
  initial_cash: 1000000,
  max_positions: 10,
  stop_loss_pct: -8.0,
  take_profit_pct: 20.0,
  max_drawdown_limit: 20,
})

const assetChartRef = ref<HTMLDivElement>()
let assetChart: echarts.ECharts | null = null

const runBacktest = async () => {
  loading.value = true
  result.value = null
  try {
    const res = await backtestApi.run(form.value)
    result.value = res.data
    ElMessage.success('回测完成！')
    await nextTick()
    renderAssetChart()
  } catch {
    // ignored
  } finally {
    loading.value = false
  }
}

const renderAssetChart = () => {
  if (!result.value?.portfolio_states?.length) return
  if (!assetChartRef.value) return

  if (!assetChart) {
    assetChart = echarts.init(assetChartRef.value, 'dark')
  }

  const states = result.value.portfolio_states
  const dates = states.map((s: any) => s.date)
  const values = states.map((s: any) => s.total_value)

  assetChart.setOption({
    backgroundColor: 'transparent',
    title: { text: '总资产变化曲线', left: 'center', textStyle: { fontSize: 14 } },
    tooltip: { trigger: 'axis' },
    grid: { left: '8%', right: '5%', top: 50, bottom: 50 },
    xAxis: { type: 'category', data: dates, boundaryGap: false },
    yAxis: { type: 'value', name: '总资产（元）' },
    series: [
      {
        name: '总资产',
        type: 'line',
        data: values,
        smooth: true,
        lineStyle: { color: '#409eff', width: 2 },
        areaStyle: { color: 'rgba(64, 158, 255, 0.1)' },
      },
    ],
  }, true)
  assetChart.resize()
}
</script>

<template>
  <div class="page-container">
    <h1 class="page-title">回测分析展示</h1>

    <!-- 回测配置 -->
    <el-card shadow="hover" style="margin-bottom: 16px">
      <template #header><strong>回测配置</strong></template>
      <el-form :model="form" label-width="120px" inline>
        <el-form-item label="开始日期">
          <el-date-picker v-model="form.start_date" type="date" format="YYYY-MM-DD" value-format="YYYY-MM-DD" />
        </el-form-item>
        <el-form-item label="结束日期">
          <el-date-picker v-model="form.end_date" type="date" format="YYYY-MM-DD" value-format="YYYY-MM-DD" />
        </el-form-item>
        <el-form-item label="初始资金（元）">
          <el-input-number v-model="form.initial_cash" :min="10000" :max="100000000" :step="100000" />
        </el-form-item>
        <el-form-item label="最大持仓数">
          <el-input-number v-model="form.max_positions" :min="1" :max="50" />
        </el-form-item>
        <el-form-item label="止损线(%)">
          <el-input-number v-model="form.stop_loss_pct" :min="-20" :max="-1" />
        </el-form-item>
        <el-form-item label="止盈线(%)">
          <el-input-number v-model="form.take_profit_pct" :min="5" :max="100" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" size="large" :loading="loading" @click="runBacktest">运行回测</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 回测结果 -->
    <template v-if="result">
      <!-- 结果概览 -->
      <el-card shadow="hover" style="margin-bottom: 16px">
        <template #header><strong>回测结果概览</strong></template>
        <el-row :gutter="16">
          <el-col :span="4" v-for="metric in [
            { label: '总收益率', value: result.total_return + '%', color: result.total_return >= 0 ? '#f56c6c' : '#67c23a' },
            { label: '年化收益率', value: result.annual_return + '%', color: result.annual_return >= 0 ? '#f56c6c' : '#67c23a' },
            { label: '最大回撤', value: result.max_drawdown + '%', color: '#f56c6c' },
            { label: '夏普比率', value: result.sharpe_ratio, color: '#409eff' },
            { label: '总交易次数', value: result.total_trades, color: '#e6a23c' },
            { label: '成交胜率', value: result.win_rate + '%', color: '#67c23a' },
          ]" :key="metric.label">
            <el-card shadow="never" class="metric-card">
              <div class="metric-value" :style="{ color: metric.color }">{{ metric.value }}</div>
              <div class="metric-label">{{ metric.label }}</div>
            </el-card>
          </el-col>
        </el-row>
      </el-card>

      <!-- 资产变化曲线 -->
      <el-card shadow="hover" style="margin-bottom: 16px">
        <div ref="assetChartRef" style="height: 400px" />
      </el-card>

      <!-- 交易记录 -->
      <el-card shadow="hover">
        <template #header><strong>交易记录明细</strong>（共 {{ result.transactions.length }} 条）</template>
        <el-table :data="result.transactions" stripe size="small" max-height="400">
          <el-table-column type="index" width="60" />
          <el-table-column prop="date" label="交易时间" width="120" />
          <el-table-column prop="code" label="股票代码" min-width="120" />
          <el-table-column prop="action" label="操作" width="80">
            <template #default="{ row }">
              <el-tag :type="row.action === 'BUY' ? 'danger' : 'success'" size="small">{{ row.action === 'BUY' ? '买入' : '卖出' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="price" label="股价" width="100" />
          <el-table-column prop="shares" label="数量" width="100" />
          <el-table-column prop="amount" label="金额" width="120" />
          <el-table-column prop="profit" label="盈利" width="100">
            <template #default="{ row }">
              <el-text :type="row.profit >= 0 ? 'danger' : 'success'">{{ row.profit.toFixed(2) }}</el-text>
            </template>
          </el-table-column>
          <el-table-column prop="total_value" label="账户总金额" width="120" />
        </el-table>
      </el-card>
    </template>

    <el-empty v-else-if="!loading" description="配置回测参数后点击「运行回测」" />
  </div>
</template>
