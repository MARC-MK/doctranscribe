import React, { useState, useEffect } from 'react';
import { Sun, Moon, Monitor } from 'lucide-react';

type Theme = 'dark' | 'light' | 'system';

const ThemeSwitcher: React.FC = () => {
  const [theme, setTheme] = useState<Theme>('dark');
  
  // Initialize theme from localStorage or default to 'dark'
  useEffect(() => {
    const savedTheme = localStorage.getItem('theme') as Theme | null;
    if (savedTheme) {
      setTheme(savedTheme);
      applyTheme(savedTheme);
    }
  }, []);
  
  const applyTheme = (newTheme: Theme) => {
    const root = window.document.documentElement;
    
    // Remove current theme classes
    root.classList.remove('light', 'dark');
    
    // Apply new theme
    if (newTheme === 'system') {
      const systemTheme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
      root.classList.add(systemTheme);
    } else {
      root.classList.add(newTheme);
    }
    
    // Save to localStorage
    localStorage.setItem('theme', newTheme);
  };
  
  const handleThemeChange = (newTheme: Theme) => {
    setTheme(newTheme);
    applyTheme(newTheme);
  };
  
  return (
    <div className="flex items-center gap-2 bg-background-light rounded-lg p-1">
      <button
        onClick={() => handleThemeChange('light')}
        className={`p-2 rounded-md ${
          theme === 'light' ? 'bg-background text-yellow-300' : 'text-gray-400 hover:text-white'
        }`}
        title="Light mode"
      >
        <Sun size={16} />
      </button>
      
      <button
        onClick={() => handleThemeChange('dark')}
        className={`p-2 rounded-md ${
          theme === 'dark' ? 'bg-background text-blue-400' : 'text-gray-400 hover:text-white'
        }`}
        title="Dark mode"
      >
        <Moon size={16} />
      </button>
      
      <button
        onClick={() => handleThemeChange('system')}
        className={`p-2 rounded-md ${
          theme === 'system' ? 'bg-background text-purple-400' : 'text-gray-400 hover:text-white'
        }`}
        title="System preference"
      >
        <Monitor size={16} />
      </button>
    </div>
  );
};

export default ThemeSwitcher; 