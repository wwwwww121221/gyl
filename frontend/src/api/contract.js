import api from './index'

const CONTRACT_BASE = '/contract'

export const getContractList = (params = {}) => {
  return api.get(`${CONTRACT_BASE}/list`, { params })
}

export const getContractPdfBlob = (contractId) => {
  return api.get(`${CONTRACT_BASE}/${contractId}/pdf`, {
    responseType: 'blob'
  })
}
