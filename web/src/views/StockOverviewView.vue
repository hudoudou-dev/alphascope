<script setup lang="ts">
import { ref, onMounted, watch, nextTick } from 'vue'
import * as echarts from 'echarts'
import { dataApi } from '@/api'

const stocks = ref<any[]>([])
const selectedStock = ref('')
const stockDetail = ref<any>(null)
const loading = ref(false)
const chartRef = ref<HTMLDivElement>()
let chartInstance: echarts.ECharts | null = null

const showMA = ref(true)
const maPeriods = ref([5, 20])
const showVolume = ref(true)

onMounted(async () => {
  await loadStocks()
})

const loadStocks = async () => {
  try {
    const res = await dataApi.listStocks()
    stocks.value = res.data.stocks
    if (stocks.value.length > 0) {
      selectedStock.value = stocks.value[0].code
    }
  } catch {
    // ignored
  }
}

watch(selectedStock, async (val) => {
  if (!val) return
  loading.value = true
  try {
    const res = await dataApi.getStock(val, 500)
    stockDetail.value = res.data
    await nextTick()
    renderChart()
  } catch {
    // ignored
  } finally {
    loading.value = false
  }
})

watch([showMA, maPeriods, showVolume], () => {
  renderChart()
})

const renderChart = () => {
  if (!stockDetail.value?.data || !chartRef.value) return

  if (!chartInstance) {
    chartInstance = echarts.init(chartRef.value, 'dark')
  }

  const data = stockDetail.value.data
  const dates = data.map((d: any) => d.date?.slice(0, 10) || '')
  const ohlc = data.map((d: any) => [d.open_price, d.close_price, d.low_price, d.high_price])
  const volumes = data.map((d: any) => d.volume)

  const maLines: any[] = []
  if (showMA.value) {
    for (const period of maPeriods.value) {
      const maData = calcMA(data, period)
      maLines.push({
        name: `MA${period}`,
        type: 'line',
        data: maData,
        smooth: true,
        lineStyle: { width: 1 },
      })
    }
  }

  const series: any[] = [
    {
      name: 'K线',
      type: 'candlestick',
      data: ohlc,
      itemStyle: {
        color: '#ef232a',
        color0: '#14b143',
        borderColor: '#ef232a',
        borderColor0: '#14b143',
      },
    },
    ...maLines,
  ]

  if (showVolume.value) {
    series.push({
      name: '成交量',
      type: 'bar',
      xAxisIndex: 1,
      yAxisIndex: 1,
      data: volumes,
      itemStyle: { color: 'rgba(76, 175, 80, 0.5)' },
    })
  }

  chartInstance.setOption({
    backgroundColor: 'transparent',
    title: { text: `${stockDetail.value.code} ${stockDetail.value.name || ''} K线图`, left: 'center', textStyle: { fontSize: 14 } },
    tooltip: { trigger: 'axis', axisPointer: { type: 'cross' } },
    legend: { top: 30, data: ['K线', ...maLines.map((m) => m.name), ...(showVolume.value ? ['成交量'] : [])] },
    grid: [
      { left: '8%', right: '5%', top: 60, height: showVolume.value ? '55%' : '75%' },
      { left: '8%', right: '5%', top: '75%', height: '15%' },
    ],
    xAxis: [
      { type: 'category', data: dates, boundaryGap: false, axisLine: { lineStyle: { color: '#666' } } },
      { type: 'category', gridIndex: 1, data: dates, show: false },
    ],
    yAxis: [
      { scale: true, splitLine: { lineStyle: { color: '#2a2d3a' } } },
      { gridIndex: 1, splitNumber: 2, axisLabel: { show: false }, axisLine: { show: false }, axisTick: { show: false }, splitLine: { show: false } },
    ],
    series,
  }, true)

  chartInstance.resize()
}

