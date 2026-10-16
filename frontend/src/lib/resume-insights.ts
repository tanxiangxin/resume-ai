import type { ResumeSection } from '../types/resume';

export interface HealthScoreResult {
  score: number;
  completionScore: number;
  balanceScore: number;
  richnessScore: number;
  visibleCount: number;
  filledCount: number;
  totalWords: number;
  stdDev: number;
}

/**
 * Extract meaningful text content from a resume section for word-counting.
 *
 * Excludes metadata fields that should NOT count toward word totals:
 * - personal_info: avatar (base64), customLinks handled separately
 * - items-based sections: id, startDate, endDate, current, url, location, technologies, gpa, level/score
 * - Unknown content types: returns '' instead of JSON.stringify (which would
 *   inflate counts with base64 avatar data or structural keys)
 */
export function getTextContent(section: ResumeSection): string {
  const content = section.content;
  if (!content) return '';

  if ('text' in content && typeof content.text === 'string') return content.text;

  if ('fullName' in content) {
    const SKIP_KEYS = new Set(['avatar']);
    const parts: string[] = [];
    for (const [key, val] of Object.entries(content as any)) {
      if (SKIP_KEYS.has(key)) continue;
      if (typeof val === 'string' && val) parts.push(val);
      if (key === 'customLinks' && Array.isArray(val)) {
        for (const link of val) {
          if (link.label && typeof link.label === 'string') parts.push(link.label);
          if (link.url && typeof link.url === 'string') parts.push(link.url);
        }
      }
    }
    return parts.join(' ');
  }

  if ('items' in content && Array.isArray(content.items)) {
    const ITEM_SKIP_KEYS = new Set([
      'id',
      'startDate',
      'endDate',
      'current',
      'url',
      'location',
      'technologies',
      'gpa',
      'level',
      'score',
      'repoUrl',
      'stars',
      'language',
    ]);
    return content.items
      .map((item: any) => {
        const parts: string[] = [];
        for (const [key, val] of Object.entries(item)) {
          if (ITEM_SKIP_KEYS.has(key)) continue;
          if (typeof val === 'string' && val) parts.push(val);
          if (Array.isArray(val)) parts.push(val.join(' '));
        }
        return parts.join(' ');
      })
      .join(' ');
  }

  if ('categories' in content && Array.isArray(content.categories)) {
    return content.categories
      .map((cat: any) => [cat.name, ...(cat.skills || [])].join(' '))
      .join(' ');
  }

  return '';
}

export function calculateHealthScore(sections: ResumeSection[]): HealthScoreResult {
  const visibleSections = sections.filter((s) => s.visible === true);

  if (visibleSections.length === 0) {
    return {
      score: 0,
      completionScore: 0,
      balanceScore: 0,
      richnessScore: 0,
      visibleCount: 0,
      filledCount: 0,
      totalWords: 0,
      stdDev: 0,
    };
  }

  const wordCounts = visibleSections.map((s) => getTextContent(s).trim().length);
  const completedCount = visibleSections.filter((s) => getTextContent(s).trim().length > 0).length;
  const completionScore = Math.min(completedCount * 8, 40);

  const avgCount = wordCounts.reduce((a, b) => a + b, 0) / wordCounts.length;
  const variance =
    wordCounts.reduce((sum, count) => sum + Math.pow(count - avgCount, 2), 0) / wordCounts.length;
  const stdDev = Math.sqrt(variance);
  const balanceScore = Math.max(0, 30 - (stdDev / 500) * 30);

  const totalWords = wordCounts.reduce((a, b) => a + b, 0);
  const richnessScore = Math.min((totalWords / 2000) * 30, 30);

  const score = Math.round(completionScore + balanceScore + richnessScore);

  return {
    score,
    completionScore,
    balanceScore,
    richnessScore,
    visibleCount: visibleSections.length,
    filledCount: completedCount,
    totalWords,
    stdDev: Math.round(stdDev),
  };
}

export function getScoreColorClass(score: number) {
  if (score >= 90)
    return {
      text: 'text-green-400',
      barFrom: 'from-green-500',
      barTo: 'to-green-400',
      hex: '#4ade80',
    };
  if (score >= 75)
    return {
      text: 'text-yellow-400',
      barFrom: 'from-yellow-500',
      barTo: 'to-yellow-400',
      hex: '#facc15',
    };
  if (score >= 60)
    return {
      text: 'text-orange-400',
      barFrom: 'from-orange-500',
      barTo: 'to-orange-400',
      hex: '#fb923c',
    };
  return {
    text: 'text-red-400',
    barFrom: 'from-red-500',
    barTo: 'to-red-400',
    hex: '#f87171',
  };
}

export function fmtDateTime(iso: string) {
  const d = new Date(iso);
  const mm = String(d.getMonth() + 1).padStart(2, '0');
  const dd = String(d.getDate()).padStart(2, '0');
  const hh = String(d.getHours()).padStart(2, '0');
  const min = String(d.getMinutes()).padStart(2, '0');
  return `${mm}-${dd} ${hh}:${min}`;
}
