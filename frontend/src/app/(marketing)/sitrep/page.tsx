'use client';

import { useState, useMemo, useCallback } from 'react';
import dynamic from 'next/dynamic';
import { motion } from 'framer-motion';
import {
  Shield,
  Map,
  FileText,
  Scale,
  Search,
  Filter,
  Thermometer,
  ExternalLink,
} from 'lucide-react';
import { articles } from '@/lib/sitrep/seed-data';
import { Article, NewsCategory, CATEGORY_COLORS, CATEGORY_LABELS } from '@/lib/sitrep/types';
import { filterArticles, calculateSentimentByRegion } from '@/lib/sitrep/utils';
import ArticleCard from '@/components/sitrep/ArticleCard';
import BiasSlider from '@/components/sitrep/BiasSlider';
import BriefingModal from '@/components/sitrep/BriefingModal';
import ComparisonModal from '@/components/sitrep/ComparisonModal';

// Dynamic import for map (SSR breaks react-simple-maps)
const WorldMap = dynamic(() => import('@/components/sitrep/WorldMap'), {
  ssr: false,
  loading: () => (
    <div className="w-full h-full bg-[#0a0a0f] flex items-center justify-center">
      <div className="text-cyan-400 font-mono text-sm animate-pulse">
        LOADING GLOBAL MAP...
      </div>
    </div>
  ),
});

