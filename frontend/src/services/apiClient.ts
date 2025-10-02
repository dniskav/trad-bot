import API_CONFIG from '@config/api'
import axios from 'axios'

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
    // ⚠️ FIX: Removed automatic cache-busting to reduce timestamp spam
    // Only add timestamp when explicitly requested (useCache: false)
    if (config.method === 'get' && config.params?.useCache === false) {
      config.params = {
        ...config.params,
        _t: Date.now()
      }
      // Remove the useCache flag after processing
      delete config.params.useCache
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
    const status = error?.response?.status
    const data = error?.response?.data
    const message = error?.message || (typeof data === 'string' ? data : JSON.stringify(data || {}))
    const url = error?.config?.url
    console.error('❌ API Response Error:', status ?? 'NETWORK', message, url || '')

    // Retry logic only for server errors (>=500) when config exists
    if (error?.config && typeof status === 'number' && status >= 500) {
      if (!error.config.__retryCount) {
        error.config.__retryCount = 0
      }
      if (error.config.__retryCount < API_CONFIG.RETRY_ATTEMPTS) {
        error.config.__retryCount++
        console.log(
          `🔄 Retrying request (${error.config.__retryCount}/${API_CONFIG.RETRY_ATTEMPTS})`
        )
        return new Promise((resolve) => {
          setTimeout(() => {
            resolve(apiClient(error.config))
          }, API_CONFIG.RETRY_DELAY)
        })
      }
    }

    return Promise.reject(error)
  }
)

export default apiClient
