import { Article } from './types';
import { articlesPart6 } from './seed-data-part6';

// Use only the most recent news sweep (Part 6 - March 27, 2026)
export const articles: Article[] = [...articlesPart6]
  .sort((a, b) => new Date(b.publishedAt).getTime() - new Date(a.publishedAt).getTime());

// Helper functions
export function getArticlesByCategory(category: string): Article[] {
  return articles.filter((a) => a.category === category);
}

export function getArticlesByCountry(countryCode: string): Article[] {
  return articles.filter((a) => a.countryCode === countryCode);
}

export function getBreakingNews(): Article[] {
  return articles.filter((a) => a.isBreaking);
}

export function getArticlesByBiasRange(min: number, max: number): Article[] {
  return articles.filter((a) => a.sourceBias >= min && a.sourceBias <= max);
}

export function getArticlesByTier(tier: number): Article[] {
  return articles.filter((a) => a.credibilityTier === tier);
}

export function getTranslatedArticles(): Article[] {
  return articles.filter((a) => a.originalLanguage !== undefined);
}

export default articles;
