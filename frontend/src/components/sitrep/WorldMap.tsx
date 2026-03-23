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

// Countries with active conflicts
const CONFLICT_COUNTRIES = ['UA', 'RU', 'IL', 'PS', 'YE', 'SD', 'MM', 'SY', 'IQ', 'LB', 'IR', 'AF'];
const WAR_ZONE_COUNTRIES = ['US', 'IR', 'RU', 'UA'];

const MISSILE_ROUTES = [
  {
    id: 'us-ir',
    from: [-98, 39] as [number, number],
    to: [53, 32] as [number, number],
    duration: 3.2,
    delay: 1,
  },
  {
    id: 'ru-ua',
    from: [90, 60] as [number, number],
    to: [31, 49] as [number, number],
    duration: 2.8,
    delay: 1.4,
  },
] as const;

interface WorldMapProps {
  articles: Article[];
  selectedCountry: string | null;
  onCountrySelect: (countryCode: string | null) => void;
  showHeatmap: boolean;
  sentimentData: Map<string, number>;
  selectedCategory: NewsCategory | 'all';
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
  selectedCategory,
}: WorldMapProps) {
  const [tooltip, setTooltip] = useState<{ content: string; x: number; y: number } | null>(null);
  const [zoom, setZoom] = useState(1);
  const isConflictFilter = selectedCategory === 'conflict';

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

  const missileRoutes = useMemo(
    () =>
      MISSILE_ROUTES.map((route) => {
        const dx = route.to[0] - route.from[0];
        const dy = route.to[1] - route.from[1];
        const arcLift = Math.max(10, Math.abs(dx) * 0.18);
        const controlX = dx / 2;
        const controlY = dy / 2 - arcLift;
        const path = `M0,0 Q${controlX},${controlY} ${dx},${dy}`;
        const heading = (Math.atan2(dy - controlY, dx - controlX) * 180) / Math.PI;

        return {
          ...route,
          dx,
          dy,
          controlX,
          controlY,
          path,
          heading,
        };
      }),
    []
  );

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
                const isConflictCountry = CONFLICT_COUNTRIES.includes(countryCode);
                const isWarZoneCountry = isConflictFilter && WAR_ZONE_COUNTRIES.includes(countryCode);
                
                return (
                  <g key={geo.rsmKey}>
                    {/* Glow border behind conflict countries - only show base conflict glow when NOT in conflict filter mode */}
                    {isConflictCountry && !isConflictFilter && (
                      <Geography
                        geography={geo}
                        fill="none"
                        stroke="rgba(255, 68, 68, 0.35)"
                        strokeWidth={6}
                        style={{
                          default: { outline: 'none', pointerEvents: 'none' },
                          hover: { outline: 'none', pointerEvents: 'none' },
                          pressed: { outline: 'none', pointerEvents: 'none' },
                        }}
                      />
                    )}
                    {/* War zone red border (USA, Iran, Russia, Ukraine) - pulsing */}
                    {isWarZoneCountry && (
                      <motion.g
                        initial={{ opacity: 0.5 }}
                        animate={{ opacity: [0.5, 1, 0.5] }}
                        transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut', delay: 0.25 }}
                      >
                        <Geography
                          geography={geo}
                          fill="none"
                          stroke="#f87171"
                          strokeWidth={3.2 / zoom}
                          style={{
                            default: { outline: 'none', pointerEvents: 'none' },
                            hover: { outline: 'none', pointerEvents: 'none' },
                            pressed: { outline: 'none', pointerEvents: 'none' },
                          }}
                        />
                      </motion.g>
                    )}
                    <Geography
                      geography={geo}
                      fill={
                        isWarZoneCountry
                          ? 'rgba(248, 113, 113, 0.16)'
                          : isConflictCountry
                          ? 'rgba(255, 68, 68, 0.12)'
                          : showHeatmap && sentiment !== undefined
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
                      stroke={isWarZoneCountry ? '#f87171' : isConflictCountry ? '#ff4444' : isSelected ? '#06b6d4' : '#2a2a3a'}
                      strokeWidth={isWarZoneCountry ? 2.8 / zoom : isConflictCountry ? 2.5 : isSelected ? 1 : 0.5}
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
                  </g>
                );
              })
            }
          </Geographies>

          {/* Conflict Lines - Missile Trajectories */}
          {isConflictFilter && (
            <>
              {missileRoutes.map((route) => (
                <Marker key={route.id} coordinates={route.from}>
                  <g>
                    <path
                      d={route.path}
                      stroke="#22c55e"
                      strokeWidth={2 / zoom}
                      strokeDasharray={`${5 / zoom},${5 / zoom}`}
                      strokeLinecap="round"
                      fill="none"
                      opacity={0.8}
                    />
                    <motion.g
                      animate={{
                        x: [0, route.controlX, route.dx],
                        y: [0, route.controlY, route.dy],
                      }}
                      transition={{
                        duration: route.duration,
                        repeat: Infinity,
                        ease: 'easeInOut',
                        repeatDelay: route.delay,
                      }}
                    >
                      <g transform={`rotate(${route.heading}) scale(${1 / zoom})`}>
                        <path
                          d="M-4,0 L-2,-3 L2,-3 L3,0 L2,3 L-2,3 Z"
                          fill="#22c55e"
                          stroke="#16a34a"
                          strokeWidth={0.5}
                        />
                        <path
                          d="M3,0 L6,0"
                          stroke="#22c55e"
                          strokeWidth={1.5}
                        />
                        <motion.path
                          d="M-4,0 L-7,-2 L-6,0 L-7,2 Z"
                          fill="#f59e0b"
                          animate={{ opacity: [1, 0.5, 1], scale: [1, 1.2, 1] }}
                          transition={{ duration: 0.3, repeat: Infinity }}
                        />
                      </g>
                    </motion.g>
                  </g>
                </Marker>
              ))}
            </>
          )}

          {/* Naval Forces - Ship Icons in Strait of Hormuz */}
          {[
            // Western/US Navy forces (blue ships)
            { coords: [56.0, 26.8], type: 'western', label: 'USN 5th Fleet' },
            { coords: [56.3, 26.6], type: 'western', label: 'USN 5th Fleet' },
            { coords: [55.8, 27.0], type: 'western', label: 'USN 5th Fleet' },
            // Iranian forces (red ships)
            { coords: [57.0, 26.3], type: 'iranian', label: 'IRGC Navy' },
            { coords: [56.8, 26.4], type: 'iranian', label: 'IRGC Navy' },
          ].map((ship, idx) => (
            <Marker
              key={`ship-${idx}`}
              coordinates={ship.coords as [number, number]}
            >
              <motion.g
                animate={{
                  y: [0, -2, 0],
                  x: [0, 1, 0],
                }}
                transition={{
                  duration: 3 + idx * 0.5,
                  repeat: Infinity,
                  ease: 'easeInOut',
                }}
                onMouseEnter={() => setTooltip({
                  content: ship.label,
                  x: 0,
                  y: 0,
                })}
                onMouseLeave={() => setTooltip(null)}
              >
                <g transform={`scale(${Math.max(0.65, Math.min(1.4, 1 / zoom))})`}>
                  {/* Glow behind ship */}
                  <ellipse
                    cx={0}
                    cy={0}
                    rx={10}
                    ry={6}
                    fill={ship.type === 'western' ? 'rgba(59, 130, 246, 0.25)' : 'rgba(255, 68, 68, 0.25)'}
                  />
                  {/* Ship silhouette - destroyer profile ~24px wide */}
                  <path
                    d="M-12,0 L-10,-3 L-6,-3 L-5,-6 L-3,-6 L-3,-4 L3,-4 L3,-7 L5,-7 L5,-4 L8,-3 L12,0 L10,2 L-10,2 Z"
                    fill={ship.type === 'western' ? '#3b82f6' : '#ef4444'}
                    stroke={ship.type === 'western' ? '#60a5fa' : '#ff6666'}
                    strokeWidth={0.5}
                    style={{
                      filter: `drop-shadow(0 0 6px ${ship.type === 'western' ? '#3b82f6' : '#ef4444'})`,
                    }}
                  />
                  {/* Ship wake effect */}
                  <ellipse
                    cx={-14}
                    cy={1}
                    rx={5}
                    ry={1.5}
                    fill="rgba(255, 255, 255, 0.12)"
                  />
                  <ellipse
                    cx={-18}
                    cy={1}
                    rx={3}
                    ry={1}
                    fill="rgba(255, 255, 255, 0.06)"
                  />
                </g>
              </motion.g>
            </Marker>
          ))}

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
            <div className="mt-2 pt-2 border-t border-[#2a2a3a] space-y-1">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-sm border-2 border-[#ff4444] bg-[rgba(255,68,68,0.12)]" />
                <span className="text-xs text-gray-300">War Zone</span>
              </div>
              <div className="text-[9px] text-gray-500 uppercase tracking-wider mt-1 mb-0.5">Naval Forces</div>
              <div className="flex items-center gap-2">
                <svg width="16" height="10" viewBox="-12 -7 24 10" className="flex-shrink-0">
                  <path d="M-12,0 L-10,-3 L-6,-3 L-5,-6 L-3,-6 L-3,-4 L3,-4 L3,-7 L5,-7 L5,-4 L8,-3 L12,0 L10,2 L-10,2 Z" fill="#3b82f6" />
                </svg>
                <span className="text-xs text-gray-300">Western Naval</span>
              </div>
              <div className="flex items-center gap-2">
                <svg width="16" height="10" viewBox="-12 -7 24 10" className="flex-shrink-0">
                  <path d="M-12,0 L-10,-3 L-6,-3 L-5,-6 L-3,-6 L-3,-4 L3,-4 L3,-7 L5,-7 L5,-4 L8,-3 L12,0 L10,2 L-10,2 Z" fill="#ef4444" />
                </svg>
                <span className="text-xs text-gray-300">Iranian Naval</span>
              </div>
            </div>
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
