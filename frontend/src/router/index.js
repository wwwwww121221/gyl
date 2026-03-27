import { createRouter, createWebHistory } from 'vue-router'
import WarningDashboard from '../views/WarningDashboard.vue'
import Login from '../views/Login.vue'
import MainLayout from '../layout/MainLayout.vue'
import MaterialManagement from '../views/MaterialManagement.vue'
import Register from '../views/Register.vue'
import SupplierLayout from '../layout/SupplierLayout.vue'

const routes = [
  {
    path: '/',
    redirect: () => {
      const role = localStorage.getItem('role')
      if (role === 'supplier') {
        return '/supplier/inquiries'
      }
      return '/dashboard'
    }
  },
  {
    path: '/login',
    name: 'Login',
    component: Login,
    meta: { requiresAuth: false }
  },
  {
    path: '/register',
    name: 'Register',
    component: Register,
    meta: { requiresAuth: false }
  },
  {
    path: '/dashboard',
    component: MainLayout,
    children: [
      {
        path: '',
        name: 'WarningDashboard',
        component: WarningDashboard,
        meta: { requiresRole: ['admin', 'buyer'] }
      }
    ]
  },
  {
    path: '/inquiries',
    component: MainLayout,
    redirect: '/inquiries/requests',
    children: [
      {
        path: 'requests',
        name: 'PurchaseRequests',
        component: () => import('../views/inquiries/PurchaseRequests.vue'),
        meta: { requiresRole: ['admin', 'buyer'] }
      },
      {
        path: 'tasks',
        name: 'InquiryTasks',
        component: () => import('../views/inquiries/InquiryTasks.vue'),
        meta: { requiresRole: ['admin', 'buyer'] }
      }
    ]
  },
  {
    path: '/suppliers',
    component: MainLayout,
    redirect: '/suppliers/manage',
    children: [
      {
        path: 'manage',
        name: 'SupplierManagement',
        component: () => import('../views/suppliers/SupplierManagement.vue'),
        meta: { requiresRole: ['admin', 'buyer'] }
      },
      {
        path: 'pending',
        name: 'SupplierPending',
        component: () => import('../views/suppliers/SupplierPending.vue'),
        meta: { requiresRole: ['admin', 'buyer'] }
      }
    ]
  },
  {
    path: '/materials',
    component: MainLayout,
    children: [
      {
        path: '',
        name: 'MaterialManagement',
        component: MaterialManagement,
        meta: { requiresRole: ['admin', 'buyer'] }
      }
    ]
  },
  {
    path: '/supplier',
    component: SupplierLayout,
    children: [
      {
        path: 'inquiries',
        name: 'MyInquiries',
        component: () => import('../views/supplier/MyInquiries.vue'),
        meta: { requiresRole: ['supplier'] }
      },
      {
        path: 'warnings',
        name: 'MyWarnings',
        component: () => import('../views/supplier/MyWarnings.vue'),
        meta: { requiresRole: ['supplier'] }
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// Navigation Guard
router.beforeEach((to, from) => {
  const token = localStorage.getItem('token')
  const role = localStorage.getItem('role')
  
  if (to.meta.requiresAuth === false) {
    if (token && to.path === '/login') {
      return '/' // 已经登录就不要去login了
    }
    return true
  }

  if (!token) {
    return '/login'
  }

  // Check role authorization
  if (to.meta.requiresRole && !to.meta.requiresRole.includes(role)) {
    // Role not authorized
    if (!role) {
      localStorage.removeItem('token')
      return '/login'
    }
    if (role === 'supplier') {
      if (to.path !== '/supplier/inquiries') {
        return '/supplier/inquiries'
      }
    } else {
      if (to.path !== '/dashboard') {
        return '/dashboard'
      }
    }
  }

  return true
})

export default router
