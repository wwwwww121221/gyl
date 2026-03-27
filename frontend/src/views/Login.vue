<template>
  <div class="login-container">
    <div class="login-card">
      <h2 class="login-title">
        供应链智能管理系统
      </h2>
      <el-form ref="formRef" :model="loginForm" :rules="rules" label-position="top">
        <el-form-item label="手机号/账号" prop="username">
          <el-input v-model="loginForm.username" prefix-icon="User" placeholder="请输入登录手机号或账号" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input 
            v-model="loginForm.password" 
            prefix-icon="Lock" 
            type="password" 
            placeholder="请输入密码" 
            show-password
            @keyup.enter="handleLogin"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="loading" class="login-btn" @click="handleLogin">
            登录
          </el-button>
        </el-form-item>
        <div style="text-align: right; margin-top: -10px; margin-bottom: 10px;">
          <el-button link type="primary" @click="router.push('/register')">供应商入驻注册</el-button>
        </div>
      </el-form>
      <div class="login-footer">
        <span class="copyright">© 2026 Supply Chain Agent</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { User, Lock } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'

const router = useRouter()
const formRef = ref(null)
const loading = ref(false)

const loginForm = reactive({
  username: '',
  password: ''
})

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}

const handleLogin = async () => {
  if (!formRef.value) return
  
  await formRef.value.validate(async (valid) => {
    if (valid) {
      loading.value = true
      try {
        // 使用 URLSearchParams 格式发送 form data，因为后端 OAuth2PasswordRequestForm 需要
        const params = new URLSearchParams()
        params.append('username', loginForm.username)
        params.append('password', loginForm.password)

        const res = await axios.post('/api/auth/login', params, {
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded'
          }
        })
        
        const { access_token, role } = res.data
        localStorage.setItem('token', access_token)
        localStorage.setItem('role', role)
        
        ElMessage.success('登录成功')
        
        // 根据角色跳转不同页面
        if (role === 'supplier') {
          router.push('/supplier/inquiries')
        } else {
          router.push('/')
        }
      } catch (error) {
        console.error('Login failed:', error)
        if (error.response && error.response.data && error.response.data.detail) {
          ElMessage.error(error.response.data.detail)
        } else {
          ElMessage.error('登录失败：网络错误或服务异常')
        }
      } finally {
        loading.value = false
      }
    }
  })
}
</script>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100vh;
  background-color: #f0f2f5;
  background-image: url('https://gw.alipayobjects.com/zos/rmsportal/TVYTbAXWheQpRcWDaDMu.svg');
  background-repeat: no-repeat;
  background-position: center 110px;
  background-size: 100%;
}

.login-card {
  width: 400px;
  padding: 40px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.login-title {
  text-align: center;
  margin-bottom: 30px;
  color: #303133;
  font-weight: 600;
}

.login-btn {
  width: 100%;
  padding: 20px 0;
  font-size: 16px;
}

.login-footer {
  text-align: center;
  margin-top: 20px;
}

.copyright {
  color: #909399;
  font-size: 12px;
}
</style>