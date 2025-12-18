import React, { useState, useEffect } from 'react';
import ChatWindow from './ChatWindow';

const ChatWidget = () => {
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    if (typeof window !== 'undefined') {
      const message = isOpen ? "chat-opened" : "chat-closed";
      window.parent.postMessage(message, "*");
    }
  }, [isOpen]);

  return (
    // The Container fills the Iframe
    <div className="flex flex-col h-full w-full relative overflow-hidden">
      
      {/* 
          CHAT AREA: 
          If open, it takes up the top space. 
          We leave 80px at the bottom for the button area to prevent overlap/clicking issues.
      */}
      <div 
        className={`
          flex-1 w-full transition-all duration-300 ease-in-out
          ${isOpen ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-10 pointer-events-none'}
        `}
        style={{ marginBottom: '10px' }} // Small gap between chat and button
      >
        {isOpen && <ChatWindow isOpen={isOpen} onClose={() => setIsOpen(false)} />}
      </div>

      {/* 
          BUTTON AREA: 
          Stays at the bottom right.
      */}
      <div className="flex justify-end p-4 shrink-0">
        <button
          onClick={() => setIsOpen(!isOpen)}
          className="w-14 h-14 bg-black hover:bg-gray-800 text-white rounded-full shadow-lg flex items-center justify-center transition-transform duration-200"
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