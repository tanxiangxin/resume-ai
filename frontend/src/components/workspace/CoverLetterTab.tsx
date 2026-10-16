import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  AlertCircle,
  Check,
  Clock3,
  Copy,
  Download,
  FileText,
  Loader2,
  Pencil,
  RefreshCw,
  Sparkles,
} from 'lucide-react';
import { toast } from 'sonner';
import type {
  CoverLetterBatch,
  CoverLetterLanguage,
  CoverLetterLength,
  CoverLetterStyle,
  CurrentJdProfileResponse,
} from '../../lib/api';
import {
  fetchCoverLetterBatches,
  fetchCurrentJdProfile,
  generateCoverLetter,
  retryJdProfile,
  updateCoverLetterBatch,
} from '../../lib/api';
import { addNotificationTask, markUnread } from '../../lib/notification';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../ui/select';

interface CoverLetterTabProps {
  resumeId: string;
  workspaceId: string;
  jobTitle?: string;
}

const styles: Array<{ value: CoverLetterStyle; label: string; description: string }> = [
  { value: '正式', label: '正式', description: '专业严谨' },
  { value: '亲切', label: '亲切', description: '自然友好' },
  { value: '自信', label: '自信', description: '突出优势' },
];

function errorMessage(error: unknown, fallback: string): string {
  if (error instanceof Error) return error.message;
  if (typeof error === 'object' && error !== null && 'response' in error) {
    const response = error.response;
    if (typeof response === 'object' && response !== null && 'data' in response) {
      const data = response.data;
      if (typeof data === 'object' && data !== null && 'detail' in data && typeof data.detail === 'string') {
        return data.detail;
      }
    }
  }
  return fallback;
}

