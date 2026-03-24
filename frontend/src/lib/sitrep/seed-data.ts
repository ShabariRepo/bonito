import { Article } from './types';
import { articles as articlesPart1 } from './seed-data-part1';
import { articlesPart2 } from './seed-data-part2';
import { articlesPart3 } from './seed-data-part3';
import { articlesPart4 } from './seed-data-part4';
import { articlesPart5 } from './seed-data-part5';
import { articlesPart6 } from './seed-data-part6';

// Combine all seed data and filter out articles older than 4 days
const FOUR_DAYS_MS = 4 * 24 * 60 * 60 * 1000;

export const articles: Article[] = [
  ...articlesPart1,
  ...articlesPart2,
  ...articlesPart3,
  ...articlesPart4,
  ...articlesPart5,
  ...articlesPart6,
].filter((a) => new Date().getTime() - new Date(a.publishedAt).getTime() <= FOUR_DAYS_MS)
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