const calcMA = (data: any[], period: number) => {
  const result: (number | null)[] = []
  for (let i = 0; i < data.length; i++) {
    if (i < period - 1) {
      result.push(null)
    } else {
      let sum = 0
      for (let j = 0; j < period; j++) {
        sum += data[i - j].close_price
      }
      result.push(Number((sum / period).toFixed(2)))
    }
  }
  return result
}

const tableData = ref<any[]>([])
watch(stockDetail, (val) => {
  if (val?.data) {
    tableData.value = [...val.data].reverse().map((d: any) => ({
      date: d.date?.slice(0, 10),
      open: d.open_price,
      high: d.high_price,
      low: d.low_price,
      close: d.close_price,
      volume: d.volume,
      pct_chg: d.pct_chg,
    }))
  }
})
</script>

<template>
  <div class="page-container">
    <h1 class="page-title">股票走势概览</h1>

    <!-- 统计卡片 -->
    <el-row :gutter="16" style="margin-bottom: 16px">
      <el-col :span="6">
        <el-card shadow="hover" class="metric-card">
          <div class="metric-value">{{ stocks.length }}</div>
          <div class="metric-label">总股票数</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="metric-card">
          <div class="metric-value">{{ stocks.reduce((s, d) => s + d.rows, 0).toLocaleString() }}</div>
          <div class="metric-label">总数据行数</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="metric-card">
          <div class="metric-value">{{ stocks.reduce((s, d) => s + d.file_size_kb, 0).toFixed(0) }} KB</div>
          <div class="metric-label">总文件大小</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="metric-card">
          <div class="metric-value">{{ stocks.length > 0 ? Math.round(stocks.reduce((s, d) => s + d.rows, 0) / stocks.length) : 0 }}</div>
          <div class="metric-label">平均行数</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 股票列表 -->
    <el-card shadow="hover" style="margin-bottom: 16px">
      <template #header><strong>已下载股票列表</strong></template>
      <el-table :data="stocks" stripe size="small" @row-click="(row: any) => (selectedStock = row.code)" highlight-current-row>
        <el-table-column prop="code" label="股票代码" min-width="140" />
        <el-table-column prop="name" label="股票名称" min-width="80" />
        <el-table-column prop="rows" label="数据行数" width="100" sortable />
        <el-table-column prop="start_date" label="开始日期" min-width="120" />
        <el-table-column prop="end_date" label="结束日期" min-width="120" />
        <el-table-column prop="file_size_kb" label="文件大小(KB)" width="120" sortable>
          <template #default="{ row }">{{ row.file_size_kb.toFixed(2) }}</template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- K线图 -->
    <el-card shadow="hover" style="margin-bottom: 16px">
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <strong>K线图可视化</strong>
          <div>
            <el-select v-model="selectedStock" placeholder="选择股票" size="small" style="width: 260px">
              <el-option v-for="s in stocks" :key="s.code" :label="`${s.code} ${s.name || ''}`" :value="s.code" />
            </el-select>
            <el-checkbox v-model="showMA" style="margin-left: 12px">均线</el-checkbox>
            <el-checkbox v-model="showVolume">成交量</el-checkbox>
          </div>
        </div>
      </template>
      <div ref="chartRef" style="height: 500px" v-loading="loading" />
    </el-card>

    <!-- 数据明细 -->
    <el-card shadow="hover">
      <template #header><strong>数据明细</strong> ({{ stockDetail?.name || selectedStock }})</template>
      <el-table :data="tableData" stripe size="small" max-height="400">
        <el-table-column prop="date" label="日期" width="120" />
        <el-table-column prop="open" label="开盘价" width="100" />
        <el-table-column prop="high" label="最高价" width="100" />
        <el-table-column prop="low" label="最低价" width="100" />
        <el-table-column prop="close" label="收盘价" width="100" />
        <el-table-column prop="volume" label="成交量" width="120" />
        <el-table-column prop="pct_chg" label="涨跌幅%" width="100">
          <template #default="{ row }">
            <el-text :type="row.pct_chg > 0 ? 'danger' : 'success'">{{ row.pct_chg?.toFixed(2) }}%</el-text>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>
