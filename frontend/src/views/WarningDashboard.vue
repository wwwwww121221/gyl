<template>
  <div class="dashboard-container">
    <div class="header">
      <div class="header-left">
        <h1 class="dashboard-title">供应链交付预警看板</h1>
        <el-button type="primary" :icon="Refresh" circle @click="handleRefresh" :loading="loading" class="refresh-btn" />
        <span class="refresh-time">最后更新: {{ lastUpdateTime }}</span>
      </div>
    </div>

    <!-- Tabs for Switching Views -->
    <div class="tabs-container">
      <el-tabs v-model="activeTab" class="dashboard-tabs">
        <el-tab-pane label="供应商未到货 (Unreceived)" name="unreceived"></el-tab-pane>
        <el-tab-pane label="仓库未入库 (Unstockin)" name="unstockin"></el-tab-pane>
      </el-tabs>
    </div>

    <!-- Summary Statistics -->
    <div class="summary-section">
      <div class="summary-item">
        <div class="summary-label">
          {{ activeTab === 'unreceived' ? '待交付订单 (Pending Orders)' : '待入库订单 (Pending Stockin)' }}
        </div>
        <div class="summary-value">{{ summary.total_items }}</div>
      </div>
      <div class="summary-item">
        <div class="summary-label">总物料数量 (Total Material Qty)</div>
        <div class="summary-value">{{ summary.total_qty.toFixed(0) }}</div>
      </div>
      <div class="summary-item">
        <div class="summary-label">总供应商数量 (Total Suppliers)</div>
        <div class="summary-value warning">{{ summary.supplier_count }}</div>
      </div>
    </div>

    <!-- Filter Toolbar -->
    <div class="filter-toolbar">
      <div class="filter-left">
        <el-input
          v-model="searchQuery"
          placeholder="搜索物料/项目号..."
          prefix-icon="Search"
          clearable
          style="width: 250px; margin-right: 15px;"
        />
        <el-select
          v-model="selectedSupplier"
          placeholder="选择/搜索供应商"
          clearable
          filterable
          style="width: 250px; margin-right: 15px;"
        >
          <el-option
            v-for="supplier in uniqueSuppliers"
            :key="supplier"
            :label="supplier"
            :value="supplier"
          />
        </el-select>
        <el-select
          v-model="selectedProject"
          placeholder="选择项目号"
          clearable
          filterable
          style="width: 150px"
        >
          <el-option
            v-for="project in uniqueProjects"
            :key="project"
            :label="project"
            :value="project"
          />
        </el-select>
      </div>
      <div class="filter-right">
        <span class="filter-label">到期筛选:</span>
        <el-radio-group v-model="filterDays" size="default">
          <el-radio-button label="">全部</el-radio-button>
          <el-radio-button :label="1">1天内</el-radio-button>
          <el-radio-button :label="2">2天内</el-radio-button>
          <el-radio-button :label="3">3天内</el-radio-button>
        </el-radio-group>
      </div>
    </div>

    <!-- Main Content: Grouped by Supplier -->
    <div class="main-content" v-loading="loading">
      <template v-if="Object.keys(groupedData).length > 0">
        <div v-for="(group, supplierName) in groupedData" :key="supplierName" class="supplier-card">
          <div class="supplier-header">
            <span class="supplier-name">{{ supplierName }}</span>
            <span class="supplier-badge">{{ group.length }} 项物料</span>
            <el-button type="warning" size="small" @click="handleSendWarning(supplierName, group)" style="margin-left: auto;">发送预警</el-button>
          </div>
          
          <el-table :data="group" style="width: 100%" size="small" :row-class-name="tableRowClassName" border>
            <el-table-column prop="material_name" label="物料名称 (Material)" min-width="180" show-overflow-tooltip />
            <el-table-column prop="project_number" label="项目号 (Project)" width="150" show-overflow-tooltip />
            <el-table-column 
              :prop="activeTab === 'unreceived' ? 'warning_unreceived_qty' : 'warning_unstockin_qty'" 
              :label="activeTab === 'unreceived' ? '未收数量' : '未入库数量'" 
              width="120" 
              align="center" 
            />
            <el-table-column prop="delivery_date" label="交货日期" width="180" align="center">
              <template #default="scope">
                {{ formatDateTime(scope.row.delivery_date) }}
              </template>
            </el-table-column>
            <el-table-column label="状态 (Status)" width="150" align="center">
              <template #default="scope">
                <el-tag :type="getStatusType(scope.row.days_remaining)" effect="dark" size="small">
                  {{ getStatusText(scope.row.days_remaining) }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </template>
      <el-empty v-else description="暂无符合条件的数据" />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { getWarningDashboard, sendWarningToSupplier } from '../api/warning'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh, Search } from '@element-plus/icons-vue'

