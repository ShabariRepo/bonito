'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, FileText, Clock, Shield, AlertTriangle } from 'lucide-react';
import { Article, BriefingResult } from '@/lib/sitrep/types';
import { generateBriefing } from '@/lib/sitrep/bonito';

interface BriefingModalProps {
  isOpen: boolean;
  onClose: () => void;
  articles: Article[];
}

export default function BriefingModal({ isOpen, onClose, articles }: BriefingModalProps) {
  const [briefing, setBriefing] = useState<BriefingResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleGenerate = async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await generateBriefing(articles);
      setBriefing(result);
    } catch (err) {
      setError('Failed to generate briefing. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString('en-US', {
      weekday: 'short',
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      timeZoneName: 'short',
    });
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
            className="fixed inset-4 md:inset-auto md:top-1/2 md:left-1/2 md:-translate-x-1/2 md:-translate-y-1/2 md:w-full md:max-w-4xl md:max-h-[85vh] bg-[#0a0a0f] border border-[#2a2a3a] rounded-lg overflow-hidden z-50 flex flex-col"
          >
            {/* Header */}
            <div className="flex items-center justify-between p-4 border-b border-[#2a2a3a] bg-[#111118]">
              <div className="flex items-center gap-3">
                <Shield className="w-5 h-5 text-cyan-400" />
                <h2 className="text-lg font-semibold text-white">AI Situation Briefing</h2>
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
              {!briefing && !loading && !error && (
                <div className="text-center py-12">
                  <FileText className="w-16 h-16 text-cyan-400/30 mx-auto mb-4" />
                  <h3 className="text-xl font-medium text-white mb-2">
                    Generate Intelligence Briefing
                  </h3>
                  <p className="text-gray-400 max-w-md mx-auto mb-6">
                    Our AI will analyze the current news landscape and generate a classified-style
                    situation report covering key global developments, risk assessments, and strategic
                    implications.
                  </p>
                  <div className="text-sm text-gray-500 mb-6">
                    Based on {articles.length} articles from {new Set(articles.map(a => a.countryCode)).size} countries
                  </div>
                  <button
                    onClick={handleGenerate}
                    className="px-6 py-3 bg-cyan-500/20 text-cyan-400 border border-cyan-500/50 rounded-lg hover:bg-cyan-500/30 transition font-mono"
                  >
                    GENERATE BRIEFING
                  </button>
                </div>
              )}

              {loading && (
                <div className="text-center py-12">
                  <motion.div
                    animate={{ rotate: 360 }}
                    transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
                    className="w-12 h-12 border-2 border-cyan-500/30 border-t-cyan-400 rounded-full mx-auto mb-4"
                  />
                  <p className="text-cyan-400 font-mono animate-pulse">
                    ANALYZING GLOBAL INTELLIGENCE...
                  </p>
                  <p className="text-gray-500 text-sm mt-2">
                    Processing {articles.length} sources
                  </p>
                </div>
              )}

              {error && (
                <div className="text-center py-12">
                  <AlertTriangle className="w-12 h-12 text-red-400 mx-auto mb-4" />
                  <p className="text-red-400">{error}</p>
                  <button
                    onClick={handleGenerate}
                    className="mt-4 px-4 py-2 bg-red-500/20 text-red-400 border border-red-500/50 rounded hover:bg-red-500/30 transition"
                  >
                    Retry
                  </button>
                </div>
              )}

              {briefing && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="space-y-6"
                >
                  {/* Classification header */}
                  <div className="border-2 border-amber-500/50 bg-amber-500/10 p-4 rounded">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-amber-400 font-mono text-sm tracking-widest">
                        {briefing.classification}
                      </span>
                      <span className="text-amber-400/60 font-mono text-xs">
                        SITREP-{new Date().toISOString().split('T')[0].replace(/-/g, '')}
                      </span>
                    </div>
                    <h3 className="text-xl font-bold text-white">{briefing.title}</h3>
                    <div className="flex items-center gap-2 mt-2 text-amber-400/60 text-xs font-mono">
                      <Clock className="w-3 h-3" />
                      {formatDate(briefing.timestamp)}
                    </div>
                  </div>

                  {/* Summary */}
                  <div className="bg-[#111118] border border-[#2a2a3a] rounded-lg p-4">
                    <h4 className="text-xs font-mono text-gray-500 mb-2 uppercase tracking-wider">
                      Executive Summary
                    </h4>
                    <p className="text-gray-300 leading-relaxed">{briefing.summary}</p>
                  </div>

                  {/* Key Developments */}
                  <div className="bg-[#111118] border border-[#2a2a3a] rounded-lg p-4">
                    <h4 className="text-xs font-mono text-gray-500 mb-3 uppercase tracking-wider">
                      Key Developments
                    </h4>
                    <ul className="space-y-2">
                      {briefing.keyDevelopments.map((dev, idx) => (
                        <li key={idx} className="flex items-start gap-3">
                          <span className="text-cyan-400 font-mono text-xs mt-1">
                            {String(idx + 1).padStart(2, '0')}
                          </span>
                          <span className="text-gray-300 text-sm">{dev}</span>
                        </li>
                      ))}
                    </ul>
                  </div>

                  {/* Risk Assessment */}
                  <div className="bg-[#111118] border border-[#2a2a3a] rounded-lg p-4">
                    <h4 className="text-xs font-mono text-gray-500 mb-2 uppercase tracking-wider">
                      Risk Assessment
                    </h4>
                    <div className="flex items-start gap-3">
                      <AlertTriangle className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" />
                      <p className="text-gray-300 text-sm">{briefing.riskAssessment}</p>
                    </div>
                  </div>

                  {/* Footer */}
                  <div className="text-center pt-4 border-t border-[#2a2a3a]">
                    <p className="text-xs text-gray-500 font-mono">
                      Generated by Bonito AI Intelligence System
                    </p>
                    <p className="text-[10px] text-gray-600 mt-1">
                      This briefing is for informational purposes only. Verify critical information through official channels.
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
