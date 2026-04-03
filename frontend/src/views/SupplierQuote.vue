<template>
  <div class="quote-container">
    <div v-if="loading" class="loading-state">
      <el-skeleton :rows="5" animated />
    </div>

    <div v-else-if="error" class="error-state">
      <el-result icon="error" title="链接无效或已过期" :sub-title="error">
        <template #extra>
          <el-button type="primary" @click="fetchQuoteInfo">重试</el-button>
        </template>
      </el-result>
    </div>

    <div v-else-if="quoteInfo" class="quote-content">
      <el-card class="box-card" shadow="hover">
        <template #header>
          <div class="card-header">
            <h2>{{ quoteInfo.task_title }}</h2>
            <el-tag :type="getRoundTagType(quoteInfo.round)" effect="dark" size="large">第 {{ quoteInfo.round }} 轮报价</el-tag>
          </div>
          <div class="supplier-info">
            尊敬的 <span class="highlight">{{ quoteInfo.supplier_name }}</span>，您好！请就以下物料提供您的最新报价。
          </div>
        </template>

        <div class="deadline-countdown">
          <span class="countdown-label">报价截止倒计时：</span>
          <span :class="['countdown-value', { 'countdown-urgent': isDeadlineUrgent }]">
            {{ deadlineCountdownText }}
          </span>
        </div>

        <div v-if="aiFeedback" class="ai-feedback-alert">
          <el-alert
            title="来自采购方的反馈消息："
            :description="aiFeedback"
            type="warning"
            show-icon
            :closable="false"
          />
        </div>

        <el-form :model="form" ref="formRef" label-position="top">
          <el-table :data="form.items" border stripe style="width: 100%; margin-bottom: 20px;">
            <el-table-column prop="material_code" label="物料编码" width="120" />
            <el-table-column prop="material_name" label="物料名称" min-width="150" />
            <el-table-column prop="qty" label="需求数量" width="100" align="right" />
            <el-table-column label="期望交期" width="120" align="center">
              <template #default="scope">
                <span v-if="scope.row.target_delivery_date">{{ scope.row.target_delivery_date }}</span>
                <span v-else style="color: #909399;">不限</span>
              </template>
            </el-table-column>
            <el-table-column label="交货日期" width="180">
              <template #default="scope">
                <el-form-item :prop="'items.' + scope.$index + '.delivery_date'" :rules="{ required: true, message: '请选择交期', trigger: 'change' }" style="margin-bottom: 0;">
                  <el-date-picker
                    v-model="scope.row.delivery_date"
                    type="date"
                    placeholder="选择交期"
                    style="width: 100%"
                    value-format="YYYY-MM-DD"
                    :disabled="!canQuote"
                  />
                </el-form-item>
              </template>
            </el-table-column>
            <el-table-column label="含税单价 (¥)" width="150">
              <template #default="scope">
                <el-form-item :prop="'items.' + scope.$index + '.price'" :rules="{ required: true, message: '请输入单价', trigger: 'blur' }" style="margin-bottom: 0;">
                  <el-input-number v-model="scope.row.price" :min="0" :precision="2" :step="0.1" style="width: 100%" controls-position="right" :disabled="!canQuote" />
                </el-form-item>
              </template>
            </el-table-column>
            <el-table-column label="备注说明" min-width="150">
              <template #default="scope">
                <el-form-item :prop="'items.' + scope.$index + '.remark'" style="margin-bottom: 0;">
                  <el-input v-model="scope.row.remark" placeholder="如：品牌、包装等" :disabled="!canQuote" />
                </el-form-item>
              </template>
            </el-table-column>
          </el-table>

          <div class="submit-section">
            <div class="total-price">
              预计总金额：<span class="price-val">¥ {{ calculateTotal().toFixed(2) }}</span>
            </div>
            <el-button type="primary" size="large" @click="submitQuote" :loading="submitting" :disabled="!canQuote">
              {{ submitButtonText }}
            </el-button>
          </div>
        </el-form>
      </el-card>
    </div>

    <!-- Success Result State -->
    <div v-if="successResult" class="success-state">
      <el-result icon="success" title="报价提交成功" :sub-title="successResult.message">
        <template #extra>
          <p v-if="successResult.ai_feedback" class="feedback-text">{{ successResult.ai_feedback }}</p>
          <el-button v-if="successResult.next_action === 're-quote'" type="primary" @click="resetForNextRound">
            立即进行下一轮报价
          </el-button>
          <el-button v-else type="info" disabled>等待采购方确认...</el-button>
        </template>
      </el-result>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import axios from 'axios'

