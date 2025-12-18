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
    <div className="flex flex-col h-full w-full relative">
      
      {/* 
          CHAT AREA: 
          Using conditional rendering again. 
          When closed, this DIV disappears completely.
          Memory is handled by useChat's localStorage logic.
      */}
      {isOpen && (
        <div className="absolute bottom-20 right-0 w-full h-[650px] pr-4 pb-2 box-border">
          <ChatWindow isOpen={isOpen} onClose={() => setIsOpen(false)} />
        </div>
      )}

      {/* BUTTON AREA */}
      <div className="absolute bottom-4 right-4 shrink-0">
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