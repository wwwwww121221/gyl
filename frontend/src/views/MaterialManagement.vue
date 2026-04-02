<template>
  <div class="page-container">
    <div class="header">
      <h2 class="page-title">物料管理</h2>
      <div class="search-bar">
        <el-input
          v-model="searchQuery"
          placeholder="请输入物料名称"
          clearable
          class="search-input"
          @keyup.enter="handleSearch"
        />
        <el-button type="primary" :loading="loading" @click="handleSearch">查询</el-button>
      </div>
    </div>

    <div v-if="showEmpty" class="content-card empty-wrap">
      <el-empty description="输入物料名称查询历史成交记录" />
    </div>

    <div v-else class="content-body">
      <el-row :gutter="20">
        <el-col :span="12">
          <el-card class="panel-card">
            <template #header>
              <span>历史成交明细</span>
            </template>
            <el-table :data="historyItems" v-loading="loading" style="width: 100%">
              <el-table-column label="成交日期" min-width="120">
                <template #default="{ row }">
                  {{ formatDate(row.date) }}
                </template>
              </el-table-column>
              <el-table-column prop="supplier_name" label="供应商" min-width="150" />
              <el-table-column label="单价" min-width="120">
                <template #default="{ row }">
                  <span class="price-text">¥ {{ formatAmount(row.price) }}</span>
                </template>
              </el-table-column>
              <el-table-column label="数量" min-width="100">
                <template #default="{ row }">
                  {{ formatQty(row.qty) }}
                </template>
              </el-table-column>
              <el-table-column label="操作" width="120" fixed="right">
                <template #default="{ row }">
                  <el-button link type="primary" @click="handleViewContract(row)">查看合同</el-button>
                </template>
              </el-table-column>
            </el-table>
          </el-card>
        </el-col>

        <el-col :span="12">
          <el-card class="panel-card">
            <template #header>
              <span>价格趋势分析</span>
            </template>
            <div ref="chartRef" class="chart-container" />
          </el-card>
        </el-col>
      </el-row>
    </div>
  </div>
</template>

<script setup>
import * as echarts from 'echarts'
import { computed, nextTick, onMounted, onUnmounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getContractPdfBlob } from '../api/contract'
import { getMaterialHistory } from '../api/material'

const searchQuery = ref('')
const loading = ref(false)
const searched = ref(false)
const historyItems = ref([])
const chartRef = ref(null)
let chartInstance = null

const showEmpty = computed(() => !searched.value || historyItems.value.length === 0)

const formatDate = (value) => {
  if (!value) return '-'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return value
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

const formatAmount = (value) => {
  const num = Number(value || 0)
  return num.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

const formatQty = (value) => {
  const num = Number(value || 0)
  return num.toLocaleString('zh-CN', { maximumFractionDigits: 2 })
}

const openBlobInNewTab = (blob) => {
  const url = URL.createObjectURL(blob)
  const tab = window.open(url, '_blank')
  if (!tab) {
    ElMessage.warning('浏览器阻止了新窗口，请允许弹窗后重试')
  }
  setTimeout(() => URL.revokeObjectURL(url), 30000)
}

const handleViewContract = async (row) => {
  if (!row?.contract_id) {
    ElMessage.warning('未找到关联合同')
    return
  }
  try {
    const res = await getContractPdfBlob(row.contract_id)
    openBlobInNewTab(res.data)
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '合同预览失败')
  }
}

const ensureChartInstance = () => {
  if (!chartRef.value) return
  if (!chartInstance) {
    chartInstance = echarts.init(chartRef.value)
  }
}

const renderChart = (data = []) => {
  ensureChartInstance()
  if (!chartInstance) return
  const sorted = [...data].sort((a, b) => new Date(a.date) - new Date(b.date))
  const option = {
    tooltip: {
      trigger: 'axis',
      formatter: (params) => {
        const first = params?.[0]
        if (!first) return ''
        return `${first.axisValue}<br/>单价：¥ ${formatAmount(first.data)}`
      }
    },
    grid: { left: 48, right: 24, top: 30, bottom: 40 },
    xAxis: {
      type: 'category',
      data: sorted.map(item => formatDate(item.date))
    },
    yAxis: {
      type: 'value',
      name: '单价 (元)',
      scale: true,
      axisLabel: {
        formatter: value => `¥ ${value}`
      }
    },
    series: [
      {
        name: '成交单价',
        type: 'line',
        smooth: true,
        data: sorted.map(item => Number(item.price || 0)),
        lineStyle: { width: 3, color: '#f56c6c' },
        itemStyle: { color: '#f56c6c' },
        markPoint: {
          data: [{ type: 'max', name: '最高价' }, { type: 'min', name: '最低价' }]
        }
      }
    ]
  }
  chartInstance.setOption(option, true)
  chartInstance.resize()
}

const disposeChart = () => {
  if (chartInstance) {
    chartInstance.dispose()
    chartInstance = null
  }
}

const handleResize = () => {
  if (chartInstance) {
    chartInstance.resize()
  }
}

const handleSearch = async () => {
  const keyword = searchQuery.value.trim()
  searched.value = true
  if (!keyword) {
    historyItems.value = []
    renderChart([])
    return
  }
  loading.value = true
  try {
    const res = await getMaterialHistory({ material_name: keyword })
    historyItems.value = res.data?.items || []
    await nextTick()
    renderChart(historyItems.value)
  } catch (error) {
    historyItems.value = []
    renderChart([])
    ElMessage.error(error.response?.data?.detail || '查询失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  ensureChartInstance()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  disposeChart()
})
</script>

<style scoped>
.page-container {
  padding: 0;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-title {
  margin: 0;
  font-size: 24px;
  color: #303133;
}

.search-bar {
  display: flex;
  gap: 12px;
  align-items: center;
}

.search-input {
  width: 320px;
}

.content-card {
  background: white;
  padding: 20px;
  border-radius: 8px;
  min-height: 460px;
}

.empty-wrap {
  display: flex;
  justify-content: center;
  align-items: center;
}

.content-body {
  min-height: 460px;
}

.panel-card {
  background: white;
  min-height: 460px;
}

.chart-container {
  height: 400px;
}

.price-text {
  color: #f56c6c;
  font-weight: 700;
}
</style>