const loading = ref(false)
const lastUpdateTime = ref('-')
const searchQuery = ref('')
const selectedProject = ref('')
const selectedSupplier = ref('')
const filterDays = ref('') // '' for all, number for days
const activeTab = ref('unreceived')

const unreceivedList = ref([])
const unstockinList = ref([])

// Helper to calculate days remaining
const calculateDaysRemaining = (dateStr) => {
  const deliveryDate = new Date(dateStr)
  const now = new Date()
  // Reset time part for accurate day calculation
  now.setHours(0, 0, 0, 0)
  deliveryDate.setHours(0, 0, 0, 0)
  
  const diffTime = deliveryDate - now
  return Math.ceil(diffTime / (1000 * 60 * 60 * 24))
}

const uniqueProjects = computed(() => {
  const source = activeTab.value === 'unreceived' ? unreceivedList.value : unstockinList.value
  const projects = new Set(source.map(item => item.project_number).filter(Boolean))
  return Array.from(projects).sort()
})

const uniqueSuppliers = computed(() => {
  const source = activeTab.value === 'unreceived' ? unreceivedList.value : unstockinList.value
  const suppliers = new Set(source.map(item => item.supplier_name).filter(Boolean))
  return Array.from(suppliers).sort()
})

// 1. First filter the raw list based on search and days
const filteredList = computed(() => {
  let result = activeTab.value === 'unreceived' ? unreceivedList.value : unstockinList.value

  // Search Filter
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    result = result.filter(item => 
      (item.material_name && item.material_name.toLowerCase().includes(query)) || 
      (item.project_number && item.project_number.toLowerCase().includes(query))
    )
  }

  // Supplier Filter
  if (selectedSupplier.value) {
    result = result.filter(item => item.supplier_name === selectedSupplier.value)
  }

  // Project Filter
  if (selectedProject.value) {
    result = result.filter(item => item.project_number === selectedProject.value)
  }

  // Days Filter
  if (filterDays.value !== '') {
    result = result.filter(item => {
      const days = calculateDaysRemaining(item.delivery_date)
      if (filterDays.value === -1) {
        return days < 0 // Overdue
      } else {
        return days <= filterDays.value && days >= 0
      }
    })
  }

  return result
})

// 2. Then Aggregate: Same Material + Project + Delivery Date
const aggregatedList = computed(() => {
  const map = new Map()
  
  filteredList.value.forEach(item => {
    // Create a unique key
    const key = `${item.supplier_name}_${item.material_name}_${item.project_number}_${item.delivery_date}`
    
    if (map.has(key)) {
      const existing = map.get(key)
      if (activeTab.value === 'unreceived') {
        existing.warning_unreceived_qty += item.warning_unreceived_qty
      } else {
        existing.warning_unstockin_qty += item.warning_unstockin_qty
      }
    } else {
      map.set(key, { ...item }) // Clone item
    }
  })
  
  return Array.from(map.values())
})

