<template>
  <div class="layout-container">
    <el-container>
      <el-aside width="220px">
        <el-menu
          :default-active="activeMenu"
          class="el-menu-vertical-demo"
          background-color="#304156"
          text-color="#bfcbd9"
          active-text-color="#409EFF"
          router
        >
          <div class="logo">
            <span class="logo-text">SC Agent</span>
          </div>
          <el-menu-item index="/dashboard">
            <el-icon><DataBoard /></el-icon>
            <span>预警看板</span>
          </el-menu-item>
          <el-sub-menu index="/inquiries">
            <template #title>
              <el-icon><List /></el-icon>
              <span>询价管理</span>
            </template>
            <el-menu-item index="/inquiries/requests">采购申请列表</el-menu-item>
            <el-menu-item index="/inquiries/tasks">询价单</el-menu-item>
          </el-sub-menu>
          <el-sub-menu index="/suppliers">
            <template #title>
              <el-icon><User /></el-icon>
              <span>供应商管理</span>
            </template>
            <el-menu-item index="/suppliers/pending">待审核</el-menu-item>
            <el-menu-item index="/suppliers/manage">已审核管理</el-menu-item>
          </el-sub-menu>
          <el-menu-item index="/materials">
            <el-icon><Goods /></el-icon>
            <span>物料管理</span>
          </el-menu-item>
          <el-menu-item index="/contracts">
            <el-icon><Document /></el-icon>
            <span>合同管理</span>
          </el-menu-item>
          <el-menu-item index="/templates">
            <el-icon><Files /></el-icon>
            <span>模板配置</span>
          </el-menu-item>
        </el-menu>
      </el-aside>
      <el-container>
        <el-header>
          <div class="header-left">
            <el-icon class="hamburger" @click="toggleSidebar"><Expand /></el-icon>
            <el-breadcrumb separator="/">
              <el-breadcrumb-item :to="{ path: '/' }">首页</el-breadcrumb-item>
              <el-breadcrumb-item>{{ currentRouteName }}</el-breadcrumb-item>
            </el-breadcrumb>
          </div>
          <div class="header-right">
            <el-dropdown trigger="click">
              <span class="el-dropdown-link">
                Admin <el-icon class="el-icon--right"><arrow-down /></el-icon>
              </span>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item>个人中心</el-dropdown-item>
                  <el-dropdown-item divided @click="handleLogout">退出登录</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </el-header>
        <el-main>
          <router-view />
        </el-main>
      </el-container>
    </el-container>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { DataBoard, User, Goods, Expand, ArrowDown, List, Document, Files } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

const router = useRouter()
const route = useRoute()
const isCollapse = ref(false)

const activeMenu = computed(() => {
  return route.path
})

const currentRouteName = computed(() => {
  const map = {
    '/dashboard': '预警看板',
    '/inquiries/requests': '采购申请列表',
    '/inquiries/tasks': '询价单',
    '/suppliers/pending': '待审核供应商',
    '/suppliers/manage': '已审核供应商',
    '/materials': '物料管理',
    '/contracts': '合同管理',
    '/templates': '模板配置'
  }
  return map[route.path] || '未知页面'
})

const toggleSidebar = () => {
  isCollapse.value = !isCollapse.value
}

const handleLogout = () => {
  localStorage.removeItem('token')
  ElMessage.success('已退出登录')
  router.push('/login')
}
</script>

<style scoped>
.layout-container {
  height: 100vh;
}

.el-container {
  height: 100%;
}

.el-aside {
  background-color: #304156;
  color: #333;
  transition: width 0.3s;
  overflow-x: hidden;
}

.el-menu {
  border-right: none;
}

.logo {
  height: 60px;
  line-height: 60px;
  background: #2b2f3a;
  text-align: center;
  overflow: hidden;
}

.logo-text {
  color: #fff;
  font-weight: 600;
  font-size: 20px;
  font-family: Avenir, Helvetica Neue, Arial, Helvetica, sans-serif;
  vertical-align: middle;
}

.el-header {
  background-color: #fff;
  color: #333;
  line-height: 60px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 20px;
  box-shadow: 0 1px 4px rgba(0,21,41,.08);
  z-index: 9;
}

.header-left {
  display: flex;
  align-items: center;
}

.hamburger {
  font-size: 20px;
  cursor: pointer;
  margin-right: 20px;
}

.header-right {
  display: flex;
  align-items: center;
}

.el-dropdown-link {
  cursor: pointer;
  color: #409EFF;
  display: flex;
  align-items: center;
}

.el-main {
  background-color: #f0f2f5;
  padding: 20px;
}
</style>
