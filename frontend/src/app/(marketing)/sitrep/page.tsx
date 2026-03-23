'use client';

import { useState, useMemo, useCallback } from 'react';
import Image from 'next/image';
import { Special_Elite } from 'next/font/google';
import dynamic from 'next/dynamic';
import { motion } from 'framer-motion';
import {
  Map,
  FileText,
  Scale,
  Search,
  Filter,
  Thermometer,
  Activity,
  Bot,
  BrainCircuit,
  ServerCog,
  ShieldCheck,
  ExternalLink,
} from 'lucide-react';

const specialElite = Special_Elite({
  weight: '400',
  subsets: ['latin'],
  display: 'swap',
  variable: '--font-typewriter',
});
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

  // Static agent data for public showcase
  const staticAgents = [
    {
      id: 'watchdog',
      codename: 'WATCHDOG',
      role: 'Source Ingestion and Enrichment',
      description: 'Continuously monitors 200+ global news feeds, enriches articles with geopolitical metadata, and routes signals to the analysis pipeline.',
      metric: '14,200+ articles ingested',
      icon: ServerCog,
    },
    {
      id: 'prism',
      codename: 'PRISM',
      role: 'Bias Detection and Cross-Reference',
      description: 'Analyzes each article for political lean, cross-references claims against multiple sources, and flags narrative divergence.',
      metric: '97.2% cross-ref accuracy',
      icon: BrainCircuit,
    },
    {
      id: 'sentinel',
      codename: 'SENTINEL',
      role: 'Conflict Signal Routing',
      description: 'Detects escalation patterns, maps conflict zones in real-time, and triggers alerts when threat levels shift.',
      metric: '38 active conflict zones',
      icon: ShieldCheck,
    },
    {
      id: 'overwatch',
      codename: 'OVERWATCH',
      role: 'Orchestration and Synthesis',
      description: 'Coordinates all agents, resolves conflicting assessments, and generates the unified intelligence picture you see above.',
      metric: '4 agents coordinated',
      icon: Bot,
    },
  ];

  return (
    <div className={`min-h-screen bg-[#0a0a0f] text-white ${specialElite.variable}`} style={{ fontFamily: 'var(--font-typewriter), "Courier New", monospace' }}>
      {/* Header */}
      <header className="border-b border-[#2a2a3a] bg-[#0a0a0f]/95 backdrop-blur sticky top-0 z-40">
        <div className="max-w-[1800px] mx-auto px-4 py-3">
          <div className="flex flex-wrap items-center justify-center gap-x-4 gap-y-1 text-xs font-mono text-gray-500">
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

          {/* Bias slider */}
          <div className="mt-3 flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-center">
            <div className="flex justify-center lg:justify-start lg:w-[320px] lg:flex-none">
              <img
                src="/sitrep-logo.png"
                alt="SITREP"
                className="h-12 w-auto object-contain"
              />
            </div>
            <div className="mx-auto w-full max-w-xl lg:mx-0 lg:flex-1 lg:max-w-2xl">
              <BiasSlider value={biasValue} onChange={setBiasValue} />
            </div>
          </div>
        </div>
      </header>

      {/* Main content */}
      <div className="max-w-[1800px] mx-auto pb-20">
        <div className="flex flex-col lg:flex-row lg:h-[calc(100vh-280px)]">
          {/* Map area */}
          <div className="relative min-h-[520px] flex-1 lg:h-full">
            <WorldMap
              articles={filteredArticles}
              selectedCountry={selectedCountry}
              onCountrySelect={setSelectedCountry}
              showHeatmap={showHeatmap}
              sentimentData={sentimentData}
              selectedCategory={selectedCategory}
            />
          </div>

          {/* Sidebar */}
          <div className="w-full lg:h-full lg:w-[420px] border-l border-[#2a2a3a] bg-[#0a0a0f] flex flex-col overflow-hidden">
            {/* Category filters */}
            <div className="p-3 border-b border-[#2a2a3a]">
              <div className="flex items-center gap-2 mb-2">
                <Filter className="w-3 h-3 text-gray-500" />
                <span className="text-[10px] font-mono text-gray-500 uppercase tracking-wider">
                  Categories
                </span>
              </div>
              <div className="flex flex-wrap gap-1.5">
                {categories.map((cat) => {
                  const isConflict = cat === 'conflict';
                  const isSelected = selectedCategory === cat;
                  
                  return (
                    <motion.button
                      key={cat}
                      onClick={() => setSelectedCategory(cat)}
                      animate={isConflict && !isSelected ? {
                        boxShadow: [
                          '0 0 8px rgba(239,68,68,0.4), 0 0 16px rgba(239,68,68,0.2)',
                          '0 0 12px rgba(239,68,68,0.6), 0 0 24px rgba(239,68,68,0.3)',
                          '0 0 8px rgba(239,68,68,0.4), 0 0 16px rgba(239,68,68,0.2)'
                        ]
                      } : undefined}
                      transition={isConflict && !isSelected ? {
                        duration: 2,
                        repeat: Infinity,
                        ease: 'easeInOut'
                      } : undefined}
                      className={`relative text-[10px] font-mono uppercase tracking-wider px-2.5 py-1 rounded-full border transition ${
                        isSelected
                          ? 'text-white border-cyan-500/50 bg-cyan-500/20'
                          : isConflict
                          ? 'text-red-300 border-red-500/60 bg-red-500/15 shadow-[0_0_10px_rgba(239,68,68,0.5)]'
                          : 'text-gray-500 border-[#2a2a3a] hover:border-gray-500'
                      }`}
                      style={
                        isSelected && cat !== 'all'
                          ? {
                              borderColor: `${CATEGORY_COLORS[cat as NewsCategory]}80`,
                              backgroundColor: `${CATEGORY_COLORS[cat as NewsCategory]}20`,
                              color: CATEGORY_COLORS[cat as NewsCategory],
                            }
                          : undefined
                      }
                    >
                      {cat === 'all' ? 'All' : CATEGORY_LABELS[cat as NewsCategory]}
                      {isConflict && (
                        <motion.span 
                          className="absolute -top-1 -right-1 w-2 h-2 bg-red-500 rounded-full"
                          animate={{
                            scale: [1, 1.3, 1],
                            opacity: [1, 0.5, 1]
                          }}
                          transition={{
                            duration: 1.5,
                            repeat: Infinity,
                            ease: 'easeInOut'
                          }}
                        />
                      )}
                      {isConflict && (
                        <motion.span 
                          className="ml-1 text-[8px] text-red-300 font-bold"
                          animate={{
                            opacity: [0.7, 1, 0.7]
                          }}
                          transition={{
                            duration: 1.8,
                            repeat: Infinity,
                            ease: 'easeInOut'
                          }}
                        >
                          LIVE
                        </motion.span>
                      )}
                    </motion.button>
                  );
                })}
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

        {/* Bottom info section - Public Agentic Backend Showcase */}
        <section className="border-t border-[#2a2a3a] bg-[#0a0a0f] px-4 py-8 lg:px-6">
          {/* Summary Stats Row */}
          <div className="max-w-[1800px] mx-auto mb-8">
            <div className="grid grid-cols-3 gap-4">
              <div className="rounded-xl border border-cyan-500/20 bg-cyan-500/5 p-4 text-center">
                <div className="text-[10px] font-mono uppercase tracking-[0.2em] text-cyan-400">Active Agents</div>
                <div className="mt-1 text-2xl font-semibold text-white">4</div>
              </div>
              <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-4 text-center">
                <div className="text-[10px] font-mono uppercase tracking-[0.2em] text-emerald-400">Sources Monitored</div>
                <div className="mt-1 text-2xl font-semibold text-white">200+</div>
              </div>
              <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 p-4 text-center">
                <div className="text-[10px] font-mono uppercase tracking-[0.2em] text-amber-400">Conflict Zones Tracked</div>
                <div className="mt-1 text-2xl font-semibold text-white">38</div>
              </div>
            </div>
          </div>

          {/* Two Column Layout */}
          <div className="max-w-[1800px] mx-auto grid gap-6 lg:grid-cols-2">
            {/* Left Column: UNDER THE HOOD */}
            <div className="space-y-4">
              <div className="flex items-center gap-2">
                <Activity className="w-4 h-4 text-cyan-400" />
                <h2 className="text-sm font-mono uppercase tracking-[0.22em] text-gray-300">
                  Under The Hood
                </h2>
              </div>

              {/* Traditional News Aggregator - Muted/Strikethrough Style */}
              <div className="rounded-2xl border border-[#2a2a3a] bg-[#0d0d12] p-5 opacity-50">
                <div className="flex items-center gap-2 mb-3">
                  <span className="text-[11px] font-mono uppercase tracking-[0.18em] text-gray-500 line-through">
                    Traditional News Aggregator
                  </span>
                </div>
                <p className="text-sm leading-6 text-gray-600 line-through">
                  Static RSS feeds. Manual curation. No analysis. Just headlines.
                </p>
              </div>

              {/* SITREP: Agent-Powered Intelligence - Highlighted */}
              <div className="rounded-2xl border border-cyan-500/30 bg-[#111118] p-5 relative overflow-hidden">
                <div className="absolute top-0 right-0 w-32 h-32 bg-cyan-500/5 rounded-full blur-3xl -mr-16 -mt-16" />
                <div className="flex items-center gap-2 mb-3 relative">
                  <BrainCircuit className="w-4 h-4 text-cyan-400" />
                  <span className="text-[11px] font-mono uppercase tracking-[0.18em] text-cyan-400">
                    SITREP: Agent-Powered Intelligence
                  </span>
                </div>
                <p className="text-sm leading-6 text-gray-300 relative">
                  SITREP deploys autonomous AI agents operating in parallel. WATCHDOG monitors global feeds and enriches signals with geopolitical context. PRISM runs continuous bias detection and cross-references claims across sources. SENTINEL handles conflict signal routing and real-time map visualization. OVERWATCH orchestrates the entire operation, resolving divergent assessments and synthesizing unified intelligence. This is not aggregation — this is active analysis.
                </p>
              </div>

              {/* Bonito Callout */}
              <div className="rounded-xl border border-[#2a2a3a] bg-[#111118] p-4 flex items-start gap-3">
                <ServerCog className="w-4 h-4 text-cyan-400 mt-0.5 flex-shrink-0" />
                <p className="text-xs leading-5 text-gray-400">
                  <span className="text-cyan-400 font-mono">Built on Bonito</span> — the open infrastructure layer for agentic backends. Every article you see was processed by agents, not scripts.
                </p>
              </div>
            </div>

            {/* Right Column: AGENT ROSTER */}
            <div className="space-y-4">
              <div className="flex items-center gap-2">
                <Bot className="w-4 h-4 text-cyan-400" />
                <h2 className="text-sm font-mono uppercase tracking-[0.22em] text-gray-300">
                  Agent Roster
                </h2>
              </div>

              <div className="grid gap-3">
                {staticAgents.map((agent) => {
                  const Icon = agent.icon;

                  return (
                    <div key={agent.id} className="rounded-2xl border border-[#2a2a3a] bg-[#111118] p-4 hover:border-cyan-500/20 transition-colors">
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex gap-3">
                          <div className="mt-0.5 rounded-xl border border-cyan-500/20 bg-cyan-500/10 p-2.5">
                            <Icon className="w-4 h-4 text-cyan-400" />
                          </div>
                          <div>
                            <div className="flex items-center gap-2">
                              <span className="text-sm font-semibold text-white font-mono">{agent.codename}</span>
                              <span className="rounded-full px-2 py-0.5 text-[9px] font-mono uppercase tracking-wider border border-emerald-500/30 bg-emerald-500/10 text-emerald-300">
                                Active
                              </span>
                            </div>
                            <div className="mt-1 text-[10px] font-mono uppercase tracking-[0.12em] text-cyan-400">
                              {agent.role}
                            </div>
                            <div className="mt-2 text-xs leading-5 text-gray-400">
                              {agent.description}
                            </div>
                          </div>
                        </div>
                      </div>
                      <div className="mt-3 pt-3 border-t border-[#2a2a3a] flex items-center justify-between">
                        <span className="text-[10px] font-mono uppercase tracking-[0.16em] text-gray-500">
                          Operational Metric
                        </span>
                        <span className="text-[10px] font-mono text-cyan-400">
                          {agent.metric}
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Last Sweep Timestamp */}
              <div className="flex items-center justify-end gap-2 text-[10px] font-mono text-gray-500">
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                Last sweep: 18:00 UTC
              </div>
            </div>
          </div>
        </section>
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
            <div className="h-6 w-px bg-[#2a2a3a] mx-1" />
            <div className="relative flex items-center">
              <Search className="absolute left-3 w-4 h-4 text-gray-500" />
              <input
                type="text"
                placeholder="Search..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="h-9 w-48 rounded-lg border border-[#2a2a3a] bg-[#111118] pl-9 pr-3 text-xs text-gray-300 placeholder-gray-600 focus:outline-none focus:border-cyan-500/50 font-mono"
              />
            </div>
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
