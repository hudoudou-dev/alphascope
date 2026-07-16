<script setup lang="ts">
import { ref, nextTick, onBeforeUnmount } from 'vue'
import * as echarts from 'echarts'
import { ElMessage } from 'element-plus'
import { backtestApi } from '@/api'

const loading = ref(false)
const result = ref<any>(null)

// 进度相关
const progressPercent = ref(0)
const progressMessage = ref('')
const progressStatus = ref<'success' | 'exception' | 'warning' | ''>('')
let pollTimer: ReturnType<typeof setInterval> | null = null

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

/** 轮询任务状态，完成后获取结果 */
const pollTask = async (taskId: string) => {
  try {
    const res = await backtestApi.status(taskId)
    const { status, progress, message, error } = res.data

    progressPercent.value = progress
    progressMessage.value = message

    if (status === 'completed') {
      stopPolling()
      progressStatus.value = 'success'
      progressMessage.value = '回测完成，正在加载结果...'

      // 获取完整结果
      try {
        const resultRes = await backtestApi.result(taskId)
        result.value = resultRes.data
        progressMessage.value = ''
        loading.value = false
        ElMessage.success('回测完成！')
        await nextTick()
        renderAssetChart()
      } catch (e: any) {
        const detail = e.response?.data?.detail || '获取结果失败'
        ElMessage.error(detail)
        loading.value = false
        progressStatus.value = 'exception'
        progressMessage.value = detail
      }
      return
    }

    if (status === 'failed') {
      stopPolling()
      progressStatus.value = 'exception'
      progressMessage.value = error || '回测执行失败'
      loading.value = false
      ElMessage.error(error || '回测执行失败')
      return
    }

    // 仍在运行中，继续轮询
  } catch {
    // 轮询失败不中断，可能网络抖动
  }
}

const startPolling = (taskId: string) => {
  stopPolling()
  // 立即查询一次，然后每 1.5 秒轮询
  pollTask(taskId)
  pollTimer = setInterval(() => pollTask(taskId), 1500)
}

const stopPolling = () => {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

onBeforeUnmount(() => {
  stopPolling()
  assetChart?.dispose()
})

const runBacktest = async () => {
  loading.value = true
  result.value = null
  progressPercent.value = 0
  progressMessage.value = '正在提交回测任务...'
  progressStatus.value = ''

  try {
    const res = await backtestApi.submit(form.value)
    const { task_id } = res.data
    ElMessage.success('回测任务已提交，后台计算中...')
    progressMessage.value = '任务已提交，等待后台执行...'
    startPolling(task_id)
  } catch (e: any) {
    loading.value = false
    progressMessage.value = ''
    // error already shown by interceptor
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

    <!-- 进度条 -->
    <el-card v-if="loading || progressMessage" shadow="hover" style="margin-bottom: 16px">
      <template #header><strong>回测进度</strong></template>
      <div style="padding: 8px 0">
        <el-progress
          :percentage="progressPercent"
          :status="progressStatus"
          :stroke-width="20"
        />
        <p style="margin-top: 12px; color: #909399; text-align: center;">
          {{ progressMessage }}
        </p>
        <p v-if="loading" style="margin-top: 4px; color: #c0c4cc; font-size: 12px; text-align: center;">
          回测需要处理大量历史数据，请耐心等待，无需保持页面打开...
        </p>
      </div>
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
          <el-table-column prop="code" label="股票代码" width="100" />
          <el-table-column prop="name" label="股票名称" min-width="100" />
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