const summary = computed(() => {
  const list = aggregatedList.value
  let totalQty = 0
  if (activeTab.value === 'unreceived') {
    totalQty = list.reduce((sum, item) => sum + item.warning_unreceived_qty, 0)
  } else {
    totalQty = list.reduce((sum, item) => sum + item.warning_unstockin_qty, 0)
  }
  const uniqueSuppliers = new Set(list.map(item => item.supplier_name)).size
  
  return {
    total_items: list.length,
    supplier_count: uniqueSuppliers,
    total_qty: totalQty
  }
})

// 3. Finally Group by Supplier for display
const groupedData = computed(() => {
  const groups = {}
  aggregatedList.value.forEach(item => {
    const supplier = item.supplier_name || 'Unknown Supplier'
    if (!groups[supplier]) {
      groups[supplier] = []
    }
    
    const daysRemaining = calculateDaysRemaining(item.delivery_date)
    
    groups[supplier].push({
      ...item,
      days_remaining: daysRemaining
    })
  })
  
  // Sort items within each group by quantity (descending)
  Object.keys(groups).forEach(supplier => {
    groups[supplier].sort((a, b) => {
      const qtyA = activeTab.value === 'unreceived' ? a.warning_unreceived_qty : a.warning_unstockin_qty
      const qtyB = activeTab.value === 'unreceived' ? b.warning_unreceived_qty : b.warning_unstockin_qty
      return qtyB - qtyA
    })
  })
  
  // Sort suppliers by number of items (descending)
  return Object.keys(groups).sort((a, b) => {
    return groups[b].length - groups[a].length
  }).reduce(
    (obj, key) => { 
      obj[key] = groups[key]; 
      return obj;
    }, 
    {}
  );
})

const getStatusType = (days) => {
  if (days < 0) return 'danger'
  if (days <= 3) return 'warning'
  return 'success'
}

const getStatusText = (days) => {
  if (days < 0) return `逾期 ${Math.abs(days)} 天`
  if (days === 0) return '今天到货'
  return `还有 ${days} 天`
}

const formatDateTime = (dateStr) => {
  if (!dateStr) return '-'
  // Only show date part as time is usually 00:00:00 or not relevant for day-level warning
  return new Date(dateStr).toLocaleDateString() 
}

const tableRowClassName = ({ row }) => {
  if (row.days_remaining < 0) return 'danger-row'
  if (row.days_remaining <= 3) return 'warning-row'
  return ''
}

const handleRefresh = () => {
  fetchData()
}

const fetchData = async () => {
  loading.value = true
  try {
    const res = await getWarningDashboard()
    const data = res.data
    // summary is now computed from unreceivedList
    unreceivedList.value = data.supplier_unreceived
    unstockinList.value = data.warehouse_unstockin
    lastUpdateTime.value = new Date().toLocaleString()
    ElMessage.success('数据已更新')
  } catch (error) {
    console.error('Failed to fetch dashboard data:', error)
    ElMessage.error('Failed to load dashboard data')
  } finally {
    loading.value = false
  }
}

const handleSendWarning = async (supplierName, items) => {
  try {
    await ElMessageBox.confirm(
      `确定要向 ${supplierName} 发送预警通知吗？将包含 ${items.length} 项物料信息。`,
      '发送预警',
      {
        confirmButtonText: '确定发送',
        cancelButtonText: '取消',
        type: 'warning',
      }
    )
    
    // Convert items for the backend payload
    const payload = {
      supplier_name: supplierName,
      items: items.map(item => ({
        material_name: item.material_name,
        warning_unreceived_qty: activeTab.value === 'unreceived' ? item.warning_unreceived_qty : item.warning_unstockin_qty,
        delivery_date: formatDateTime(item.delivery_date)
      }))
    }
    
    await sendWarningToSupplier(payload)
    ElMessage.success('预警发送成功')
  } catch (error) {
    if (error !== 'cancel') {
      console.error('Failed to send warning:', error)
      ElMessage.error(error.response?.data?.detail || '预警发送失败')
    }
  }
}

onMounted(() => {
  fetchData()
  // Refresh every 5 minutes
  setInterval(fetchData, 300000)
})
</script>

