import { LayoutGrid, FileSearch, Users, Pencil, Trash2, Sparkles, FileText } from "lucide-react";
import {
  typography,
  button,
  icon,
  transition,
} from "../../lib/component-styles";

export type MainTab = "overview" | "jd" | "greeting" | "cover-letter" | "interview" | "meta";

interface WorkspaceTabsProps {
  activeTab: MainTab;
  onTabChange: (tab: MainTab) => void;
  onEdit?: () => void;
  onDelete?: () => void;
}

const tabs: { id: MainTab; label: string; icon: React.ReactNode }[] = [
  { id: "overview", label: "概览", icon: <LayoutGrid className={icon.md} /> },
  { id: "jd", label: "JD 分析", icon: <FileSearch className={icon.md} /> },
  { id: "greeting", label: "招呼语", icon: <Sparkles className={icon.md} /> },
  { id: "cover-letter", label: "求职信", icon: <FileText className={icon.md} /> },
  { id: "interview", label: "面试管理", icon: <Users className={icon.md} /> },
  { id: "meta", label: "元数据", icon: <Pencil className={icon.md} /> },
];

export default function WorkspaceTabs({
  activeTab,
  onTabChange,
  onEdit,
  onDelete,
}: WorkspaceTabsProps) {
  return (
    <div
      className="flex items-center justify-between border-b border-border px-4 shrink-0"
      role="tablist"
    >
      {/* 标签栏 */}
      <div className="flex">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => onTabChange(tab.id)}
            role="tab"
            aria-selected={activeTab === tab.id}
            aria-controls={`tabpanel-${tab.id}`}
            className={`py-2.5 px-3.5 ${typography.body.sm} font-medium flex items-center gap-2 ${transition.colors} relative outline-none ${
              activeTab === tab.id
                ? "text-foreground"
                : "text-muted-foreground hover:text-foreground hover:bg-muted/30"
            }`}
          >
            {tab.icon}
            {tab.label}
            {activeTab === tab.id && (
              <span className="absolute bottom-0 left-2 right-2 h-[3px] bg-primary rounded-full" />
            )}
          </button>
        ))}
      </div>

      {/* 操作按钮 - 使用统一样式 */}
      <div className="flex items-center gap-1.5">
        {onEdit && (
          <button
            type="button"
            onClick={onEdit}
            className={`${button.sm.ghost} flex items-center gap-1.5 border border-border focus:outline-none focus:ring-2 focus:ring-primary/50`}
          >
            <Pencil className={icon.sm} />
            <span>编辑</span>
          </button>
        )}
        {onDelete && (
          <button
            type="button"
            onClick={onDelete}
            className={`${button.sm.ghost} flex items-center gap-1.5 border border-border hover:text-red-400 hover:border-red-500/30 hover:bg-red-500/10 focus:outline-none focus:ring-2 focus:ring-primary/50`}
          >
            <Trash2 className={icon.sm} />
            <span>删除</span>
          </button>
        )}
      </div>
    </div>
  );
}
