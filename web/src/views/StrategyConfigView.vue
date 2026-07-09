<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { strategyApi } from '@/api'

const loading = ref(false)
const saving = ref(false)

const form = ref({
  market_cap_min: 50,
  market_cap_max: 20000,
  price_min: 5.0,
  price_max: 2000.0,
  limit_up_min: 0,
  limit_down_max: 3,
  limit_stat_period: 60,
  max_up_threshold: 10.0,
  max_down_threshold: -10.0,
  initial_cash: 1000000,
  max_positions: 10,
  top_n: 20,
  min_score_threshold: 70.0,
  ma_alignment_weight: 40,
  price_position_weight: 30,
  trend_strength_weight: 30,
})

const weightTotal = () =>
  form.value.ma_alignment_weight + form.value.price_position_weight + form.value.trend_strength_weight

onMounted(async () => {
  loading.value = true
  try {
    const res = await strategyApi.getConfig()
    Object.assign(form.value, res.data)
  } catch {
    // ignored
  } finally {
    loading.value = false
  }
})

const save = async () => {
  saving.value = true
  try {
    const res = await strategyApi.updateConfig(form.value)
    ElMessage.success(res.data.message)
  } catch {
    // ignored
  } finally {
    saving.value = false
  }
}

const reset = async () => {
  try {
    await ElMessageBox.confirm('确定要将所有配置重置为默认值吗？', '确认重置', { type: 'warning' })
    const res = await strategyApi.resetConfig()
    ElMessage.warning(res.data.message)
    const cfg = await strategyApi.getConfig()
    Object.assign(form.value, cfg.data)
  } catch {
    // cancelled
  }
}
</script>

<template>
  <div class="page-container" v-loading="loading">
    <h1 class="page-title">选股策略配置</h1>

    <el-alert type="info" :closable="false" style="margin-bottom: 20px">
      所有配置与 config/settings.yaml 同步。保存后立即生效，重置将恢复为默认值。
    </el-alert>

    <!-- 市值与价格 -->
    <h2 class="section-title">市值与价格区间</h2>
    <el-row :gutter="20">
      <el-col :span="6">
        <el-form-item label="最小市值（亿元）">
          <el-input-number v-model="form.market_cap_min" :min="0" :max="20000" style="width: 100%" />
        </el-form-item>
      </el-col>
      <el-col :span="6">
        <el-form-item label="最大市值（亿元）">
          <el-input-number v-model="form.market_cap_max" :min="0" :max="20000" style="width: 100%" />
        </el-form-item>
      </el-col>
      <el-col :span="6">
        <el-form-item label="最小股价（元）">
          <el-input-number v-model="form.price_min" :min="0" :max="2000" :step="0.5" style="width: 100%" />
        </el-form-item>
      </el-col>
      <el-col :span="6">
        <el-form-item label="最大股价（元）">
          <el-input-number v-model="form.price_max" :min="0" :max="2000" :step="0.5" style="width: 100%" />
        </el-form-item>
      </el-col>
    </el-row>

    <!-- 涨跌停配置 -->
    <h2 class="section-title">涨跌停配置</h2>
    <el-row :gutter="20">
      <el-col :span="6">
        <el-form-item label="最小涨停次数">
          <el-input-number v-model="form.limit_up_min" :min="0" :max="20" style="width: 100%" />
        </el-form-item>
      </el-col>
      <el-col :span="6">
        <el-form-item label="最大跌停次数">
          <el-input-number v-model="form.limit_down_max" :min="0" :max="20" style="width: 100%" />
        </el-form-item>
      </el-col>
      <el-col :span="6">
        <el-form-item label="统计周期（天）">
          <el-slider v-model="form.limit_stat_period" :min="5" :max="60" show-input style="width: 100%" />
        </el-form-item>
      </el-col>
      <el-col :span="3">
        <el-form-item label="涨幅阈值(%)">
          <el-slider v-model="form.max_up_threshold" :min="0" :max="20" :step="0.5" show-input style="width: 100%" />
        </el-form-item>
      </el-col>
      <el-col :span="3">
        <el-form-item label="跌幅阈值(%)">
          <el-slider v-model="form.max_down_threshold" :min="-20" :max="0" :step="0.5" show-input style="width: 100%" />
        </el-form-item>
      </el-col>
    </el-row>

    <!-- 持仓配置 -->
    <h2 class="section-title">持仓配置</h2>
    <el-row :gutter="20">
      <el-col :span="6">
        <el-form-item label="初始资金（元）">
          <el-input-number v-model="form.initial_cash" :min="10000" :max="100000000" :step="10000" style="width: 100%" />
        </el-form-item>
      </el-col>
      <el-col :span="6">
        <el-form-item label="最大持仓数">
          <el-slider v-model="form.max_positions" :min="1" :max="20" show-input style="width: 100%" />
        </el-form-item>
      </el-col>
      <el-col :span="6">
        <el-form-item label="Top-N 数量">
          <el-slider v-model="form.top_n" :min="5" :max="50" show-input style="width: 100%" />
        </el-form-item>
      </el-col>
      <el-col :span="6">
        <el-form-item label="最小评分阈值">
          <el-slider v-model="form.min_score_threshold" :min="0" :max="100" :step="5" show-input style="width: 100%" />
        </el-form-item>
      </el-col>
    </el-row>

    <!-- 评分权重 -->
    <h2 class="section-title">评分权重配置</h2>
    <el-row :gutter="20">
      <el-col :span="8">
        <el-form-item label="均线排列权重(%)">
          <el-slider v-model="form.ma_alignment_weight" :min="0" :max="100" show-input style="width: 100%" />
        </el-form-item>
      </el-col>
      <el-col :span="8">
        <el-form-item label="价格位置权重(%)">
          <el-slider v-model="form.price_position_weight" :min="0" :max="100" show-input style="width: 100%" />
        </el-form-item>
      </el-col>
      <el-col :span="8">
        <el-form-item label="趋势强度权重(%)">
          <el-slider v-model="form.trend_strength_weight" :min="0" :max="100" show-input style="width: 100%" />
        </el-form-item>
      </el-col>
    </el-row>

    <el-alert
      :type="weightTotal() === 100 ? 'success' : 'warning'"
      :closable="false"
      style="margin-bottom: 20px"
    >
      权重总和：{{ weightTotal() }}% {{ weightTotal() === 100 ? '✓' : '（建议调整为100%）' }}
    </el-alert>

    <!-- 操作按钮 -->
    <div style="text-align: center; padding: 20px 0">
      <el-button type="primary" size="large" :loading="saving" @click="save">保存配置</el-button>
      <el-button size="large" @click="reset">重置配置</el-button>
    </div>
  </div>
</template>
