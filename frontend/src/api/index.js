import axios from 'axios'
import { ElMessage } from 'element-plus'

const api = axios.create({
  baseURL: '/api',
  timeout: 10000
})

// Request interceptor
api.interceptors.request.use(
  config => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`
    }
    return config
  },
  error => {
    return Promise.reject(error)
  }
)

// Response interceptor
api.interceptors.response.use(
  response => {
    return response
  },
  error => {
    if (error.response) {
      if (error.response.status === 401) {
        // Clear token and redirect to login
        localStorage.removeItem('token')
        ElMessage.error('登录已过期，请重新登录')
        // Use window.location to avoid circular dependency with router
        window.location.href = '/login'
      } else {
        ElMessage.error(error.response.data.detail || '请求失败')
      }
    } else {
      ElMessage.error('网络错误或服务不可用')
    }
    return Promise.reject(error)
  }
)

export default api
