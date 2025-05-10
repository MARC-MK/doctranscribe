import React from "react";

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "default" | "outline" | "secondary" | "ghost";
  size?: "default" | "sm" | "lg" | "icon";
}

export function Button({
  className = "",
  variant = "default",
  size = "default",
  children,
  ...props
}: ButtonProps) {
  const variantClasses = {
    default: "bg-blue-600 hover:bg-blue-700 text-white",
    outline: "border border-gray-600 hover:bg-gray-800 text-gray-300",
    secondary: "bg-gray-800 hover:bg-gray-700 text-gray-300",
    ghost: "hover:bg-gray-800 text-gray-300",
  };

  const sizeClasses = {
    default: "h-10 py-2 px-4 text-sm",
    sm: "h-8 py-1 px-3 text-xs",
    lg: "h-12 py-3 px-6 text-base",
    icon: "h-10 w-10 p-2",
  };

  const baseClass =
    "inline-flex items-center justify-center rounded-md font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:pointer-events-none";

  return (
    <button
      className={`${baseClass} ${variantClasses[variant]} ${sizeClasses[size]} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}
