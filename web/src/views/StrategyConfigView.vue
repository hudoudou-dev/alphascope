<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
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
  // 4子策略融合权重
  trend_weight: 35,
  momentum_weight: 25,
  volume_price_weight: 25,
  quality_weight: 15,
  // 风控开关
  enable_risk_control: true,
  enable_st_filter: true,
  enable_limit_filter: true,
  // 高级评分（实验性，默认关闭）
  cross_sectional_enabled: false,
  regime_enabled: false,
})

const weightTotal = computed(() =>
  form.value.trend_weight + form.value.momentum_weight + form.value.volume_price_weight + form.value.quality_weight
)

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

    <!-- 4子策略融合权重 -->
    <h2 class="section-title">子策略融合权重（4子策略）</h2>
    <el-alert type="info" :closable="false" style="margin-bottom: 12px">
      以下权重控制4套子策略在综合评分中的占比。权重会被自动归一化（即使总和不为100%），无需精确调整。
    </el-alert>
    <el-row :gutter="16">
      <el-col :span="5">
        <el-form-item label="趋势策略(%)">
          <el-slider v-model="form.trend_weight" :min="0" :max="100" show-input style="width: 100%" />
          <div class="factor-hint">ADX + MA排列 + MACD + 回调买点</div>
        </el-form-item>
      </el-col>
      <el-col :span="5">
        <el-form-item label="动量策略(%)">
          <el-slider v-model="form.momentum_weight" :min="0" :max="100" show-input style="width: 100%" />
          <div class="factor-hint">短期反转 + 多周期动量 + RSI</div>
        </el-form-item>
      </el-col>
      <el-col :span="5">
        <el-form-item label="量价策略(%)">
          <el-slider v-model="form.volume_price_weight" :min="0" :max="100" show-input style="width: 100%" />
          <div class="factor-hint">量比 + 换手率 + 量价相关 + OBV</div>
        </el-form-item>
      </el-col>
      <el-col :span="5">
        <el-form-item label="质量策略(%)">
          <el-slider v-model="form.quality_weight" :min="0" :max="100" show-input style="width: 100%" />
          <div class="factor-hint">波动率 + 偏度 + 基本面</div>
        </el-form-item>
      </el-col>
      <el-col :span="4">
        <el-alert
          :type="weightTotal === 100 ? 'success' : 'warning'"
          :closable="false"
          style="height: 100%; display: flex; align-items: center; justify-content: center; flex-direction: column; min-height: 80px"
        >
          <div style="font-size: 20px; font-weight: bold">{{ weightTotal }}%</div>
          <div style="font-size: 12px">{{ weightTotal === 100 ? '✓ 已平衡' : '⚠ 自动归一化' }}</div>
        </el-alert>
      </el-col>
    </el-row>

    <!-- 风控配置 -->
    <h2 class="section-title">风控配置</h2>
    <el-row :gutter="20">
      <el-col :span="8">
        <el-form-item>
          <el-checkbox v-model="form.enable_risk_control" label="启用风控" size="large" />
          <div class="factor-hint" style="margin-left: 24px">涨停/ST 过滤</div>
        </el-form-item>
      </el-col>
      <el-col :span="8">
        <el-form-item>
          <el-checkbox v-model="form.enable_st_filter" label="ST股过滤" size="large" />
          <div class="factor-hint" style="margin-left: 24px">自动过滤ST退市风险股票</div>
        </el-form-item>
      </el-col>
      <el-col :span="8">
        <el-form-item>
          <el-checkbox v-model="form.enable_limit_filter" label="涨停股过滤" size="large" />
          <div class="factor-hint" style="margin-left: 24px">当日涨停不可买入</div>
        </el-form-item>
      </el-col>
    </el-row>

    <!-- 高级评分（实验性） -->
    <h2 class="section-title">高级评分（实验性）</h2>
    <el-row :gutter="20">
      <el-col :span="8">
        <el-form-item>
          <el-checkbox v-model="form.cross_sectional_enabled" label="横截面标准化" size="large" />
          <div class="factor-hint" style="margin-left: 24px">按全市场横截面归一化子策略得分</div>
        </el-form-item>
      </el-col>
      <el-col :span="8">
        <el-form-item>
          <el-checkbox v-model="form.regime_enabled" label="行情自适应权重" size="large" />
          <div class="factor-hint" style="margin-left: 24px">依据市场广度/波动率切换子策略权重</div>
        </el-form-item>
      </el-col>
    </el-row>

    <!-- 操作按钮 -->
    <div style="text-align: center; padding: 20px 0">
      <el-button type="primary" size="large" :loading="saving" @click="save">保存配置</el-button>
      <el-button size="large" @click="reset">重置配置</el-button>
    </div>
  </div>
</template>

<style scoped>
.factor-hint {
  font-size: 11px;
  color: #909399;
  margin-top: 2px;
}
</style>
