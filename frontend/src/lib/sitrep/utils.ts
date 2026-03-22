import { Article, NewsCategory, CATEGORY_COLORS } from './types';

export function formatTimeAgo(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const seconds = Math.floor((now.getTime() - date.getTime()) / 1000);
  
  if (seconds < 60) return 'just now';
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  if (seconds < 604800) return `${Math.floor(seconds / 86400)}d ago`;
  return date.toLocaleDateString();
}

export function getCategoryColor(category: NewsCategory): string {
  return CATEGORY_COLORS[category];
}

export function getCredibilityBadgeColor(tier: number): string {
  switch (tier) {
    case 1:
      return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/50';
    case 2:
      return 'bg-gray-400/20 text-gray-300 border-gray-400/50';
    case 3:
      return 'bg-amber-600/20 text-amber-500 border-amber-600/50';
    case 4:
      return 'bg-gray-600/20 text-gray-400 border-gray-600/50';
    default:
      return 'bg-gray-600/20 text-gray-400 border-gray-600/50';
  }
}

export function getBSMeterColor(score: number | null): string {
  if (score === null) return 'bg-gray-600';
  if (score >= 60) return 'bg-green-500';
  if (score >= 30) return 'bg-amber-500';
  return 'bg-red-500';
}

export function getBSMeterLabel(score: number | null): string {
  if (score === null) return 'Not Analyzed';
  if (score >= 60) return 'Reliable';
  if (score >= 30) return 'Questionable';
  return 'High BS Risk';
}

export function getBiasLabel(bias: number): string {
  if (bias < -0.6) return 'Far Left';
  if (bias < -0.3) return 'Left';
  if (bias < -0.1) return 'Center-Left';
  if (bias <= 0.1) return 'Center';
  if (bias <= 0.3) return 'Center-Right';
  if (bias <= 0.6) return 'Right';
  return 'Far Right';
}

export function getBiasColor(bias: number): string {
  if (bias < -0.3) return 'bg-blue-500';
  if (bias < -0.1) return 'bg-blue-400';
  if (bias <= 0.1) return 'bg-gray-400';
  if (bias <= 0.3) return 'bg-red-400';
  return 'bg-red-500';
}

export function filterArticles(
  articles: Article[],
  options: {
    category?: NewsCategory | 'all';
    biasMin?: number;
    biasMax?: number;
    tier?: number | 'all';
    countryCode?: string | 'all';
    search?: string;
  }
): Article[] {
  return articles.filter((article) => {
    if (options.category && options.category !== 'all' && article.category !== options.category) {
      return false;
    }
    if (options.biasMin !== undefined && article.sourceBias < options.biasMin) {
      return false;
    }
    if (options.biasMax !== undefined && article.sourceBias > options.biasMax) {
      return false;
    }
    if (options.tier && options.tier !== 'all' && article.credibilityTier !== options.tier) {
      return false;
    }
    if (options.countryCode && options.countryCode !== 'all' && article.countryCode !== options.countryCode) {
      return false;
    }
    if (options.search) {
      const searchLower = options.search.toLowerCase();
      const matchesSearch =
        article.title.toLowerCase().includes(searchLower) ||
        article.summary.toLowerCase().includes(searchLower) ||
        article.source.toLowerCase().includes(searchLower) ||
        article.country.toLowerCase().includes(searchLower);
      if (!matchesSearch) return false;
    }
    return true;
  });
}

export function groupArticlesByCountry(articles: Article[]): Map<string, Article[]> {
  const grouped = new Map<string, Article[]>();
  articles.forEach((article) => {
    const existing = grouped.get(article.countryCode) || [];
    existing.push(article);
    grouped.set(article.countryCode, existing);
  });
  return grouped;
}

export function getUniqueCountries(articles: Article[]): { name: string; code: string; count: number }[] {
  const countryMap = new Map<string, { name: string; count: number }>();
  articles.forEach((article) => {
    const existing = countryMap.get(article.countryCode);
    if (existing) {
      existing.count++;
    } else {
      countryMap.set(article.countryCode, { name: article.country, count: 1 });
    }
  });
  return Array.from(countryMap.entries())
    .map(([code, data]) => ({ code, name: data.name, count: data.count }))
    .sort((a, b) => b.count - a.count);
}

export function calculateSentimentByRegion(articles: Article[]): Map<string, number> {
  const regionSentiment = new Map<string, { total: number; count: number }>();
  
  articles.forEach((article) => {
    // Simple sentiment based on category
    let score = 0;
    switch (article.category) {
      case 'conflict':
        score = -0.7;
        break;
      case 'economy':
        score = article.bsScore && article.bsScore > 60 ? 0.2 : -0.2;
        break;
      case 'tech':
        score = 0.3;
        break;
      case 'climate':
        score = -0.4;
        break;
      case 'politics':
        score = -0.1;
        break;
      case 'culture':
        score = 0.1;
        break;
    }
    
    const existing = regionSentiment.get(article.countryCode) || { total: 0, count: 0 };
    existing.total += score;
    existing.count++;
    regionSentiment.set(article.countryCode, existing);
  });
  
  const result = new Map<string, number>();
  regionSentiment.forEach((data, code) => {
    result.set(code, data.total / data.count);
  });
  return result;
}