export default function SitrepPage() {
  // State
  const [biasValue, setBiasValue] = useState(0);
  const [selectedCategory, setSelectedCategory] = useState<NewsCategory | 'all'>('all');
  const [selectedCountry, setSelectedCountry] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [showHeatmap, setShowHeatmap] = useState(false);
  const [selectedArticles, setSelectedArticles] = useState<string[]>([]);
  const [briefingOpen, setBriefingOpen] = useState(false);
  const [comparisonOpen, setComparisonOpen] = useState(false);

  // Filtered articles
  const filteredArticles = useMemo(() => {
    const biasRange = biasValue === 0 ? 1.0 : 0.5;
    return filterArticles(articles, {
      category: selectedCategory,
      biasMin: biasValue === 0 ? -1 : biasValue - biasRange,
      biasMax: biasValue === 0 ? 1 : biasValue + biasRange,
      countryCode: selectedCountry || 'all',
      search: searchQuery,
    });
  }, [biasValue, selectedCategory, selectedCountry, searchQuery]);

  // Sentiment data for heatmap
  const sentimentData = useMemo(() => calculateSentimentByRegion(articles), []);

  // Article selection for comparison
  const handleArticleSelect = useCallback((articleId: string) => {
    setSelectedArticles((prev) => {
      if (prev.includes(articleId)) {
        return prev.filter((id) => id !== articleId);
      }
      if (prev.length >= 2) {
        return [prev[1], articleId];
      }
      return [...prev, articleId];
    });
  }, []);

  const handleCompare = useCallback(() => {
    if (selectedArticles.length === 2) {
      setComparisonOpen(true);
    }
  }, [selectedArticles]);

  const categories: (NewsCategory | 'all')[] = [
    'all',
    'conflict',
    'politics',
    'tech',
    'economy',
    'climate',
    'culture',
  ];

  return (
    <div className="min-h-screen bg-[#0a0a0f] text-white">
      {/* Header */}
      <header className="border-b border-[#2a2a3a] bg-[#0a0a0f]/95 backdrop-blur sticky top-0 z-40">
        <div className="max-w-[1800px] mx-auto px-4 py-3">
          <div className="flex items-center justify-between gap-4">
            {/* Logo */}
            <div className="flex items-center gap-3">
              <Shield className="w-6 h-6 text-cyan-400" />
              <div>
                <h1 className="text-lg font-bold tracking-wider font-mono text-white">
                  SITREP
                </h1>
                <p className="text-[10px] text-gray-500 font-mono tracking-widest">
                  GLOBAL SITUATION ROOM
                </p>
              </div>
            </div>

            {/* Search */}
            <div className="flex-1 max-w-md">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
                <input
                  type="text"
                  placeholder="Search articles, sources, countries..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-10 pr-4 py-2 bg-[#111118] border border-[#2a2a3a] rounded-lg text-sm text-gray-300 placeholder-gray-600 focus:outline-none focus:border-cyan-500/50 font-mono"
                />
              </div>
            </div>

            {/* Stats */}
            <div className="hidden md:flex items-center gap-4 text-xs font-mono text-gray-500">
              <span>
                <span className="text-cyan-400">{filteredArticles.length}</span> /{' '}
                {articles.length} ARTICLES
              </span>
              <span>
                <span className="text-cyan-400">
                  {new Set(articles.map((a) => a.countryCode)).size}
                </span>{' '}
                COUNTRIES
              </span>
              <span>
                <span className="text-cyan-400">
                  {new Set(articles.map((a) => a.source)).size}
                </span>{' '}
                SOURCES
              </span>
            </div>
          </div>

          {/* Bias slider */}
          <div className="mt-3 max-w-xl">
            <BiasSlider value={biasValue} onChange={setBiasValue} />
          </div>
        </div>
      </header>

      {/* Main content */}
      <div className="max-w-[1800px] mx-auto flex flex-col lg:flex-row" style={{ height: 'calc(100vh - 160px)' }}>
        {/* Map area */}
        <div className="flex-1 relative">
          <WorldMap
            articles={filteredArticles}
            selectedCountry={selectedCountry}
            onCountrySelect={setSelectedCountry}
            showHeatmap={showHeatmap}
            sentimentData={sentimentData}
          />
        </div>

        {/* Sidebar */}
        <div className="w-full lg:w-[420px] border-l border-[#2a2a3a] bg-[#0a0a0f] flex flex-col overflow-hidden">
          {/* Category filters */}
          <div className="p-3 border-b border-[#2a2a3a]">
            <div className="flex items-center gap-2 mb-2">
              <Filter className="w-3 h-3 text-gray-500" />
              <span className="text-[10px] font-mono text-gray-500 uppercase tracking-wider">
                Categories
              </span>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {categories.map((cat) => (
                <button
                  key={cat}
                  onClick={() => setSelectedCategory(cat)}
                  className={`text-[10px] font-mono uppercase tracking-wider px-2.5 py-1 rounded-full border transition ${
                    selectedCategory === cat
                      ? 'text-white border-cyan-500/50 bg-cyan-500/20'
                      : 'text-gray-500 border-[#2a2a3a] hover:border-gray-500'
                  }`}
                  style={
                    selectedCategory === cat && cat !== 'all'
                      ? {
                          borderColor: `${CATEGORY_COLORS[cat as NewsCategory]}80`,
                          backgroundColor: `${CATEGORY_COLORS[cat as NewsCategory]}20`,
                          color: CATEGORY_COLORS[cat as NewsCategory],
                        }
                      : undefined
                  }
                >
                  {cat === 'all' ? 'All' : CATEGORY_LABELS[cat as NewsCategory]}
                </button>
              ))}
            </div>
            {selectedCountry && (
              <button
                onClick={() => setSelectedCountry(null)}
                className="mt-2 text-[10px] font-mono text-cyan-400 hover:text-cyan-300"
              >
                Clear country filter ({selectedCountry})
              </button>
            )}
          </div>

          {/* Article feed */}
          <div className="flex-1 overflow-y-auto p-3 space-y-3">
            {filteredArticles.length === 0 ? (
              <div className="text-center py-12">
                <Map className="w-10 h-10 text-gray-600 mx-auto mb-3" />
                <p className="text-gray-500 text-sm">No articles match your filters</p>
                <button
                  onClick={() => {
                    setBiasValue(0);
                    setSelectedCategory('all');
                    setSelectedCountry(null);
                    setSearchQuery('');
                  }}
                  className="mt-3 text-xs text-cyan-400 hover:text-cyan-300"
                >
                  Reset filters
                </button>
              </div>
            ) : (
              filteredArticles.map((article) => (
                <ArticleCard
                  key={article.id}
                  article={article}
                  isSelected={selectedArticles.includes(article.id)}
                  onSelect={() => handleArticleSelect(article.id)}
                  onCompare={
                    selectedArticles.length === 2 && selectedArticles.includes(article.id)
                      ? handleCompare
                      : undefined
                  }
                />
              ))
            )}
          </div>
        </div>
      </div>

      {/* Bottom toolbar */}
      <div className="fixed bottom-0 left-0 right-0 border-t border-[#2a2a3a] bg-[#0a0a0f]/95 backdrop-blur z-30">
        <div className="max-w-[1800px] mx-auto px-4 py-2 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setBriefingOpen(true)}
              className="flex items-center gap-2 px-4 py-2 bg-[#111118] border border-[#2a2a3a] rounded-lg text-xs font-mono text-gray-400 hover:text-cyan-400 hover:border-cyan-500/50 transition"
            >
              <FileText className="w-4 h-4" />
              Briefing
            </button>
            <button
              onClick={handleCompare}
              disabled={selectedArticles.length < 2}
              className="flex items-center gap-2 px-4 py-2 bg-[#111118] border border-[#2a2a3a] rounded-lg text-xs font-mono text-gray-400 hover:text-cyan-400 hover:border-cyan-500/50 transition disabled:opacity-30 disabled:cursor-not-allowed"
            >
              <Scale className="w-4 h-4" />
              Compare {selectedArticles.length > 0 && `(${selectedArticles.length}/2)`}
            </button>
            <button
              onClick={() => setShowHeatmap(!showHeatmap)}
              className={`flex items-center gap-2 px-4 py-2 bg-[#111118] border rounded-lg text-xs font-mono transition ${
                showHeatmap
                  ? 'text-amber-400 border-amber-500/50 bg-amber-500/10'
                  : 'text-gray-400 border-[#2a2a3a] hover:text-cyan-400 hover:border-cyan-500/50'
              }`}
            >
              <Thermometer className="w-4 h-4" />
              Heatmap
            </button>
          </div>

          <div className="flex items-center gap-3">
            <a
              href="https://getbonito.com"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-2 text-xs text-gray-500 hover:text-gray-400 transition"
            >
              Powered by <span className="text-cyan-400 font-semibold">Bonito AI</span>
              <ExternalLink className="w-3 h-3" />
            </a>
          </div>
        </div>
      </div>

      {/* Modals */}
      <BriefingModal
        isOpen={briefingOpen}
        onClose={() => setBriefingOpen(false)}
        articles={filteredArticles}
      />
      <ComparisonModal
        isOpen={comparisonOpen}
        onClose={() => setComparisonOpen(false)}
        articles={articles}
        selectedArticles={selectedArticles}
      />
    </div>
  );
}
