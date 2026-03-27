<template>
  <div class="page-container">
    <div class="content-card">
      <div class="toolbar">
        <div class="toolbar-left">
          <el-input
            v-model="searchQuery"
            placeholder="搜索任务标题..."
            :prefix-icon="Search"
            clearable
            style="width: 250px;"
          />
        </div>
        <div class="toolbar-right">
          <el-button type="primary" @click="fetchTasks" :icon="Refresh" circle />
        </div>
      </div>

      <div class="table-container">
        <el-table 
          v-loading="loadingTasks" 
          :data="filteredTaskList" 
          border 
          stripe 
          highlight-current-row
          style="width: 100%"
          height="100%"
        >
          <el-table-column type="index" label="序号" width="80" align="center" />
          <el-table-column prop="title" label="任务标题" />
          <el-table-column prop="status" label="状态" width="120">
            <template #default="scope">
              <el-tag :type="getTaskStatusType(scope.row.status)">{{ scope.row.status }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="created_at" label="创建时间" width="180">
            <template #default="scope">
              {{ formatDateTime(scope.row.created_at) }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="250" align="center">
            <template #default="scope">
              <el-button size="small" type="primary" @click="viewTaskDetails(scope.row)">
                详情 / 管理
              </el-button>
              <el-button 
                v-if="scope.row.status === 'closed'" 
                size="small" 
                type="danger" 
                plain
                @click="handleDeleteTask(scope.row)"
              >
                删除
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>

    <!-- Dialog: Task Details -->
    <el-dialog v-model="detailsVisible" title="询价任务详情" width="85%" top="5vh" class="custom-dialog">
      <div v-if="currentTaskDetails" v-loading="loadingDetails" class="task-details-container">
        
        <!-- Header Info Card -->
        <el-card shadow="never" class="info-card">
          <template #header>
            <div class="card-header">
              <div class="header-title">
                <span class="task-title">{{ currentTaskDetails.title }}</span>
                <el-tag :type="getTaskStatusType(currentTaskDetails.status)" effect="dark" size="default" style="margin-left: 15px;">
                  {{ currentTaskDetails.status === 'active' ? '进行中' : (currentTaskDetails.status === 'closed' ? '已结束' : currentTaskDetails.status) }}
                </el-tag>
              </div>
              <div class="header-actions">
                <el-button v-if="currentTaskDetails.status === 'active'" type="danger" plain @click="handleCloseTask()">
                  终止任务 (流标)
                </el-button>
              </div>
            </div>
          </template>
          <el-descriptions :column="3" border size="small">
            <el-descriptions-item label="期望单价(¥)">
              <span style="color: #f56c6c; font-weight: bold; font-size: 16px;">详见下方明细</span>
            </el-descriptions-item>
            <el-descriptions-item label="最大自动谈判轮次">
              <el-tag type="info" size="small">{{ currentTaskDetails.strategy_config?.max_rounds }} 轮</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="AI 期望降价幅度">
              <el-tag type="warning" size="small">{{ (currentTaskDetails.strategy_config?.bargain_ratio * 100).toFixed(0) }}%</el-tag>
            </el-descriptions-item>
          </el-descriptions>
        </el-card>

        <!-- Main Content Tabs -->
        <el-tabs v-model="detailsActiveTab" class="details-tabs" type="border-card">
          
          <!-- Tab 1: Suppliers -->
          <el-tab-pane label="供应商与报价动态" name="suppliers">
            <div class="tab-toolbar">
              <el-form :inline="true" :model="supplierForm" class="supplier-form" size="default">
                <el-form-item label="新增供应商">
                  <el-input v-model="supplierForm.name" placeholder="输入供应商名称" style="width: 200px;" />
                </el-form-item>
                <el-form-item>
                  <el-button type="primary" @click="handleAddSupplier" :loading="addingSupplier" :disabled="currentTaskDetails.status !== 'active'">
                    添加供应商
                  </el-button>
                </el-form-item>
              </el-form>
            </div>

            <el-table :data="currentTaskDetails.links" border stripe style="width: 100%">
              <el-table-column type="expand">
                <template #default="props">
                  <div class="expand-content">
                    <h4 class="expand-title"><el-icon style="vertical-align: middle; margin-right: 5px;"><DocumentCopy /></el-icon>历史报价记录</h4>
                    <el-timeline style="padding-top: 10px;">
                      <el-timeline-item
                        v-for="(quotes, round) in props.row.quotes"
                        :key="round"
                        :timestamp="`第 ${round} 轮报价`"
                        placement="top"
                        type="primary"
                      >
                        <el-card shadow="hover" body-style="padding: 10px;">
                          <el-table :data="quotes" border size="small">
                            <el-table-column prop="item_id" label="明细项ID" width="100" align="center" />
                            <el-table-column prop="qty" label="可供数量" width="100" align="center" />
                            <el-table-column prop="delivery_date" label="承诺交期" width="120" align="center">
                              <template #default="scope">
                                {{ formatDate(scope.row.delivery_date) }}
                              </template>
                            </el-table-column>
                            <el-table-column prop="price" label="单价(¥)" width="120" align="right">
                              <template #default="scope">
                                <span style="color: #f56c6c; font-weight: bold;">{{ Number(scope.row.price).toFixed(2) }}</span>
                              </template>
                            </el-table-column>
                            <el-table-column prop="remark" label="备注说明" />
                          </el-table>
                        </el-card>
                      </el-timeline-item>
                    </el-timeline>
                    <el-empty v-if="!props.row.quotes || Object.keys(props.row.quotes).length === 0" description="暂无报价记录" :image-size="60"></el-empty>
                  </div>
                </template>
              </el-table-column>

              <el-table-column prop="supplier_name" label="供应商名称" min-width="150" />
              <el-table-column prop="status" label="当前状态" width="120" align="center">
                <template #default="scope">
                  <el-tag :type="getLinkStatusType(scope.row.status)" effect="light">{{ getLinkStatusText(scope.row.status) }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="current_round" label="当前轮次" width="100" align="center" />

              <el-table-column label="操作" width="120" align="center" fixed="right">
                <template #default="scope">
                  <el-button 
                    v-if="currentTaskDetails.status === 'active' && scope.row.status !== 'deal' && scope.row.status !== 'reject'" 
                    size="small" 
                    type="success" 
                    plain
                    @click="handleCloseTask(scope.row.link_id)">
                    选定成交
                  </el-button>
                  <span v-else-if="scope.row.status === 'deal'" style="color: #67c23a; font-weight: bold;">已成交</span>
                  <span v-else-if="scope.row.status === 'reject'" style="color: #909399;">已淘汰</span>
                  <span v-else>-</span>
                </template>
              </el-table-column>
            </el-table>
          </el-tab-pane>

          <!-- Tab 2: Items -->
          <el-tab-pane label="询价明细 (Items)" name="items">
            <el-table :data="currentTaskDetails.items" border stripe size="small">
              <el-table-column prop="id" label="明细项ID" width="100" align="center" />
              <el-table-column prop="material_code" label="物料编码" width="150" />
              <el-table-column prop="material_name" label="物料名称" min-width="200" />
              <el-table-column prop="qty" label="需求数量" width="120" align="right" />
              <el-table-column prop="target_price" label="设定期望单价(¥)" width="150" align="right">
                <template #default="scope">
                  <span v-if="scope.row.target_price" style="color: #f56c6c; font-weight: bold;">{{ Number(scope.row.target_price).toFixed(2) }}</span>
                  <span v-else style="color: #909399;">不设限</span>
                </template>
              </el-table-column>
              <el-table-column prop="delivery_date" label="需求日期" width="150" align="center">
                <template #default="scope">{{ formatDate(scope.row.delivery_date) }}</template>
              </el-table-column>
            </el-table>
          </el-tab-pane>

        </el-tabs>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { getInquiryTasks, addSupplierToTask, getTaskDetails, closeInquiryTask } from '../../api/inquiry'
import api from '../../api/index'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh, DocumentCopy, Search } from '@element-plus/icons-vue'

const loadingTasks = ref(false)
const taskList = ref([])
const searchQuery = ref('')

const filteredTaskList = computed(() => {
  if (!searchQuery.value) return taskList.value
  return taskList.value.filter(task => 
    task.title.toLowerCase().includes(searchQuery.value.toLowerCase())
  )
})

const detailsVisible = ref(false)
const detailsActiveTab = ref('suppliers')
const currentTask = ref(null)
const currentTaskDetails = ref(null)
const loadingDetails = ref(false)
const addingSupplier = ref(false)
const supplierForm = reactive({
  name: '',
  contact: '',
  phone: ''
})

const fetchTasks = async () => {
  loadingTasks.value = true
  try {
    const res = await getInquiryTasks()
    taskList.value = res.data
  } catch (error) {
    console.error(error)
    ElMessage.error('获取任务列表失败')
  } finally {
    loadingTasks.value = false
  }
}

const viewTaskDetails = async (task) => {
  currentTask.value = task
  detailsActiveTab.value = 'suppliers'
  detailsVisible.value = true
  loadingDetails.value = true
  try {
    const res = await getTaskDetails(task.id)
    currentTaskDetails.value = res.data
  } catch (error) {
    console.error(error)
    ElMessage.error('获取任务详情失败')
  } finally {
    loadingDetails.value = false
  }
}

const handleCloseTask = async (linkId = null) => {
  try {
    await closeInquiryTask(currentTaskDetails.value.id, linkId)
    ElMessage.success(linkId ? '已选定该供应商并自动关闭任务' : '任务已手动结束 (流标)')
    viewTaskDetails(currentTask.value)
    fetchTasks()
  } catch (error) {
    console.error(error)
    ElMessage.error('操作失败')
  }
}

const handleDeleteTask = async (task) => {
  try {
    await ElMessageBox.confirm('确认删除该询价单吗？相关的报价记录将一并删除，且操作不可恢复。', '警告', {
      confirmButtonText: '确认删除',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    await api.delete(`/inquiry/tasks/${task.id}`)
    ElMessage.success('删除成功')
    fetchTasks()
  } catch (e) {
    if (e !== 'cancel') {
      console.error(e)
      ElMessage.error('删除失败')
    }
  }
}

const handleAddSupplier = async () => {
  if (!supplierForm.name) {
    ElMessage.warning('请输入供应商名称')
    return
  }
  addingSupplier.value = true
  try {
    await addSupplierToTask(currentTask.value.id, {
      supplier_name: supplierForm.name,
      contact_person: supplierForm.contact,
      phone: supplierForm.phone
    })
    ElMessage.success(`供应商添加成功`)
    supplierForm.name = ''
    viewTaskDetails(currentTask.value)
  } catch (error) {
    console.error(error)
    ElMessage.error('添加供应商失败')
  } finally {
    addingSupplier.value = false
  }
}

const getLinkStatusType = (status) => {
  const map = {
    'sent': 'info',
    'quoted': 'primary',
    'negotiation': 'warning',
    'deal': 'success',
    'reject': 'danger'
  }
  return map[status] || ''
}

const getLinkStatusText = (status) => {
  const map = {
    'sent': '已发送(未报)',
    'quoted': '已报价',
    'negotiation': '谈判中',
    'deal': '已成交',
    'reject': '已淘汰'
  }
  return map[status] || status
}

const formatDateTime = (dateStr) => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString()
}

const formatDate = (dateStr) => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleDateString()
}

const getTaskStatusType = (status) => {
  const map = {
    'active': 'success',
    'closed': 'info',
    'cancelled': 'danger'
  }
  return map[status] || ''
}

onMounted(() => {
  fetchTasks()
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

/* 任务详情弹窗美化 */
.task-details-container {
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

.header-title {
  display: flex;
  align-items: center;
}

.task-title {
  font-size: 18px;
  font-weight: bold;
  color: #303133;
}

.details-tabs {
  box-shadow: 0 2px 12px 0 rgba(0,0,0,0.05);
  border-radius: 8px;
  overflow: hidden;
}

.tab-toolbar {
  margin-bottom: 15px;
  display: flex;
  justify-content: flex-start;
  align-items: center;
  background-color: #f5f7fa;
  padding: 10px 15px;
  border-radius: 4px;
}

.supplier-form {
  margin-bottom: 0;
}

.supplier-form .el-form-item {
  margin-bottom: 0;
  margin-right: 15px;
}

.expand-content {
  padding: 20px 40px;
  background-color: #fafafa;
  border-top: 1px solid #ebeef5;
  border-bottom: 1px solid #ebeef5;
}

.expand-title {
  margin-top: 0;
  margin-bottom: 15px;
  color: #606266;
  font-size: 15px;
}
</style>