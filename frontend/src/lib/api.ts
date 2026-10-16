import axios from 'axios';
import type { Workspace, KeywordMatch, MissingKeyword, JdRequirement } from '../types/workspace';
import type { WorkTask } from '../types/work';
import type { ResumeSection } from '../types/resume';
import type {
  InterviewCollection,
  InterviewCollectionDetail,
  InterviewRound,
  CreateInterviewCollectionParams,
  CreateInterviewCollectionWithRoundsParams,
  CreateInterviewRoundParams,
  UpdateInterviewRoundParams,
  UpdateRoundStatusParams,
  BuiltInInterviewer,
  BuiltInInterviewerType,
  InterviewChatParams,
} from '../types/interview';

const api = axios.create({
  baseURL: 'http://localhost:8000',
});

export async function fetchWorkspaces(): Promise<Workspace[]> {
  const { data } = await api.get<Workspace[]>('/resume/list');
  return data;
}

export async function createWorkspace(template: string, title?: string): Promise<Workspace> {
  const { data } = await api.post<Workspace>('/resume/create', {
    title: title || '未命名工作空间',
    template,
    themeConfig: {},
    isDefault: false,
    language: 'zh',
  });
  return data;
}

export async function fetchWorkTasks(taskType?: string, status?: string): Promise<WorkTask[]> {
  const { data } = await api.get<WorkTask[]>('/work/list', {
    params: { task_type: taskType, status },
  });
  return data;
}

export type ProviderType = 'openai' | 'anthropic';

export interface ProviderConfigItem {
  baseUrl: string;
  apiKey: string;
  model: string;
}

export interface ProviderConfig {
  providers: Record<ProviderType, ProviderConfigItem>;
  active: ProviderType;
}

export async function getProviderConfig(): Promise<ProviderConfig> {
  const { data } = await api.get<ProviderConfig>('/config/provider');
  return data;
}

export async function updateProviderConfig(
  type: ProviderType,
  config: Partial<ProviderConfigItem>,
): Promise<ProviderConfig> {
  const { data } = await api.put<ProviderConfig>('/config/provider', {
    type,
    ...config,
  });
  return data;
}

export async function switchProviderConfig(active: ProviderType): Promise<ProviderConfig> {
  const { data } = await api.patch<ProviderConfig>('/config/provider/switch', {
    active,
  });
  return data;
}

export type JdProfileStatus =
  | 'pending_config'
  | 'queued'
  | 'running'
  | 'ready'
  | 'failed'
  | 'obsolete';

export interface JobDescriptionProfile {
  id: number;
  resumeId: string;
  sourceHash: string;
  schemaVersion: number;
  status: JdProfileStatus;
  profile?: unknown | null;
  errorMessage?: string | null;
  attempts: number;
  providerType?: string | null;
  model?: string | null;
  trigger?: string | null;
  createdAt?: string | null;
  updatedAt?: string | null;
}

export interface CurrentJdProfileResponse {
  resumeId: string;
  sourceHash?: string | null;
  hasJobDescription: boolean;
  profile?: JobDescriptionProfile | null;
  needsParse: boolean;
}

export async function fetchCurrentJdProfile(
  resumeId: string,
): Promise<CurrentJdProfileResponse> {
  const { data } = await api.get<CurrentJdProfileResponse>(`/jd-profile/${resumeId}/current`);
  return data;
}

export async function retryJdProfile(resumeId: string): Promise<CurrentJdProfileResponse> {
  const { data } = await api.post<CurrentJdProfileResponse>(`/jd-profile/${resumeId}/retry`);
  return data;
}

export type CoverLetterStyle = '正式' | '亲切' | '自信';
export type CoverLetterLanguage = '中文' | 'English';
export type CoverLetterLength = 'short' | 'standard';

export interface CoverLetterParams {
  style: CoverLetterStyle;
  language: CoverLetterLanguage;
  length: CoverLetterLength;
  companyName?: string;
  recipientName?: string;
  additionalInstructions?: string;
}

