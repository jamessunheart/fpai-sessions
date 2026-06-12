import { ReactNode } from 'react';

interface CardProps {
  children: ReactNode;
  className?: string;
  hover?: boolean;
  onClick?: () => void;
}

export default function Card({ children, className = '', hover = false, onClick }: CardProps) {
  return (
    <div 
      className={`bg-white dark:bg-slate-800 backdrop-blur-xl shadow-md dark:shadow-slate-900/50 border border-slate-200 dark:border-slate-700 rounded-2xl p-6 ${hover ? 'hover:shadow-xl dark:hover:shadow-slate-900/70 hover:border-slate-300 dark:hover:border-slate-600 transition-all duration-300 hover:-translate-y-1' : ''} ${className}`}
      onClick={onClick}
    >
      {children}
    </div>
  );
}