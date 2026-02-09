/**
 * Flexible loading skeleton components for better UX during data loading.
 */

import React from 'react';

interface SkeletonProps {
  className?: string;
  width?: string;
  height?: string;
}

// Base skeleton element
export const Skeleton: React.FC<SkeletonProps> = ({ 
  className = '', 
  width = '100%', 
  height = '1rem' 
}) => {
  return (
    <div 
      className={`animate-pulse bg-gray-200 dark:bg-gray-700 rounded ${className}`}
      style={{ width, height }}
    />
  );
};

// Card skeleton for provider cards, model cards, etc.
export const CardSkeleton: React.FC<{ count?: number }> = ({ count = 1 }) => {
  return (
    <>
      {Array.from({ length: count }, (_, i) => (
        <div key={i} className="border border-gray-200 dark:border-gray-700 rounded-lg p-6 space-y-4">
          <div className="flex items-center space-x-3">
            <Skeleton width="48px" height="48px" className="rounded-full" />
            <div className="space-y-2">
              <Skeleton width="120px" height="16px" />
              <Skeleton width="80px" height="14px" />
            </div>
          </div>
          <div className="space-y-2">
            <Skeleton width="100%" height="14px" />
            <Skeleton width="75%" height="14px" />
          </div>
          <div className="flex justify-between">
            <Skeleton width="60px" height="20px" className="rounded-full" />
            <Skeleton width="80px" height="32px" className="rounded" />
          </div>
        </div>
      ))}
    </>
  );
};

// Table skeleton for data tables
export const TableSkeleton: React.FC<{ rows?: number; cols?: number }> = ({ 
  rows = 5, 
  cols = 4 
}) => {
  return (
    <div className="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
      {/* Table header */}
      <div className="bg-gray-50 dark:bg-gray-800 px-6 py-4 border-b border-gray-200 dark:border-gray-700">
        <div className="grid grid-cols-4 gap-4">
          {Array.from({ length: cols }, (_, i) => (
            <Skeleton key={i} width="80px" height="16px" />
          ))}
        </div>
      </div>
      
      {/* Table rows */}
      <div className="divide-y divide-gray-200 dark:divide-gray-700">
        {Array.from({ length: rows }, (_, rowIndex) => (
          <div key={rowIndex} className="px-6 py-4">
            <div className="grid grid-cols-4 gap-4 items-center">
              {Array.from({ length: cols }, (_, colIndex) => (
                <Skeleton key={colIndex} width="100%" height="16px" />
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

// Page header skeleton
export const PageHeaderSkeleton: React.FC = () => {
  return (
    <div className="space-y-4 mb-8">
      <div className="flex justify-between items-start">
        <div className="space-y-2">
          <Skeleton width="200px" height="32px" />
          <Skeleton width="300px" height="16px" />
        </div>
        <Skeleton width="120px" height="36px" className="rounded" />
      </div>
    </div>
  );
};

// Stats cards skeleton
export const StatsCardskeleton: React.FC<{ count?: number }> = ({ count = 4 }) => {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
      {Array.from({ length: count }, (_, i) => (
        <div key={i} className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
          <div className="flex items-center justify-between">
            <div className="space-y-2">
              <Skeleton width="80px" height="14px" />
              <Skeleton width="60px" height="24px" />
            </div>
            <Skeleton width="40px" height="40px" className="rounded-full" />
          </div>
          <div className="mt-4">
            <Skeleton width="100px" height="12px" />
          </div>
        </div>
      ))}
    </div>
  );
};

// List skeleton for simple lists
export const ListSkeleton: React.FC<{ items?: number }> = ({ items = 5 }) => {
  return (
    <div className="space-y-3">
      {Array.from({ length: items }, (_, i) => (
        <div key={i} className="flex items-center space-x-3 p-3 border border-gray-200 dark:border-gray-700 rounded">
          <Skeleton width="32px" height="32px" className="rounded" />
          <div className="flex-1 space-y-1">
            <Skeleton width="150px" height="16px" />
            <Skeleton width="100px" height="14px" />
          </div>
          <Skeleton width="60px" height="24px" className="rounded" />
        </div>
      ))}
    </div>
  );
};

export default {
  Skeleton,
  CardSkeleton,
  TableSkeleton,
  PageHeaderSkeleton,
  StatsCardskeleton,
  ListSkeleton,
};