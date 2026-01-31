/**
 * Live2D 模型配置
 * 
 * 推荐的免费 Live2D 模型：
 * 1. Live2D 官方示例模型
 * 2. Booth.pm 上的免费模型
 * 3. Vroid Studio 导出的模型
 */

// 默认模型配置
export const live2dModels = {
  // Live2D 官方示例模型 - Haru
  haru: {
    name: 'Haru',
    description: 'Live2D 官方示例模型',
    url: '/models/live2d/haru/haru_greeter_t03.model3.json',
    author: 'Live2D',
    license: 'Free for non-commercial use',
    expressions: ['Normal', 'Happy', 'Thinking'],
    motions: ['Idle', 'Speaking', 'Breathing']
  }
}

// 模型下载链接（需要手动下载）
export const modelDownloadLinks = {
  koharu: {
    github: 'https://github.com/guansss/pixi-live2d-display/tree/master/packages/demo/models/koharu',
    download: 'https://cdn.jsdelivr.net/gh/guansss/pixi-live2d-display@latest/packages/demo/models/koharu/koharu.model3.json'
  }
}

/**
 * 获取模型 URL
 */
export function getModelUrl(modelKey) {
  const model = live2dModels[modelKey]
  if (model) {
    return model.url
  }
  return live2dModels.koharu.url
}

/**
 * 验证模型文件是否存在
 */
export async function checkModelExists(url) {
  try {
    const response = await fetch(url, { method: 'HEAD' })
    return response.ok
  } catch {
    return false
  }
}