export interface CoverLetterBatch {
  id: string;
  resumeId: string;
  workspaceId?: string | null;
  sourceHash: string;
  resumeContentHash: string;
  profileId?: number | null;
  profileSchemaVersion: number;
  status: 'pending' | 'running' | 'success' | 'error' | 'obsolete';
  params: CoverLetterParams;
  generatedContent?: string | null;
  editedContent?: string | null;
  errorMessage?: string | null;
  createdAt?: string | null;
  updatedAt?: string | null;
}

export async function generateCoverLetter(
  resumeId: string,
  params: CoverLetterParams,
): Promise<TaskIdResponse> {
  const { data } = await api.post<TaskIdResponse>('/cover-letter', {
    resumeId,
    ...params,
  });
  return data;
}

export async function fetchCoverLetterBatches(resumeId: string): Promise<CoverLetterBatch[]> {
  const { data } = await api.get<CoverLetterBatch[]>(`/cover-letter/${resumeId}/list`);
  return data;
}

export async function updateCoverLetterBatch(
  batchId: string,
  content: string,
): Promise<CoverLetterBatch> {
  const { data } = await api.patch<CoverLetterBatch>(`/cover-letter/batch/${batchId}`, {
    content,
  });
  return data;
}

export type GreetingStyle = 'professional' | 'natural' | 'match_focused';

export interface GreetingMatchPoint {
  requirementId: string;
  evidence: string;
}

export interface GreetingVariant {
  style: GreetingStyle;
  text: string;
  matchPoints: GreetingMatchPoint[];
}

export interface GreetingBatch {
  id: string;
  resumeId: string;
  workspaceId?: string | null;
  sourceHash: string;
  resumeContentHash: string;
  schemaVersion: number;
  status: 'pending' | 'running' | 'success' | 'error' | 'obsolete';
  result?: { schemaVersion: number; variants: GreetingVariant[] } | null;
  userEdits: Record<string, string>;
  selectedStyle?: GreetingStyle | null;
  errorMessage?: string | null;
  createdAt?: string | null;
  updatedAt?: string | null;
}

export async function generateGreeting(resumeId: string): Promise<TaskIdResponse> {
  const { data } = await api.post<TaskIdResponse>('/greeting/generate', { resume_id: resumeId });
  return data;
}

export async function fetchGreetingBatches(resumeId: string): Promise<GreetingBatch[]> {
  const { data } = await api.get<GreetingBatch[]>(`/greeting/${resumeId}/list`);
  return data;
}

export async function updateGreetingBatch(
  batchId: string,
  payload: { user_edits?: Record<string, string>; selected_style?: GreetingStyle },
): Promise<GreetingBatch> {
  const { data } = await api.patch<GreetingBatch>(`/greeting/batch/${batchId}`, payload);
  return data;
}

export interface TextBlock {
  type: 'text';
  text: string;
}

export interface ThinkingBlock {
  type: 'thinking';
  thinking: string;
}

export interface ToolUseBlock {
  type: 'tool_use';
  id: string;
  name: string;
  input: Record<string, unknown>;
}

export interface ToolResultBlock {
  type: 'tool_result';
  toolUseId: string;
  content: string;
  isError: boolean;
}

export type ContentBlock = ThinkingBlock | TextBlock | ToolUseBlock | ToolResultBlock;

export interface ConversationMessage {
  id: number;
  conversationId: string;
  role: 'user' | 'assistant';
  content: ContentBlock[];
  createdAt: string | null;
}

export async function getConversationMessages(
  conversationId: string,
): Promise<ConversationMessage[]> {
  const { data } = await api.get<ConversationMessage[]>(
    `/conversation-message/list/${conversationId}`,
  );
  return data;
}

export interface CreateMessageParams {
  conversationId: string;
  userInput: string;
}

export async function createMessage(params: CreateMessageParams): Promise<ConversationMessage> {
  const { data } = await api.post<ConversationMessage>('/conversation-message/create', {
    conversationId: params.conversationId,
    userInput: params.userInput,
  });
  return data;
}

