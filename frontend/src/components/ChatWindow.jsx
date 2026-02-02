import React, { useState, useRef, useEffect } from 'react';
import { useChat } from '../hooks/useChat';
import ProductCard from './ProductCard';
import TryOnModal from './TryOnModal'; 

const ChatWindow = ({ isOpen, onClose, theme }) => {
  // NEW: Get cache state and setter from useChat
  const { messages, sendMessage, loading, allowImage, chatEnded, tryOnCache, addTryOnImage } = useChat();
  
  const [input, setInput] = useState('');
  const [tryOnProduct, setTryOnProduct] = useState(null);

  const messagesEndRef = useRef(null);
  const fileInputRef = useRef(null); 

  // Find User Photo
  const userPhotoMsg = [...messages].reverse().find(m => m.type === 'user-image');
  const userPhoto = userPhotoMsg ? userPhotoMsg.imageUrl : null;

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading, isOpen]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!input.trim()) return;
    sendMessage(input); 
    setInput('');
  };

  const handleIconClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      sendMessage(null, file); 
    }
    e.target.value = null; 
  };

  return (
    <div className="w-full h-full bg-white rounded-2xl shadow-2xl flex flex-col border border-gray-200 overflow-hidden font-sans relative">
      
      {/* HEADER */}
      <div className="bg-[var(--brand-color)] p-4 flex justify-between items-center text-white shadow-md shrink-0 h-16 z-10">
        <div>
          <h3 className="font-bold text-lg leading-none">{theme.title}</h3>
          <p className="text-xs text-white/90 mt-1">{theme.subtitle}</p>
        </div>
        <button 
          onClick={onClose} 
          className="hover:bg-white/20 p-1 rounded-full w-8 h-8 flex items-center justify-center transition-colors"
        >
          ✕
        </button>
      </div>

      {/* MESSAGES */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-gray-50 scrollbar-thin scrollbar-thumb-gray-300 min-h-0">
        {messages.map((msg, idx) => (
          <div key={idx} className={`flex ${msg.type === 'user' || msg.type === 'user-image' ? 'justify-end' : 'justify-start'}`}>
            
            {msg.type === 'products' ? (
              <div className="w-full max-w-[95%]">
                {msg.items.map((product) => (
                  <ProductCard 
                    key={product.id} 
                    product={product} 
                    theme={theme}
                    hasUserPhoto={!!userPhoto}
                    onTryOn={(prod) => setTryOnProduct(prod)}
                  />
                ))}
              </div>
            ) : msg.type === 'user-image' ? (
              <div className="max-w-[70%] bg-[var(--brand-color)] p-2 rounded-2xl rounded-br-none shadow-sm">
                <img src={msg.imageUrl} alt="Uploaded" className="rounded-lg w-full h-auto object-cover" />
              </div>
            ) : (
              <div className={`max-w-[85%] px-4 py-3 text-sm shadow-sm whitespace-pre-wrap leading-relaxed ${
                msg.type === 'user' 
                  ? 'bg-[var(--brand-color)] text-white rounded-2xl rounded-br-none' 
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

      {/* INPUT AREA */}
      <form onSubmit={handleSubmit} className="p-3 bg-white border-t border-gray-100 flex gap-2 shadow-sm shrink-0 z-10 items-center">
        <input type="file" accept="image/*" ref={fileInputRef} onChange={handleFileChange} className="hidden" />
        {allowImage && !chatEnded && (
          <button type="button" onClick={handleIconClick} className="text-gray-400 hover:text-[var(--brand-color)] transition-colors p-2 animate-fade-in" title="Upload Photo" disabled={loading}>
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" /></svg>
          </button>
        )}
        <input type="text" value={input} onChange={(e) => setInput(e.target.value)} placeholder={chatEnded ? "Conversation ended." : "Type your reply..."} maxLength={200} className="flex-1 border border-gray-300 rounded-full px-4 py-2 text-sm focus:outline-none focus:border-[var(--brand-color)] focus:ring-1 focus:ring-[var(--brand-color)] transition-all disabled:bg-gray-100 disabled:text-gray-500" disabled={loading || chatEnded} />
        <button type="submit" disabled={loading || !input.trim() || chatEnded} className="bg-[var(--brand-color)] text-white px-4 py-2 rounded-full hover:bg-[var(--brand-hover)] disabled:opacity-50 disabled:cursor-not-allowed transition-all font-medium text-sm shadow-sm">Send</button>
      </form>

      {/* MODAL */}
      {tryOnProduct && userPhoto && (
        <TryOnModal 
          userImage={userPhoto} 
          product={tryOnProduct} 
          onClose={() => setTryOnProduct(null)} 
          // PASS CACHING PROPS
          cachedResult={tryOnCache[tryOnProduct.id]} // Look up by ID
          onSuccess={(url) => addTryOnImage(tryOnProduct.id, url)} // Save on success
        />
      )}

    </div>
  );
};

export default ChatWindow;