import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Eye, LayoutTemplate, Loader2, X } from 'lucide-react';
import { toast } from 'sonner';
import TemplateCard from '../components/template/TemplateCard';
import ResumePreview from '../components/preview/ResumePreview';
import { mockResume } from '../data/mockResume';
import { templateLabelsMap, TEMPLATE_ORDER } from '../lib/template-labels';
import { createWorkspace } from '../lib/api';

export default function TemplateGallery() {
  const navigate = useNavigate();
  const [previewTemplate, setPreviewTemplate] = useState<string | null>(null);
  const [usingTemplateId, setUsingTemplateId] = useState<string | null>(null);

  const handleUse = async (templateId: string) => {
    if (usingTemplateId) return;

    setUsingTemplateId(templateId);
    try {
      const workspace = await createWorkspace(templateId);
      toast.success(`已使用「${templateLabelsMap[templateId] || templateId}」模板创建简历`);
      navigate(`/workspace/${workspace.id}/template/edit`);
    } catch (err: any) {
      toast.error(err?.message || '创建简历失败');
    } finally {
      setUsingTemplateId(null);
    }
  };

  return (
    <div className="flex flex-col h-full">
      <div className="shrink-0 mb-8 rounded-2xl border border-border bg-card p-6">
        <p className="mb-3 text-xs font-medium tracking-widest text-primary">THE TEMPLATE COLLECTION</p>
        <h1 className="m-0 text-3xl font-bold text-foreground">找到属于你的表达方式</h1>
        <p className="text-sm text-muted-foreground mt-3">从简洁到创意，选一个适合你的模板，把精力留给真正重要的经历。</p>
      </div>

      <div className="flex-1 overflow-y-auto min-h-0">
        <div className="flex justify-center">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
            {TEMPLATE_ORDER.map((id) => {
              const label = templateLabelsMap[id] || id;
              const previewResume = { ...mockResume, template: id };

              return (
                <TemplateCard
                  key={id}
                  templateId={id}
                  templateName={label}
                  resume={previewResume}
                  onPreview={setPreviewTemplate}
                  onUse={handleUse}
                  isUsing={usingTemplateId === id}
                />
              );
            })}
          </div>
        </div>
      </div>

      {previewTemplate && (
        <PreviewModal
          templateId={previewTemplate}
          onClose={() => setPreviewTemplate(null)}
          onUse={handleUse}
          isUsing={usingTemplateId === previewTemplate}
        />
      )}
    </div>
  );
}

function PreviewModal({
  templateId,
  onClose,
  onUse,
  isUsing,
}: {
  templateId: string;
  onClose: () => void;
  onUse: (id: string) => void;
  isUsing: boolean;
}) {
  const previewResume = { ...mockResume, template: templateId };
  const templateName = templateLabelsMap[templateId] || templateId;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="relative w-full max-w-4xl h-[90vh] flex flex-col bg-background rounded-xl border border-border overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-4 py-3 border-b border-border">
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 text-sm font-semibold text-foreground">
              <Eye className="h-4 w-4 text-muted-foreground" />
              <span>预览</span>
              <span className="text-muted-foreground font-normal">{templateName}</span>
            </div>
            <button
              onClick={() => onUse(templateId)}
              disabled={isUsing}
              className="flex items-center gap-1 rounded-md p-1.5 text-sm font-medium text-primary transition-colors hover:bg-teal-500/10 hover:text-primary disabled:cursor-not-allowed disabled:opacity-70"
            >
              {isUsing ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <LayoutTemplate className="h-4 w-4" />
              )}
              <span>{isUsing ? '创建中...' : '使用此模板'}</span>
            </button>
          </div>
          <button
            onClick={onClose}
            className="rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="flex-1 overflow-auto bg-card p-8">
          <div className="flex justify-center">
            <div className="w-[595px] border border-foreground/10 rounded-lg overflow-hidden">
              <ResumePreview resume={previewResume} />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
