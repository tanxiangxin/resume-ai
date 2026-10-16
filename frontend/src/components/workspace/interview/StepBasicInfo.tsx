interface StepBasicInfoProps {
  name: string;
  subResumeTitle?: string;
  onChange: (name: string) => void;
}

export default function StepBasicInfo({ name, subResumeTitle, onChange }: StepBasicInfoProps) {
  return (
    <div className="space-y-4">
      <div>
        <label className="text-xs text-muted-foreground mb-1.5 block">
          方案名称 <span className="text-red-400">*</span>
        </label>
        <input
          type="text"
          value={name}
          onChange={(e) => onChange(e.target.value)}
          placeholder="如：高级前端工程师面试"
          className="w-full px-3 py-2 bg-background border border-foreground/10 rounded-lg text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-teal-500/50 focus:border-teal-500/50"
          autoFocus
        />
      </div>

      {subResumeTitle && (
        <div>
          <label className="text-xs text-muted-foreground mb-1.5 block">关联子简历</label>
          <div className="px-3 py-2 bg-muted/30 border border-border rounded-lg text-foreground text-sm">
            {subResumeTitle}
          </div>
        </div>
      )}
    </div>
  );
}
