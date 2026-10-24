import axios from 'axios'
import { useAuthStore } from '../stores/authStore'

export interface NotificationItem {
  id: number
  notification_type: string
  title: string
  message: string
  is_read: boolean
  resource_type?: string | null
  resource_id?: number | null
  created_at: string
}

export interface AnalyticsSummary {
  total_systems: number
  by_risk_level: Record<string, number>
  by_compliance_status: Record<string, number>
  documents_generated: number
  average_compliance_score: number | null
}

export interface ComplianceSnapshot {
  ai_system_id: number
  compliance_score: number | null
  compliance_status: string
  risk_level: string | null
  snapshotted_at: string
}

export interface ComplianceTimeline {
  ai_system_id: number
  ai_system_name: string
  snapshots: ComplianceSnapshot[]
}

const api = axios.create({
  baseURL: '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
})

// Add auth token to requests
api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Handle 401 errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      useAuthStore.getState().logout()
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

// Auth API
export const authApi = {
  login: async (email: string, password: string) => {
    const formData = new URLSearchParams()
    formData.append('username', email)
    formData.append('password', password)
    const { data } = await api.post('/auth/login', formData, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    })
    return data
  },
  register: async (userData: {
    email: string
    password: string
    full_name?: string
    company_name?: string
  }) => {
    const { data } = await api.post('/auth/register', userData)
    return data
  },
  getMe: async (token?: string) => {
    const { data } = await api.get(
      '/auth/me',
      token ? { headers: { Authorization: `Bearer ${token}` } } : undefined
    )
    return data
  },
}

// AI Systems API
export const aiSystemsApi = {
  list: async () => {
    const { data } = await api.get('/ai-systems/')
    return data
  },
  get: async (id: number) => {
    const { data } = await api.get(`/ai-systems/${id}`)
    return data
  },
  create: async (system: {
    name: string
    description?: string
    use_case?: string
    sector?: string
  }) => {
    const { data } = await api.post('/ai-systems/', system)
    return data
  },
  update: async (id: number, system: Record<string, unknown>) => {
    const { data } = await api.put(`/ai-systems/${id}`, system)
    return data
  },
  delete: async (id: number) => {
    await api.delete(`/ai-systems/${id}`)
  },
}

// Classification API
export const classificationApi = {
  classify: async (data: Record<string, unknown>) => {
    const response = await api.post('/classification/classify', data)
    return response.data
  },
  classifyAndSave: async (systemId: number, data: Record<string, unknown>) => {
    const response = await api.post(`/classification/classify/${systemId}`, data)
    return response.data
  },
}

// Documents API
export const documentsApi = {
  list: async () => {
    const { data } = await api.get('/documents/')
    return data
  },
  get: async (id: number) => {
    const { data } = await api.get(`/documents/${id}`)
    return data
  },
  generate: async (request: {
    document_type: string
    ai_system_id: number
  }) => {
    const { data } = await api.post('/documents/generate', request)
    return data
  },
  update: async (id: number, content: string) => {
    const { data } = await api.put(`/documents/${id}`, { content })
    return data
  },
  downloadPdf: async (id: number): Promise<Blob> => {
    const { data } = await api.get(`/documents/${id}/pdf`, { responseType: 'blob' })
    return data as Blob
  },
  delete: async (id: number) => {
    await api.delete(`/documents/${id}`)
  },
}

// Notifications API
export const notificationsApi = {
  list: (unreadOnly = false): Promise<NotificationItem[]> =>
    api.get(`/notifications?unread_only=${unreadOnly}`).then((r) => r.data),
  markRead: (ids: number[]) =>
    api.post('/notifications/read', { ids }),
  remove: (id: number) =>
    api.delete(`/notifications/${id}`),
}

// Analytics API
export const analyticsApi = {
  summary: async (): Promise<AnalyticsSummary> => {
    const { data } = await api.get('/analytics/summary')
    return data
  },
  timeline: async (systemId: number, days = 30): Promise<ComplianceTimeline> => {
    const { data } = await api.get(
      `/analytics/compliance-timeline?system_id=${systemId}&days=${days}`
    )
    return data
  },
}

export default api
