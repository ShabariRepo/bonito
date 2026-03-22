import { BiasAnalysisResult, FactCheckResult, BriefingResult, NarrativeComparison, TranslationResult, Article, LANGUAGE_NAMES, CATEGORY_LABELS } from './types';

const BONITO_API_KEY = process.env.BONITO_API_KEY;
const BONITO_API_URL = process.env.BONITO_API_URL || 'https://api.getbonito.com/v1';

// Mock data generators for development
function generateMockBiasAnalysis(text: string): BiasAnalysisResult {
  const keywords = {
    left: ['progressive', 'workers', 'inequality', 'climate', 'social justice', 'union', 'reform', 'universal'],
    right: ['freedom', 'market', 'tax cuts', 'deregulation', 'border', 'defense', 'traditional', 'liberty'],
  };
  
  const textLower = text.toLowerCase();
  let leftScore = 0;
  let rightScore = 0;
  
  keywords.left.forEach((k) => {
    if (textLower.includes(k)) leftScore += 0.15;
  });
  keywords.right.forEach((k) => {
    if (textLower.includes(k)) rightScore += 0.15;
  });
  
  const score = Math.max(-0.9, Math.min(0.9, rightScore - leftScore + (Math.random() * 0.2 - 0.1)));
  
  let analysis: string;
  if (score < -0.5) {
    analysis = 'Analysis indicates strong progressive framing with emphasis on systemic issues and collective solutions. Language choices align with left-leaning policy perspectives.';
  } else if (score < -0.2) {
    analysis = 'Moderate left-leaning bias detected. Article presents perspectives that favor interventionist policies and social equity frameworks.';
  } else if (score < 0.2) {
    analysis = 'Centrist presentation with relatively balanced coverage. Minor tonal variations detected but within acceptable journalistic standards.';
  } else if (score < 0.5) {
    analysis = 'Moderate right-leaning bias detected. Emphasis on market mechanisms, individual responsibility, and traditional frameworks.';
  } else {
    analysis = 'Analysis indicates strong conservative framing with emphasis on free markets, limited government, and traditional values. Language choices align with right-leaning policy perspectives.';
  }
  
  return {
    score,
    analysis,
    confidence: 0.7 + Math.random() * 0.25,
  };
}

function generateMockFactCheck(text: string): FactCheckResult {
  const redFlags: string[] = [];
  const sensationalWords = ['shocking', 'devastating', 'unprecedented', 'massive', 'total disaster'];
  
  const textLower = text.toLowerCase();
  sensationalWords.forEach((word) => {
    if (textLower.includes(word)) {
      redFlags.push(`Sensationalist language detected: "${word}"`);
    }
  });
  
  if (textLower.includes('sources say') || textLower.includes('some people claim')) {
    redFlags.push('Vague attribution without specific sourcing');
  }
  
  if (textLower.includes('always') || textLower.includes('never') || textLower.includes('everyone knows')) {
    redFlags.push('Absolute language that may oversimplify complex issues');
  }
  
  // Generate score based on red flags
  const baseScore = 85;
  const deduction = redFlags.length * 15;
  const score = Math.max(20, Math.min(95, baseScore - deduction + Math.random() * 10));
  
  let reasoning: string;
  if (score >= 80) {
    reasoning = 'Content appears well-sourced with factual claims that can be verified. Language is measured and avoids sensationalism. Multiple perspectives are presented where applicable.';
  } else if (score >= 60) {
    reasoning = 'Most claims appear factual but some context may be missing. Occasional use of loaded language detected. Readers should verify key statistics independently.';
  } else if (score >= 40) {
    reasoning = 'Significant concerns identified. Missing context, selective presentation of facts, and/or emotionally loaded language may mislead readers. Cross-reference with other sources recommended.';
  } else {
    reasoning = 'High risk of misinformation. Multiple red flags including unsourced claims, sensationalist language, and potentially false equivalencies. Treat with substantial skepticism.';
  }
  
  return {
    score,
    reasoning,
    claims: redFlags.length > 0
      ? redFlags.map((flag) => ({ claim: flag, verdict: 'unverified' as const, evidence: 'Automated detection' }))
      : [{ claim: 'No major red flags detected', verdict: 'true' as const, evidence: 'Clean analysis' }],
  };
}

