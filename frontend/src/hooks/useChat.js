import { useState, useEffect, useCallback } from 'react';
import { v4 as uuidv4 } from 'uuid';

const IDLE_TIMEOUT_MS = 60 * 60 * 1000; 

const compressImage = (file) => {
  return new Promise((resolve) => {
    const reader = new FileReader();
    reader.readAsDataURL(file);
    reader.onload = (event) => {
      const img = new Image();
      img.src = event.target.result;
      img.onload = () => {
        const canvas = document.createElement('canvas');
        const MAX_WIDTH = 800; 
        const scaleSize = MAX_WIDTH / img.width;
        canvas.width = MAX_WIDTH;
        canvas.height = img.height * scaleSize;

        const ctx = canvas.getContext('2d');
        ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
        
        resolve(canvas.toDataURL('image/jpeg', 0.7)); 
      };
    };
  });
};

export const useChat = () => {
  const initialMessage = { 
    type: 'bot', 
    text: "Welcome! I can help you find the perfect gift. Who are you shopping for today?" 
  };

  const [messages, setMessages] = useState([initialMessage]);
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  
  // Flags
  const [allowImage, setAllowImage] = useState(false);
  const [chatEnded, setChatEnded] = useState(false);
  
  const [clientId, setClientId] = useState('artsy'); 

  // 1. CAPTURE CLIENT ID & LOAD HISTORY
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const params = new URLSearchParams(window.location.search);
      const idFromUrl = params.get('client_id');
      const currentClient = idFromUrl || 'artsy';
      setClientId(currentClient);

      const sessionKey = `chat_session_${currentClient}`;
      let storedId = localStorage.getItem(sessionKey);
      if (!storedId) {
        storedId = uuidv4();
        localStorage.setItem(sessionKey, storedId);
      }
      setSessionId(storedId);

      // Load History
      const historyKey = `chat_history_${currentClient}`;
      const savedString = localStorage.getItem(historyKey);
      
      if (savedString) {
        try {
          const saved = JSON.parse(savedString);
          if ((Date.now() - saved.timestamp) < IDLE_TIMEOUT_MS) {
            setMessages(saved.data);
            // RESTORE FLAGS
            setAllowImage(saved.allowImage === true);
            setChatEnded(saved.chatEnded === true);
          } else {
            localStorage.removeItem(historyKey);
          }
        } catch (e) {
          localStorage.removeItem(historyKey);
        }
      }
    }
  }, []); 

  // 2. SAVE HISTORY (With Client Key)
  useEffect(() => {
    // Save if we have messages OR if flags changed
    if (messages.length > 1 || allowImage || chatEnded) {
      const historyKey = `chat_history_${clientId}`;
      const payload = JSON.stringify({
        timestamp: Date.now(),
        data: messages,
        allowImage: allowImage,
        chatEnded: chatEnded
      });
      localStorage.setItem(historyKey, payload);
    }
  }, [messages, clientId, allowImage, chatEnded]); 

  const sendMessage = useCallback(async (text, imageFile = null) => {
    if ((!text || !text.trim()) && !imageFile) return;

    setLoading(true);
    let newUserMsg;
    let base64Image = null;

    if (imageFile) {
      base64Image = await compressImage(imageFile);
      newUserMsg = { type: 'user-image', imageUrl: base64Image };
    } else {
      newUserMsg = { type: 'user', text };
    }

    setMessages(prev => [...prev, newUserMsg]);

    try {
      const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
      
      const currentHistory = [...messages, newUserMsg];

      const apiHistory = currentHistory
        .filter(msg => msg.type === 'user' || msg.type === 'bot' || msg.type === 'user-image')
        .map((msg, index) => {
          if (index === currentHistory.length - 1 && msg.type === 'user-image') {
            return {
              role: 'user',
              content: "Image uploaded", 
              image: msg.imageUrl 
            };
          }
          
          if (msg.type === 'user-image') {
            return { role: 'user', content: "[User sent an image]" };
          }

          return {
            role: msg.type === 'user' ? 'user' : 'assistant',
            content: msg.text || "" 
          };
        });

      const response = await fetch(`${API_BASE}/api/chat/message`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
            messages: apiHistory,
            client_id: clientId 
        }),
      });

      const data = await response.json();
      setLoading(false); 
      
      setAllowImage(data.allow_image || false);
      
      if (data.chat_ended) {
        setChatEnded(true);
      }

      if (data.text_bubbles && Array.isArray(data.text_bubbles)) {
        for (let i = 0; i < data.text_bubbles.length; i++) {
          const bubbleText = data.text_bubbles[i];
          
          // --- FIX: Skip empty bubbles ---
          if (!bubbleText || bubbleText.trim() === "") continue;

          setMessages(prev => [...prev, { type: 'bot', text: bubbleText }]);
          
          if (i < data.text_bubbles.length - 1) {
            setLoading(true); 
            await new Promise(resolve => setTimeout(resolve, 3000));
            setLoading(false);
          }
        }
      } 
      else if (data.message && data.message.trim() !== "") {
        setMessages(prev => [...prev, { type: 'bot', text: data.message }]);
      }

      if (data.products && data.products.length > 0) {
        if (data.text_bubbles?.length > 0) {
            setLoading(true);
            await new Promise(resolve => setTimeout(resolve, 3000));
            setLoading(false);
        }
        setMessages(prev => [...prev, { type: 'products', items: data.products }]);
      }

    } catch (error) {
      console.error("Chat Error:", error);
      setMessages(prev => [...prev, { type: 'bot', text: "I'm having a little trouble connecting. Could you say that again?" }]);
      setLoading(false);
    }
  }, [messages, clientId]); 

  return { messages, sendMessage, loading, allowImage, chatEnded };
};

export default useChat;