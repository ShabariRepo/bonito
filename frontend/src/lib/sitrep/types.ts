export type NewsCategory = 'conflict' | 'politics' | 'tech' | 'economy' | 'culture' | 'climate';

export type CredibilityTier = 1 | 2 | 3 | 4;

export interface Article {
  id: string;
  title: string;
  originalTitle?: string; // For translated articles
  summary: string;
  source: string;
  sourceReliability: number; // 1-5
  sourceBias: number; // -1 to 1 (left to right)
  category: NewsCategory;
  country: string;
  countryCode: string;
  lat: number;
  lng: number;
  publishedAt: string;
  url: string;
  bsScore: number | null; // 0-100
  biasAnalysis: string | null;
  credibilityTier: CredibilityTier;
  isBreaking?: boolean;
  originalLanguage?: string; // ISO 639-1 code (ja, de, fr, etc.)
}

// Alias for backward compatibility
export type NewsArticle = Article;

export interface BiasAnalysisResult {
  score: number; // -1 to 1
  analysis: string;
  confidence: number;
}

export interface FactCheckResult {
  score: number; // 0-100
  reasoning: string;
  claims: Array<{
    claim: string;
    verdict: 'true' | 'false' | 'misleading' | 'unverified';
    evidence: string;
  }>;
}

export interface BriefingResult {
  title: string;
  classification: 'UNCLASSIFIED' | 'CONFIDENTIAL' | 'SECRET';
  timestamp: string;
  summary: string;
  keyDevelopments: string[];
  riskAssessment: string;
}

export interface NarrativeComparison {
  topic: string;
  leftFraming: string;
  rightFraming: string;
  differences: string[];
  aiAnalysis: string;
}

export interface TranslationResult {
  translatedText: string;
  detectedLanguage?: string;
  confidence: number;
  model: string;
}

export interface NarrativeCluster {
  id: string;
  title: string;
  summary: string;
  category: NewsCategory;
  articles: Article[];
  timeline: Array<{
    date: string;
    event: string;
  }>;
}

export interface BriefingSection {
  title: string;
  content: string;
  priority: 'high' | 'medium' | 'low';
}

export interface SituationBriefing {
  generatedAt: string;
  summary: string;
  sections: BriefingSection[];
  topStories: Article[];
}

export interface ComparisonAnalysis {
  topic: string;
  leftSource: Article;
  rightSource: Article;
  analysis: string;
  framingDifferences: string[];
  keyDivergences: string[];
  consensusAreas: string[];
}

export interface MapMarker {
  id: string;
  lat: number;
  lng: number;
  category: NewsCategory;
  count: number;
  articles: Article[];
}

export const CATEGORY_COLORS: Record<NewsCategory, string> = {
  conflict: '#ef4444', // red-500
  politics: '#f59e0b', // amber-500
  tech: '#06b6d4', // cyan-500
  economy: '#22c55e', // green-500
  culture: '#a855f7', // purple-500
  climate: '#14b8a6', // teal-500
};

export const CATEGORY_LABELS: Record<NewsCategory, string> = {
  conflict: 'Conflict',
  politics: 'Politics',
  tech: 'Technology',
  economy: 'Economy',
  culture: 'Culture',
  climate: 'Climate',
};

export const CREDIBILITY_TIER_NAMES: Record<number, string> = {
  1: 'Tier 1 - Premium',
  2: 'Tier 2 - Standard',
  3: 'Tier 3 - Digital',
  4: 'Tier 4 - Opinion',
};

export const CREDIBILITY_TIER_COLORS: Record<number, string> = {
  1: '#fbbf24', // gold
  2: '#9ca3af', // silver
  3: '#b45309', // bronze
  4: '#6b7280', // grey
};

export const categoryColors: Record<NewsCategory, string> = {
  conflict: '#ff3333',
  politics: '#ffaa00',
  tech: '#00d4ff',
  economy: '#00ff88',
  culture: '#b347d9',
  climate: '#22c55e',
};

export const categoryLabels: Record<NewsCategory, string> = {
  conflict: 'Conflict/Crisis',
  politics: 'Politics',
  tech: 'Technology',
  economy: 'Economy',
  culture: 'Culture',
  climate: 'Climate',
};

export const credibilityLabels: Record<CredibilityTier, { label: string; color: string }> = {
  1: { label: 'Tier 1', color: '#ffd700' },
  2: { label: 'Tier 2', color: '#c0c0c0' },
  3: { label: 'Tier 3', color: '#cd7f32' },
  4: { label: 'Tier 4', color: '#6b7280' },
};

export const biasLabels: Record<string, { label: string; color: string }> = {
  'far-left': { label: 'Far Left', color: '#3b82f6' },
  'left': { label: 'Left', color: '#60a5fa' },
  'center-left': { label: 'Center Left', color: '#93c5fd' },
  'center': { label: 'Center', color: '#9ca3af' },
  'center-right': { label: 'Center Right', color: '#fca5a5' },
  'right': { label: 'Right', color: '#f87171' },
  'far-right': { label: 'Far Right', color: '#ef4444' },
};

export const LANGUAGE_NAMES: Record<string, string> = {
  ja: 'Japanese',
  de: 'German',
  fr: 'French',
  pt: 'Portuguese',
  ar: 'Arabic',
  zh: 'Chinese',
  es: 'Spanish',
  ko: 'Korean',
  ru: 'Russian',
  hi: 'Hindi',
  it: 'Italian',
  fi: 'Finnish',
  da: 'Danish',
};

export const LANGUAGE_FLAGS: Record<string, string> = {
  ja: '🇯🇵',
  de: '🇩🇪',
  fr: '🇫🇷',
  pt: '🇧🇷',
  ar: '🇸🇦',
  zh: '🇨🇳',
  es: '🇪🇸',
  ko: '🇰🇷',
  ru: '🇷🇺',
  hi: '🇮🇳',
  it: '🇮🇹',
  fi: '🇫🇮',
  da: '🇩🇰',
};

export function getBiasCategory(bias: number): string {
  if (bias <= -0.7) return 'far-left';
  if (bias <= -0.3) return 'left';
  if (bias <= -0.1) return 'center-left';
  if (bias <= 0.1) return 'center';
  if (bias <= 0.3) return 'center-right';
  if (bias <= 0.7) return 'right';
  return 'far-right';
}

export function getBiasColor(bias: number): string {
  return biasLabels[getBiasCategory(bias)]?.color || '#9ca3af';
}

export function getBsScoreColor(score: number): string {
  if (score >= 80) return '#00ff88';
  if (score >= 60) return '#22c55e';
  if (score >= 40) return '#ffaa00';
  if (score >= 20) return '#f97316';
  return '#ff3333';
}

export function getBsScoreLabel(score: number): string {
  if (score >= 80) return 'Reliable';
  if (score >= 60) return 'Mostly Reliable';
  if (score >= 40) return 'Mixed';
  if (score >= 20) return 'Mostly Unreliable';
  return 'Unreliable';
}
