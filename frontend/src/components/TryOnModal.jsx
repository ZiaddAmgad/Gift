import React, { useState, useEffect } from 'react';

const TryOnModal = ({ userImage, product, onClose, cachedResult, onSuccess }) => {
  const [status, setStatus] = useState('loading'); // 'loading', 'success', 'error'
  const [resultImage, setResultImage] = useState(null);
  const [isComparing, setIsComparing] = useState(false);

  useEffect(() => {
    // 1. CHECK CACHE FIRST
    if (cachedResult) {
      setResultImage(cachedResult);
      setStatus('success');
      return; // STOP. Do not fetch.
    }

    // 2. FETCH IF NO CACHE
    const generatePreview = async () => {
      try {
        const params = new URLSearchParams(window.location.search);
        const clientId = params.get('client_id') || 'artsy';
        const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
        
        const response = await fetch(`${API_BASE}/api/chat/try-on`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            user_image: userImage,
            product_image_url: product.image_url,
            product_title: product.title,
            client_id: clientId
          }),
        });

        if (!response.ok) throw new Error('Generation failed');

        const data = await response.json();
        setResultImage(data.image_url);
        setStatus('success');
        
        // 3. SAVE TO SESSION CACHE
        if (onSuccess) {
            onSuccess(data.image_url); // Call parent function
        }

      } catch (error) {
        console.error("Try-On Error:", error);
        setStatus('error');
      }
    };

    generatePreview();
  }, [userImage, product, cachedResult, onSuccess]);

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 font-sans animate-fade-in">
      <div className="bg-white rounded-2xl overflow-hidden max-w-sm w-full relative shadow-2xl flex flex-col">
        
        {/* CLOSE BUTTON */}
        <button onClick={onClose} className="absolute top-3 right-3 z-20 bg-black/40 hover:bg-black/60 text-white rounded-full w-8 h-8 flex items-center justify-center transition-colors backdrop-blur-md">✕</button>

        {/* IMAGE AREA */}
        <div 
          className="relative aspect-square bg-gray-100 select-none touch-none"
          onMouseDown={() => setIsComparing(true)}
          onMouseUp={() => setIsComparing(false)}
          onMouseLeave={() => setIsComparing(false)}
          onTouchStart={() => setIsComparing(true)}
          onTouchEnd={() => setIsComparing(false)}
        >
          {status === 'loading' && (
            <div className="absolute inset-0 flex flex-col items-center justify-center z-10 bg-white/90">
              <div className="relative">
                <div className="w-16 h-16 border-4 border-gray-200 border-t-yellow-500 rounded-full animate-spin"></div>
                <div className="absolute inset-0 flex items-center justify-center text-xl">✨</div>
              </div>
              <p className="text-sm text-gray-600 font-medium mt-4 animate-pulse">Styling your look...</p>
            </div>
          )}

          {status === 'error' && (
            <div className="absolute inset-0 flex flex-col items-center justify-center z-10 p-6 text-center">
              <span className="text-4xl mb-2">😔</span>
              <p className="text-gray-800 font-medium">Couldn't generate the preview.</p>
              <button onClick={onClose} className="mt-4 text-sm text-gray-500 underline">Close</button>
            </div>
          )}

          {resultImage && (
            <img src={resultImage} alt="Virtual Try-On" className={`absolute inset-0 w-full h-full object-cover transition-opacity duration-200 ${isComparing ? 'opacity-0' : 'opacity-100'}`} />
          )}

          <img src={userImage} alt="Original" className={`absolute inset-0 w-full h-full object-cover transition-opacity duration-200 ${status === 'success' && !isComparing ? 'opacity-0' : 'opacity-100'}`} />
          
          {status === 'success' && (
            <div className="absolute bottom-3 left-1/2 -translate-x-1/2 bg-black/50 backdrop-blur-md text-white text-[10px] px-3 py-1 rounded-full pointer-events-none">
              {isComparing ? "Original Photo" : "Hold to Compare"}
            </div>
          )}
        </div>

        {/* FOOTER */}
        <div className="p-5 text-center bg-white border-t border-gray-100">
          <h3 className="font-bold text-gray-900 text-sm line-clamp-1">{product.title}</h3>
          <p className="text-xs text-gray-500 mt-1">AI-generated preview. Fit is approximate.</p>
          <a href={product.linkUrl} target="_top" className="mt-4 block w-full bg-black text-white py-3 rounded-xl text-sm font-bold hover:bg-gray-800 transition-colors">View Product Details</a>
        </div>
      </div>
    </div>
  );
};

export default TryOnModal;