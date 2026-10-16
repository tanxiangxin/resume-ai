import { useCallback, useEffect, useState } from 'react';
import { AlertCircle, Check, Clipboard, Copy, Clock3, Loader2, Pencil, RefreshCw, Sparkles, X } from 'lucide-react';
import { toast } from 'sonner';
import type { CurrentJdProfileResponse, GreetingBatch, GreetingStyle, GreetingVariant } from '../../lib/api';
import { fetchCurrentJdProfile, fetchGreetingBatches, generateGreeting, updateGreetingBatch } from '../../lib/api';
import { addNotificationTask, markUnread } from '../../lib/notification';

interface GreetingTabProps {
  resumeId: string;
  workspaceId: string;
  jobTitle?: string;
}

const styleLabels: Record<GreetingStyle, string> = {
  professional: '稳重专业',
  natural: '自然真诚',
  match_focused: '突出匹配',
};

export default function GreetingTab({ resumeId, workspaceId, jobTitle }: GreetingTabProps) {
  const [batches, setBatches] = useState<GreetingBatch[]>([]);
  const [profile, setProfile] = useState<CurrentJdProfileResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [editingStyle, setEditingStyle] = useState<GreetingStyle | null>(null);
  const [editing, setEditing] = useState<Record<string, string>>({});
  const [copied, setCopied] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const [nextBatches, nextProfile] = await Promise.all([
        fetchGreetingBatches(resumeId),
        fetchCurrentJdProfile(resumeId),
      ]);
      setBatches(nextBatches);
      setProfile(nextProfile);
      const latest = nextBatches.find((batch) => batch.status === 'success');
      if (latest) setEditing(latest.userEdits || {});
    } catch (error: any) {
      toast.error(error?.message || '加载招呼语失败');
    } finally {
      setLoading(false);
    }
  }, [resumeId]);

  useEffect(() => { refresh(); }, [refresh]);

  useEffect(() => {
    const handler = (event: Event) => {
      const detail = (event as CustomEvent).detail;
      if (detail?.taskType === 'greeting_generate') refresh();
    };
    window.addEventListener('global-sse-complete', handler);
    window.addEventListener('global-sse-error', handler);
    return () => {
      window.removeEventListener('global-sse-complete', handler);
      window.removeEventListener('global-sse-error', handler);
    };
  }, [refresh]);

  useEffect(() => {
    const status = profile?.profile?.status;
    if (status !== 'queued' && status !== 'running') return;
    const timer = window.setTimeout(async () => {
      try { setProfile(await fetchCurrentJdProfile(resumeId)); } catch {}
    }, 2500);
    return () => window.clearTimeout(timer);
  }, [profile?.profile?.status, resumeId]);

  const latestBatch = batches[0];
  const variants = latestBatch?.result?.variants || [];
  const profileReady = profile?.profile?.status === 'ready';
  const isWaiting = batches.some((batch) => batch.status === 'pending' || batch.status === 'running');

  const handleGenerate = async () => {
    if (!profile?.hasJobDescription) {
      toast.error('请先为当前子简历填写 JD');
      return;
    }
    try {
      const { taskId } = await generateGreeting(resumeId);
      setGenerating(true);
      markUnread();
      addNotificationTask({
        id: taskId,
        taskType: 'greeting_generate',
        status: 'running',
        workspaceId,
        metaInfo: { title: jobTitle || 'Boss 招呼语', resumeId, workspaceId },
        errorMessage: null,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      });
      await refresh();
      toast.success('招呼语生成任务已启动');
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || error?.message || '生成招呼语失败');
    } finally {
      setGenerating(false);
    }
  };

  const saveEdit = async (batch: GreetingBatch) => {
    try { await updateGreetingBatch(batch.id, { user_edits: { ...batch.userEdits, ...editing } }); }
    catch (error: any) { toast.error(error?.message || '保存编辑失败'); }
  };

  const cancelEdit = (variant: GreetingVariant) => {
    if (!latestBatch) return;
    setEditing((current) => ({
      ...current,
      [variant.style]: latestBatch.userEdits[variant.style] || variant.text,
    }));
    setEditingStyle(null);
  };

  const handleCopy = async (variant: GreetingVariant, batch: GreetingBatch, isHistory = false) => {
    const text = isHistory
      ? batch.userEdits[variant.style] || variant.text
      : editing[variant.style] || variant.text;
    await navigator.clipboard.writeText(text);
    setCopied(variant.style);
    if (!isHistory) {
      await updateGreetingBatch(batch.id, {
        user_edits: { ...batch.userEdits, ...editing },
        selected_style: variant.style,
      });
    }
    window.setTimeout(() => setCopied(null), 1600);
  };

  if (loading && !latestBatch) {
    return <div className="flex h-full items-center justify-center text-sm text-muted-foreground">加载中...</div>;
  }

  return (
    <div className="flex h-full min-h-0 w-full flex-col gap-3">
      <div className="flex shrink-0 items-start justify-between gap-4 border-b border-border bg-background pb-4 pt-1">
        <div>
          <h2 className="flex items-center gap-2 text-lg font-semibold text-foreground"><Sparkles className="h-5 w-5 text-primary" />Boss 招呼语</h2>
          <p className="mt-1 text-xs text-muted-foreground">基于当前 JD Profile 和子简历内容生成，所有候选都只使用已有经历。</p>
        </div>
        <div className="flex items-center gap-2">
          <button type="button" onClick={handleGenerate} disabled={generating || isWaiting || !profile?.hasJobDescription} className="flex items-center gap-2 rounded-lg bg-primary px-3 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-50">
            {generating || isWaiting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
            {isWaiting ? '等待生成中' : '生成招呼语'}
          </button>
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto pr-1">
      {!profile?.hasJobDescription && <div className="flex items-center gap-2 rounded-lg border border-amber-500/30 bg-amber-500/10 p-4 text-sm text-amber-700 dark:text-amber-300"><AlertCircle className="h-4 w-4 shrink-0" />请先在“元数据”页签填写当前子简历的 JD。</div>}
      {profile?.hasJobDescription && !profileReady && <div className="flex items-center justify-between rounded-lg border border-blue-500/30 bg-blue-500/10 p-4 text-sm text-blue-700 dark:text-blue-300"><span className="flex items-center gap-2"><Clock3 className="h-4 w-4" />JD Profile {profile?.profile?.status === 'failed' ? '解析失败' : '正在解析'}，生成时会自动等待。</span><button type="button" onClick={refresh} className="rounded-md p-1.5 hover:bg-blue-500/10" aria-label="刷新状态"><RefreshCw className="h-4 w-4" /></button></div>}
      {latestBatch?.status === 'error' && <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-700 dark:text-red-300">{latestBatch.errorMessage || '招呼语生成失败，请稍后重试。'}</div>}

      {variants.length > 0 && latestBatch && <div className="space-y-3">
        {variants.map((variant) => {
          const value = editing[variant.style] ?? variant.text;
          const isEditing = editingStyle === variant.style;
          return <div key={variant.style} className={`border p-4 transition-colors ${isEditing ? 'border-primary/70 bg-primary/[0.04] ring-1 ring-primary/20' : latestBatch.status === 'obsolete' ? 'border-amber-500/30 opacity-70' : 'border-border'}`}>
            <div className="mb-2 flex items-center justify-between gap-3"><span className={`text-sm font-medium ${isEditing ? 'text-primary' : 'text-foreground'}`}>{styleLabels[variant.style]}</span><div className="flex items-center gap-2"><button type="button" onClick={() => handleCopy(variant, latestBatch)} className="flex items-center gap-1.5 rounded-md border border-border px-2.5 py-1.5 text-xs text-muted-foreground hover:bg-muted hover:text-foreground">{copied === variant.style ? <Check className="h-3.5 w-3.5 text-emerald-500" /> : <Copy className="h-3.5 w-3.5" />}{copied === variant.style ? '已复制' : '复制'}</button>{latestBatch.status === 'success' && (isEditing ? <><button type="button" onClick={() => cancelEdit(variant)} className="flex items-center gap-1.5 rounded-md border border-border px-2.5 py-1.5 text-xs text-muted-foreground hover:bg-muted hover:text-foreground"><X className="h-3.5 w-3.5" />取消</button><button type="button" onClick={async () => { await saveEdit(latestBatch); setEditingStyle(null); }} className="flex items-center gap-1.5 rounded-md bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground shadow-sm hover:bg-primary/90"><Check className="h-3.5 w-3.5" />保存修改</button></> : <button type="button" onClick={() => setEditingStyle(variant.style)} className="flex items-center gap-1.5 rounded-md border border-border px-2.5 py-1.5 text-xs text-muted-foreground hover:bg-muted hover:text-foreground"><Pencil className="h-3.5 w-3.5" />编辑</button>)}</div></div>
            <textarea value={value} readOnly={!isEditing} onChange={(event) => setEditing((current) => ({ ...current, [variant.style]: event.target.value }))} className={`min-h-[74px] w-full resize-y text-sm leading-7 text-foreground outline-none ${isEditing ? 'rounded-md border border-primary/40 bg-background px-3 py-2 shadow-sm focus:border-primary focus:ring-2 focus:ring-primary/20' : 'border-0 bg-transparent p-0 cursor-default'}`} />
            <div className="mt-3 flex flex-wrap gap-2">{variant.matchPoints.map((point) => <span key={`${point.requirementId}-${point.evidence}`} className="inline-flex items-center gap-1 rounded-md bg-muted px-2 py-1 text-[11px] text-muted-foreground"><Clipboard className="h-3 w-3" />{point.evidence}</span>)}</div>
          </div>;
        })}
      </div>}

      {batches.length > 1 && <details className="border-t border-border pt-4"><summary className="cursor-pointer text-sm font-medium text-muted-foreground">历史生成批次（{batches.length - 1}）</summary><div className="mt-3 space-y-3">{batches.slice(1).map((batch) => <details key={batch.id} className="border border-border p-3"><summary className="cursor-pointer text-xs text-muted-foreground">{new Date(batch.createdAt || '').toLocaleString()} · {batch.status === 'obsolete' ? '已过期' : batch.status === 'success' ? '已完成' : batch.status}</summary><div className="mt-3 space-y-3">{(batch.result?.variants || []).map((variant) => <div key={variant.style} className="border border-border/70 p-3"><div className="mb-2 flex items-center justify-between gap-2"><span className="text-xs font-medium text-foreground">{styleLabels[variant.style]}</span><button type="button" onClick={() => handleCopy(variant, batch, true)} className="flex items-center gap-1 rounded-md border border-border px-2 py-1 text-[11px] text-muted-foreground hover:bg-muted hover:text-foreground"><Copy className="h-3 w-3" />复制</button></div><p className="whitespace-pre-wrap text-sm leading-7 text-foreground">{batch.userEdits[variant.style] || variant.text}</p><div className="mt-2 flex flex-wrap gap-2">{variant.matchPoints.map((point) => <span key={`${point.requirementId}-${point.evidence}`} className="rounded-md bg-muted px-2 py-1 text-[11px] text-muted-foreground">{point.evidence}</span>)}</div></div>)}</div></details>)}</div></details>}
      </div>
    </div>
  );
}
