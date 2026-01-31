# Live2D 虚拟形象配置

## 概述

本项目支持集成 Live2D 虚拟形象，在 AI 说话时显示动画效果。

## 功能特性

- 🎭 **口型同步** - 根据语音音量自动调整嘴巴开合
- 🦁 **自然晃动** - 说话时身体轻微晃动
- 👁️ **眨眼动画** - 空闲时随机眨眼
- 🌬️ **呼吸效果** - 空闲时轻微呼吸动画
- 🎨 **随机动作** - 随机触发小动作增加生动感

## 模型配置

### 1. 下载 Live2D 模型

将 Live2D 模型文件 (`.model3.json` + `.3.json` + 纹理图片) 放入：

```
frontend/public/models/live2d/
└── your-model/
    ├── your-model.model3.json
    ├── your-model.motion3.json
    └── textures/
        └── texture_00.png
```

### 2. 免费模型资源

| 来源 | 链接 | 说明 |
|-----|------|------|
| Live2D 官方示例 | [GitHub](https://github.com/guansss/pixi-live2d-display/tree/master/packages/demo/models) | 包含 Koharu 等模型 |
| Booth.pm | https://booth.pm/ | 日本同人模型平台 |
| Vroid Studio | https://vroid.com/ | 可导出为 Live2D |

### 3. 配置模型路径

编辑 `src/config/live2d.js`:

```javascript
export const live2dModels = {
  yourModel: {
    name: '你的模型名',
    url: '/models/live2d/your-model/your-model.model3.json',
    author: '作者名',
    license: '许可证'
  }
}
```

或在组件中直接指定：

```vue
<Live2DCharacter model-url="/models/live2d/koharu/koharu.model3.json" />
```

## 核心组件

### Live2DCharacter.vue

主要组件，包含：
- `speak(audioUrl)` - 播放音频并触发说话动画
- `startSpeaking()` - 开始说话动画
- `stopSpeaking()` - 停止说话动画
- `loadModel()` - 加载模型

### useAudioAnalyzer.js

音频分析器，用于：
- 分析音频音量
- 实时回调音量值用于口型控制

## 动画参数

### 可调参数

| 参数 | 范围 | 说明 |
|-----|------|------|
| ParamMouthOpenY | 0-1 | 嘴巴开合度 |
| ParamJawOpen | 0-0.5 | 下巴角度 |
| PARAM_BODY_ANGLE_X/Z | -0.1~0.1 | 身体晃动 |
| PARAM_EYE_L/R_OPEN | 0-1 | 眼睛开合 |

### 自定义动画

在 `Live2DCharacter.vue` 中修改动画逻辑：

```javascript
// 调整说话时的晃动幅度
const breathe = Math.sin(Date.now() / 500) * 0.02  // 改为 0.01-0.05

// 调整空闲动画频率
idleInterval = setInterval(() => {
  // 自定义逻辑
}, 100)  // 改为 50-200
```

## 浏览器兼容性

- ✅ Chrome 60+
- ✅ Firefox 55+
- ✅ Safari 14+
- ✅ Edge 79+

需要 WebGL 支持。

## 注意事项

1. **模型格式** - 使用 `.model3.json` 格式 (Cubism 3+)
2. **CORS** - 跨域加载模型需要正确配置服务器
3. **性能** - 模型越大，启动越慢，建议优化模型面数
4. **版权** - 注意模型的许可证（商业/非商业）

## 故障排除

### 模型加载失败
- 检查模型文件路径是否正确
- 确保模型文件可访问（CORS）
- 查看浏览器控制台错误信息

### 口型不匹配
- 调整 `setMouthOpen()` 中的映射参数
- 不同模型的参数名可能不同

### 动画卡顿
- 减少动画帧率（增加 interval 时间）
- 使用更轻量的模型

## 相关文档

- [Live2D Cubism SDK](https://www.live2d.com/sdk/)
- [Cubism SDK for Web](https://docs.live2d.com/cubism-sdk-tutorials/top/)
- [PIXI Live2D Display](https://github.com/guansss/pixi-live2d-display)
