'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Scale, ArrowRight, AlertCircle } from 'lucide-react';
import { Article, NarrativeComparison } from '@/lib/sitrep/types';
import { compareNarratives } from '@/lib/sitrep/bonito';
import { getBiasLabel, getBiasColor } from '@/lib/sitrep/utils';

interface ComparisonModalProps {
  isOpen: boolean;
  onClose: () => void;
  articles: Article[];
  selectedArticles: string[];
}

export default function ComparisonModal({
  isOpen,
  onClose,
  articles,
  selectedArticles,
}: ComparisonModalProps) {
  const [comparison, setComparison] = useState<NarrativeComparison | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const article1 = articles.find((a) => a.id === selectedArticles[0]);
  const article2 = articles.find((a) => a.id === selectedArticles[1]);

  const handleCompare = async () => {
    if (!article1 || !article2) return;
    setLoading(true);
    setError(null);
    try {
      const result = await compareNarratives(article1, article2);
      setComparison(result);
    } catch (err) {
      setError('Failed to generate comparison. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50"
            onClick={onClose}
          />

          {/* Modal */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            className="fixed inset-4 md:inset-auto md:top-1/2 md:left-1/2 md:-translate-x-1/2 md:-translate-y-1/2 md:w-full md:max-w-5xl md:max-h-[85vh] bg-[#0a0a0f] border border-[#2a2a3a] rounded-lg overflow-hidden z-50 flex flex-col"
          >
            {/* Header */}
            <div className="flex items-center justify-between p-4 border-b border-[#2a2a3a] bg-[#111118]">
              <div className="flex items-center gap-3">
                <Scale className="w-5 h-5 text-cyan-400" />
                <h2 className="text-lg font-semibold text-white">Narrative Comparison</h2>
              </div>
              <button
                onClick={onClose}
                className="p-2 hover:bg-[#2a2a3a] rounded-lg transition"
              >
                <X className="w-5 h-5 text-gray-400" />
              </button>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-auto p-6">
              {/* Selected articles */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
                {article1 && (
                  <div className="bg-[#111118] border border-blue-500/30 rounded-lg p-4">
                    <div className="flex items-center gap-2 mb-2">
                      <div className="w-2 h-2 rounded-full bg-blue-500" />
                      <span className="text-xs font-mono text-blue-400">
                        {getBiasLabel(article1.sourceBias)}
                      </span>
                    </div>
                    <p className="text-sm text-gray-300 line-clamp-2">{article1.title}</p>
                    <p className="text-xs text-gray-500 mt-1">{article1.source}</p>
                  </div>
                )}
                {article2 && (
                  <div className="bg-[#111118] border border-red-500/30 rounded-lg p-4">
                    <div className="flex items-center gap-2 mb-2">
                      <div className="w-2 h-2 rounded-full bg-red-500" />
                      <span className="text-xs font-mono text-red-400">
                        {getBiasLabel(article2.sourceBias)}
                      </span>
                    </div>
                    <p className="text-sm text-gray-300 line-clamp-2">{article2.title}</p>
                    <p className="text-xs text-gray-500 mt-1">{article2.source}</p>
                  </div>
                )}
              </div>

              {!comparison && !loading && !error && (
                <div className="text-center py-8">
                  <p className="text-gray-400 mb-4">
                    Compare how different political perspectives frame the same topic
                  </p>
                  <button
                    onClick={handleCompare}
                    className="px-6 py-3 bg-cyan-500/20 text-cyan-400 border border-cyan-500/50 rounded-lg hover:bg-cyan-500/30 transition font-mono"
                  >
                    GENERATE COMPARISON
                  </button>
                </div>
              )}

              {loading && (
                <div className="text-center py-8">
                  <motion.div
                    animate={{ rotate: 360 }}
                    transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
                    className="w-10 h-10 border-2 border-cyan-500/30 border-t-cyan-400 rounded-full mx-auto mb-4"
                  />
                  <p className="text-cyan-400 font-mono animate-pulse">
                    ANALYZING NARRATIVE DIVERGENCE...
                  </p>
                </div>
              )}

              {error && (
                <div className="text-center py-8">
                  <AlertCircle className="w-10 h-10 text-red-400 mx-auto mb-4" />
                  <p className="text-red-400">{error}</p>
                  <button
                    onClick={handleCompare}
                    className="mt-4 px-4 py-2 bg-red-500/20 text-red-400 border border-red-500/50 rounded hover:bg-red-500/30 transition"
                  >
                    Retry
                  </button>
                </div>
              )}

              {comparison && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="space-y-6"
                >
                  {/* Topic */}
                  <div className="bg-[#111118] border border-[#2a2a3a] rounded-lg p-4">
                    <h4 className="text-xs font-mono text-gray-500 mb-2 uppercase tracking-wider">
                      Topic
                    </h4>
                    <p className="text-lg text-white font-medium">{comparison.topic}</p>
                  </div>

                  {/* Framing comparison */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="bg-blue-500/5 border border-blue-500/20 rounded-lg p-4">
                      <h4 className="text-xs font-mono text-blue-400 mb-3 uppercase tracking-wider">
                        Left-leaning Framing
                      </h4>
                      <p className="text-sm text-gray-300 leading-relaxed">
                        {comparison.leftFraming}
                      </p>
                    </div>
                    <div className="bg-red-500/5 border border-red-500/20 rounded-lg p-4">
                      <h4 className="text-xs font-mono text-red-400 mb-3 uppercase tracking-wider">
                        Right-leaning Framing
                      </h4>
                      <p className="text-sm text-gray-300 leading-relaxed">
                        {comparison.rightFraming}
                      </p>
                    </div>
                  </div>

                  {/* Key differences */}
                  <div className="bg-[#111118] border border-[#2a2a3a] rounded-lg p-4">
                    <h4 className="text-xs font-mono text-gray-500 mb-3 uppercase tracking-wider">
                      Key Differences
                    </h4>
                    <ul className="space-y-2">
                      {comparison.differences.map((diff, idx) => (
                        <li key={idx} className="flex items-start gap-3">
                          <ArrowRight className="w-4 h-4 text-cyan-400 mt-0.5 flex-shrink-0" />
                          <span className="text-sm text-gray-300">{diff}</span>
                        </li>
                      ))}
                    </ul>
                  </div>

                  {/* AI Analysis */}
                  <div className="bg-cyan-500/5 border border-cyan-500/20 rounded-lg p-4">
                    <h4 className="text-xs font-mono text-cyan-400 mb-3 uppercase tracking-wider">
                      AI Analysis
                    </h4>
                    <p className="text-sm text-gray-300 leading-relaxed">
                      {comparison.aiAnalysis}
                    </p>
                  </div>
                </motion.div>
              )}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
