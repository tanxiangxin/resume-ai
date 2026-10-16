import { useMemo, useState, useRef, useEffect } from 'react';
import { ZoomIn, ZoomOut, FileDown, ChevronDown } from 'lucide-react';
import ResumePreview from '@/components/preview/ResumePreview';
import {
  extractPreviewHtml,
  PAGINATION_OPTIONS,
  type PaginationStrategy,
} from '@/lib/export-utils';
import { exportPdf } from '@/lib/api';
import { useResumeStore } from '@/stores/resume-store';
import type { Resume } from '@/types/resume';

const A4_WIDTH = 794;

interface EditorPreviewPanelProps {
  className?: string;
}

export function EditorPreviewPanel({ className }: EditorPreviewPanelProps = {}) {
  const { currentResume, sections } = useResumeStore();
  const [zoom, setZoom] = useState(80);
  const [isGeneratingPdf, setIsGeneratingPdf] = useState(false);
  const [paginationStrategy, setPaginationStrategy] = useState<PaginationStrategy>('standard');
  const [showPaginationMenu, setShowPaginationMenu] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  // 点击外部关闭下拉菜单
  useEffect(() => {
    if (!showPaginationMenu) return;
    const handler = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setShowPaginationMenu(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [showPaginationMenu]);

  const liveResume = useMemo<Resume | null>(() => {
    if (!currentResume) return null;
    return { ...currentResume, sections } as Resume;
  }, [currentResume, sections]);

  // PDF预览 - 调用后端API生成真实PDF
  const handlePdfPreview = async () => {
    const html = extractPreviewHtml(paginationStrategy);
    if (!html) return;

    setIsGeneratingPdf(true);
    try {
      const pdfBlob = await exportPdf(html);
      const url = URL.createObjectURL(pdfBlob);
      window.open(url, '_blank');
      // 延迟释放URL，给浏览器时间加载
      setTimeout(() => URL.revokeObjectURL(url), 60000);
    } catch (error) {
      console.error('PDF预览失败:', error);
    } finally {
      setIsGeneratingPdf(false);
    }
  };

  if (!liveResume) return null;

  const scale = zoom / 100;

  return (
    <div
      className={`flex min-w-0 flex-[6] flex-col border-l border-border bg-background ${className ?? ''}`}
    >
      <div className="flex shrink-0 items-center justify-between border-b border-border bg-card px-4 py-2">
        <span className="text-xs font-medium text-muted-foreground">预览</span>
        <div className="flex items-center gap-2">
          {/* PDF预览按钮 + 分页方案选择 */}
          <div className="relative flex items-center" ref={menuRef}>
            <button
              type="button"
              onClick={handlePdfPreview}
              disabled={isGeneratingPdf}
              className="flex h-7 items-center gap-1 rounded-l-md border border-r-0 border-border px-2 text-xs transition-colors hover:bg-accent disabled:opacity-50"
              title="生成真实PDF预览（与导出完全一致）"
            >
              <FileDown className="h-3.5 w-3.5" />
              <span>{isGeneratingPdf ? '生成中...' : 'PDF预览'}</span>
            </button>
            <button
              type="button"
              onClick={() => setShowPaginationMenu((v) => !v)}
              className="flex h-7 items-center gap-0.5 rounded-r-md border border-border px-1.5 text-xs transition-colors hover:bg-accent"
              title="选择分页方案"
            >
              <span className="text-muted-foreground">
                {PAGINATION_OPTIONS.find((o) => o.key === paginationStrategy)?.label}
              </span>
              <ChevronDown className="h-3 w-3 text-muted-foreground" />
            </button>
            {showPaginationMenu && (
              <div className="absolute right-0 top-full z-50 mt-1 w-56 rounded-lg border border-border bg-card p-1 shadow-lg">
                {PAGINATION_OPTIONS.map(({ key, label, description }) => (
                  <button
                    key={key}
                    type="button"
                    onClick={() => {
                      setPaginationStrategy(key);
                      setShowPaginationMenu(false);
                    }}
                    className={`flex w-full flex-col rounded-md px-3 py-2 text-left transition-colors hover:bg-accent ${
                      paginationStrategy === key ? 'bg-accent' : ''
                    }`}
                  >
                    <span
                      className={`text-xs font-medium ${
                        paginationStrategy === key ? 'text-primary' : 'text-foreground'
                      }`}
                    >
                      {label}
                    </span>
                    <span className="text-[10px] text-muted-foreground">{description}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
          {/* 缩放控制 */}
          <div className="flex items-center gap-1">
            <button
              type="button"
              onClick={() => setZoom((z) => Math.max(30, z - 10))}
              disabled={zoom <= 30}
              className="flex h-7 w-7 cursor-pointer items-center justify-center rounded transition-colors hover:bg-accent disabled:opacity-40"
            >
              <ZoomOut className="h-3.5 w-3.5" />
            </button>
            <span className="w-10 text-center text-xs text-muted-foreground">{zoom}%</span>
            <button
              type="button"
              onClick={() => setZoom((z) => Math.min(150, z + 10))}
              disabled={zoom >= 150}
              className="flex h-7 w-7 cursor-pointer items-center justify-center rounded transition-colors hover:bg-accent disabled:opacity-40"
            >
              <ZoomIn className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
      </div>
      <div className="min-h-0 flex-1 overflow-auto">
        <div className="flex justify-center p-4">
          <div
            className="bg-white shadow-md"
            style={{ width: '100%', maxWidth: A4_WIDTH, zoom: scale }}
          >
            <ResumePreview resume={liveResume} />
          </div>
        </div>
      </div>
    </div>
  );
}
