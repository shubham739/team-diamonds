/**
 * API configuration for frontend
 * Determines the backend API base URL based on environment
 */

const API_BASE_URL = (() => {
  // In development with Vite proxy, use relative paths
  if (typeof window !== 'undefined' && (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')) {
    return '/api'
  }
  
  // In production on CloudFront, use full backend URL with API Gateway stage
  return 'https://baii6ilfl2.execute-api.us-east-2.amazonaws.com/prod'
})()

export function getApiUrl(path) {
  return `${API_BASE_URL}${path.startsWith('/') ? path : '/' + path}`
}

export default API_BASE_URL
