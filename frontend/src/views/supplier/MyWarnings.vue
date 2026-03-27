<template>
  <div class="my-warnings-container">
    <div class="header">
      <h2>我的预警通知</h2>
      <el-button type="primary" :icon="Refresh" circle @click="fetchMessages" :loading="loading" />
    </div>

    <div v-loading="loading">
      <el-empty v-if="messages.length === 0" description="暂无预警通知" />
      
      <div v-else class="message-list">
        <el-card 
          v-for="msg in messages" 
          :key="msg.id" 
          class="message-card"
          :class="{ 'is-unread': !msg.is_read }"
        >
          <template #header>
            <div class="card-header">
              <span class="time">{{ formatDateTime(msg.created_at) }}</span>
              <el-tag v-if="!msg.is_read" type="danger" size="small">未读</el-tag>
              <el-tag v-else type="info" size="small">已读</el-tag>
            </div>
          </template>
          
          <div class="message-content">
            <pre>{{ msg.content }}</pre>
          </div>
          
          <div class="card-actions" v-if="!msg.is_read">
            <el-button type="primary" size="small" @click="handleMarkRead(msg.id)">
              标为已读
            </el-button>
          </div>
        </el-card>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getMyWarningMessages, markWarningMessageRead } from '../../api/warning'
import { ElMessage } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'

const loading = ref(false)
const messages = ref([])

const formatDateTime = (dateStr) => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString()
}

const fetchMessages = async () => {
  loading.value = true
  try {
    const res = await getMyWarningMessages()
    // Sort by created_at descending
    messages.value = res.data.sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
  } catch (error) {
    console.error('Failed to fetch messages:', error)
    ElMessage.error('获取预警通知失败')
  } finally {
    loading.value = false
  }
}

const handleMarkRead = async (id) => {
  try {
    await markWarningMessageRead(id)
    ElMessage.success('已标记为已读')
    // Update local state
    const msg = messages.value.find(m => m.id === id)
    if (msg) {
      msg.is_read = true
    }
  } catch (error) {
    console.error('Failed to mark as read:', error)
    ElMessage.error('操作失败')
  }
}

onMounted(() => {
  fetchMessages()
})
</script>

<style scoped>
.my-warnings-container {
  padding: 20px;
  max-width: 1000px;
  margin: 0 auto;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.header h2 {
  margin: 0;
  color: #303133;
}

.message-list {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.message-card {
  transition: all 0.3s;
}

.message-card.is-unread {
  border-left: 4px solid #f56c6c;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.time {
  color: #909399;
  font-size: 14px;
}

.message-content {
  color: #606266;
  font-size: 14px;
  line-height: 1.6;
}

.message-content pre {
  margin: 0;
  white-space: pre-wrap;
  font-family: inherit;
}

.card-actions {
  margin-top: 15px;
  display: flex;
  justify-content: flex-end;
}
</style>