export default function CoverLetterTab({ resumeId, workspaceId, jobTitle }: CoverLetterTabProps) {
  const [batches, setBatches] = useState<CoverLetterBatch[]>([]);
  const [profile, setProfile] = useState<CurrentJdProfileResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [editing, setEditing] = useState(false);
  const [content, setContent] = useState('');
  const [copied, setCopied] = useState(false);
  const [style, setStyle] = useState<CoverLetterStyle>('正式');
  const [language, setLanguage] = useState<CoverLetterLanguage>('中文');
  const [length, setLength] = useState<CoverLetterLength>('standard');
  const [companyName, setCompanyName] = useState('');
  const [recipientName, setRecipientName] = useState('');
  const [additionalInstructions, setAdditionalInstructions] = useState('');

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const [nextBatches, nextProfile] = await Promise.all([
        fetchCoverLetterBatches(resumeId),
        fetchCurrentJdProfile(resumeId),
      ]);
      setBatches(nextBatches);
      setProfile(nextProfile);
      const latest = nextBatches[0];
      if (latest) {
        setContent(latest.editedContent || latest.generatedContent || '');
        if (latest.params) {
          setStyle(latest.params.style);
          setLanguage(latest.params.language);
          setLength(latest.params.length);
          setCompanyName(latest.params.companyName || '');
          setRecipientName(latest.params.recipientName || '');
          setAdditionalInstructions(latest.params.additionalInstructions || '');
        }
      }
    } catch (error: unknown) {
      toast.error(errorMessage(error, '加载求职信失败'));
    } finally {
      setLoading(false);
    }
  }, [resumeId]);

  useEffect(() => { void refresh(); }, [refresh]);

  useEffect(() => {
    const handler = (event: Event) => {
      const detail = (event as CustomEvent).detail;
      if (detail?.taskType === 'cover_letter_generate') void refresh();
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
    const timer = window.setTimeout(() => { void refresh(); }, 2500);
    return () => window.clearTimeout(timer);
  }, [profile?.profile?.status, refresh]);

  const latest = batches[0];
  const activeBatch = batches.some((batch) => batch.status === 'pending' || batch.status === 'running');
  const profileReady = profile?.profile?.status === 'ready';
  const hasContent = Boolean(content.trim());

  const handleGenerate = async () => {
    if (!profile?.hasJobDescription) {
      toast.error('请先在“元数据”页签填写当前子简历的 JD');
      return;
    }
    try {
      setGenerating(true);
      const { taskId } = await generateCoverLetter(resumeId, {
        style,
        language,
        length,
        companyName: companyName.trim() || undefined,
        recipientName: recipientName.trim() || undefined,
        additionalInstructions: additionalInstructions.trim() || undefined,
      });
      markUnread();
      addNotificationTask({
        id: taskId,
        taskType: 'cover_letter_generate',
        status: 'running',
        workspaceId,
        metaInfo: { title: jobTitle || '求职信', resumeId, workspaceId },
        errorMessage: null,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      });
      toast.success(profileReady ? '求职信生成任务已启动' : '已提交，等待 JD Profile 解析完成');
      await refresh();
    } catch (error: unknown) {
      toast.error(errorMessage(error, '生成求职信失败'));
    } finally {
      setGenerating(false);
    }
  };

  const handleRetryProfile = async () => {
    try {
      setProfile(await retryJdProfile(resumeId));
      toast.success('JD Profile 解析已触发');
    } catch (error: unknown) {
      toast.error(errorMessage(error, '重试 JD Profile 失败'));
    }
  };

  const saveContent = async () => {
    if (!latest || !content.trim()) return;
    try {
      await updateCoverLetterBatch(latest.id, content);
      setEditing(false);
      await refresh();
      toast.success('求职信已保存');
    } catch (error: unknown) {
      toast.error(errorMessage(error, '保存求职信失败'));
    }
  };

  const copyContent = async () => {
    await navigator.clipboard.writeText(content);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1600);
  };

  const downloadContent = () => {
    const blob = new Blob([content.trim()], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `求职信_${new Date().toISOString().slice(0, 10)}.txt`;
    anchor.click();
    URL.revokeObjectURL(url);
  };

  const statusText = useMemo(() => {
    if (!profile?.hasJobDescription) return '请先填写 JD';
    if (profileReady) return 'JD Profile 已就绪';
    if (profile?.profile?.status === 'failed') return 'JD Profile 解析失败，请先重试';
    if (profile?.profile?.status === 'pending_config') return '请先配置 AI 提供商';
    return 'JD Profile 解析中，生成任务会自动等待';
  }, [profile, profileReady]);

  if (loading && !latest) {
    return <div className="flex h-full items-center justify-center text-sm text-muted-foreground">加载中...</div>;
  }

  return (
    <div className="flex h-full min-h-0 w-full flex-col gap-4">
      <div className="flex shrink-0 items-start justify-between gap-4 border-b border-border pb-4">
        <div>
          <h2 className="flex items-center gap-2 text-lg font-semibold text-foreground">
            <FileText className="h-5 w-5 text-primary" /> 求职信
          </h2>
          <p className="mt-1 text-xs text-muted-foreground">
            基于当前子简历、原始 JD 和结构化 JD Profile 生成。
          </p>
        </div>
        <button
          type="button"
          onClick={handleGenerate}
          disabled={generating || activeBatch || !profile?.hasJobDescription}
          className="flex items-center gap-2 rounded-lg bg-primary px-3 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {generating || activeBatch ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
          {activeBatch ? '等待生成中' : '生成求职信'}
        </button>
      </div>

      <div className="flex min-h-0 flex-1 gap-4 overflow-y-auto pr-1">
        <div className="w-[300px] shrink-0 space-y-3">
          <div className="rounded-xl border border-border bg-card p-4">
            <div className="mb-3 flex items-center justify-between">
              <span className="text-sm font-medium text-foreground">生成设置</span>
              <span className="text-xs text-muted-foreground">{jobTitle || '当前岗位'}</span>
            </div>
            <label className="mb-1 block text-xs text-muted-foreground">风格</label>
            <div className="mb-3 grid grid-cols-3 gap-1">
              {styles.map((item) => (
                <button key={item.value} type="button" onClick={() => setStyle(item.value)} className={`rounded-lg border px-2 py-2 text-xs transition-colors ${style === item.value ? 'border-primary bg-primary/10 text-primary ring-1 ring-primary/20' : 'border-border text-muted-foreground hover:border-primary/40 hover:bg-muted'}`}>
                  <span className="block font-medium">{item.label}</span>
                  <span className={`mt-0.5 block text-[10px] ${style === item.value ? 'text-primary/80' : 'text-muted-foreground/70'}`}>{item.description}</span>
                </button>
              ))}
            </div>
            <label className="mb-1 block text-xs text-muted-foreground">语言</label>
            <Select value={language} onValueChange={(value) => setLanguage(value as CoverLetterLanguage)}>
              <SelectTrigger className="mb-3 h-9 bg-background text-sm">
                <SelectValue placeholder="选择语言" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="中文">中文</SelectItem>
                <SelectItem value="English">English</SelectItem>
              </SelectContent>
            </Select>
            <label className="mb-1 block text-xs text-muted-foreground">长度</label>
            <Select value={length} onValueChange={(value) => setLength(value as CoverLetterLength)}>
              <SelectTrigger className="mb-3 h-9 bg-background text-sm">
                <SelectValue placeholder="选择长度" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="short">短版 · 约 250-400 字</SelectItem>
                <SelectItem value="standard">标准版 · 约 450-700 字</SelectItem>
              </SelectContent>
            </Select>
            <input value={companyName} onChange={(event) => setCompanyName(event.target.value)} placeholder="公司名称（选填）" className="mb-2 w-full rounded-md border border-input bg-background px-2 py-2 text-sm" />
            <input value={recipientName} onChange={(event) => setRecipientName(event.target.value)} placeholder="收件人（选填）" className="mb-2 w-full rounded-md border border-input bg-background px-2 py-2 text-sm" />
            <textarea value={additionalInstructions} onChange={(event) => setAdditionalInstructions(event.target.value)} placeholder="补充要求（选填）" className="min-h-20 w-full resize-y rounded-md border border-input bg-background px-2 py-2 text-sm" />
          </div>

          <div className={`flex items-start gap-2 rounded-xl border p-3 text-xs ${profileReady ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300' : 'border-blue-500/30 bg-blue-500/10 text-blue-700 dark:text-blue-300'}`}>
            {profileReady ? <Check className="mt-0.5 h-4 w-4 shrink-0" /> : <Clock3 className="mt-0.5 h-4 w-4 shrink-0" />}
            <span>{statusText}</span>
            {!profileReady && <div className="ml-auto flex shrink-0 items-center gap-1"><button type="button" onClick={() => void refresh()} className="rounded p-1 hover:bg-blue-500/10" aria-label="刷新 Profile 状态"><RefreshCw className="h-3.5 w-3.5" /></button>{(profile?.profile?.status === 'failed' || profile?.profile?.status === 'obsolete') && <button type="button" onClick={() => void handleRetryProfile()} className="rounded px-1.5 py-1 text-[11px] hover:bg-blue-500/10">重试</button>}</div>}
          </div>
          {!profile?.hasJobDescription && <div className="flex items-start gap-2 rounded-xl border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-amber-700 dark:text-amber-300"><AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />请在元数据页签填写当前子简历的 JD。</div>}
        </div>

        <div className="min-w-0 flex-1 space-y-3">
          {latest?.status === 'error' && <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-700 dark:text-red-300">{latest.errorMessage || '求职信生成失败，请稍后重试。'}</div>}
          {latest?.status === 'obsolete' && <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-4 text-sm text-amber-700 dark:text-amber-300">当前求职信对应的 JD 或简历内容已变化，请重新生成。</div>}
          {hasContent && latest && latest.status === 'success' && (
            <div className="rounded-xl border border-border bg-card p-5">
              <div className="mb-3 flex items-center justify-between gap-3">
                <span className="text-sm font-medium text-foreground">最新求职信</span>
                <div className="flex items-center gap-2">
                  {editing ? <button type="button" onClick={() => void saveContent()} className="flex items-center gap-1 rounded-md bg-primary px-2.5 py-1.5 text-xs text-primary-foreground"><Check className="h-3.5 w-3.5" />保存</button> : <button type="button" onClick={() => setEditing(true)} className="flex items-center gap-1 rounded-md border border-border px-2.5 py-1.5 text-xs text-muted-foreground hover:bg-muted"><Pencil className="h-3.5 w-3.5" />编辑</button>}
                  <button type="button" onClick={() => void copyContent()} className="flex items-center gap-1 rounded-md border border-border px-2.5 py-1.5 text-xs text-muted-foreground hover:bg-muted"><Copy className="h-3.5 w-3.5" />{copied ? '已复制' : '复制'}</button>
                  <button type="button" onClick={downloadContent} className="flex items-center gap-1 rounded-md border border-border px-2.5 py-1.5 text-xs text-muted-foreground hover:bg-muted"><Download className="h-3.5 w-3.5" />下载</button>
                </div>
              </div>
              <textarea value={content} readOnly={!editing} onChange={(event) => setContent(event.target.value)} className={`min-h-[430px] w-full resize-y rounded-lg text-sm leading-7 text-foreground outline-none ${editing ? 'border border-primary/40 bg-background px-4 py-3 focus:border-primary focus:ring-2 focus:ring-primary/20' : 'border-0 bg-transparent p-0'}`} />
            </div>
          )}
          {!hasContent && !activeBatch && <div className="flex min-h-[300px] flex-col items-center justify-center rounded-xl border border-dashed border-border text-center text-muted-foreground"><FileText className="mb-3 h-10 w-10 opacity-30" /><p className="text-sm">还没有求职信</p><p className="mt-1 text-xs">配置参数后点击“生成求职信”</p></div>}
          {batches.length > 1 && <details className="rounded-xl border border-border bg-card p-4"><summary className="cursor-pointer text-sm font-medium text-muted-foreground">历史生成记录（{batches.length - 1}）</summary><div className="mt-3 space-y-3">{batches.slice(1).map((batch) => <details key={batch.id} className="rounded-lg border border-border p-3"><summary className="cursor-pointer text-xs text-muted-foreground">{new Date(batch.createdAt || '').toLocaleString()} · {batch.status === 'success' ? '已完成' : batch.status === 'obsolete' ? '已过期' : batch.status}</summary><p className="mt-3 whitespace-pre-wrap text-sm leading-7 text-foreground">{batch.editedContent || batch.generatedContent || batch.errorMessage || '暂无内容'}</p></details>)}</div></details>}
        </div>
      </div>
    </div>
  );
}