function generateMockBriefing(articles: Article[]): BriefingResult {
  const conflicts = articles.filter((a) => a.category === 'conflict');
  const politics = articles.filter((a) => a.category === 'politics');
  const economy = articles.filter((a) => a.category === 'economy');
  
  const keyDevelopments = [
    `Active military engagements reported in ${conflicts.length} regions with civilian impact concerns`,
    `Political instability indicators elevated in major economies including Germany and Argentina`,
    `Economic policy shifts: Nigeria subsidy removal, Turkish rate hikes, OPEC+ production cuts`,
    `Technology regulation advancing: EU AI Act implementation, California AI safety laws`,
    `Climate impacts accelerating: Antarctic ice loss, Great Barrier Reef bleaching event`,
  ];
  
  return {
    title: 'GLOBAL SITUATION REPORT - MARCH 21, 2026',
    classification: 'UNCLASSIFIED',
    timestamp: new Date().toISOString(),
    summary: 'Global instability indicators remain elevated with active conflicts in Ukraine, Middle East, and Africa. Economic pressures mounting across developing markets as inflation persists. Technology governance frameworks advancing in Western jurisdictions. Climate impacts continue accelerating with new scientific confirmation of irreversible Antarctic ice loss.',
    keyDevelopments,
    riskAssessment: 'MODERATE-HIGH: Military escalation risk in Eastern Europe and South China Sea. Economic contagion possible from Argentine and Turkish crises. Cyber threat level unchanged. Climate displacement pressures increasing.',
  };
}

function generateMockComparison(a1: Article, a2: Article): NarrativeComparison {
  const topic = a1.category === a2.category ? 
    CATEGORY_LABELS[a1.category] : 
    'Multiple Topics';
  
  const leftArticle = a1.sourceBias <= a2.sourceBias ? a1 : a2;
  const rightArticle = a1.sourceBias <= a2.sourceBias ? a2 : a1;
  
  return {
    topic,
    leftFraming: `${leftArticle.source} emphasizes systemic issues, government intervention, and collective impact. The narrative focuses on vulnerable populations and structural causes.`,
    rightFraming: `${rightArticle.source} emphasizes individual agency, market solutions, and security concerns. The narrative focuses on economic efficiency and traditional frameworks.`,
    differences: [
      'Emphasis: Left source highlights government responsibility; Right source emphasizes individual/market solutions',
      'Tone: Left uses empathetic language toward affected groups; Right uses concern-focused language on broader impacts',
      'Causation: Left attributes issues to systemic failures; Right attributes to policy choices or external factors',
    ],
    aiAnalysis: `These articles demonstrate classic ideological framing divergence on ${topic.toLowerCase()}. The left-leaning source (${leftArticle.source}) structures the narrative around collective impact and systemic reform, while the right-leaning source (${rightArticle.source}) emphasizes efficiency, security, and traditional frameworks. Both present factual information but with selective emphasis that aligns with their editorial perspective. Readers consuming only one source would miss important contextual dimensions presented in the other.`,
  };
}

