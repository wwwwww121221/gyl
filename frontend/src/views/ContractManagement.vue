<template>
  <div class="page-container">
    <div class="header">
      <h2 class="page-title">合同管理</h2>
    </div>

    <div class="content-card">
      <el-table :data="contracts" v-loading="loading" style="width: 100%">
        <el-table-column prop="contract_no" label="合同编号" min-width="180" />
        <el-table-column prop="inquiry_name" label="项目/询价单" min-width="180" />
        <el-table-column prop="supplier_name" label="供应商" min-width="160" />
        <el-table-column label="总金额" min-width="120">
          <template #default="{ row }">
            {{ formatAmount(row.total_amount) }}
          </template>
        </el-table-column>
        <el-table-column label="状态" min-width="130">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">
              {{ row.status || '未知' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="handlePreview(row)">预览 PDF</el-button>
            <el-button link type="success" @click="handleDownload(row)">下载</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrap">
        <el-pagination
          background
          layout="total, prev, pager, next, sizes"
          :total="total"
          :page-size="pageSize"
          :current-page="currentPage"
          :page-sizes="[10, 20, 50, 100]"
          @current-change="handlePageChange"
          @size-change="handleSizeChange"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getContractList, getContractPdfBlob } from '../api/contract'

const loading = ref(false)
const contracts = ref([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)

const fetchContracts = async () => {
  loading.value = true
  try {
    const params = {
      skip: (currentPage.value - 1) * pageSize.value,
      limit: pageSize.value
    }
    const res = await getContractList(params)
    contracts.value = res.data.items || []
    total.value = res.data.total || 0
  } catch (error) {
    console.error(error)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchContracts()
})

const formatAmount = (amount) => {
  const num = Number(amount || 0)
  return `¥ ${num.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

const getStatusType = (status) => {
  if (!status) return 'info'
  if (status.includes('待')) return 'warning'
  if (status.includes('generated') || status.includes('完成')) return 'success'
  return 'info'
}

const openBlobInNewTab = (blob) => {
  const url = URL.createObjectURL(blob)
  const tab = window.open(url, '_blank')
  if (!tab) {
    ElMessage.warning('浏览器阻止了新窗口，请允许弹窗后重试')
  }
  setTimeout(() => URL.revokeObjectURL(url), 30000)
}

const handlePreview = async (row) => {
  try {
    const res = await getContractPdfBlob(row.id)
    openBlobInNewTab(res.data)
  } catch (error) {
    console.error(error)
  }
}

const handleDownload = async (row) => {
  try {
    const res = await getContractPdfBlob(row.id)
    const blob = res.data
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `${row.contract_no || 'contract'}.pdf`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  } catch (error) {
    console.error(error)
  }
}

const handlePageChange = (page) => {
  currentPage.value = page
  fetchContracts()
}

const handleSizeChange = (size) => {
  pageSize.value = size
  currentPage.value = 1
  fetchContracts()
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
  background: #fff;
  padding: 20px;
  border-radius: 8px;
}

.pagination-wrap {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
</style>