export interface ResumeAssistantParams {
  resumeId: string;
  type: 'openai' | 'anthropic';
  baseUrl: string;
  apiKey: string;
  model: string;
  input: string;
}

export interface SSEToolResultEvent {
  type: 'tool_result';
  data: {
    is_error: boolean;
    tool_use_id: string;
    content: string;
    section_content?: Record<string, unknown>;
  };
}

export type SSEEventType =
  | 'next'
  | 'thinking_start'
  | 'thinking_delta'
  | 'text_start'
  | 'text_delta'
  | 'tool_use'
  | 'tool_result'
  | 'done'
  | 'error';

export interface SSEEvent {
  type: SSEEventType;
  data: Record<string, unknown>;
}

export function streamResumeAssistant(
  params: ResumeAssistantParams,
  onEvent: (event: SSEEvent) => void,
): { eventSource: null; cleanup: () => void } {
  let aborted = false;

  const cleanup = () => {
    aborted = true;
  };

  const baseURL = api.defaults.baseURL || 'http://localhost:8000';

  fetch(`${baseURL}/resume-assistant`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      resumeId: params.resumeId,
      type: params.type,
      baseUrl: params.baseUrl,
      apiKey: params.apiKey,
      model: params.model,
      input: params.input,
    }),
  })
    .then(async (response) => {
      if (!response.ok) {
        onEvent({
          type: 'error',
          data: { message: `HTTP ${response.status}: ${response.statusText}` },
        });
        return;
      }
      if (!response.body) {
        onEvent({ type: 'error', data: { message: 'Response body is null' } });
        return;
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let currentEventType = '';

      while (true) {
        if (aborted) break;
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('event:')) {
            currentEventType = line.slice(6).trim();
          } else if (line.startsWith('data:')) {
            const data = line.slice(5).trim();
            if (currentEventType === 'done' || data === '[DONE]') {
              onEvent({ type: 'done', data: {} });
              return;
            }
            if (currentEventType && data) {
              try {
                const eventData = JSON.parse(data);
                onEvent({
                  type: currentEventType as SSEEventType,
                  data: eventData,
                });
              } catch {
                console.error('Failed to parse SSE data:', data);
              }
            }
            currentEventType = '';
          }
        }
      }
    })
    .catch((err) => {
      if (!aborted) {
        onEvent({ type: 'error', data: { message: err.message } });
      }
    });

  return { eventSource: null, cleanup };
}

export interface UploadParseParams {
  type: ProviderType;
  baseUrl: string;
  apiKey: string;
  model: string;
  template: string;
  title?: string;
}

export interface TaskIdResponse {
  taskId: string;
}

export async function uploadAndParse(
  file: File,
  params: UploadParseParams,
): Promise<TaskIdResponse> {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('type', params.type);
  formData.append('base_url', params.baseUrl);
  formData.append('api_key', params.apiKey);
  formData.append('model', params.model);
  formData.append('template', params.template);
  formData.append('title', params.title || '未命名简历');
  const { data } = await api.post<TaskIdResponse>('/parser', formData);
  return data;
}

export async function fetchResumeSections(resumeId: string): Promise<ResumeSection[]> {
  const { data } = await api.get<any[]>(`/resume-section/${resumeId}`);
  return [...data].sort((a, b) => {
    const left = a.sortOrder ?? a.sort_order ?? 0;
    const right = b.sortOrder ?? b.sort_order ?? 0;
    return left - right;
  });
}

export async function fetchResumeSectionById(sectionId: string): Promise<any> {
  const { data } = await api.get<any>(`/resume-section/one?id=${sectionId}`);
  return data;
}

export async function updateResumeSection(section: any): Promise<any> {
  const { data } = await api.put('/resume-section/update', section);
  return data;
}

export async function createResumeSection(section: any): Promise<any> {
  const { data } = await api.post('/resume-section/create', section);
  return data;
}

