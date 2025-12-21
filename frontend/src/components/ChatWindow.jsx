import React, { useState, useRef, useEffect } from 'react';
import { useChat } from '../hooks/useChat';
import ProductCard from './ProductCard';

const ChatWindow = ({ isOpen, onClose }) => {
  const { messages, sendMessage, loading } = useChat();
  const [input, setInput] = useState('');
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  // Scroll on load (restore history) and on new messages
  useEffect(() => {
    scrollToBottom();
  }, [messages, loading, isOpen]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!input.trim()) return;
    sendMessage(input);
    setInput('');
  };

  return (
    <div className="w-full h-full bg-white rounded-2xl shadow-2xl flex flex-col border border-gray-200 overflow-hidden font-sans">
      
      {/* 1. HEADER: Fixed Height (shrink-0) */}
      <div className="bg-black p-4 flex justify-between items-center text-white shadow-md shrink-0 h-16 z-10">
        <div>
          <h3 className="font-bold text-lg leading-none">Fortuna AI</h3>
          <p className="text-xs text-gray-300 opacity-90 mt-1">Gift Concierge</p>
        </div>
        <button 
          onClick={onClose} 
          className="hover:bg-gray-800 p-1 rounded-full w-8 h-8 flex items-center justify-center transition-colors"
        >
          ✕
        </button>
      </div>

      {/* 2. MESSAGES: Takes remaining space, Internal Scroll */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-gray-50 scrollbar-thin scrollbar-thumb-gray-300 min-h-0">
        {messages.map((msg, idx) => (
          <div key={idx} className={`flex ${msg.type === 'user' ? 'justify-end' : 'justify-start'}`}>
            
            {msg.type === 'products' ? (
              <div className="w-full max-w-[95%]">
                {msg.items.map((product) => (
                  <ProductCard key={product.id} product={product} />
                ))}
              </div>
            ) : (
              // --- THE FIX: Added 'whitespace-pre-wrap leading-relaxed' here ---
              <div className={`max-w-[85%] px-4 py-3 text-sm shadow-sm whitespace-pre-wrap leading-relaxed ${
                msg.type === 'user' 
                  ? 'bg-black text-white rounded-2xl rounded-br-none' 
                  : 'bg-white border border-gray-100 text-gray-800 rounded-2xl rounded-bl-none'
              }`}>
                {msg.text}
              </div>
            )}
            
          </div>
        ))}
        
        {loading && (
          <div className="flex justify-start">
            <div className="bg-white border border-gray-100 px-4 py-3 rounded-2xl rounded-bl-none shadow-sm flex items-center space-x-1">
              <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce"></div>
              <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce delay-75"></div>
              <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce delay-150"></div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* 3. INPUT: Fixed Height (shrink-0) */}
      <form onSubmit={handleSubmit} className="p-3 bg-white border-t border-gray-100 flex gap-2 shadow-sm shrink-0 z-10">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Describe her style..."
          className="flex-1 border border-gray-300 rounded-full px-4 py-2 text-sm focus:outline-none focus:border-black focus:ring-1 focus:ring-black transition-all"
          disabled={loading}
        />
        <button 
          type="submit" 
          disabled={loading || !input.trim()}
          className="bg-black text-white px-4 py-2 rounded-full hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed transition-all font-medium text-sm shadow-sm"
        >
          Send
        </button>
      </form>
    </div>
  );
};

export default ChatWindow;