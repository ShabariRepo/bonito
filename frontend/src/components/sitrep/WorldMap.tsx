'use client';

import { useState, useMemo } from 'react';
import { geoEquirectangular } from 'd3-geo';
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
const MAP_VIEWBOX = { width: 800, height: 600 };

const MISSILE_ROUTES = [
  {
    id: 'us-ir',
    from: [-98, 38.5] as [number, number],
    to: [54.3, 32.1] as [number, number],
    duration: 3.2,
    delay: 1,
  },
  {
    id: 'ru-ua',
    from: [89.5, 59.5] as [number, number],
    to: [31.2, 49.2] as [number, number],
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

function getQuadraticPoint(
  start: [number, number],
  control: [number, number],
  end: [number, number],
  t: number
): [number, number] {
  const x = (1 - t) * (1 - t) * start[0] + 2 * (1 - t) * t * control[0] + t * t * end[0];
  const y = (1 - t) * (1 - t) * start[1] + 2 * (1 - t) * t * control[1] + t * t * end[1];
  return [x, y];
}

function getQuadraticAngle(
  start: [number, number],
  control: [number, number],
  end: [number, number],
  t: number
): number {
  const dx = 2 * (1 - t) * (control[0] - start[0]) + 2 * t * (end[0] - control[0]);
  const dy = 2 * (1 - t) * (control[1] - start[1]) + 2 * t * (end[1] - control[1]);
  return (Math.atan2(dy, dx) * 180) / Math.PI;
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
  const zoom = 1;
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

  const projection = useMemo(
    () =>
      geoEquirectangular()
        .scale(147)
        .translate([MAP_VIEWBOX.width / 2, MAP_VIEWBOX.height / 2])
        .center([0, 0]),
    []
  );

  const missileRoutes = useMemo(() => {
    return MISSILE_ROUTES.map((route) => {
      const start = projection(route.from);
      const end = projection(route.to);
      if (!start || !end) return null;

      const arcLift = Math.max(90, Math.abs(end[0] - start[0]) * 0.45);
      const control: [number, number] = [
        (start[0] + end[0]) / 2,
        Math.min(start[1], end[1]) - arcLift,
      ];
      const path = `M${start[0]},${start[1]} Q${control[0]},${control[1]} ${end[0]},${end[1]}`;

      const sampleSteps = Array.from({ length: 25 }, (_, index) => index / 24);
      const rocketFrames = sampleSteps.map((step) => {
        const [x, y] = getQuadraticPoint(start as [number, number], control, end as [number, number], step);
        const angle = getQuadraticAngle(start as [number, number], control, end as [number, number], Math.min(step + 0.015, 1));
        return { x, y, angle };
      });

      return {
        ...route,
        start: start as [number, number],
        end: end as [number, number],
        control,
        path,
        rocketFrames,
      };
    });
  }, [projection]);

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
        width={MAP_VIEWBOX.width}
        height={MAP_VIEWBOX.height}
        className="w-full h-full"
        style={{
          background: 'transparent',
        }}
      >
        <ZoomableGroup zoom={1} minZoom={1} maxZoom={1} translateExtent={[[0, 0], [800, 400]]}>
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

      <svg
        viewBox={`0 0 ${MAP_VIEWBOX.width} ${MAP_VIEWBOX.height}`}
        className="absolute inset-0 h-full w-full pointer-events-none"
        aria-hidden="true"
      >
        {isConflictFilter &&
          missileRoutes.map((route) => {
            if (!route) return null;

            return (
              <g key={route.id}>
                <path
                  d={route.path}
                  stroke="#22c55e"
                  strokeWidth={2 / zoom}
                  strokeDasharray={`${6 / zoom},${6 / zoom}`}
                  strokeLinecap="round"
                  fill="none"
                  opacity={0.85}
                  style={{ filter: 'drop-shadow(0 0 8px rgba(34,197,94,0.35))' }}
                />
                <motion.g
                  animate={{
                    transform: route.rocketFrames.map(
                      (frame) => `translate(${frame.x}px, ${frame.y}px) rotate(${frame.angle}deg)`
                    ),
                  }}
                  transition={{
                    duration: route.duration,
                    repeat: Infinity,
                    ease: 'linear',
                    repeatDelay: route.delay,
                  }}
                >
                  <g style={{ filter: 'drop-shadow(0 0 10px rgba(34,197,94,0.6))' }}>
                    <path
                      d="M-7,0 L-3.5,-4.2 L3.5,-4.2 L6,0 L3.5,4.2 L-3.5,4.2 Z"
                      fill="#22c55e"
                      stroke="#14532d"
                      strokeWidth={0.8}
                    />
                    <path
                      d="M6,0 L11,0"
                      stroke="#86efac"
                      strokeWidth={2}
                      strokeLinecap="round"
                    />
                    <circle cx={-1.5} cy={0} r={1.2} fill="#d9f99d" opacity={0.9} />
                    <motion.path
                      d="M-7,0 L-12,-3 L-10,0 L-12,3 Z"
                      fill="#f59e0b"
                      animate={{ opacity: [1, 0.35, 1] }}
                      transition={{ duration: 0.25, repeat: Infinity }}
                    />
                  </g>
                </motion.g>
              </g>
            );
          })}
      </svg>

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
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
