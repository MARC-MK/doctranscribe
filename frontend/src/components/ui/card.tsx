import React from 'react';

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {}

export function Card({ className = '', children, ...props }: CardProps) {
  return (
    <div
      className={`rounded-lg border border-gray-700 bg-gray-900 shadow-sm ${className}`}
      {...props}
    >
      {children}
    </div>
  );
}

export default Card; 