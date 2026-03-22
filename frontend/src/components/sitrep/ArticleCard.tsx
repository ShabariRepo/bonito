'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown, ExternalLink, AlertCircle, HelpCircle, Languages, Globe } from 'lucide-react';
import { Article, LANGUAGE_FLAGS, LANGUAGE_NAMES } from '@/lib/sitrep/types';
import {
  formatTimeAgo,
  getCategoryColor,
  getCredibilityBadgeColor,
  getBSMeterColor,
  getBSMeterLabel,
  getBiasLabel,
  getBiasColor,
} from '@/lib/sitrep/utils';
import { analyzeBias, factCheck, translateArticle } from '@/lib/sitrep/bonito';

interface ArticleCardProps {
  article: Article;
  isSelected: boolean;
  onSelect: () => void;
  onCompare?: () => void;
}

export default function ArticleCard({
  article,
  isSelected,
  onSelect,
  onCompare,
}: ArticleCardProps) {
  const [expanded, setExpanded] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [bsScore, setBsScore] = useState<number | null>(article.bsScore);
  const [biasAnalysis, setBiasAnalysis] = useState<string | null>(article.biasAnalysis);
  const [error, setError] = useState<string | null>(null);
  const [showOriginal, setShowOriginal] = useState(false);
  const [translating, setTranslating] = useState(false);
  const [translationInfo, setTranslationInfo] = useState<string | null>(null);

  const isTranslated = article.originalLanguage !== undefined;
  const languageFlag = isTranslated ? LANGUAGE_FLAGS[article.originalLanguage!] : null;
  const languageName = isTranslated ? LANGUAGE_NAMES[article.originalLanguage!] : null;

  const handleAnalyze = async () => {
    setAnalyzing(true);
    setError(null);
    try {
      const [biasResult, factResult] = await Promise.all([
        analyzeBias(article.summary),
        factCheck(article.summary),
      ]);
      setBsScore(factResult.score);
      setBiasAnalysis(biasResult.analysis);
    } catch (err) {
      setError('Analysis failed. Please try again.');
    } finally {
      setAnalyzing(false);
    }
  };

  const handleTranslate = async () => {
    if (!isTranslated) return;
    setTranslating(true);
    try {
      const result = await translateArticle(article.summary, article.originalLanguage!);
      setTranslationInfo(`Translated by Bonito AI (${result.model}) with ${(result.confidence * 100).toFixed(1)}% confidence`);
    } catch (err) {
      setTranslationInfo('Translation powered by Bonito AI');
    } finally {
      setTranslating(false);
    }
  };

  const categoryColor = getCategoryColor(article.category);
  const displayTitle = showOriginal && article.originalTitle ? article.originalTitle : article.title;

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className={`border rounded-lg overflow-hidden transition-all ${
        isSelected
          ? 'border-cyan-500/50 bg-cyan-950/20'
          : 'border-[#2a2a3a] bg-[#111118] hover:border-[#3a3a4a]'
      }`}
    >
      {/* Header */}
      <div
        className="p-4 cursor-pointer"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            {/* Meta row */}
            <div className="flex items-center gap-2 mb-2 flex-wrap">
              {/* Category indicator */}
              <span
                className="text-[10px] font-mono uppercase tracking-wider px-2 py-0.5 rounded"
                style={{
                  backgroundColor: `${categoryColor}20`,
                  color: categoryColor,
                  border: `1px solid ${categoryColor}40`,
                }}
              >
                {article.category}
              </span>
              
              {/* Breaking badge */}
              {article.isBreaking && (
                <span className="text-[10px] font-mono uppercase tracking-wider px-2 py-0.5 rounded bg-red-500/20 text-red-400 border border-red-500/40 animate-pulse">
                  BREAKING
                </span>
              )}
              
              {/* Credibility tier */}
              <span
                className={`text-[10px] font-mono uppercase tracking-wider px-2 py-0.5 rounded border ${getCredibilityBadgeColor(
                  article.credibilityTier
                )}`}
              >
                Tier {article.credibilityTier}
              </span>
              
              {/* Translation badge */}
              {isTranslated && (
                <span 
                  className="text-[10px] font-mono uppercase tracking-wider px-2 py-0.5 rounded bg-purple-500/20 text-purple-400 border border-purple-500/40 flex items-center gap-1"
                  title={`Translated from ${languageName}`}
                >
                  <Languages className="w-3 h-3" />
                  {languageFlag} AI Translated
                </span>
              )}
              
              {/* Time */}
              <span className="text-[10px] text-gray-500 font-mono">
                {formatTimeAgo(article.publishedAt)}
              </span>
            </div>
            
            {/* Title */}
            <h3 className="text-sm font-medium text-gray-100 leading-snug line-clamp-2">
              {displayTitle}
            </h3>
            
            {/* Source and bias */}
            <div className="flex items-center gap-3 mt-2">
              <span className="text-xs text-gray-400">{article.source}</span>
              <div className="flex items-center gap-1">
                <div
                  className={`w-2 h-2 rounded-full ${getBiasColor(article.sourceBias)}`}
                />
                <span className="text-[10px] text-gray-500">
                  {getBiasLabel(article.sourceBias)}
                </span>
              </div>
            </div>
          </div>
          
          {/* Expand icon */}
          <motion.div
            animate={{ rotate: expanded ? 180 : 0 }}
            transition={{ duration: 0.2 }}
          >
            <ChevronDown className="w-4 h-4 text-gray-500" />
          </motion.div>
        </div>
      </div>

      {/* Expanded content */}
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="border-t border-[#2a2a3a]"
          >
            <div className="p-4 space-y-4">
              {/* Translation info bar */}
              {isTranslated && (
                <div className="bg-purple-500/5 border border-purple-500/20 rounded-lg p-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Globe className="w-4 h-4 text-purple-400" />
                      <span className="text-xs text-purple-300">
                        {languageFlag} Translated from {languageName}
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      {article.originalTitle && (
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setShowOriginal(!showOriginal);
                          }}
                          className="text-[10px] px-2 py-1 bg-purple-500/20 text-purple-400 border border-purple-500/40 rounded hover:bg-purple-500/30 transition"
                        >
                          {showOriginal ? 'Show English' : 'Show Original'}
                        </button>
                      )}
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleTranslate();
                        }}
                        disabled={translating}
                        className="text-[10px] px-2 py-1 bg-[#1a1a24] text-purple-400 border border-purple-500/40 rounded hover:bg-purple-500/20 transition disabled:opacity-50"
                      >
                        {translating ? '...' : 'Retranslate'}
                      </button>
                    </div>
                  </div>
                  {translationInfo && (
                    <p className="text-[10px] text-purple-400/60 mt-2 font-mono">
                      {translationInfo}
                    </p>
                  )}
                </div>
              )}

              {/* Summary */}
              <p className="text-sm text-gray-300 leading-relaxed">
                {article.summary}
              </p>

              {/* BS Meter */}
              <div className="bg-[#0a0a0f] rounded-lg p-3">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono text-gray-400">BS METER</span>
                    {bsScore === null ? (
                      <span className="text-xs text-gray-500">Not analyzed</span>
                    ) : (
                      <span
                        className={`text-xs font-mono ${
                          bsScore >= 60
                            ? 'text-green-400'
                            : bsScore >= 30
                            ? 'text-amber-400'
                            : 'text-red-400'
                        }`}
                      >
                        {bsScore}/100 - {getBSMeterLabel(bsScore)}
                      </span>
                    )}
                  </div>
                  {bsScore === null && !analyzing && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleAnalyze();
                      }}
                      className="text-xs px-3 py-1 bg-cyan-500/20 text-cyan-400 border border-cyan-500/40 rounded hover:bg-cyan-500/30 transition"
                    >
                      Analyze
                    </button>
                  )}
                  {analyzing && (
                    <span className="text-xs text-gray-500 animate-pulse">
                      Analyzing...
                    </span>
                  )}
                </div>
                
                {/* BS Meter bar */}
                <div className="h-2 bg-[#1a1a24] rounded-full overflow-hidden">
                  {bsScore !== null ? (
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${bsScore}%` }}
                      transition={{ duration: 0.5 }}
                      className={`h-full ${getBSMeterColor(bsScore)}`}
                    />
                  ) : (
                    <div className="h-full bg-gray-600/30" />
                  )}
                </div>
                
                {/* Bias analysis */}
                {biasAnalysis && (
                  <div className="mt-3 pt-3 border-t border-[#2a2a3a]">
                    <div className="flex items-start gap-2">
                      <HelpCircle className="w-4 h-4 text-cyan-400 mt-0.5 flex-shrink-0" />
                      <p className="text-xs text-gray-400 leading-relaxed">
                        {biasAnalysis}
                      </p>
                    </div>
                  </div>
                )}
                
                {error && (
                  <div className="mt-2 text-xs text-red-400 flex items-center gap-1">
                    <AlertCircle className="w-3 h-3" />
                    {error}
                  </div>
                )}
              </div>

              {/* Actions */}
              <div className="flex items-center justify-between pt-2">
                <div className="flex items-center gap-2">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onSelect();
                    }}
                    className={`text-xs px-3 py-1.5 rounded border transition ${
                      isSelected
                        ? 'bg-cyan-500/20 text-cyan-400 border-cyan-500/50'
                        : 'bg-[#1a1a24] text-gray-400 border-[#2a2a3a] hover:border-gray-500'
                    }`}
                  >
                    {isSelected ? 'Selected' : 'Select for Compare'}
                  </button>
                  
                  {onCompare && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onCompare();
                      }}
                      className="text-xs px-3 py-1.5 rounded border bg-[#1a1a24] text-gray-400 border-[#2a2a3a] hover:border-gray-500 transition"
                    >
                      Compare
                    </button>
                  )}
                </div>
                
                <a
                  href={article.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  onClick={(e) => e.stopPropagation()}
                  className="flex items-center gap-1 text-xs text-cyan-400 hover:text-cyan-300 transition"
                >
                  Read Original
                  <ExternalLink className="w-3 h-3" />
                </a>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
