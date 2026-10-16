import type {
  JdAnalysis,
  JdRequirement,
  SkillMatch,
  Strength,
  Suggestion,
} from '../types/workspace';

export function enrichJdAnalysis(analysis: JdAnalysis): JdAnalysis {
  const enriched: JdAnalysis = { ...analysis };

  const kwCount = Array.isArray(enriched.keywordMatches) ? enriched.keywordMatches.length : 0;
  const pmCount = Array.isArray(enriched.partialMatches) ? enriched.partialMatches.length : 0;
  const mkCount = Array.isArray(enriched.missingKeywords) ? enriched.missingKeywords.length : 0;
  if (!enriched.totalRequirements) {
    enriched.totalRequirements = kwCount + pmCount + mkCount;
  }
  if (!enriched.version) enriched.version = 1;

  if (enriched.keywordMatches) {
    enriched.keywordMatches = enriched.keywordMatches.map((km) => ({
      ...km,
      category: km.category ?? 'preferred',
      importance: km.importance ?? 3,
      matchType: km.matchType ?? 'exact',
    }));
  }

  if (!enriched.partialMatches) {
    enriched.partialMatches = [];
  }

  if (enriched.missingKeywords) {
    enriched.missingKeywords = enriched.missingKeywords.map((mk) => ({
      ...mk,
      category: mk.category ?? 'preferred',
      importance: mk.importance ?? 2,
    }));
  }

  if (!enriched.skillMatches) {
    const skills: SkillMatch[] = [];
    if (enriched.keywordMatches) {
      enriched.keywordMatches.forEach((km) => {
        if (!skills.find((s) => s.skill === km.keyword)) {
          skills.push({
            skill: km.keyword,
            matchScore: km.matchType === 'exact' ? 95 : 85,
            category: 'technical',
          });
        }
      });
    }
    enriched.skillMatches = skills;
  }

  if (!enriched.strengths) {
    const strengths: Strength[] = [];
    if (enriched.overallScore >= 80) {
      strengths.push({ description: '整体匹配度优秀', type: 'skill_match' });
    }
    if (enriched.keywordMatches && enriched.keywordMatches.length >= 3) {
      strengths.push({ description: '关键技能高度匹配', type: 'skill_match' });
    }
    enriched.strengths = strengths;
  }

  const rawRequirements: any[] =
    (enriched as any).jdRequirements || (enriched as any).jd_requirements || [];
  enriched.jdRequirements = rawRequirements.map(
    (item: any): JdRequirement => ({
      name: item.name || '',
      category: item.category || 'hard_skill',
      importance: item.importance || 'preferred',
      level: item.level ?? null,
    }),
  );

  if (enriched.suggestions && Array.isArray(enriched.suggestions)) {
    enriched.suggestions = enriched.suggestions.map(
      (s: any): Suggestion => ({
        sectionId: s.sectionId || s.section_id || '',
        current: s.current || '',
        suggested: s.suggested || '',
        priority: s.priority || 'medium',
        type: s.type || 'wording',
        rationale: s.rationale || '优化措辞以更好地匹配职位描述',
        targetDimension: s.targetDimension || 'skills',
        expectedScoreDelta: s.expectedScoreDelta || 3,
      }),
    );
  }

  return enriched;
}

export function enrichJdAnalysisList(analyses: JdAnalysis[]): JdAnalysis[] {
  return analyses.map((a, idx) =>
    enrichJdAnalysis({
      ...a,
      version: a.version || analyses.length - idx,
    }),
  );
}
