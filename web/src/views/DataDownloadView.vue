<script setup lang="ts">
import { ref, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { dataApi } from '@/api'

const loading = ref(false)
const taskId = ref('')
const taskStatus = ref<any>(null)
const wsConnected = ref(false)
let ws: WebSocket | null = null

const form = ref({
  mode: 'batch' as 'single' | 'batch' | 'full',
  codesText: '',
  startDate: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10),
  endDate: new Date().toISOString().slice(0, 10),
  adjust: 'qfq',
})

const adjustOptions = [
  { label: '前复权', value: 'qfq' },
  { label: '后复权', value: 'hfq' },
  { label: '不复权', value: 'none' },
]

const startDownload = async () => {
  let codes: string[] = []

  if (form.value.mode === 'single') {
    if (!form.value.codesText.trim()) {
      ElMessage.warning('请输入股票代码')
      return
    }
    codes = [form.value.codesText.trim()]
  } else if (form.value.mode === 'batch') {
    codes = form.value.codesText
      .split(/[\n,]/)
      .map((c) => c.trim())
      .filter(Boolean)
    if (codes.length === 0) {
      ElMessage.warning('请输入至少一个股票代码')
      return
    }
  }

  loading.value = true
  try {
    const payload: any = {
      start_date: form.value.startDate,
      end_date: form.value.endDate,
      adjust: form.value.adjust,
      mode: form.value.mode,
    }
    if (form.value.mode !== 'full') {
      payload.codes = codes
    }

    const res = await dataApi.download(payload)
    taskId.value = res.data.task_id
    ElMessage.success(`下载任务已启动，共 ${res.data.total} 只`)
    connectWebSocket()
  } catch {
    // error handled by interceptor
  } finally {
    loading.value = false
  }
}

const connectWebSocket = () => {
  closeWebSocket()

  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const wsHost = import.meta.env.DEV ? 'localhost:8000' : window.location.host
  const wsUrl = `${protocol}//${wsHost}/api/data/download/${taskId.value}/ws`

  ws = new WebSocket(wsUrl)

  ws.onopen = () => {
    wsConnected.value = true
  }

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      taskStatus.value = data
      if (!data.is_running) {
        closeWebSocket()
      }
    } catch {
      // ignore parse errors
    }
  }

  ws.onerror = () => {
    wsConnected.value = false
  }

  ws.onclose = () => {
    wsConnected.value = false
  }
}

const closeWebSocket = () => {
  if (ws) {
    ws.close()
    ws = null
  }
  wsConnected.value = false
}

const stopDownload = async () => {
  if (!taskId.value) return
  try {
    await dataApi.stopDownload(taskId.value)
    ElMessage.warning('已停止下载')
  } catch {
    // ignored
  }
}

onUnmounted(() => {
  closeWebSocket()
})
</script>

