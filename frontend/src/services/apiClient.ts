import axios from 'axios'
import API_CONFIG from '../config/api'

// Create axios instance
const apiClient = axios.create({
  baseURL: API_CONFIG.BASE_URL,
  timeout: API_CONFIG.TIMEOUT,
  headers: {
    'Content-Type': 'application/json'
  }
})

// Request interceptor
apiClient.interceptors.request.use(
  (config) => {
    // Add timestamp to prevent caching
    if (config.method === 'get') {
      config.params = {
        ...config.params,
        _t: Date.now()
      }
    }

    console.log(`🌐 API Request: ${config.method?.toUpperCase()} ${config.url}`)
    return config
  },
  (error) => {
    console.error('❌ API Request Error:', error)
    return Promise.reject(error)
  }
)

// Response interceptor
apiClient.interceptors.response.use(
  (response) => {
    console.log(`✅ API Response: ${response.status} ${response.config.url}`)
    return response
  },
  (error) => {
    console.error('❌ API Response Error:', error.response?.status, error.response?.data)

    // Retry logic for failed requests
    if (error.response?.status >= 500 && error.config && !error.config.__retryCount) {
      error.config.__retryCount = 0
    }

    if (error.config && error.config.__retryCount < API_CONFIG.RETRY_ATTEMPTS) {
      error.config.__retryCount++
      console.log(`🔄 Retrying request (${error.config.__retryCount}/${API_CONFIG.RETRY_ATTEMPTS})`)

      return new Promise((resolve) => {
        setTimeout(() => {
          resolve(apiClient(error.config))
        }, API_CONFIG.RETRY_DELAY)
      })
    }

    return Promise.reject(error)
  }
)

export default apiClient
