import React from "react";

interface ProgressProps extends React.HTMLAttributes<HTMLDivElement> {
  value?: number;
  max?: number;
}

export function Progress({
  value = 0,
  max = 100,
  className = "",
  ...props
}: ProgressProps) {
  const percentage = Math.min(100, Math.round((value / max) * 100));

  return (
    <div
      className={`h-2 w-full overflow-hidden rounded-full bg-gray-800 ${className}`}
      role="progressbar"
      aria-valuemin={0}
      aria-valuemax={max}
      aria-valuenow={value}
      {...props}
    >
      <div
        className="h-full bg-blue-600 transition-all"
        style={{ width: `${percentage}%` }}
      />
    </div>
  );
}

export default Progress;
