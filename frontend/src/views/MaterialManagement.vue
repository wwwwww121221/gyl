<template>
  <div class="page-container">
    <div class="header">
      <h2 class="page-title">物料管理</h2>
      <el-button type="primary" icon="Plus">新增物料</el-button>
    </div>
    
    <div class="content-card">
      <el-empty description="物料管理模块开发中..." />
    </div>
  </div>
</template>

<script setup>
import { Plus } from '@element-plus/icons-vue'
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

.content-card {
  background: white;
  padding: 40px;
  border-radius: 8px;
  min-height: 400px;
  display: flex;
  justify-content: center;
  align-items: center;
}
</style>