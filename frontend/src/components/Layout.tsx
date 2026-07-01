import React from 'react';
import { Activity } from 'lucide-react';

export const Layout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return (
    <div className="min-h-screen bg-dark-900 text-gray-100 font-sans flex flex-col">
      {/* Top Navigation */}
      <header className="border-b border-dark-700 bg-dark-800/80 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3 cursor-pointer">
            <div className="p-2 bg-brand-500/10 rounded-xl border border-brand-500/20">
              <Activity className="text-brand-400 w-6 h-6" />
            </div>
            <div>
              <h1 className="text-lg font-semibold tracking-tight text-white">Veloce Engine</h1>
              <p className="text-[10px] uppercase tracking-wider text-gray-400 font-medium -mt-1">Analytics Intelligence</p>
            </div>
          </div>
          <nav className="flex items-center gap-6 text-sm text-gray-400 font-medium">
            <a href="/" className="hover:text-white transition-colors">Workspace</a>
            <a href="http://127.0.0.1:8000/docs" target="_blank" rel="noreferrer" className="hover:text-white transition-colors">API Docs</a>
          </nav>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 w-full">
        {children}
      </main>

      {/* Footer */}
      <footer className="border-t border-dark-700 py-6 text-center text-xs text-gray-500">
        &copy; {new Date().getFullYear()} Veloce Engine. Powered by FastAPI & React.
      </footer>
    </div>
  );
};