<template>
  <div class="page-container">
    <h1 class="page-title">股票数据更新</h1>

    <el-alert type="info" :closable="false" style="margin-bottom: 20px">
      增量更新策略：已存在的股票自动识别最新日期，只下载新增数据。支持多数据源自动切换（AKShare → BaoStock → Tushare）。
    </el-alert>

    <el-row :gutter="20">
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header><strong>下载配置</strong></template>

          <el-form :model="form" label-width="100px">
            <el-form-item label="下载范围">
              <el-radio-group v-model="form.mode">
                <el-radio-button value="single">单股下载</el-radio-button>
                <el-radio-button value="batch">批量清单</el-radio-button>
                <el-radio-button value="full">全量下载</el-radio-button>
              </el-radio-group>
            </el-form-item>

            <el-form-item v-if="form.mode !== 'full'" label="股票代码">
              <el-input
                v-model="form.codesText"
                :type="form.mode === 'batch' ? 'textarea' : 'text'"
                :rows="5"
                :placeholder="form.mode === 'single' ? '例如: 600519' : '每行一个或用逗号分隔\n600519\n000001\n300750'"
              />
            </el-form-item>

            <el-form-item v-else label="说明">
              <el-text type="warning">全量下载将获取所有A股股票数据（主板/创业板/科创板），可能耗时较长。</el-text>
            </el-form-item>

            <el-form-item label="时间范围">
              <el-col :span="11">
                <el-date-picker v-model="form.startDate" type="date" placeholder="开始日期" format="YYYY-MM-DD" value-format="YYYY-MM-DD" style="width: 100%" />
              </el-col>
              <el-col :span="2" style="text-align: center">~</el-col>
              <el-col :span="11">
                <el-date-picker v-model="form.endDate" type="date" placeholder="结束日期" format="YYYY-MM-DD" value-format="YYYY-MM-DD" style="width: 100%" />
              </el-col>
            </el-form-item>

            <el-form-item label="复权类型">
              <el-select v-model="form.adjust" style="width: 100%">
                <el-option v-for="o in adjustOptions" :key="o.value" :label="o.label" :value="o.value" />
              </el-select>
            </el-form-item>

            <el-form-item>
              <el-button type="primary" :loading="loading" @click="startDownload">开始下载</el-button>
              <el-button v-if="taskStatus?.is_running" type="danger" @click="stopDownload">停止下载</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>

      <el-col :span="12">
        <el-card shadow="hover">
          <template #header>
            <div style="display: flex; justify-content: space-between; align-items: center">
              <strong>下载进度</strong>
              <el-tag v-if="wsConnected" type="success" size="small" effect="dark">
                <span style="display: inline-flex; align-items: center; gap: 4px">
                  <span style="width: 6px; height: 6px; border-radius: 50%; background: #67c23a; display: inline-block"></span>
                  WebSocket 已连接
                </span>
              </el-tag>
              <el-tag v-else-if="taskStatus" type="info" size="small">HTTP</el-tag>
            </div>
          </template>

          <template v-if="taskStatus">
            <el-progress
              :percentage="taskStatus.progress_pct"
              :status="taskStatus.is_running ? '' : (taskStatus.failed > 0 ? 'warning' : 'success')"
              :stroke-width="20"
              :text-inside="true"
              style="margin-bottom: 16px"
            />

            <el-descriptions :column="2" border size="small" style="margin-bottom: 16px">
              <el-descriptions-item label="总数">{{ taskStatus.total }}</el-descriptions-item>
              <el-descriptions-item label="已完成">
                <el-text type="success">{{ taskStatus.completed }}</el-text>
              </el-descriptions-item>
              <el-descriptions-item label="失败">
                <el-text type="danger">{{ taskStatus.failed }}</el-text>
              </el-descriptions-item>
              <el-descriptions-item label="预计剩余">{{ taskStatus.eta }}</el-descriptions-item>
              <el-descriptions-item label="当前股票" :span="2">
                {{ taskStatus.current_code || '—' }}
              </el-descriptions-item>
              <el-descriptions-item label="当前数据源" :span="2">
                {{ taskStatus.current_provider || '—' }}
              </el-descriptions-item>
            </el-descriptions>

            <el-text type="info" size="small"><strong>下载日志：</strong></el-text>
            <div class="log-box">
              <div v-for="(log, i) in taskStatus.logs" :key="i" class="log-line" :class="{
                'log-success': log.startsWith('[SUCCESS]'),
                'log-error': log.startsWith('[ERROR]'),
                'log-warning': log.startsWith('[WARNING]'),
              }">{{ log }}</div>
            </div>
          </template>

          <el-empty v-else description="暂无下载任务" />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<style scoped lang="scss">
.log-box {
  max-height: 300px;
  overflow-y: auto;
  background: #1a1d29;
  border-radius: 6px;
  padding: 10px;
  margin-top: 8px;

  .log-line {
    font-family: 'Monaco', 'Menlo', monospace;
    font-size: 12px;
    line-height: 1.8;
    color: #cfd3dc;

    &.log-success { color: #67c23a; }
    &.log-error { color: #f56c6c; }
    &.log-warning { color: #e6a23c; }
  }
}
</style>