// Mock translation function
function generateMockTranslation(text: string, fromLang: string): TranslationResult {
  const languageName = LANGUAGE_NAMES[fromLang] || fromLang;
  
  // Simulate translation by adding a note about the source language
  // In reality, this would be actual translated text
  const mockTranslations: Record<string, string> = {
    ja: '[Translated from Japanese] The content has been processed through Bonito\'s neural translation engine with cultural context preservation.',
    de: '[Translated from German] The content has been processed through Bonito\'s neural translation engine maintaining technical precision.',
    fr: '[Translated from French] The content has been processed through Bonito\'s neural translation engine preserving diplomatic nuances.',
    pt: '[Translated from Portuguese] The content has been processed through Bonito\'s neural translation engine with regional adaptation.',
    ar: '[Translated from Arabic] The content has been processed through Bonito\'s neural translation engine with right-to-left layout preservation.',
    zh: '[Translated from Chinese] The content has been processed through Bonito\'s neural translation engine with character optimization.',
    es: '[Translated from Spanish] The content has been processed through Bonito\'s neural translation engine with idiomatic adaptation.',
    ko: '[Translated from Korean] The content has been processed through Bonito\'s neural translation engine with honorific level adjustment.',
    ru: '[Translated from Russian] The content has been processed through Bonito\'s neural translation engine with case structure adaptation.',
    hi: '[Translated from Hindi] The content has been processed through Bonito\'s neural translation engine with script transliteration.',
  };
  
  return {
    translatedText: mockTranslations[fromLang] || `[Translated from ${languageName}] Content processed through Bonito translation engine.`,
    detectedLanguage: fromLang,
    confidence: 0.92 + Math.random() * 0.07,
    model: 'bonito-translate-v2.1',
  };
}

// API functions
export async function analyzeBias(text: string): Promise<BiasAnalysisResult> {
  if (!BONITO_API_KEY) {
    // Return mock data for development
    await new Promise((resolve) => setTimeout(resolve, 1500)); // Simulate API delay
    return generateMockBiasAnalysis(text);
  }
  
  const response = await fetch(`${BONITO_API_URL}/analyze/bias`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${BONITO_API_KEY}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ text }),
  });
  
  if (!response.ok) {
    throw new Error(`Bias analysis failed: ${response.statusText}`);
  }
  
  return response.json();
}

export async function factCheck(text: string): Promise<FactCheckResult> {
  if (!BONITO_API_KEY) {
    await new Promise((resolve) => setTimeout(resolve, 2000));
    return generateMockFactCheck(text);
  }
  
  const response = await fetch(`${BONITO_API_URL}/analyze/fact-check`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${BONITO_API_KEY}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ text }),
  });
  
  if (!response.ok) {
    throw new Error(`Fact check failed: ${response.statusText}`);
  }
  
  return response.json();
}

export async function generateBriefing(articleList: Article[]): Promise<BriefingResult> {
  if (!BONITO_API_KEY) {
    await new Promise((resolve) => setTimeout(resolve, 3000));
    return generateMockBriefing(articleList);
  }
  
  const response = await fetch(`${BONITO_API_URL}/briefing/generate`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${BONITO_API_KEY}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ articles: articleList }),
  });
  
  if (!response.ok) {
    throw new Error(`Briefing generation failed: ${response.statusText}`);
  }
  
  return response.json();
}

export async function compareNarratives(a1: Article, a2: Article): Promise<NarrativeComparison> {
  if (!BONITO_API_KEY) {
    await new Promise((resolve) => setTimeout(resolve, 2500));
    return generateMockComparison(a1, a2);
  }

  const response = await fetch(`${BONITO_API_URL}/analyze/compare`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${BONITO_API_KEY}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ article1: a1, article2: a2 }),
  });

  if (!response.ok) {
    throw new Error(`Narrative comparison failed: ${response.statusText}`);
  }

  return response.json();
}

export async function translateArticle(text: string, fromLang: string): Promise<TranslationResult> {
  if (!BONITO_API_KEY) {
    await new Promise((resolve) => setTimeout(resolve, 1500));
    return generateMockTranslation(text, fromLang);
  }

  const response = await fetch(`${BONITO_API_URL}/translate`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${BONITO_API_KEY}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ text, sourceLanguage: fromLang, targetLanguage: 'en' }),
  });

  if (!response.ok) {
    throw new Error(`Translation failed: ${response.statusText}`);
  }

  return response.json();
}
