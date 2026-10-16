export type InterviewStatus = 'not_started' | 'in_progress' | 'completed';

export interface InterviewCollection {
  id: string;
  name: string;
  subResumeId: string;
  status: InterviewStatus;
  metaInfo: Record<string, unknown> | null;
  createdAt: string;
  updatedAt: string;
}

export interface InterviewRound {
  id: string;
  interviewCollectionId: string;
  name: string;
  interviewerName: string;
  interviewerTitle: string;
  interviewerBio: string;
  questionStyle: string;
  assessmentDimensions: string[];
  personalityTraits: string[];
  status: InterviewStatus;
  sortOrder: number;
  metaInfo: Record<string, unknown> | null;
  createdAt: string;
  updatedAt: string;
}

export interface InterviewCollectionDetail extends InterviewCollection {
  rounds: InterviewRound[];
}

export interface CreateInterviewCollectionParams {
  name: string;
  subResumeId: string;
}

export interface CreateInterviewRoundParams {
  interviewCollectionId: string;
  name: string;
  interviewerName: string;
  interviewerTitle?: string;
  interviewerBio?: string;
  questionStyle?: string;
  assessmentDimensions?: string[];
  personalityTraits?: string[];
  sortOrder?: number;
}

export type BuiltInInterviewerType =
  | 'hr'
  | 'technical'
  | 'scenario'
  | 'project'
  | 'behavioral'
  | 'leader';

export interface BuiltInInterviewer {
  type: BuiltInInterviewerType;
  name: string;
  title: string;
  roundName: string;
  avatarText: string;
  avatarColor: string;
  bio: string;
  questionStyle: string;
  assessmentDimensions: string[];
  personalityTraits: string[];
}

export interface InterviewRoundDraft {
  name: string;
  interviewerName: string;
  interviewerTitle?: string;
  interviewerBio?: string;
  questionStyle?: string;
  assessmentDimensions?: string[];
  personalityTraits?: string[];
  interviewerType?: BuiltInInterviewerType;
}

export interface CreateInterviewCollectionWithRoundsParams {
  name: string;
  subResumeId: string;
  rounds: InterviewRoundDraft[];
}

export interface UpdateInterviewRoundParams {
  id: string;
  name?: string;
  interviewerName?: string;
  interviewerTitle?: string;
  interviewerBio?: string;
  questionStyle?: string;
  assessmentDimensions?: string[];
  personalityTraits?: string[];
  sortOrder?: number;
}

export interface UpdateRoundStatusParams {
  roundId: string;
  status: InterviewStatus;
}

export type InterviewChatAction = 'start' | 'answer' | 'skip' | 'hint';

export interface InterviewChatParams {
  roundId: string;
  action: InterviewChatAction;
  content?: string;
  model: string;
  type: string;
  apiKey: string;
  baseUrl: string;
}