<style scoped>
.dashboard-container {
  padding: 20px;
  background-color: #f0f2f5;
  min-height: 100vh;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  background: white;
  padding: 15px 20px;
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0,0,0,0.05);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 15px;
}

.refresh-btn {
  margin-right: 10px;
  transition: transform 0.5s;
}

.refresh-btn:hover {
  transform: rotate(180deg);
}

.dashboard-title {
  margin: 0;
  font-size: 24px;
  color: #303133;
  font-weight: 600;
}

.refresh-time {
  color: #909399;
  font-size: 14px;
}

.tabs-container {
  margin-bottom: 20px;
  background: white;
  padding: 10px 20px 0;
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0,0,0,0.05);
}

:deep(.el-tabs__nav-wrap::after) {
  height: 1px;
  background-color: #f0f2f5;
}

:deep(.el-tabs__item) {
  font-size: 16px;
  font-weight: 500;
  color: #606266;
  padding-bottom: 10px;
}

:deep(.el-tabs__item.is-active) {
  color: #409EFF;
  font-weight: 600;
}

.summary-section {
  display: flex;
  gap: 20px;
  margin-bottom: 20px;
}

.summary-item {
  flex: 1;
  background: white;
  padding: 25px;
  border-radius: 8px;
  text-align: center;
  box-shadow: 0 4px 12px 0 rgba(0,0,0,0.05);
  transition: all 0.3s;
  border-left: 4px solid #409EFF;
}

.summary-item:nth-child(2) {
  border-left-color: #67C23A;
}

.summary-item:nth-child(3) {
  border-left-color: #E6A23C;
}

.summary-item:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 24px 0 rgba(0,0,0,0.1);
}

.summary-label {
  color: #606266;
  font-size: 16px;
  margin-bottom: 12px;
  font-weight: 500;
}

.summary-value {
  color: #303133;
  font-size: 36px;
  font-weight: bold;
  font-family: 'Helvetica Neue', Helvetica, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', '微软雅黑', Arial, sans-serif;
}

.summary-value.warning {
  color: #E6A23C;
}

.filter-toolbar {
  background: white;
  padding: 15px 20px;
  border-radius: 8px;
  margin-bottom: 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  box-shadow: 0 2px 12px 0 rgba(0,0,0,0.05);
}

/* Enhanced Search Input */
:deep(.el-input__wrapper) {
  box-shadow: 0 0 0 1px #dcdfe6 inset;
  border-radius: 20px;
  padding-left: 15px;
  transition: all 0.3s;
}

:deep(.el-input__wrapper:hover), :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px #409EFF inset !important;
}

.filter-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.filter-label {
  font-size: 14px;
  color: #606266;
}

/* Filter Radio Group Pills */
:deep(.el-radio-button:first-child .el-radio-button__inner) {
  border-radius: 20px 0 0 20px;
}

:deep(.el-radio-button:last-child .el-radio-button__inner) {
  border-radius: 0 20px 20px 0;
}

.main-content {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(600px, 1fr));
  gap: 20px;
}

.supplier-card {
  background: white;
  border-radius: 8px;
  padding: 0;
  box-shadow: 0 2px 12px 0 rgba(0,0,0,0.05);
  overflow: hidden;
  border: 1px solid #EBEEF5;
  transition: box-shadow 0.3s;
}

.supplier-card:hover {
  box-shadow: 0 8px 20px 0 rgba(0,0,0,0.1);
}

.supplier-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px 20px;
  background-color: #FAFAFA;
  border-bottom: 1px solid #EBEEF5;
}

.supplier-name {
  font-size: 16px;
  font-weight: bold;
  color: #303133;
}

.supplier-badge {
  background-color: #ecf5ff;
  color: #409eff;
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 12px;
  border: 1px solid #d9ecff;
}

:deep(.danger-row) {
  background-color: #fef0f0 !important;
}

:deep(.warning-row) {
  background-color: #fdf6ec !important;
}

:deep(.el-table .cell) {
  padding: 0 8px;
}
</style>
