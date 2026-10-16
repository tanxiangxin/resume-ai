export interface JdRequirement {
  name: string;
  category:
    | 'hard_skill'
    | 'soft_skill'
    | 'tool'
    | 'domain_knowledge'
    | 'certification'
    | 'education'
    | 'experience'
    | 'language';
  importance: 'mandatory' | 'preferred' | 'bonus';
  level?: string | null;
}

export interface KeywordMatch {
  keyword: string;
  category: 'required' | 'preferred' | 'bonus';
  importance: number;
  matchType: 'exact' | 'synonym' | 'contextual';
  evidence?: string;
}

export interface PartialMatch {
  keyword: string;
  resumeLevel: string;
  jobLevel: string;
  gapDescription: string;
}

export interface MissingKeyword {
  keyword: string;
  category: 'required' | 'preferred' | 'bonus';
  importance: number;
  suggestion?: string;
}

export interface SkillMatch {
  skill: string;
  matchScore: number;
  category: 'technical' | 'domain' | 'tool' | 'soft_skill' | 'certification';
}

export interface Strength {
  description: string;
  type:
    | 'skill_match'
    | 'experience_match'
    | 'project_relevance'
    | 'certification'
    | 'education_match'
    | 'unique_advantage';
}

export interface Suggestion {
  sectionId: string;
  current: string;
  suggested: string;
  priority: 'high' | 'medium' | 'low';
  type: 'content_gap' | 'wording' | 'keyword_add' | 'format' | 'structure';
  rationale: string;
  targetDimension?: 'skills' | 'experience' | 'education';
  expectedScoreDelta?: number;
}

export interface JdAnalysis {
  id: number;
  resumeId: string;
  jobDescription: string;
  overallScore: number;
  atsScore: number;
  summary: string;
  keywordMatches: KeywordMatch[];
  missingKeywords: MissingKeyword[];
  suggestions: any[];
  createdAt: string;
  // v4 extended fields (may come from backend or be enriched client-side)
  version?: number;
  totalRequirements?: number;
  partialMatches?: PartialMatch[];
  skillMatches?: SkillMatch[];
  strengths?: Strength[];
  jdRequirements?: JdRequirement[];
}

export interface SubResume {
  id: string;
  title: string;
  jobTitle?: string;
  jobDescription?: string;
  matchScore?: number;
  latestAnalysis?: JdAnalysis;
  createdAt: string;
  updatedAt: string;
}

export interface Workspace {
  id: string;
  workspaceId: string | null;
  title: string;
  template: string;
  themeConfig: Record<string, unknown>;
  isDefault: boolean;
  language: string;
  shareToken: string | null;
  isPublic: boolean;
  sharePassword: string | null;
  viewCount: number;
  subResumeIds: string[];
  createdAt: string;
  updatedAt: string;
}
