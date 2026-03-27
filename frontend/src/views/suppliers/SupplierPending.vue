<template>
  <div class="page-container">
    <div class="header">
      <h2 class="page-title">待审核供应商</h2>
    </div>
    
    <div class="content-card">
      <el-table :data="pendingSuppliers" style="width: 100%" v-loading="loading">
        <el-table-column type="index" label="序号" width="80" />
        <el-table-column prop="name" label="供应商名称" />
        <el-table-column prop="contact_person" label="联系人" />
        <el-table-column prop="phone" label="联系电话" />
        <el-table-column prop="email" label="电子邮箱" />
        
        <el-table-column prop="status" label="状态">
          <template #default>
            <el-tag type="warning">待审核</el-tag>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="200">
          <template #default="{ row }">
            <el-button size="small" type="success" @click="handleApprove(row)">
              通过
            </el-button>
            <el-button size="small" type="danger" @click="handleReject(row)">
              拒绝
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import api from '../../api/index'
import { ElMessage, ElMessageBox } from 'element-plus'

const allSuppliers = ref([])
const loading = ref(false)

const fetchSuppliers = async () => {
  loading.value = true
  try {
    const res = await api.get('/supplier/list')
    allSuppliers.value = res.data
  } catch (error) {
    console.error(error)
  } finally {
    loading.value = false
  }
}

// Only show pending suppliers
const pendingSuppliers = computed(() => {
  return allSuppliers.value.filter(s => s.status === 'pending')
})

onMounted(() => {
  fetchSuppliers()
})

const handleApprove = async (row) => {
  try {
    await ElMessageBox.confirm(`确认通过供应商 "${row.name}" 的入驻申请吗？`, '提示', {
      confirmButtonText: '确认',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    loading.value = true
    await api.put(`/supplier/${row.id}`, {
      status: 'approved',
      level: 'general' // Default level
    })
    ElMessage.success('审核已通过')
    fetchSuppliers()
  } catch (e) {
    if (e !== 'cancel') console.error(e)
  } finally {
    loading.value = false
  }
}

const handleReject = async (row) => {
  try {
    await ElMessageBox.confirm(`确认拒绝供应商 "${row.name}" 的入驻申请吗？`, '警告', {
      confirmButtonText: '确认',
      cancelButtonText: '取消',
      type: 'danger'
    })
    
    loading.value = true
    await api.put(`/supplier/${row.id}`, {
      status: 'rejected',
    })
    ElMessage.success('已拒绝该申请')
    fetchSuppliers()
  } catch (e) {
    if (e !== 'cancel') console.error(e)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.page-container {
  padding: 20px;
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
  min-height: 400px;
}
</style>
