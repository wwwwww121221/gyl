<template>
  <div class="page-container">
    <div class="content-card">
      <div class="toolbar">
        <div class="toolbar-left">
          <el-input
            v-model="searchQuery"
            placeholder="搜索询价单标题..."
            :prefix-icon="Search"
            clearable
            style="width: 250px;"
          />
          <el-select v-model="statusFilter" placeholder="状态筛选" clearable style="width: 150px">
            <el-option label="未确认" value="unconfirmed" />
            <el-option label="已确认" value="confirmed" />
            <el-option label="已成交" value="deal" />
            <el-option label="已取消" value="cancelled" />
          </el-select>
        </div>
        <div class="toolbar-right">
          <el-button type="primary" @click="fetchInquiries" :icon="Refresh" circle />
        </div>
      </div>

      <div class="table-container">
        <el-table 
          :data="filteredInquiries" 
          style="width: 100%" 
          height="100%"
          v-loading="loading" 
          border 
          stripe
          highlight-current-row
        >
          <el-table-column type="index" label="序号" width="80" align="center" />
          <el-table-column prop="task_title" label="询价单标题" min-width="200" />
          <el-table-column prop="created_at" label="发布时间" :formatter="formatDate" width="150" align="center" />
          <el-table-column prop="current_round" label="当前轮次" width="100" align="center" />
          <el-table-column prop="status" label="状态" width="120" align="center">
            <template #default="{ row }">
              <el-tag :type="getNewStatusType(row)" effect="light">
                {{ getNewStatusText(row) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="240" align="center" fixed="right">
            <template #default="{ row }">
              <el-button size="small" type="primary" @click="handleDetail(row)">
                查看详情 / 报价
              </el-button>
              <el-button
                v-if="canViewContract(row)"
                size="small"
                type="success"
                plain
                @click="handleViewContract(row)"
              >
                查看合同
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>

    <!-- Detail & Quote Dialog -->
    <el-dialog v-model="dialogVisible" title="询价单详情与报价" width="850px" top="5vh" class="custom-dialog">
      <div v-if="currentInquiry" class="dialog-content">
        <el-card shadow="never" class="info-card">
          <template #header>
            <div class="card-header">
              <span class="task-title">{{ currentInquiry.task_title }}</span>
              <el-tag :type="getNewStatusType(currentInquiry)" effect="dark">
                {{ getNewStatusText(currentInquiry) }}
              </el-tag>
            </div>
          </template>
          <el-descriptions :column="2" border size="small">
            <el-descriptions-item label="当前轮次">
              <el-tag type="info" size="small">第 {{ currentInquiry.round }} 轮</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="操作提示">
              <span v-if="canQuote" style="color: #e6a23c; font-weight: bold;">请在下方填写报价并提交</span>
              <span v-else-if="isDeadlinePassed" style="color: #f56c6c; font-weight: bold;">当前询价已截止，无法报价</span>
              <span v-else style="color: #909399;">当前状态不可报价</span>
            </el-descriptions-item>
          </el-descriptions>
          <div class="deadline-countdown">
            <span class="countdown-label">报价截止倒计时：</span>
            <span :class="['countdown-value', { 'countdown-urgent': isDeadlineUrgent }]">
              {{ deadlineCountdownText }}
            </span>
          </div>
        </el-card>

        <div v-if="currentInquiry.latest_ai_feedback" class="feedback-box">
          <div class="feedback-title"><el-icon><ChatLineRound /></el-icon> 采购方/系统反馈</div>
          <div class="feedback-content">{{ currentInquiry.latest_ai_feedback }}</div>
        </div>

        <div class="table-section-title">
          <span class="title-text">物料明细及报价</span>
        </div>
        
        <el-table :data="currentInquiry.items" style="width: 100%" border stripe size="small">
          <el-table-column prop="material_name" label="物料名称" />
          <el-table-column prop="material_code" label="物料编码" />
          <el-table-column prop="qty" label="采购数量" width="100" />
          <el-table-column prop="delivery_date" label="期望交期" :formatter="formatDate" />
          <el-table-column label="您的可供数量" width="130">
            <template #default="{ row }">
              <el-input-number 
                v-model="quoteForm[row.request_id].qty" 
                :min="1" 
                size="small" 
                :disabled="!canQuote"
              />
            </template>
          </el-table-column>
          <el-table-column label="您的承诺交期" width="150">
            <template #default="{ row }">
              <el-date-picker 
                v-model="quoteForm[row.request_id].delivery_date" 
                type="date" 
                placeholder="选择交期" 
                size="small" 
                style="width: 100%" 
                value-format="YYYY-MM-DD"
                :disabled="!canQuote"
              />
            </template>
          </el-table-column>
          <el-table-column label="您的报价(元)" width="150">
            <template #default="{ row }">
              <el-input-number 
                v-model="quoteForm[row.request_id].price" 
                :min="0" 
                :precision="2" 
                :step="0.1" 
                size="small" 
                :disabled="!canQuote"
              />
            </template>
          </el-table-column>
          <el-table-column label="备注">
            <template #default="{ row }">
              <el-input 
                v-model="quoteForm[row.request_id].remark" 
                size="small" 
                placeholder="其他备注" 
                :disabled="!canQuote"
              />
            </template>
          </el-table-column>
        </el-table>
      </div>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="dialogVisible = false">关闭</el-button>
          <el-button type="primary" @click="submitQuote" :loading="submitLoading" :disabled="!canQuote">
            {{ quoteButtonText }}
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'
import api from '../../api/index'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh, Search, ChatLineRound } from '@element-plus/icons-vue'

const inquiries = ref([])
const loading = ref(false)
const searchQuery = ref('')
const statusFilter = ref('')

const getDisplayStatus = (row) => {
  if (row.status === 'deal') {
    return 'deal'
  }
  if (row.task_status === 'closed' || row.task_status === 'cancelled') {
    return 'cancelled'
  }
  if (row.status === 'sent') {
    return 'unconfirmed'
  }
  return 'confirmed'
}

const filteredInquiries = computed(() => {
  let result = inquiries.value

  if (searchQuery.value) {
    const q = searchQuery.value.toLowerCase()
    result = result.filter(task => task.task_title.toLowerCase().includes(q))
  }

  if (statusFilter.value) {
    result = result.filter(task => getDisplayStatus(task) === statusFilter.value)
  }

  return result
})

const dialogVisible = ref(false)
const currentInquiry = ref(null)
const quoteForm = ref({})
const submitLoading = ref(false)
const currentLinkId = ref(null)
const nowTs = ref(Date.now())
let timerId = null

const fetchInquiries = async () => {
  loading.value = true
  try {
    const res = await api.get('/supplier/my-inquiries')
    inquiries.value = res.data
  } catch (error) {
    console.error(error)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchInquiries()
  timerId = window.setInterval(() => {
    nowTs.value = Date.now()
  }, 1000)
})

onUnmounted(() => {
  if (timerId) {
    window.clearInterval(timerId)
  }
})

const getNewStatusText = (row) => {
  const status = getDisplayStatus(row)
  const map = {
    unconfirmed: '未确认',
    confirmed: '已确认',
    cancelled: '已取消',
    deal: '已成交'
  }
  return map[status]
}

const getNewStatusType = (row) => {
  const status = getDisplayStatus(row)
  const map = {
    unconfirmed: 'info',
    confirmed: 'primary',
    cancelled: 'danger',
    deal: 'success'
  }
  return map[status]
}

const getStatusText = (status) => {
  const map = {
    sent: '未确认',
    quoted: '已确认',
    negotiation: '已确认',
    deal: '已确认',
    reject: '已确认'
  }
  return map[status] || status
}

const getStatusType = (status) => {
  const map = {
    sent: 'info',
    quoted: 'primary',
    negotiation: 'warning',
    deal: 'success',
    reject: 'danger'
  }
  return map[status] || 'info'
}

const getContractPath = (row) => row.contract_pdf || row.contract_pdf_path || ''

const canViewContract = (row) => {
  return getDisplayStatus(row) === 'deal' && !!getContractPath(row)
}

const handleViewContract = (row) => {
  const contractPath = getContractPath(row)
  if (!contractPath) {
    ElMessage.warning('合同文件尚未生成，请稍后重试')
    return
  }
  const contractUrl = contractPath.startsWith('http')
    ? contractPath
    : `http://localhost:8000${contractPath}`
  window.open(contractUrl, '_blank')
}

const formatDate = (row, column, cellValue) => {
  if (!cellValue) return '-'
  return new Date(cellValue).toLocaleDateString()
}

const handleDetail = async (row) => {
  currentLinkId.value = row.inquiry_supplier_id
  try {
    const res = await api.get(`/supplier/inquiry/${currentLinkId.value}`)
    currentInquiry.value = res.data
    
    // Initialize quote form
    const form = {}
    res.data.items.forEach(item => {
      form[item.request_id] = {
        qty: item.qty, // default to requested qty
        price: 0,
        delivery_date: item.delivery_date ? String(item.delivery_date).substring(0, 10) : '', // default to requested date if exists
        remark: ''
      }
    })
    quoteForm.value = form
    
    dialogVisible.value = true
  } catch (error) {
    console.error(error)
  }
}

const getDeadlineMeta = (deadline) => {
  if (!deadline) return { passed: false, text: '未设置截止时间', urgent: false }
  const deadlineMs = new Date(deadline).getTime()
  if (Number.isNaN(deadlineMs)) return { passed: false, text: '截止时间无效', urgent: false }
  const diffMs = deadlineMs - nowTs.value
  if (diffMs <= 0) return { passed: true, text: '已截止报价', urgent: true }
  const totalSeconds = Math.floor(diffMs / 1000)
  const days = Math.floor(totalSeconds / 86400)
  const hours = Math.floor((totalSeconds % 86400) / 3600)
  const minutes = Math.floor((totalSeconds % 3600) / 60)
  const seconds = totalSeconds % 60
  const text = days > 0
    ? `${days}天 ${hours}时 ${minutes}分 ${seconds}秒`
    : `${hours}时 ${minutes}分 ${seconds}秒`
  return { passed: false, text, urgent: diffMs < 2 * 3600 * 1000 }
}

const deadlineMeta = computed(() => getDeadlineMeta(currentInquiry.value?.deadline))
const deadlineCountdownText = computed(() => deadlineMeta.value.text)
const isDeadlineUrgent = computed(() => deadlineMeta.value.urgent)
const isDeadlinePassed = computed(() => deadlineMeta.value.passed)

const canQuote = computed(() => {
  if (!currentInquiry.value) return false
  if (currentInquiry.value.task_status === 'closed' || currentInquiry.value.task_status === 'cancelled') return false
  if (isDeadlinePassed.value) return false
  return ['sent', 'negotiation'].includes(currentInquiry.value.status) && new Date() < new Date(currentInquiry.value.deadline)
})

const quoteButtonText = computed(() => {
  if (isDeadlinePassed.value) return '已截止报价'
  if (!canQuote.value) return '当前不可报价'
  return '提交报价'
})

const submitQuote = async () => {
  if (!currentInquiry.value) return
  
  const buildPayload = (forceSubmit = false) => {
    const items = Object.keys(quoteForm.value).map(reqId => {
      let d = quoteForm.value[reqId].delivery_date;
      if (d && d.length === 10) {
        d = d + 'T00:00:00';
      }
      return {
        request_id: parseInt(reqId),
        qty: quoteForm.value[reqId].qty,
        price: quoteForm.value[reqId].price,
        delivery_date: d || null,
        remark: quoteForm.value[reqId].remark
      }
    })
    return { items, force_submit: forceSubmit }
  }
  
  const payload = buildPayload(false)
  
  // validation
  const invalid = payload.items.some(item => item.price <= 0)
  if (invalid) {
    ElMessage.warning('请输入有效的报价金额')
    return
  }
  
  submitLoading.value = true
  try {
    const res = await api.post(`/supplier/inquiry/${currentLinkId.value}/quote`, payload)
    
    // 拦截后端预警：如果是异常报价，弹出确认框
    if (res.data?.next_action === 'confirm_anomaly') {
      try {
        await ElMessageBox.confirm(
          res.data.message,
          '异常报价确认',
          {
            confirmButtonText: '确认无误，强行提交',
            cancelButtonText: '返回修改',
            type: 'warning'
          }
        )
        // 供应商点击“强行提交”，带上 force_submit: true 重新发起请求
        submitLoading.value = true
        const forceRes = await api.post(`/supplier/inquiry/${currentLinkId.value}/quote`, buildPayload(true))
        ElMessage.success(forceRes.data.message || '强行提交成功')
        dialogVisible.value = false
        fetchInquiries()
      } catch {
        // 用户点击取消，停留在当前弹窗修改价格
      }
    } else {
      // 价格正常，直接走成功逻辑
      ElMessage.success(res.data.message || '报价提交成功')
      dialogVisible.value = false
      fetchInquiries()
    }
  } catch (error) {
    console.error(error)
    ElMessage.error(error.response?.data?.detail || '提交失败')
  } finally {
    submitLoading.value = false
  }
}
</script>

<style scoped>
.page-container {
  padding: 20px;
  height: calc(100vh - 100px);
  display: flex;
  flex-direction: column;
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

.content-card {
  background: white;
  padding: 20px;
  border-radius: 8px;
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 2px 12px 0 rgba(0,0,0,0.05);
}

.table-container {
  flex: 1;
  overflow: hidden;
}

.toolbar {
  margin-bottom: 15px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-shrink: 0;
}

.toolbar-left, .toolbar-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

/* Dialog Styles */
.dialog-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.info-card {
  border-radius: 8px;
  background-color: #fcfcfc;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.task-title {
  font-size: 16px;
  font-weight: bold;
  color: #303133;
}

.feedback-box {
  background-color: #fdf6ec;
  border: 1px solid #faecd8;
  border-radius: 4px;
  padding: 15px;
}

.feedback-title {
  color: #e6a23c;
  font-weight: bold;
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  gap: 5px;
}

.feedback-content {
  color: #606266;
  line-height: 1.5;
  font-size: 14px;
}

.table-section-title {
  border-left: 4px solid #409eff;
  padding-left: 10px;
  margin-bottom: 10px;
}

.title-text {
  font-size: 15px;
  font-weight: bold;
  color: #303133;
}

.deadline-countdown {
  margin-top: 12px;
  font-size: 14px;
}

.countdown-label {
  color: #606266;
}

.countdown-value {
  color: #303133;
  font-weight: 500;
}

.countdown-urgent {
  color: #f56c6c;
  font-weight: 700;
}
</style>