export async function fetchResumeDetail(resumeId: string): Promise<any> {
  const { data } = await api.get(`/resume/${resumeId}`);
  return data;
}

export async function deleteResumeSection(id: string): Promise<void> {
  await api.delete('/resume-section/delete', { params: { id } });
}

export async function updateResume(data: {
  id: string;
  title?: string;
  template?: string;
  themeConfig?: Record<string, unknown>;
  metaInfo?: Record<string, unknown>;
}): Promise<any> {
  const { data: res } = await api.put('/resume/update', data);
  return res;
}

export async function deleteWorkspace(id: string): Promise<void> {
  await api.delete('/resume/delete', { params: { id } });
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
  version?: number;
  totalRequirements?: number;
  partialMatches?: any[];
  skillMatches?: any[];
  strengths?: any[];
  jdRequirements?: JdRequirement[];
}

export async function fetchJdAnalysisList(resumeId: string): Promise<JdAnalysis[]> {
  const { data } = await api.get<JdAnalysis[]>(`/jd-analysis/list/${resumeId}`);
  return data;
}

export interface CreateSubResumeParams {
  workspaceId: string;
  jobDescription: string;
  title?: string;
  jobTitle?: string;
  template?: string;
  themeConfig?: Record<string, unknown>;
  language?: string;
}

export interface WorkspaceSummary {
  id: string;
  title: string;
  template: string;
  themeConfig: Record<string, unknown>;
  isDefault: boolean;
  language: string;
  createdAt: string;
  updatedAt: string;
  subResumeIds: string[];
}

export async function createSubResume(params: CreateSubResumeParams): Promise<WorkspaceSummary> {
  const { data } = await api.post<WorkspaceSummary>('/resume/sub/create', {
    workspaceId: params.workspaceId,
    jobDescription: params.jobDescription,
    title: params.title || '未命名简历',
    jobTitle: params.jobTitle || null,
    template: params.template || 'classic',
    themeConfig: params.themeConfig || {},
    language: params.language || 'zh',
  });
  return data;
}

export interface CreateSubResumeWithAIParams {
  workspaceId: string;
  jobDescription: string;
  jobTitle?: string;
  template?: string;
  title?: string;
  themeConfig?: Record<string, unknown>;
  language?: string;
  type: ProviderType;
  baseUrl: string;
  apiKey: string;
  model: string;
}

export async function createSubResumeWithAI(
  params: CreateSubResumeWithAIParams,
): Promise<TaskIdResponse> {
  const { data } = await api.post<TaskIdResponse>('/resume-assistant/sub-resumes', {
    workspaceId: params.workspaceId,
    jobDescription: params.jobDescription,
    title: params.title || '未命名简历',
    jobTitle: params.jobTitle || '',
    template: params.template || 'classic',
    themeConfig: params.themeConfig || {},
    language: params.language || 'zh',
    type: params.type,
    baseUrl: params.baseUrl,
    apiKey: params.apiKey,
    model: params.model,
  });
  return data;
}

export async function fetchErrorTasks(): Promise<WorkTask[]> {
  const [parseErrors, jdProfileErrors, jdErrors, greetingErrors] = await Promise.all([
    fetchWorkTasks('parse', 'error'),
    fetchWorkTasks('jd_parse', 'error'),
    fetchWorkTasks('sub_resume_generate', 'error'),
    fetchWorkTasks('greeting_generate', 'error'),
    fetchWorkTasks('cover_letter_generate', 'error'),
  ]);
  return [...parseErrors, ...jdProfileErrors, ...jdErrors, ...greetingErrors];
}

export interface RetryTaskParams {
  taskId: string;
  type: ProviderType;
  baseUrl: string;
  apiKey: string;
  model: string;
}

export async function retryTask(params: RetryTaskParams): Promise<TaskIdResponse> {
  const formData = new FormData();
  formData.append('type', params.type);
  formData.append('base_url', params.baseUrl);
  formData.append('api_key', params.apiKey);
  formData.append('model', params.model);
  const { data } = await api.post<TaskIdResponse>(`/parser/retry/${params.taskId}`, formData);
  return data;
}

