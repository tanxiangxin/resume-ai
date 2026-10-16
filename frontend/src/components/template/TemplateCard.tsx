import type { Resume } from '../../types/resume';
import ResumePreview from '../preview/ResumePreview';
import { Eye, LayoutTemplate, Loader2 } from 'lucide-react';

interface TemplateCardProps {
  templateId: string;
  templateName: string;
  resume: Resume;
  onPreview: (templateId: string) => void;
  onUse: (templateId: string) => void;
  isUsing?: boolean;
}

export default function TemplateCard({
  templateId,
  templateName,
  resume,
  onPreview,
  onUse,
  isUsing = false,
}: TemplateCardProps) {
  return (
    <div
      className="group flex flex-col rounded-2xl overflow-hidden bg-card border border-border transition-colors duration-200 hover:border-muted-foreground/30 hover:bg-muted/50"
      style={{ width: '300px' }}
    >
      <div className="px-4 py-3 text-center">
        <h3 className="text-base font-bold text-foreground tracking-wide">{templateName}</h3>
      </div>

      <div className="relative overflow-hidden rounded-xl mx-2 mb-2" style={{ height: '340px' }}>
        <div
          className="absolute origin-top"
          style={{
            left: '50%',
            top: '0',
            width: '794px',
            transform: 'translateX(-50%) scale(0.30)',
          }}
        >
          <ResumePreview resume={resume} />
        </div>
      </div>

      <div className="flex gap-2.5 px-4 pb-4">
        <button
          onClick={() => onPreview(templateId)}
          className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg cursor-pointer bg-transparent border border-muted-foreground/30 text-foreground hover:bg-muted hover:text-foreground hover:border-muted-foreground/50 transition-all text-sm"
        >
          <Eye className="w-3.5 h-3.5" />
          <span>预览</span>
        </button>
        <button
          onClick={() => onUse(templateId)}
          disabled={isUsing}
          className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg cursor-pointer bg-teal-500/20 text-primary hover:bg-teal-500/30 hover:text-primary font-medium transition-all text-sm disabled:cursor-not-allowed disabled:opacity-70"
        >
          {isUsing ? (
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
          ) : (
            <LayoutTemplate className="w-3.5 h-3.5" />
          )}
          <span>{isUsing ? '创建中...' : '使用'}</span>
        </button>
      </div>
    </div>
  );
}
