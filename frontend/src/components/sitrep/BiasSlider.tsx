'use client';

import { useState, useRef, useEffect } from 'react';
import { motion } from 'framer-motion';

interface BiasSliderProps {
  value: number;
  onChange: (value: number) => void;
  min?: number;
  max?: number;
}

export default function BiasSlider({
  value,
  onChange,
  min = -1,
  max = 1,
}: BiasSliderProps) {
  const [isDragging, setIsDragging] = useState(false);
  const trackRef = useRef<HTMLDivElement>(null);

  const percentage = ((value - min) / (max - min)) * 100;

  const handleMove = (clientX: number) => {
    if (!trackRef.current) return;
    const rect = trackRef.current.getBoundingClientRect();
    const x = clientX - rect.left;
    const newPercentage = Math.max(0, Math.min(100, (x / rect.width) * 100));
    const newValue = min + (newPercentage / 100) * (max - min);
    onChange(Math.round(newValue * 100) / 100);
  };

  const handleMouseDown = (e: React.MouseEvent) => {
    setIsDragging(true);
    handleMove(e.clientX);
  };

  const handleTouchStart = (e: React.TouchEvent) => {
    setIsDragging(true);
    handleMove(e.touches[0].clientX);
  };

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (isDragging) handleMove(e.clientX);
    };

    const handleTouchMove = (e: TouchEvent) => {
      if (isDragging) handleMove(e.touches[0].clientX);
    };

    const handleEnd = () => {
      setIsDragging(false);
    };

    if (isDragging) {
      window.addEventListener('mousemove', handleMouseMove);
      window.addEventListener('mouseup', handleEnd);
      window.addEventListener('touchmove', handleTouchMove);
      window.addEventListener('touchend', handleEnd);
    }

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleEnd);
      window.removeEventListener('touchmove', handleTouchMove);
      window.removeEventListener('touchend', handleEnd);
    };
  }, [isDragging]);

  const getLabel = (val: number): string => {
    if (val < -0.6) return 'Far Left';
    if (val < -0.3) return 'Left';
    if (val < -0.1) return 'Center-Left';
    if (val <= 0.1) return 'Center';
    if (val <= 0.3) return 'Center-Right';
    if (val <= 0.6) return 'Right';
    return 'Far Right';
  };

  const getColor = (val: number): string => {
    if (val < -0.3) return '#3b82f6';
    if (val < -0.1) return '#60a5fa';
    if (val <= 0.1) return '#9ca3af';
    if (val <= 0.3) return '#f87171';
    return '#ef4444';
  };

  return (
    <div className="w-full">
      {/* Label */}
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-mono text-gray-400">POLITICAL BIAS FILTER</span>
        <motion.span
          key={value}
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-xs font-mono"
          style={{ color: getColor(value) }}
        >
          {getLabel(value)} ({value > 0 ? '+' : ''}{value.toFixed(1)})
        </motion.span>
      </div>

      {/* Slider track */}
      <div
        ref={trackRef}
        className="relative h-8 bg-[#1a1a24] rounded-full cursor-pointer select-none overflow-hidden"
        onMouseDown={handleMouseDown}
        onTouchStart={handleTouchStart}
      >
        {/* Gradient background */}
        <div
          className="absolute inset-0 opacity-30"
          style={{
            background: `linear-gradient(to right, 
              #3b82f6 0%, 
              #60a5fa 25%, 
              #9ca3af 50%, 
              #f87171 75%, 
              #ef4444 100%
            )`,
          }}
        />

        {/* Center marker */}
        <div className="absolute top-0 bottom-0 left-1/2 w-px bg-white/20" />

        {/* Labels */}
        <div className="absolute inset-0 flex items-center justify-between px-4 pointer-events-none">
          <span className="text-[10px] font-mono text-blue-400/60">LEFT</span>
          <span className="text-[10px] font-mono text-gray-400/60">CENTER</span>
          <span className="text-[10px] font-mono text-red-400/60">RIGHT</span>
        </div>

        {/* Thumb */}
        <motion.div
          className="absolute top-1 w-6 h-6 rounded-full border-2 shadow-lg"
          style={{
            left: `calc(${percentage}% - 12px)`,
            backgroundColor: '#0a0a0f',
            borderColor: getColor(value),
            boxShadow: `0 0 10px ${getColor(value)}40`,
          }}
          animate={{
            scale: isDragging ? 1.2 : 1,
          }}
          transition={{ duration: 0.15 }}
        />

        {/* Active zone indicator */}
        <div
          className="absolute top-0 bottom-0 bg-white/5 pointer-events-none"
          style={{
            width: `${Math.abs(percentage - 50)}%`,
            ...(percentage > 50 
              ? { left: '50%', right: 'auto' }
              : { left: `${percentage}%`, right: '50%' }
            ),
          }}
        />
      </div>

      {/* Value readout */}
      <div className="flex items-center justify-between mt-2 text-[10px] font-mono text-gray-500">
        <span>-1.0</span>
        <span className="text-gray-400">
          Showing articles from {value < 0 ? 'Left' : value > 0 ? 'Right' : 'All'} sources
          {value !== 0 && ` (±${Math.abs(value).toFixed(1)} range)`}
        </span>
        <span>+1.0</span>
      </div>
    </div>
  );
}
