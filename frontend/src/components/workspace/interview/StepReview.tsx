import type { InterviewerProfile } from './CustomInterviewerModal';

interface DraftRound {
  tempId: string;
  name: string;
  interviewer: InterviewerProfile;
}

interface StepReviewProps {
  name: string;
  rounds: DraftRound[];
}

export default function StepReview({ name, rounds }: StepReviewProps) {
  return (
    <div className="space-y-4">
      <div className="p-3 rounded-lg border border-border bg-muted/20">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-[10px] text-muted-foreground">方案名称</span>
        </div>
        <p className="text-sm font-medium">{name}</p>
      </div>

      <div>
        <p className="text-xs text-muted-foreground mb-2">共 {rounds.length} 轮面试</p>
        <div className="space-y-2">
          {rounds.map((round, index) => (
            <div key={round.tempId} className="p-3 rounded-lg border border-border bg-card">
              <div className="flex items-center gap-2 mb-1.5">
                <span className="text-[10px] font-mono text-muted-foreground">#{index + 1}</span>
                <span className="text-xs font-medium">{round.name}</span>
              </div>
              <div className="flex items-center gap-1.5 text-[10px] text-muted-foreground">
                <span>{round.interviewer.name}</span>
                {round.interviewer.title && (
                  <>
                    <span>·</span>
                    <span>{round.interviewer.title}</span>
                  </>
                )}
              </div>
              {round.interviewer.assessmentDimensions.length > 0 && (
                <div className="flex flex-wrap gap-1 mt-2">
                  {round.interviewer.assessmentDimensions.map((dim) => (
                    <span
                      key={dim}
                      className="text-[9px] px-1.5 py-0.5 rounded bg-teal-500/10 text-primary"
                    >
                      {dim}
                    </span>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
