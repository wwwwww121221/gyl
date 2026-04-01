import api from './index'

const TEMPLATE_BASE = '/template'

export const getTemplateList = (params = {}) => {
  return api.get(`${TEMPLATE_BASE}/list`, { params })
}

export const getTemplateDetail = (id) => {
  return api.get(`${TEMPLATE_BASE}/${id}`)
}

export const createTemplate = (data) => {
  return api.post(`${TEMPLATE_BASE}`, data)
}

export const updateTemplate = (id, data) => {
  return api.put(`${TEMPLATE_BASE}/${id}`, data)
}

export const deleteTemplate = (id) => {
  return api.delete(`${TEMPLATE_BASE}/${id}`)
}

export const uploadTemplateFile = (file) => {
  const formData = new FormData()
  formData.append('file', file)
  return api.post(`${TEMPLATE_BASE}/upload`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}
