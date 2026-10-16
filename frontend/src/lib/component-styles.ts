/**
 * 统一组件样式规范
 * 定义一致的字体层级、间距、交互状态
 */

// 字体层级系统
export const typography = {
  // 标题层级
  heading: {
    lg: "text-lg font-semibold", // 18px - 主要标题
    md: "text-sm font-semibold", // 14px - 卡片标题
    sm: "text-xs font-medium", // 12px - 次要标题
  },
  // 正文层级
  body: {
    md: "text-sm text-foreground", // 14px - 主要内容
    sm: "text-xs text-foreground", // 12px - 次要内容
    xs: "text-[11px] text-foreground", // 11px - 辅助内容
  },
  // 辅助文本
  caption: {
    md: "text-xs text-muted-foreground", // 12px
    sm: "text-[11px] text-muted-foreground", // 11px
    xs: "text-[10px] text-muted-foreground", // 10px - 最小文本
  },
  // 标签文本
  label: {
    md: "text-xs font-medium",
    sm: "text-[11px] font-medium",
  },
} as const;

// 间距系统
export const spacing = {
  // 卡片间距
  cardGap: "space-y-4", // 16px - 卡片之间
  sectionGap: "space-y-6", // 24px - 区块之间

  // 内边距
  cardPadding: "p-5", // 20px - 卡片内边距
  sectionPadding: "p-6", // 24px - 区域内边距
  compactPadding: "p-3", // 12px - 紧凑内边距

  // 元素间距
  elementGap: "gap-4", // 16px - 元素之间
  compactGap: "gap-2", // 8px - 紧凑间距
  tightGap: "gap-1.5", // 6px - 最小间距
} as const;

// 统一卡片样式
export const card = {
  base: "rounded-xl border border-border bg-card shadow-sm",
  interactive:
    "rounded-xl border border-border bg-card shadow-sm hover:shadow-md transition-shadow",
} as const;

// 统一按钮样式
export const button = {
  // 主要按钮
  primary:
    "px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors text-sm font-medium",

  // 次要按钮
  secondary:
    "px-4 py-2 rounded-lg border border-border bg-muted text-foreground hover:bg-muted/70 transition-colors text-sm font-medium",

  // 幽灵按钮
  ghost:
    "px-3 py-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted/50 transition-colors text-sm",

  // 小按钮
  sm: {
    primary:
      "px-3 py-1.5 rounded-md bg-primary text-primary-foreground hover:bg-primary/90 transition-colors text-xs font-medium",
    secondary:
      "px-3 py-1.5 rounded-md border border-border bg-muted text-foreground hover:bg-muted/70 transition-colors text-xs",
    ghost:
      "px-2 py-1 rounded-md text-muted-foreground hover:text-foreground hover:bg-muted/50 transition-colors text-xs",
  },

  // 图标按钮
  icon: {
    sm: "w-7 h-7 flex items-center justify-center rounded-md text-muted-foreground hover:text-foreground hover:bg-muted/50 transition-colors",
    md: "w-8 h-8 flex items-center justify-center rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted/50 transition-colors",
  },
} as const;

// 统一输入框样式
export const input = {
  base: "w-full px-3 py-2 bg-background border border-input rounded-lg text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary/50 transition-colors",
  textarea:
    "w-full px-3 py-2 bg-background border border-input rounded-lg text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary/50 transition-colors resize-none",
} as const;

// 统一徽章样式
export const badge = {
  success:
    "inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] bg-green-100 dark:bg-green-500/15 text-green-700 dark:text-green-300 border border-green-300 dark:border-green-500/30",
  warning:
    "inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] bg-yellow-100 dark:bg-yellow-500/15 text-yellow-700 dark:text-yellow-300 border border-yellow-300 dark:border-yellow-500/30",
  error:
    "inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] bg-red-100 dark:bg-red-500/15 text-red-700 dark:text-red-300 border border-red-300 dark:border-red-500/30",
  info: "inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] bg-blue-100 dark:bg-blue-500/15 text-blue-700 dark:text-blue-300 border border-blue-300 dark:border-blue-500/30",
  muted:
    "inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] bg-muted text-muted-foreground border border-border",
} as const;

// 统一图标尺寸
export const icon = {
  xs: "w-3 h-3", // 12px
  sm: "w-3.5 h-3.5", // 14px
  md: "w-4 h-4", // 16px
  lg: "w-5 h-5", // 20px
  xl: "w-6 h-6", // 24px
} as const;

// 统一过渡动画
export const transition = {
  fast: "transition-all duration-150",
  normal: "transition-all duration-200",
  slow: "transition-all duration-300",
  colors: "transition-colors duration-200",
} as const;

// 统一圆角
export const rounded = {
  sm: "rounded-md", // 6px
  md: "rounded-lg", // 8px
  lg: "rounded-xl", // 12px
  full: "rounded-full",
} as const;

// 统一阴影
export const shadow = {
  sm: "shadow-sm",
  md: "shadow-md",
  lg: "shadow-lg",
} as const;

// 交互状态样式
export const interaction = {
  // 可点击元素
  clickable: "cursor-pointer select-none",
  // 禁用状态
  disabled: "opacity-50 cursor-not-allowed pointer-events-none",
  // 聚焦状态
  focus:
    "focus:outline-none focus:ring-2 focus:ring-primary/50 focus:ring-offset-2",
  // 选中状态
  selected: "bg-muted ring-1 ring-primary/30",
} as const;

// 统一进度条样式
export const progressBar = {
  track: "h-1.5 bg-muted rounded-full overflow-hidden",
  fill: "h-full rounded-full transition-all duration-700",
} as const;

// 统一分割线样式
export const divider = {
  horizontal: "border-t border-border",
  vertical: "border-l border-border",
} as const;

// 统一空状态样式
export const emptyState = {
  container:
    "flex flex-col items-center justify-center py-8 text-muted-foreground gap-3",
  icon: "w-10 h-10 opacity-20",
  title: "text-sm",
  description: "text-xs opacity-60",
} as const;