export interface CreateMatchTaskParams {
  resume_id: string;
  type: ProviderType;
  base_url: string;
  api_key: string;
  model: string;
}

export async function checkRunningMatchTask(resumeId: string): Promise<TaskIdResponse | null> {
  const { data } = await api.get<WorkTask[]>('/work/list', {
    params: {
      task_type: 'jd_score',
      status: 'running',
      meta_contains: JSON.stringify({ resume_id: resumeId }),
    },
  });
  return data.length > 0 ? { taskId: data[0].id } : null;
}

export async function checkRunningInterviewSummaryTask(
  roundId: string,
): Promise<TaskIdResponse | null> {
  const { data } = await api.get<WorkTask[]>('/work/list', {
    params: {
      task_type: 'interview_summary',
      status: 'running',
      meta_contains: JSON.stringify({ round_id: roundId }),
    },
  });
  return data.length > 0 ? { taskId: data[0].id } : null;
}

export async function checkRunningCollectionSummaryTask(
  collectionId: string,
): Promise<TaskIdResponse | null> {
  const { data } = await api.get<WorkTask[]>('/work/list', {
    params: {
      task_type: 'collection_summary',
      meta_contains: JSON.stringify({ collection_id: collectionId }),
    },
  });
  return data.length > 0 ? { taskId: data[0].id } : null;
}

export async function createMatchTask(params: CreateMatchTaskParams): Promise<TaskIdResponse> {
  const { data } = await api.post<TaskIdResponse>('/jd-analysis/match', {
    resume_id: params.resume_id,
    type: params.type,
    base_url: params.base_url,
    api_key: params.api_key,
    model: params.model,
  });
  return data;
}

export async function exportPdf(html: string, timeoutMs: number = 30000): Promise<Blob> {
  const { data } = await api.post('/export/pdf', { html, timeoutMs }, { responseType: 'blob' });
  return data;
}

export async function exportTxt(resumeId: string): Promise<Blob> {
  const { data } = await api.get(`/export/txt/${resumeId}`, {
    responseType: 'blob',
  });
  return data;
}

export async function exportJson(resumeId: string): Promise<Blob> {
  const { data } = await api.get(`/export/json/${resumeId}`, {
    responseType: 'blob',
  });
  return data;
}

export async function createInterviewCollection(
  params: CreateInterviewCollectionParams,
): Promise<InterviewCollection> {
  const { data } = await api.post<InterviewCollection>('/interview/collection', params);
  return data;
}

export async function listInterviewCollections(
  subResumeId: string,
): Promise<InterviewCollectionDetail[]> {
  const { data } = await api.get<InterviewCollectionDetail[]>(
    `/interview/collection/list/${subResumeId}`,
  );
  return data;
}

export async function getInterviewCollection(id: string): Promise<InterviewRound[]> {
  const { data } = await api.get<InterviewRound[]>(`/interview/collection/${id}`);
  return data;
}

export async function deleteInterviewCollection(id: string): Promise<void> {
  await api.delete('/interview/collection/delete', { params: { id } });
}

export async function createInterviewCollectionWithRounds(
  params: CreateInterviewCollectionWithRoundsParams,
): Promise<InterviewCollectionDetail> {
  const { data } = await api.post<InterviewCollectionDetail>(
    '/interview/collection/with-rounds',
    params,
  );
  return data;
}

export async function createInterviewRound(
  params: CreateInterviewRoundParams,
): Promise<InterviewRound> {
  const { data } = await api.post<InterviewRound>('/interview/round', params);
  return data;
}

export async function updateInterviewRound(
  data: UpdateInterviewRoundParams,
): Promise<InterviewRound> {
  const { data: res } = await api.put<InterviewRound>('/interview/round/update', data);
  return res;
}

