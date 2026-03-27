<template>
  <div class="layout-container">
    <el-container class="main-container">
      <el-aside width="200px" class="aside">
        <div class="logo">
          <h2>供应商服务平台</h2>
        </div>
        <el-menu
          :default-active="activeMenu"
          class="el-menu-vertical"
          background-color="#304156"
          text-color="#bfcbd9"
          active-text-color="#409EFF"
          router
        >
          <el-menu-item index="/supplier/inquiries">
            <el-icon><Document /></el-icon>
            <span>我的询价单</span>
          </el-menu-item>
          <el-menu-item index="/supplier/warnings">
            <el-icon><Warning /></el-icon>
            <span>发货预警</span>
          </el-menu-item>
        </el-menu>
      </el-aside>
      
      <el-container>
        <el-header class="header">
          <div class="header-left">
            <h3>{{ pageTitle }}</h3>
          </div>
          <div class="header-right">
            <el-dropdown @command="handleCommand">
              <span class="el-dropdown-link user-info">
                <el-avatar size="small" icon="UserFilled" style="margin-right: 8px;" />
                {{ username }}
                <el-icon class="el-icon--right"><arrow-down /></el-icon>
              </span>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="logout">退出登录</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </el-header>
        
        <el-main class="main-content">
          <router-view v-slot="{ Component }">
            <transition name="fade" mode="out-in">
              <component :is="Component" />
            </transition>
          </router-view>
        </el-main>
      </el-container>
    </el-container>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { Document, Warning, ArrowDown } from '@element-plus/icons-vue'
import { jwtDecode } from "jwt-decode";

const router = useRouter()
const route = useRoute()

const activeMenu = computed(() => route.path)

const pageTitle = computed(() => {
  const map = {
    '/supplier/inquiries': '我的询价单',
    '/supplier/warnings': '发货预警'
  }
  return map[route.path] || '供应商服务平台'
})

const username = ref('Supplier')
try {
  const token = localStorage.getItem('token')
  if (token) {
    const decoded = jwtDecode(token)
    username.value = decoded.sub || 'Supplier'
  }
} catch (e) {
  console.error('Failed to parse token')
}

const handleCommand = (command) => {
  if (command === 'logout') {
    localStorage.removeItem('token')
    localStorage.removeItem('role')
    router.push('/login')
  }
}
</script>

<style scoped>
.layout-container {
  height: 100vh;
  width: 100vw;
}

.main-container {
  height: 100%;
}

.aside {
  background-color: #304156;
  color: white;
  display: flex;
  flex-direction: column;
}

.logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-bottom: 1px solid #1f2d3d;
}

.logo h2 {
  margin: 0;
  font-size: 18px;
  color: #fff;
  white-space: nowrap;
}

.el-menu-vertical {
  border-right: none;
  flex: 1;
}

.header {
  background-color: #fff;
  box-shadow: 0 1px 4px rgba(0,21,41,.08);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  z-index: 10;
}

.header-left h3 {
  margin: 0;
  color: #303133;
  font-weight: 500;
}

.user-info {
  display: flex;
  align-items: center;
  cursor: pointer;
  color: #606266;
}

.main-content {
  background-color: #f0f2f5;
  padding: 20px;
  position: relative;
}

/* 过渡动画 */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>