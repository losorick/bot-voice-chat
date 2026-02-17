/**
 * API 配置
 * 根据当前域名动态获取 API baseURL
 */

// 获取当前域名的 API baseURL
export function getApiBaseUrl() {
  // 如果是在服务器上运行（通过域名访问），使用当前域名
  // 否则使用 localhost:5002 作为开发环境
  const currentHost = window.location.host
  
  // 检查是否使用已知的外网域名
  const knownDomains = [
    'mmchong.games',
    'mmctest.top'
  ]
  
  const isProduction = knownDomains.some(domain => currentHost.includes(domain))
  
  if (isProduction) {
    // 使用当前域名的协议和主机，端口由域名决定（80/443）
    return `${window.location.protocol}//${currentHost}`
  }
  
  // 开发环境使用本地
  return 'http://localhost:5002'
}

// 导出统一的 API URL
export const API_BASE_URL = getApiBaseUrl()