export async function updateInterviewRoundStatus(
  params: UpdateRoundStatusParams,
): Promise<InterviewRound> {
  const { data } = await api.put<InterviewRound>('/interview/round/status', params);
  return data;
}

export async function deleteInterviewRound(id: string): Promise<void> {
  await api.delete('/interview/round/delete', { params: { id } });
}

export interface RegenerateSummaryResponse {
  taskId: string;
}

export interface RegenerateSummaryParams {
  roundId: string;
  type: string;
  apiKey: string;
  baseUrl?: string;
  model: string;
}

export async function regenerateRoundSummary(
  params: RegenerateSummaryParams,
): Promise<RegenerateSummaryResponse> {
  const { roundId, type, apiKey, baseUrl, model } = params;
  const { data } = await api.post<RegenerateSummaryResponse>(
    `/interview/round/${roundId}/regenerate-summary`,
    { type, apiKey, baseUrl, model },
  );
  return data;
}

export interface RegenerateCollectionSummaryParams {
  collectionId: string;
  type: string;
  apiKey: string;
  baseUrl?: string;
  model: string;
}

export async function regenerateCollectionSummary(
  params: RegenerateCollectionSummaryParams,
): Promise<RegenerateSummaryResponse> {
  const { collectionId, type, apiKey, baseUrl, model } = params;
  const { data } = await api.post<RegenerateSummaryResponse>(
    `/interview/collection/${collectionId}/regenerate-summary`,
    { type, apiKey, baseUrl, model },
  );
  return data;
}

export async function fetchBuiltInInterviewers(): Promise<BuiltInInterviewer[]> {
  const { data } = await api.get<Array<Record<string, unknown>>>(
    '/interview/built-in-interviewers',
  );
  return data.map((item) => ({
    type: item.type as BuiltInInterviewerType,
    name: item.name as string,
    title: item.title as string,
    roundName: (item.round_name ?? item.roundName) as string,
    avatarText: (item.avatar_text ?? item.avatarText) as string,
    avatarColor: (item.avatar_color ?? item.avatarColor) as string,
    bio: item.bio as string,
    questionStyle: (item.question_style ?? item.questionStyle) as string,
    assessmentDimensions: (item.assessment_dimensions ?? item.assessmentDimensions) as string[],
    personalityTraits: (item.personality_traits ?? item.personalityTraits) as string[],
  }));
}

export function streamInterviewChat(
  params: InterviewChatParams,
  onEvent: (event: SSEEvent) => void,
): { cleanup: () => void } {
  let aborted = false;

  const cleanup = () => {
    aborted = true;
  };

  const baseURL = api.defaults.baseURL || 'http://localhost:8000';

  fetch(`${baseURL}/interview/round/${params.roundId}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      action: params.action,
      content: params.content || '',
      model: params.model,
      type: params.type,
      apiKey: params.apiKey,
      baseUrl: params.baseUrl,
    }),
  })
    .then(async (response) => {
      if (!response.ok) {
        let errorMsg = `HTTP ${response.status}`;
        try {
          const errBody = await response.json();
          errorMsg = errBody.detail || errorMsg;
        } catch {
          void 0;
        }
        onEvent({ type: 'error', data: { message: errorMsg } });
        return;
      }
      if (!response.body) {
        onEvent({ type: 'error', data: { message: 'Response body is null' } });
        return;
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let currentEventType = '';

      while (true) {
        if (aborted) break;
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('event:')) {
            currentEventType = line.slice(6).trim();
          } else if (line.startsWith('data:')) {
            const data = line.slice(5).trim();
            if (currentEventType && data) {
              try {
                const eventData = JSON.parse(data);
                onEvent({
                  type: currentEventType as SSEEventType,
                  data: eventData,
                });
              } catch {
                console.error('Failed to parse SSE data:', data);
              }
            }
            currentEventType = '';
          }
        }
      }
    })
    .catch((err) => {
      if (!aborted) {
        onEvent({ type: 'error', data: { message: err.message } });
      }
    });

  return { cleanup };
}
