import { useState, useEffect, useCallback } from 'react';
import { v4 as uuidv4 } from 'uuid';

const IDLE_TIMEOUT_MS = 60 * 60 * 1000; 

export const useChat = () => {
  const initialMessage = { 
    type: 'bot', 
    text: "Welcome! I can help you find the perfect gift. Who are you shopping for today?" 
  };

  // --- 🛠️ DEBUG: TEST PRODUCT CARD ---
  const testProductMessage = {
    type: 'products',
    items: [
      {
        id: "9338476069081",
        title: "Tex Flower Set",
        price: 2100,
        description: "A beautiful boho style set.",
        style: "Boho",
        image_url: "https://koaysilver.com/cdn/shop/files/IMG_7679.jpg?v=1715694380&width=600", // Empty to test placeholder, or add a real URL here
        product_url: "" // Empty to test the auto-generated handle link
      }
    ]
  };

  // Added 'testProductMessage' to the initial state so it renders immediately
  const [messages, setMessages] = useState([initialMessage, testProductMessage]);
  
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState(null);

  useEffect(() => {
    if (typeof window === 'undefined') return;

    let storedId = localStorage.getItem('chat_session_id');
    if (!storedId) {
      storedId = uuidv4();
      localStorage.setItem('chat_session_id', storedId);
    }
    setSessionId(storedId);

    // Commented out history restoration for testing so the test card always shows
    /* 
    const savedString = localStorage.getItem('chat_history');
    if (savedString) {
      try {
        const saved = JSON.parse(savedString);
        if ((Date.now() - saved.timestamp) < IDLE_TIMEOUT_MS) {
          setMessages(saved.data);
        } else {
          localStorage.removeItem('chat_history');
        }
      } catch (e) {
        localStorage.removeItem('chat_history');
      }
    }
    */
  }, []);

  useEffect(() => {
    if (messages.length > 1) {
      const payload = JSON.stringify({
        timestamp: Date.now(),
        data: messages
      });
      localStorage.setItem('chat_history', payload);
    }
  }, [messages]);

  const sendMessage = useCallback(async (text) => {
    if (!text || !text.trim()) return;

    const newUserMsg = { type: 'user', text };
    const newHistory = [...messages, newUserMsg];
    setMessages(newHistory);
    setLoading(true);

    try {
      const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
      
      const apiHistory = newHistory
        .filter(msg => msg.type === 'user' || msg.type === 'bot')
        .map(msg => ({
          role: msg.type === 'user' ? 'user' : 'assistant',
          content: msg.text || "" 
        }));

      const response = await fetch(`${API_BASE}/api/chat/message`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ messages: apiHistory }),
      });

      const data = await response.json();
      setLoading(false); 

      if (data.text_bubbles && Array.isArray(data.text_bubbles)) {
        for (let i = 0; i < data.text_bubbles.length; i++) {
          const bubbleText = data.text_bubbles[i];
          setMessages(prev => [...prev, { type: 'bot', text: bubbleText }]);
          
          if (i < data.text_bubbles.length - 1) {
            setLoading(true); 
            await new Promise(resolve => setTimeout(resolve, 3000));
            setLoading(false);
          }
        }
      } 
      else if (data.message) {
        setMessages(prev => [...prev, { type: 'bot', text: data.message }]);
      }

      if (data.products && data.products.length > 0) {
        if (data.text_bubbles?.length > 0) {
            setLoading(true);
            await new Promise(resolve => setTimeout(resolve, 1000));
            setLoading(false);
        }
        setMessages(prev => [...prev, { type: 'products', items: data.products }]);
      }

    } catch (error) {
      console.error("Chat Error:", error);
      setMessages(prev => [...prev, { type: 'bot', text: "I'm having a little trouble connecting. Could you say that again?" }]);
      setLoading(false);
    }
  }, [messages]); 

  return { messages, sendMessage, loading };
};

export default useChat;