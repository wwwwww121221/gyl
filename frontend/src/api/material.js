import request from './index'

const MATERIAL_BASE = '/material'

export const getMaterialHistory = (params = {}) => {
  return request.get(`${MATERIAL_BASE}/history`, { params })
}