const route = useRoute()
const token = route.params.token

const loading = ref(true)
const error = ref('')
const quoteInfo = ref(null)
const formRef = ref(null)
const submitting = ref(false)
const aiFeedback = ref('')
const successResult = ref(null)
const nowTs = ref(Date.now())
let timerId = null

const form = reactive({
  items: []
})

// 创建一个不需要携带 Authorization 头的 axios 实例
const api = axios.create({
  baseURL: 'http://localhost:8000/api', // 改回正确的 baseURL
  timeout: 30000
})

const fetchQuoteInfo = async () => {
  loading.value = true
  error.value = ''
  successResult.value = null
  try {
    const res = await api.get(`/supplier/quote/${token}`)
    
    if (res.data.message && res.data.message.includes('closed')) {
      error.value = res.data.message
      quoteInfo.value = null
      return
    }

    quoteInfo.value = res.data
    
    if (res.data.status === 'quoted') {
      successResult.value = {
        message: '您的报价已收到，当前正在等待其他供应商完成本轮报价。',
        ai_feedback: res.data.latest_ai_feedback || '请稍后刷新页面查看最新谈判进展。',
        next_action: 'wait'
      }
      quoteInfo.value = null // hide form
      return
    }
    
    if (res.data.status === 'deal') {
      successResult.value = {
        message: '恭喜，本次询价已达成合作！',
        ai_feedback: res.data.latest_ai_feedback || '感谢您的报价，请等待后续采购订单。',
        next_action: 'deal'
      }
      quoteInfo.value = null
      return
    }
    
    if (res.data.status === 'reject') {
      successResult.value = {
        message: '本次询价已结束。',
        ai_feedback: res.data.latest_ai_feedback || '很遗憾，您的报价未能被采纳，感谢您的参与。',
        next_action: 'reject'
      }
      quoteInfo.value = null
      return
    }

    // 如果有 ai_feedback，并且状态不是 quoted，说明是 negotiation 状态
    if (res.data.latest_ai_feedback) {
      aiFeedback.value = res.data.latest_ai_feedback
    }

    // 初始化表单数据，继承后端传递的上一轮数据
    form.items = res.data.items.map(item => ({
      request_id: item.request_id,
      material_code: item.material_code,
      material_name: item.material_name,
      qty: item.qty,
      target_delivery_date: item.target_delivery_date ? String(item.target_delivery_date).substring(0, 10) : '',
      price: item.price !== null ? item.price : undefined,
      delivery_date: item.delivery_date ? String(item.delivery_date).substring(0, 10) : '',
      remark: item.remark || ''
    }))
  } catch (err) {
    console.error(err)
    error.value = err.response?.data?.detail || '获取报价信息失败，请检查网络或联系采购员'
  } finally {
    loading.value = false
  }
}

const calculateTotal = () => {
  return form.items.reduce((total, item) => {
    const p = item.price || 0
    const q = item.qty || 0
    return total + (p * q)
  }, 0)
}

