import React, { useState, useEffect } from 'react';
import ChatWindow from './ChatWindow';
import { themes } from '../config/themes'; // Import the config

const ChatWidget = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [isLoaded, setIsLoaded] = useState(false);
  
  // State for the current theme
  const [currentTheme, setCurrentTheme] = useState(themes.default);

  useEffect(() => {
    if (typeof window !== 'undefined') {
      setIsLoaded(true);

      // 1. Detect Client ID from URL
      const params = new URLSearchParams(window.location.search);
      const clientId = params.get('client_id');

      // 2. Select Theme (Fallback to default if ID not found)
      const selectedTheme = themes[clientId] || themes.default;
      setCurrentTheme(selectedTheme);
    }
  }, []);

  useEffect(() => {
    if (!isLoaded) return;
    const message = isOpen ? "chat-opened" : "chat-closed";
    window.parent.postMessage(message, "*");
    localStorage.setItem('widget_is_open', isOpen);
  }, [isOpen, isLoaded]);

  const toggleOpen = () => {
    setIsOpen(prev => !prev);
  };

  if (!isLoaded) return null;

  return (
    // 3. INJECT CSS VARIABLES HERE
    // This makes --brand-color available to all children components
    <div 
      className="flex flex-col h-full w-full relative font-sans"
      style={{
        '--brand-color': currentTheme.primary,
        '--brand-hover': currentTheme.hover,
      }}
    >
      
      {isOpen && (
        <div className="absolute bottom-20 right-0 w-full h-[calc(100%-90px)] pr-4 pb-2 box-border">
          {/* Pass theme text props down */}
          <ChatWindow 
            isOpen={isOpen} 
            onClose={() => setIsOpen(false)} 
            theme={currentTheme} 
          />
        </div>
      )}

      <div className="absolute bottom-4 right-4 shrink-0">
        <button
          onClick={toggleOpen}
          // Use the variable for dynamic background
          className="w-14 h-14 bg-[var(--brand-color)] hover:bg-[var(--brand-hover)] text-white rounded-full shadow-lg flex items-center justify-center transition-transform duration-200"
        >
          {isOpen ? (
            <span className="text-xl">✕</span> 
          ) : (
            <svg className="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
            </svg>
          )}
        </button>
      </div>
    </div>
  );
};

export default ChatWidget;