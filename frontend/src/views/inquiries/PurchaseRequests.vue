<template>
  <div class="page-container">
    <div class="header">
      <h2 class="page-title">采购申请列表</h2>
    </div>
    
    <div class="content-card">
      <div class="toolbar">
        <div class="toolbar-left">
          <el-button type="primary" @click="showCreateTaskDialog">
            创建询价任务 <span v-if="selectedRequests.length > 0">({{ selectedRequests.length }})</span>
          </el-button>
          <el-button type="success" :icon="Download" @click="handleSyncErp" :loading="syncingErp">
            同步ERP数据
          </el-button>
        </div>
        <div class="toolbar-right">
          <el-input
            v-model="searchQuery"
            placeholder="搜索物料/单据/项目..."
            :prefix-icon="Search"
            clearable
            style="width: 250px;"
          />
        </div>
      </div>

      <div class="table-container">
        <el-table
          v-loading="syncingErp"
          :data="paginatedRequestList"
          @selection-change="handleSelectionChange"
          border
          style="width: 100%"
          row-key="_uid"
          size="small"
          height="100%"
        >
          <el-table-column type="selection" width="55" :reserve-selection="true" />
          <el-table-column prop="id" label="ID" width="60" />
          <el-table-column prop="bill_no" label="单据编号" width="120" />
          <el-table-column prop="bill_type" label="单据类型" width="100" />
          <el-table-column label="项目信息" min-width="150">
            <template #default="scope">
              <div v-if="scope.row.project_info">
                <div>{{ scope.row.project_info.number }}</div>
                <small style="color: #909399">{{ scope.row.project_info.name }}</small>
              </div>
              <span v-else>-</span>
            </template>
          </el-table-column>
          <el-table-column prop="material_name" label="物料名称" min-width="120" show-overflow-tooltip />
          <el-table-column prop="material_code" label="物料编码" width="120" />
          <el-table-column prop="qty" label="数量" width="100" />
          <el-table-column prop="delivery_date" label="需求日期" width="120">
            <template #default="scope">
              {{ formatDate(scope.row.delivery_date) }}
            </template>
          </el-table-column>
          <el-table-column prop="created_at" label="创建时间" width="160">
            <template #default="scope">
              {{ formatDateTime(scope.row.created_at) }}
            </template>
          </el-table-column>
          <el-table-column prop="status" label="状态" width="120">
            <template #default="scope">
              <el-tag :type="getStatusType(scope.row.status)">{{ getStatusText(scope.row.status) }}</el-tag>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <div class="pagination-container">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[50, 100, 200, 500]"
          background
          layout="total, sizes, prev, pager, next, jumper"
          :total="filteredRequestList.length"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </div>

    <!-- Dialog: Create Task -->
    <el-dialog v-model="dialogVisible" title="创建新询价任务" width="800px">
      <el-form :model="taskForm" label-width="100px" size="default">
        <el-form-item label="任务标题">
          <el-input v-model="taskForm.title" placeholder="例如：3月份电子元器件采购" />
        </el-form-item>
        
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="最大轮次">
              <el-input-number v-model="taskForm.strategy_config.max_rounds" :min="1" :max="10" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="砍价比例">
              <el-input-number v-model="taskForm.strategy_config.bargain_ratio" :step="0.01" :min="0" :max="1" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="指定供应商">
          <el-select v-model="taskForm.supplier_ids" multiple placeholder="请选择要派发的供应商（选填，不选则后续手动添加）" style="width: 100%">
            <el-option v-for="s in supplierList" :key="s.id" :label="s.name" :value="s.id">
              <span style="float: left">{{ s.name }}</span>
              <span style="float: right; color: var(--el-text-color-secondary); font-size: 13px">
                {{ s.level === 'core' ? '核心' : '一般' }}
              </span>
            </el-option>
          </el-select>
        </el-form-item>

        <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 20px;">
          <span style="font-size: 14px; color: #606266; font-weight: bold;">询价物料清单</span>
          <el-button type="primary" link @click="addCustomMaterial">+ 添加自定义物料</el-button>
        </div>
        <el-divider style="margin: 8px 0;"></el-divider>
        
        <el-table :data="selectedRequestsForTask" border size="small" style="margin-bottom: 10px;">
          <el-table-column label="物料编码" width="120">
            <template #default="scope">
              <el-input v-if="scope.row.is_custom" v-model="scope.row.material_code" size="small" placeholder="选填" />
              <span v-else>{{ scope.row.material_code }}</span>
            </template>
          </el-table-column>
          <el-table-column label="物料名称" min-width="150">
            <template #default="scope">
              <el-input v-if="scope.row.is_custom" v-model="scope.row.material_name" size="small" placeholder="必填" />
              <span v-else>{{ scope.row.material_name }}</span>
            </template>
          </el-table-column>
          <el-table-column label="需求数量" width="120">
            <template #default="scope">
              <el-input-number v-model="scope.row.qty" :min="1" size="small" style="width: 100%" controls-position="right" />
            </template>
          </el-table-column>
          <el-table-column label="期望交期" width="150">
            <template #default="scope">
              <el-date-picker v-model="scope.row.delivery_date" type="date" placeholder="选择交期" size="small" style="width: 100%" value-format="YYYY-MM-DD" />
            </template>
          </el-table-column>
          <el-table-column label="期望单价(¥)" width="130">
            <template #default="scope">
              <el-input-number v-model="scope.row.target_price" :min="0" :precision="2" :step="0.1" size="small" placeholder="不设限" style="width: 100%" controls-position="right" />
            </template>
          </el-table-column>
          <el-table-column label="操作" width="60" align="center">
            <template #default="scope">
              <el-button type="danger" link @click="removeMaterial(scope.$index)">移除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" @click="confirmCreateTask" :loading="creatingTask">
            创建任务
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed, watch } from 'vue'
import { createInquiryTask, syncErpRequisitions } from '../../api/inquiry'
import api from '../../api/index'
import { ElMessage } from 'element-plus'
import { Download, Search } from '@element-plus/icons-vue'
import { useRouter } from 'vue-router'

