# Resume AI 前端

React 19 + TypeScript + Vite 8，默认使用 Paper & Sage 亮色主题。

```bash
npm ci
npm run dev -- --host 127.0.0.1
npm run build
```

需要 Node.js 22.12+；本地后端地址为 `http://localhost:8000`。

- `src/index.css`：主题变量与基础排版。
- `src/studio.css`：首页、侧栏和工作空间卡片的视觉样式。
- `src/stores/settings-store.ts`：主题偏好，首次进入默认为亮色。
- `src/pages/Dashboard.tsx`：工作空间、搜索、加载与空状态。

完整功能、模型配置与后端启动步骤见[项目 README](../README.md)。
