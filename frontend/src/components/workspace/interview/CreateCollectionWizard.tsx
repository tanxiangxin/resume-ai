import { useState } from 'react';
import { X, ChevronLeft, ChevronRight, Check } from 'lucide-react';
import StepBasicInfo from './StepBasicInfo';
import StepConfigureRounds from './StepConfigureRounds';
import StepReview from './StepReview';
import type { InterviewerProfile } from './CustomInterviewerModal';

interface DraftRound {
  tempId: string;
  name: string;
  interviewer: InterviewerProfile;
}

interface CreateCollectionWizardProps {
  open: boolean;
  onClose: () => void;
  subResumeId: string;
  subResumeTitle?: string;
  onSubmit: (name: string, rounds: DraftRound[]) => Promise<void>;
}

const STEPS = [{ label: '基本信息' }, { label: '配置轮次' }, { label: '确认提交' }];

export default function CreateCollectionWizard({
  open,
  onClose,
  subResumeId: _subResumeId,
  subResumeTitle,
  onSubmit,
}: CreateCollectionWizardProps) {
  const [step, setStep] = useState(0);
  const [name, setName] = useState('');
  const [rounds, setRounds] = useState<DraftRound[]>([]);
  const [loading, setLoading] = useState(false);

  if (!open) return null;

  const canProceed = (): boolean => {
    if (step === 0) return name.trim().length > 0;
    if (step === 1) return rounds.length > 0;
    return true;
  };

  const handleNext = () => {
    if (!canProceed()) return;
    if (step < STEPS.length - 1) {
      setStep(step + 1);
    }
  };

  const handlePrev = () => {
    if (step > 0) {
      setStep(step - 1);
    }
  };

  const handleSubmit = async () => {
    if (!name.trim() || rounds.length === 0) return;
    setLoading(true);
    try {
      await onSubmit(name.trim(), rounds);
      setName('');
      setRounds([]);
      setStep(0);
      onClose();
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    setName('');
    setRounds([]);
    setStep(0);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/60" onClick={handleClose} />
      <div className="relative bg-card border border-border rounded-xl w-full max-w-xl mx-4 shadow-2xl flex flex-col max-h-[90vh]">
        <div className="flex items-center justify-between p-5 border-b border-border">
          <h2 className="text-sm font-semibold">新建面试方案</h2>
          <button
            type="button"
            onClick={handleClose}
            className="p-1 rounded text-muted-foreground hover:text-foreground transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="flex items-center gap-2 px-5 py-3 border-b border-border">
          {STEPS.map((s, i) => (
            <div key={s.label} className="flex items-center gap-2 flex-1">
              <div
                className={`flex items-center justify-center w-5 h-5 rounded-full text-[10px] font-medium shrink-0 ${
                  i < step
                    ? 'bg-teal-500 text-white'
                    : i === step
                      ? 'bg-teal-500/20 text-primary ring-1 ring-teal-500/50'
                      : 'bg-muted/30 text-muted-foreground'
                }`}
              >
                {i < step ? <Check className="w-3 h-3" /> : i + 1}
              </div>
              <span
                className={`text-[10px] whitespace-nowrap ${
                  i <= step ? 'text-foreground' : 'text-muted-foreground'
                }`}
              >
                {s.label}
              </span>
              {i < STEPS.length - 1 && <div className="flex-1 h-px bg-border mx-1" />}
            </div>
          ))}
        </div>

        <div className="flex-1 overflow-y-auto p-5">
          {step === 0 && (
            <StepBasicInfo name={name} subResumeTitle={subResumeTitle} onChange={setName} />
          )}
          {step === 1 && <StepConfigureRounds rounds={rounds} onChange={setRounds} />}
          {step === 2 && <StepReview name={name} rounds={rounds} />}
        </div>

        <div className="flex items-center justify-between p-5 border-t border-border">
          <button
            type="button"
            onClick={handlePrev}
            disabled={step === 0}
            className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs text-muted-foreground hover:text-foreground hover:bg-white/5 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
          >
            <ChevronLeft className="w-3.5 h-3.5" />
            上一步
          </button>

          {step < STEPS.length - 1 ? (
            <button
              type="button"
              onClick={handleNext}
              disabled={!canProceed()}
              className="flex items-center gap-1 px-4 py-1.5 rounded-lg bg-teal-500 text-white text-xs font-medium hover:bg-teal-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              下一步
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          ) : (
            <button
              type="button"
              onClick={handleSubmit}
              disabled={loading || rounds.length === 0}
              className="flex items-center gap-1.5 px-5 py-2 rounded-lg bg-teal-500 text-white text-xs font-medium hover:bg-teal-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {loading ? '创建中...' : '确认创建'}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