const router = useRouter()

const syncingErp = ref(false)
const requestList = ref([])
const selectedRequests = ref([])
const selectedRequestsForTask = ref([])

// Search and Pagination
const searchQuery = ref('')
const currentPage = ref(1)
const pageSize = ref(100)

// 搜索条件变化时重置页码
watch(searchQuery, () => {
  currentPage.value = 1
})

const filteredRequestList = computed(() => {
  let result = [...requestList.value]

  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    result = result.filter(item => {
      const matName = item.material_name ? String(item.material_name).toLowerCase() : ''
      const billNo = item.bill_no ? String(item.bill_no).toLowerCase() : ''
      const projNum = (item.project_info && item.project_info.number) ? String(item.project_info.number).toLowerCase() : ''
      const projName = (item.project_info && item.project_info.name) ? String(item.project_info.name).toLowerCase() : ''
      
      return matName.includes(query) || 
             billNo.includes(query) || 
             projNum.includes(query) || 
             projName.includes(query)
    })
  }
  
  return result
})

const paginatedRequestList = computed(() => {
  const list = filteredRequestList.value
  const page = currentPage.value
  const size = pageSize.value
  
  const start = (page - 1) * size
  const end = start + size
  
  return list.slice(start, end)
})

const handleSizeChange = (val) => {
  pageSize.value = val
  currentPage.value = 1
}

const handleCurrentChange = (val) => {
  currentPage.value = val
}

// Create Task Dialog
const dialogVisible = ref(false)
const creatingTask = ref(false)
const supplierList = ref([])
const taskForm = reactive({
  title: '',
  supplier_ids: [],
  strategy_config: {
    max_rounds: 3,
    bargain_ratio: 0.05,
    target_total_price: undefined
  }
})

const fetchSuppliers = async () => {
  try {
    const res = await api.get('/supplier/list')
    supplierList.value = res.data
  } catch (error) {
    console.error('Failed to fetch suppliers:', error)
  }
}

const addCustomMaterial = () => {
  selectedRequestsForTask.value.push({
    is_custom: true,
    erp_request_id: `MANUAL-${Math.random().toString(36).substr(2, 9)}`,
    material_code: '',
    material_name: '',
    qty: 1,
    target_price: undefined
  })
}

const removeMaterial = (index) => {
  selectedRequestsForTask.value.splice(index, 1)
}

