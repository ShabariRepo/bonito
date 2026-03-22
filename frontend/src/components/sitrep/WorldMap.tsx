'use client';

import { useState, useMemo } from 'react';
import {
  ComposableMap,
  Geographies,
  Geography,
  Marker,
  ZoomableGroup,
} from 'react-simple-maps';
import { motion, AnimatePresence } from 'framer-motion';
import { Article, NewsCategory, CATEGORY_COLORS } from '@/lib/sitrep/types';
import { groupArticlesByCountry } from '@/lib/sitrep/utils';

// World TopoJSON - using a reliable CDN
const geoUrl = 'https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json';

interface WorldMapProps {
  articles: Article[];
  selectedCountry: string | null;
  onCountrySelect: (countryCode: string | null) => void;
  showHeatmap: boolean;
  sentimentData: Map<string, number>;
}

interface MapMarker {
  countryCode: string;
  name: string;
  coordinates: [number, number];
  articles: Article[];
  dominantCategory: NewsCategory;
}

export default function WorldMap({
  articles,
  selectedCountry,
  onCountrySelect,
  showHeatmap,
  sentimentData,
}: WorldMapProps) {
  const [tooltip, setTooltip] = useState<{ content: string; x: number; y: number } | null>(null);
  const [zoom, setZoom] = useState(1);

  const markers = useMemo((): MapMarker[] => {
    const grouped = groupArticlesByCountry(articles);
    const result: MapMarker[] = [];
    
    grouped.forEach((countryArticles, countryCode) => {
      if (countryArticles.length === 0) return;
      
      // Use the first article's coordinates (they should all be similar for a country)
      const firstArticle = countryArticles[0];
      
      // Determine dominant category
      const categoryCounts = new Map<NewsCategory, number>();
      countryArticles.forEach((a) => {
        categoryCounts.set(a.category, (categoryCounts.get(a.category) || 0) + 1);
      });
      
      let dominantCategory: NewsCategory = 'politics';
      let maxCount = 0;
      categoryCounts.forEach((count, cat) => {
        if (count > maxCount) {
          maxCount = count;
          dominantCategory = cat;
        }
      });
      
      result.push({
        countryCode,
        name: firstArticle.country,
        coordinates: [firstArticle.lng, firstArticle.lat],
        articles: countryArticles,
        dominantCategory,
      });
    });
    
    return result;
  }, [articles]);

  const getMarkerColor = (marker: MapMarker): string => {
    if (showHeatmap) {
      const sentiment = sentimentData.get(marker.countryCode) || 0;
      if (sentiment < -0.3) return '#ef4444'; // Red for negative
      if (sentiment > 0.3) return '#22c55e'; // Green for positive
      return '#f59e0b'; // Amber for neutral
    }
    return CATEGORY_COLORS[marker.dominantCategory];
  };

  const hasBreakingNews = (marker: MapMarker): boolean => {
    return marker.articles.some((a) => a.isBreaking);
  };

  return (
    <div className="relative w-full h-full bg-[#0a0a0f] overflow-hidden">
      {/* Grid overlay effect */}
      <div 
        className="absolute inset-0 pointer-events-none opacity-20"
        style={{
          backgroundImage: `
            linear-gradient(rgba(6, 182, 212, 0.1) 1px, transparent 1px),
            linear-gradient(90deg, rgba(6, 182, 212, 0.1) 1px, transparent 1px)
          `,
          backgroundSize: '50px 50px',
        }}
      />
      
      {/* Scan line effect */}
      <motion.div
        className="absolute inset-0 pointer-events-none"
        style={{
          background: 'linear-gradient(transparent 50%, rgba(6, 182, 212, 0.03) 50%)',
          backgroundSize: '100% 4px',
        }}
        animate={{
          backgroundPosition: ['0px 0px', '0px 4px'],
        }}
        transition={{
          duration: 0.5,
          repeat: Infinity,
          ease: 'linear',
        }}
      />

      <ComposableMap
        projection="geoEquirectangular"
        projectionConfig={{
          scale: 147,
          center: [0, 0],
        }}
        className="w-full h-full"
        style={{
          background: 'transparent',
        }}
      >
        <ZoomableGroup
          zoom={zoom}
          minZoom={1}
          maxZoom={4}
          translateExtent={[
            [0, 0],
            [800, 400],
          ]}
        >
          <Geographies geography={geoUrl}>
            {({ geographies }) =>
              geographies.map((geo) => {
                const countryCode = geo.properties.ISO_A2;
                const isSelected = selectedCountry === countryCode;
                const hasArticles = markers.some((m) => m.countryCode === countryCode);
                const sentiment = sentimentData.get(countryCode);
                
                return (
                  <Geography
                    key={geo.rsmKey}
                    geography={geo}
                    fill={
                      showHeatmap && sentiment !== undefined
                        ? sentiment < -0.3
                          ? 'rgba(239, 68, 68, 0.3)'
                          : sentiment > 0.3
                          ? 'rgba(34, 197, 94, 0.3)'
                          : 'rgba(245, 158, 11, 0.2)'
                        : isSelected
                        ? 'rgba(6, 182, 212, 0.3)'
                        : hasArticles
                        ? 'rgba(6, 182, 212, 0.1)'
                        : '#1a1a24'
                    }
                    stroke={isSelected ? '#06b6d4' : '#2a2a3a'}
                    strokeWidth={isSelected ? 1 : 0.5}
                    style={{
                      default: {
                        outline: 'none',
                        transition: 'all 0.3s',
                      },
                      hover: {
                        fill: hasArticles ? 'rgba(6, 182, 212, 0.2)' : '#252530',
                        outline: 'none',
                        cursor: hasArticles ? 'pointer' : 'default',
                      },
                      pressed: {
                        outline: 'none',
                      },
                    }}
                    onClick={() => {
                      if (hasArticles) {
                        onCountrySelect(isSelected ? null : countryCode);
                      }
                    }}
                    onMouseEnter={() => {
                      if (hasArticles) {
                        const marker = markers.find((m) => m.countryCode === countryCode);
                        if (marker) {
                          setTooltip({
                            content: `${marker.name}: ${marker.articles.length} articles`,
                            x: 0,
                            y: 0,
                          });
                        }
                      }
                    }}
                    onMouseLeave={() => setTooltip(null)}
                  />
                );
              })
            }
          </Geographies>

          {/* Article markers */}
          {markers.map((marker) => {
            const color = getMarkerColor(marker);
            const isSelected = selectedCountry === marker.countryCode;
            const breaking = hasBreakingNews(marker);
            
            return (
              <Marker
                key={marker.countryCode}
                coordinates={marker.coordinates}
                onClick={() => onCountrySelect(isSelected ? null : marker.countryCode)}
              >
                <g>
                  {/* Pulse animation for breaking news */}
                  {breaking && (
                    <motion.circle
                      r={8}
                      fill={color}
                      opacity={0.3}
                      animate={{
                        r: [8, 20, 8],
                        opacity: [0.5, 0, 0.5],
                      }}
                      transition={{
                        duration: 2,
                        repeat: Infinity,
                        ease: 'easeInOut',
                      }}
                    />
                  )}
                  
                  {/* Main dot */}
                  <motion.circle
                    r={isSelected ? 6 : 4}
                    fill={color}
                    stroke="#0a0a0f"
                    strokeWidth={2}
                    animate={{
                      scale: isSelected ? [1, 1.2, 1] : 1,
                    }}
                    transition={{
                      duration: 1,
                      repeat: isSelected ? Infinity : 0,
                    }}
                    style={{
                      cursor: 'pointer',
                      filter: `drop-shadow(0 0 6px ${color})`,
                    }}
                  />
                  
                  {/* Article count badge */}
                  {marker.articles.length > 1 && (
                    <text
                      y={-8}
                      textAnchor="middle"
                      fill="#fff"
                      fontSize="8"
                      fontFamily="monospace"
                      style={{ pointerEvents: 'none' }}
                    >
                      {marker.articles.length}
                    </text>
                  )}
                </g>
              </Marker>
            );
          })}
        </ZoomableGroup>
      </ComposableMap>

      {/* Tooltip */}
      <AnimatePresence>
        {tooltip && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="absolute px-3 py-2 bg-[#1a1a24] border border-[#2a2a3a] rounded text-xs text-white pointer-events-none z-50"
            style={{
              left: tooltip.x,
              top: tooltip.y,
            }}
          >
            {tooltip.content}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Legend */}
      <div className="absolute bottom-4 left-4 bg-[#0a0a0f]/90 backdrop-blur border border-[#2a2a3a] rounded-lg p-4">
        <h4 className="text-xs font-mono text-gray-400 mb-2">
          {showHeatmap ? 'SENTIMENT HEATMAP' : 'NEWS CATEGORIES'}
        </h4>
        {showHeatmap ? (
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-green-500" />
              <span className="text-xs text-gray-300">Positive</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-amber-500" />
              <span className="text-xs text-gray-300">Neutral</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-red-500" />
              <span className="text-xs text-gray-300">Negative/Conflict</span>
            </div>
          </div>
        ) : (
          <div className="space-y-1">
            {Object.entries({
              conflict: 'Conflict',
              politics: 'Politics',
              tech: 'Technology',
              economy: 'Economy',
              culture: 'Culture',
              climate: 'Climate',
            }).map(([key, label]) => (
              <div key={key} className="flex items-center gap-2">
                <div
                  className="w-3 h-3 rounded-full"
                  style={{ backgroundColor: CATEGORY_COLORS[key as NewsCategory] }}
                />
                <span className="text-xs text-gray-300">{label}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Zoom controls */}
      <div className="absolute bottom-4 right-4 flex flex-col gap-2">
        <button
          onClick={() => setZoom((z) => Math.min(z * 1.5, 4))}
          className="w-8 h-8 bg-[#1a1a24] border border-[#2a2a3a] rounded flex items-center justify-center text-gray-400 hover:text-white hover:border-cyan-500/50 transition"
        >
          +
        </button>
        <button
          onClick={() => setZoom((z) => Math.max(z / 1.5, 1))}
          className="w-8 h-8 bg-[#1a1a24] border border-[#2a2a3a] rounded flex items-center justify-center text-gray-400 hover:text-white hover:border-cyan-500/50 transition"
        >
          −
        </button>
      </div>
    </div>
  );
}
