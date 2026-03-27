<template>
  <div class="login-container">
    <div class="login-card" style="width: 500px;">
      <h2 class="login-title">供应商入驻申请</h2>
      <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
        <el-form-item label="公司名称" prop="companyName">
          <el-input v-model="form.companyName" placeholder="请输入公司全称" />
        </el-form-item>

        <el-form-item label="联系人" prop="contactPerson">
          <el-input v-model="form.contactPerson" placeholder="请输入联系人姓名" />
        </el-form-item>

        <el-form-item label="联系电话 (将作为登录账号)" prop="phone">
          <el-input v-model="form.phone" placeholder="请输入手机号" />
        </el-form-item>

        <el-form-item label="电子邮箱 (选填)" prop="email">
          <el-input v-model="form.email" placeholder="请输入电子邮箱" />
        </el-form-item>

        <el-form-item label="登录密码" prop="password">
          <el-input 
            v-model="form.password" 
            type="password" 
            placeholder="请输入密码" 
            show-password
          />
        </el-form-item>

        <el-form-item label="确认密码" prop="confirmPassword">
          <el-input 
            v-model="form.confirmPassword" 
            type="password" 
            placeholder="请再次输入密码" 
            show-password
          />
        </el-form-item>

        <el-form-item>
          <el-button type="primary" :loading="loading" class="login-btn" @click="handleRegister">
            提交入驻申请
          </el-button>
        </el-form-item>
        <div style="text-align: center; margin-top: 10px;">
          <span style="color: #606266; font-size: 14px;">已有账号？ </span>
          <el-button link type="primary" @click="router.push('/login')">直接登录</el-button>
        </div>
      </el-form>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import axios from 'axios'

const router = useRouter()
const formRef = ref(null)
const loading = ref(false)

const form = reactive({
  companyName: '',
  contactPerson: '',
  phone: '',
  email: '',
  password: '',
  confirmPassword: ''
})

const validatePass2 = (rule, value, callback) => {
  if (value === '') {
    callback(new Error('请再次输入密码'))
  } else if (value !== form.password) {
    callback(new Error('两次输入密码不一致!'))
  } else {
    callback()
  }
}

const validatePhone = (rule, value, callback) => {
  const phoneRegex = /^1[3-9]\d{9}$/
  if (value === '') {
    callback(new Error('请输入联系电话'))
  } else if (!phoneRegex.test(value)) {
    callback(new Error('请输入有效的11位手机号码'))
  } else {
    callback()
  }
}

const rules = {
  companyName: [{ required: true, message: '请输入公司全称', trigger: 'blur' }],
  contactPerson: [{ required: true, message: '请输入联系人姓名', trigger: 'blur' }],
  phone: [{ required: true, validator: validatePhone, trigger: 'blur' }],
  email: [
    { type: 'email', message: '请输入正确的邮箱地址', trigger: ['blur', 'change'] }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度不能小于 6 个字符', trigger: 'blur' }
  ],
  confirmPassword: [{ required: true, validator: validatePass2, trigger: 'blur' }]
}

const handleRegister = async () => {
  if (!formRef.value) return
  
  await formRef.value.validate(async (valid) => {
    if (valid) {
      loading.value = true
      try {
        await axios.post('/api/auth/register', {
          username: form.phone, // 使用手机号作为账号
          password: form.password,
          role: 'supplier',
          company_name: form.companyName,
          contact_person: form.contactPerson,
          phone: form.phone,
          email: form.email
        })
        
        ElMessage.success('注册成功！请等待采购方审核通过后登录。')
        router.push('/login')
      } catch (error) {
        console.error('Register failed:', error)
        ElMessage.error(error.response?.data?.detail || '注册失败')
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
  font-size: 24px;
}

.login-btn {
  width: 100%;
  margin-top: 10px;
}
</style>