const handleSyncErp = async () => {
  syncingErp.value = true
  try {
    const res = await syncErpRequisitions()
    if (res.data && res.data.length > 0) {
      requestList.value = res.data.map((item, index) => ({
        ...item,
        _uid: `sync_${index}_${Math.random().toString(36).substring(2, 9)}`
      }))
      currentPage.value = 1
      ElMessage.success(`同步成功，获取到 ${res.data.length} 条记录`)
    } else {
      ElMessage.info('未获取到新的ERP数据')
    }
  } catch (error) {
    console.error('Sync ERP failed:', error)
    ElMessage.error('同步ERP数据失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    syncingErp.value = false
  }
}

const handleSelectionChange = (val) => {
  selectedRequests.value = val
}

const showCreateTaskDialog = () => {
  const aggregatedMap = new Map()
  
  if (selectedRequests.value && selectedRequests.value.length > 0) {
    selectedRequests.value.forEach(item => {
      const dateStr = item.delivery_date ? String(item.delivery_date).substring(0, 10) : 'none'
      const key = `${item.material_code}_${dateStr}`
      
      if (aggregatedMap.has(key)) {
        const existing = aggregatedMap.get(key)
        existing.qty += Number(item.qty) || 0
        
        if (item.erp_request_id && !existing.erp_request_id.includes(item.erp_request_id)) {
          existing.erp_request_id = `${existing.erp_request_id},${item.erp_request_id}`
        }
        if (item.bill_no && !existing.bill_no.includes(item.bill_no)) {
          existing.bill_no = `${existing.bill_no},${item.bill_no}`
        }
        if (item.project_info && existing.project_info) {
          if (item.project_info.number) {
            const extNum = existing.project_info.number || '';
            if (!extNum.includes(item.project_info.number)) {
              existing.project_info.number = extNum ? `${extNum},${item.project_info.number}` : item.project_info.number;
            }
          }
          if (item.project_info.name) {
            const extName = existing.project_info.name || '';
            if (!extName.includes(item.project_info.name)) {
              existing.project_info.name = extName ? `${extName},${item.project_info.name}` : item.project_info.name;
            }
          }
        }
      } else {
        const newItem = JSON.parse(JSON.stringify(item))
        newItem.qty = Number(newItem.qty) || 0
        newItem.target_price = undefined
        aggregatedMap.set(key, newItem)
      }
    })
  }
  
  selectedRequestsForTask.value = Array.from(aggregatedMap.values())
  
  if (selectedRequestsForTask.value.length === 0) {
    addCustomMaterial()
  }
  
  const date = new Date().toISOString().slice(0, 10)
  taskForm.title = `${date} 批量询价 (${selectedRequestsForTask.value.length}项物料)`
  taskForm.supplier_ids = []
  
  fetchSuppliers()
  dialogVisible.value = true
}

const confirmCreateTask = async () => {
  for (let i = 0; i < selectedRequestsForTask.value.length; i++) {
    const item = selectedRequestsForTask.value[i]
    if (item.is_custom && !item.material_name) {
      ElMessage.warning(`第 ${i + 1} 行物料名称不能为空`)
      return
    }
  }

  if (selectedRequestsForTask.value.length === 0) {
    ElMessage.warning('请至少添加一项物料')
    return
  }

  creatingTask.value = true
  try {
    const payload = {
      title: taskForm.title,
      strategy_config: taskForm.strategy_config,
      raw_requests: selectedRequestsForTask.value.map(item => ({
        ...item,
        delivery_date: item.delivery_date ? (item.delivery_date.length === 10 ? item.delivery_date + 'T00:00:00' : item.delivery_date) : null
      })),
      supplier_ids: taskForm.supplier_ids
    }
    await createInquiryTask(payload)
    ElMessage.success('询价任务创建成功')
    dialogVisible.value = false
    
    const selectedIds = new Set(selectedRequests.value.map(r => r.erp_request_id))
    requestList.value = requestList.value.filter(r => !selectedIds.has(r.erp_request_id))
    
    // Switch to tasks page
    router.push('/inquiries/tasks')
  } catch (error) {
    console.error(error)
    ElMessage.error('创建任务失败')
  } finally {
    creatingTask.value = false
  }
}

const formatDateTime = (dateStr) => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString()
}

const formatDate = (dateStr) => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleDateString()
}

const getStatusText = (status) => {
  const map = {
    'pending_pool': '待询价',
    'in_process': '询价中',
    'completed': '已完成'
  }
  return map[status] || status
}

const getStatusType = (status) => {
  const map = {
    'pending_pool': 'info',
    'in_process': 'primary',
    'completed': 'success'
  }
  return map[status] || ''
}

onMounted(() => {
  handleSyncErp()
})
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

.toolbar-left {
  display: flex;
  gap: 10px;
}

.toolbar-right {
  display: flex;
  align-items: center;
}

.pagination-container {
  margin-top: 15px;
  display: flex;
  justify-content: flex-end;
  flex-shrink: 0;
}

:deep(.el-table .cell) {
  padding: 0 5px;
  line-height: 1.2;
}

:deep(.el-table td.el-table__cell, .el-table th.el-table__cell.is-leaf) {
  padding: 4px 0;
}
</style>