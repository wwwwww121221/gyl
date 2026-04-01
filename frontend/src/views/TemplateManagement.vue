<template>
  <div class="page-container">
    <div class="header">
      <h2 class="page-title">模板配置</h2>
      <el-button type="primary" @click="openCreateDialog">新增模板</el-button>
    </div>

    <div class="content-card">
      <el-table :data="templates" v-loading="loading" style="width: 100%">
        <el-table-column prop="name" label="模板名称" min-width="180" />
        <el-table-column prop="file_path" label="模板路径" min-width="260" />
        <el-table-column prop="default_buyer_name" label="默认采购方" min-width="180" />
        <el-table-column label="启用状态" width="120">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'">
              {{ row.is_active ? '启用中' : '未启用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="260" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openEditDialog(row)">编辑</el-button>
            <el-button link type="success" @click="toggleActive(row)">
              {{ row.is_active ? '停用' : '启用' }}
            </el-button>
            <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="560px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="110px">
        <el-form-item label="模板名称" prop="name">
          <el-input v-model="form.name" placeholder="请输入模板名称" />
        </el-form-item>
        <el-form-item label="默认采购方">
          <el-input v-model="form.default_buyer_name" placeholder="请输入默认采购方主体名称" />
        </el-form-item>
        <el-form-item label="上传Excel" prop="file">
          <el-upload
            :auto-upload="false"
            :limit="1"
            accept=".xlsx,.xls"
            :on-change="handleFileChange"
            :on-remove="handleFileRemove"
          >
            <el-button type="primary">选择文件</el-button>
            <template #tip>
              <div class="upload-tip">
                {{ selectedFileName || '请上传 .xlsx 或 .xls 文件' }}
              </div>
            </template>
          </el-upload>
        </el-form-item>
        <el-form-item label="启用模板">
          <el-switch v-model="form.is_active" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitLoading" @click="handleSubmit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  createTemplate,
  deleteTemplate,
  getTemplateList,
  updateTemplate,
  uploadTemplateFile
} from '../api/template'

const loading = ref(false)
const templates = ref([])
const dialogVisible = ref(false)
const submitLoading = ref(false)
const editingId = ref(null)
const selectedFile = ref(null)
const selectedFileName = ref('')
const formRef = ref(null)

const form = reactive({
  name: '',
  default_buyer_name: '',
  is_active: false,
  file_path: ''
})

const rules = {
  name: [{ required: true, message: '请输入模板名称', trigger: 'blur' }],
  file: [{
    validator: (_rule, _value, callback) => {
      if (!editingId.value && !selectedFile.value) {
        callback(new Error('请上传Excel模板文件'))
        return
      }
      callback()
    },
    trigger: 'change'
  }]
}

const dialogTitle = computed(() => (editingId.value ? '编辑模板' : '新增模板'))

const resetForm = () => {
  form.name = ''
  form.default_buyer_name = ''
  form.is_active = false
  form.file_path = ''
  selectedFile.value = null
  selectedFileName.value = ''
}

const fetchTemplates = async () => {
  loading.value = true
  try {
    const res = await getTemplateList({ skip: 0, limit: 200 })
    templates.value = res.data.items || []
  } catch (error) {
    console.error(error)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchTemplates()
})

const openCreateDialog = () => {
  editingId.value = null
  resetForm()
  dialogVisible.value = true
}

const openEditDialog = (row) => {
  editingId.value = row.id
  form.name = row.name
  form.default_buyer_name = row.default_buyer_name || ''
  form.is_active = !!row.is_active
  form.file_path = row.file_path
  selectedFile.value = null
  selectedFileName.value = row.file_path || ''
  dialogVisible.value = true
}

const handleFileChange = (file) => {
  selectedFile.value = file.raw
  selectedFileName.value = file.name
}

const handleFileRemove = () => {
  selectedFile.value = null
  selectedFileName.value = ''
}

const handleSubmit = async () => {
  if (!formRef.value) return
  try {
    await formRef.value.validate()
  } catch (error) {
    return
  }

  submitLoading.value = true
  try {
    let filePath = form.file_path
    if (selectedFile.value) {
      const uploadRes = await uploadTemplateFile(selectedFile.value)
      filePath = uploadRes.data.file_path
    }
    const payload = {
      name: form.name,
      file_path: filePath,
      default_buyer_name: form.default_buyer_name || null,
      is_active: form.is_active
    }
    if (editingId.value) {
      await updateTemplate(editingId.value, payload)
      ElMessage.success('模板更新成功')
    } else {
      await createTemplate(payload)
      ElMessage.success('模板创建成功')
    }
    dialogVisible.value = false
    await fetchTemplates()
  } catch (error) {
    console.error(error)
  } finally {
    submitLoading.value = false
  }
}

const toggleActive = async (row) => {
  try {
    await updateTemplate(row.id, {
      name: row.name,
      file_path: row.file_path,
      default_buyer_name: row.default_buyer_name || null,
      is_active: !row.is_active
    })
    ElMessage.success(!row.is_active ? '模板已启用' : '模板已停用')
    await fetchTemplates()
  } catch (error) {
    console.error(error)
  }
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm(`确认删除模板「${row.name}」吗？`, '提示', {
      type: 'warning'
    })
    await deleteTemplate(row.id)
    ElMessage.success('模板删除成功')
    await fetchTemplates()
  } catch (error) {
    if (error !== 'cancel') {
      console.error(error)
    }
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
  background: #fff;
  padding: 20px;
  border-radius: 8px;
}

.upload-tip {
  margin-top: 8px;
  color: #909399;
}
</style>
