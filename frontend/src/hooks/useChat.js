import { useState, useEffect, useCallback } from 'react';
import { v4 as uuidv4 } from 'uuid';

// 1 Hour in milliseconds
const IDLE_TIMEOUT_MS = 60 * 60 * 1000; 

export const useChat = () => {
  const initialMessage = { 
    type: 'bot', 
    text: "Welcome! I can help you find the perfect gift. Who are you shopping for today?" 
  };

  const [messages, setMessages] = useState([initialMessage]);
  const [loading, setLoading] = useState(false);
  
  // Note: Session ID is now purely for analytics, not for backend logic.
  const [sessionId, setSessionId] = useState(null);

  // 1. ON LOAD: Check if we have valid history
  useEffect(() => {
    if (typeof window === 'undefined') return;

    let storedId = localStorage.getItem('chat_session_id');
    if (!storedId) {
      storedId = uuidv4();
      localStorage.setItem('chat_session_id', storedId);
    }
    setSessionId(storedId);

    const savedString = localStorage.getItem('chat_history');
    if (savedString) {
      try {
        const saved = JSON.parse(savedString);
        const now = Date.now();
        
        if ((now - saved.timestamp) < IDLE_TIMEOUT_MS) {
          setMessages(saved.data);
        } else {
          console.log("Session expired. Clearing chat history.");
          localStorage.removeItem('chat_history');
        }
      } catch (e) {
        console.error("Error parsing chat history:", e);
        localStorage.removeItem('chat_history');
      }
    }
  }, []);

  // 2. ON UPDATE: Save history
  useEffect(() => {
    if (messages.length > 1) {
      const payload = JSON.stringify({
        timestamp: Date.now(),
        data: messages
      });
      localStorage.setItem('chat_history', payload);
    }
  }, [messages]);

  // 3. Send Logic (STATELESS VERSION)
  const sendMessage = useCallback(async (text) => {
    if (!text || !text.trim()) return;

    // A. Update UI Optimistically
    const newUserMsg = { type: 'user', text };
    const newHistory = [...messages, newUserMsg];
    setMessages(newHistory);
    setLoading(true);

    try {
      const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
      
      // B. Prepare History for Backend
      const apiHistory = newHistory
        .filter(msg => msg.type === 'user' || msg.type === 'bot')
        .map(msg => ({
          role: msg.type === 'user' ? 'user' : 'assistant',
          content: msg.text || "" 
        }));

      const response = await fetch(`${API_BASE}/api/chat/message`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          messages: apiHistory 
        }),
      });

      const data = await response.json();

      // C. Handle Response (UPDATED FOR TEXT BUBBLES ARRAY)
      if (data.text_bubbles && Array.isArray(data.text_bubbles)) {
        // Add each bubble sequentially
        const newBotMessages = data.text_bubbles.map(text => ({ type: 'bot', text }));
        setMessages(prev => [...prev, ...newBotMessages]);
      } 
      // Fallback for singular message if ever needed
      else if (data.message) {
        setMessages(prev => [...prev, { type: 'bot', text: data.message }]);
      }

      if (data.products && data.products.length > 0) {
        setMessages(prev => [...prev, { type: 'products', items: data.products }]);
      }

    } catch (error) {
      console.error("Chat Error:", error);
      setMessages(prev => [...prev, { type: 'bot', text: "I'm having a little trouble connecting. Could you say that again?" }]);
    } finally {
      setLoading(false);
    }
  }, [messages]); 

  return { messages, sendMessage, loading };
};

export default useChat;