const getRoundTagType = (round) => {
  if (round === 1) return 'info'
  if (round === 2) return 'warning'
  return 'danger'
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

const deadlineMeta = computed(() => getDeadlineMeta(quoteInfo.value?.deadline))
const deadlineCountdownText = computed(() => deadlineMeta.value.text)
const isDeadlineUrgent = computed(() => deadlineMeta.value.urgent)
const isDeadlinePassed = computed(() => deadlineMeta.value.passed)

const canQuote = computed(() => {
  if (!quoteInfo.value) return false
  if (!['sent', 'negotiation'].includes(quoteInfo.value.status)) return false
  if (isDeadlinePassed.value) return false
  return new Date() < new Date(quoteInfo.value.deadline)
})

const submitButtonText = computed(() => {
  if (isDeadlinePassed.value) return '已截止报价'
  if (!canQuote.value) return '当前不可报价'
  return '提交本轮报价'
})

const buildQuotePayload = (forceSubmit = false) => ({
  items: form.items.map(i => ({
    request_id: i.request_id,
    qty: i.qty,
    price: Number(i.price),
    delivery_date: i.delivery_date,
    remark: i.remark || ''
  })),
  force_submit: forceSubmit
})

const handleQuoteSubmitResponse = (data) => {
  successResult.value = data
  quoteInfo.value = null
}

const submitQuote = async () => {
  if (!formRef.value) return
  if (!canQuote.value) return
  
  await formRef.value.validate(async (valid) => {
    if (valid) {
      ElMessageBox.confirm(
        '确认提交当前报价吗？提交后系统将自动进行评估。',
        '提交确认',
        {
          confirmButtonText: '确认提交',
          cancelButtonText: '再看看',
          type: 'warning',
        }
      ).then(async () => {
        submitting.value = true
        try {
          const firstRes = await api.post(`/supplier/quote/${token}`, buildQuotePayload(false))
          if (firstRes.data?.next_action === 'confirm_anomaly') {
            try {
              await ElMessageBox.confirm(
                firstRes.data.message || '检测到异常报价，是否确认无误并继续提交？',
                '异常报价确认',
                {
                  confirmButtonText: '确认无误，继续提交',
                  cancelButtonText: '返回修改',
                  type: 'warning'
                }
              )
              const forceRes = await api.post(`/supplier/quote/${token}`, buildQuotePayload(true))
              handleQuoteSubmitResponse(forceRes.data)
            } catch {
            }
          } else {
            handleQuoteSubmitResponse(firstRes.data)
          }
          
        } catch (err) {
          console.error(err)
          ElMessage.error(err.response?.data?.detail || '提交报价失败')
        } finally {
          submitting.value = false
        }
      }).catch(() => {})
    } else {
      ElMessage.warning('请填写完整的报价信息')
    }
  })
}

const resetForNextRound = () => {
  aiFeedback.value = successResult.value.ai_feedback
  fetchQuoteInfo() // 重新拉取最新一轮的信息
}

onMounted(() => {
  timerId = window.setInterval(() => {
    nowTs.value = Date.now()
  }, 1000)
  if (token) {
    fetchQuoteInfo()
  } else {
    error.value = '未提供有效的链接Token'
    loading.value = false
  }
})

onUnmounted(() => {
  if (timerId) {
    window.clearInterval(timerId)
  }
})
</script>

<style scoped>
.quote-container {
  min-height: 100vh;
  background-color: #f0f2f5;
  padding: 40px 20px;
  display: flex;
  justify-content: center;
  align-items: flex-start;
}

.loading-state, .error-state, .success-state {
  width: 100%;
  max-width: 600px;
  background: white;
  padding: 40px;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.05);
}

.quote-content {
  width: 100%;
  max-width: 1000px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.card-header h2 {
  margin: 0;
  color: #303133;
}

.supplier-info {
  font-size: 14px;
  color: #606266;
}

.highlight {
  color: #409EFF;
  font-weight: bold;
  font-size: 16px;
}

.deadline-countdown {
  margin-bottom: 14px;
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

.ai-feedback-alert {
  margin-bottom: 20px;
}

.submit-section {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid #ebeef5;
}

.total-price {
  font-size: 16px;
  color: #606266;
  margin-right: 30px;
}

.price-val {
  font-size: 24px;
  color: #f56c6c;
  font-weight: bold;
}

.feedback-text {
  margin-top: 20px;
  padding: 15px;
  background-color: #fdf6ec;
  border-radius: 4px;
  color: #e6a23c;
  text-align: left;
  line-height: 1.6;
}
</style>
