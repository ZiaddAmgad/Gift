import React, { useState, useEffect } from 'react';

// NEW: Accept 'theme' prop
const TryOnModal = ({ userImage, product, onClose, cachedResult, onSuccess, theme }) => {
  const [status, setStatus] = useState('loading'); 
  const [resultImage, setResultImage] = useState(null);
  const [isComparing, setIsComparing] = useState(false);

  useEffect(() => {
    if (cachedResult) {
      setResultImage(cachedResult);
      setStatus('success');
      return; 
    }

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
        
        if (onSuccess) onSuccess(data.image_url);

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
        
        <button onClick={onClose} className="absolute top-3 right-3 z-30 bg-black/40 hover:bg-black/60 text-white rounded-full w-8 h-8 flex items-center justify-center transition-colors backdrop-blur-md">✕</button>

        {/* IMAGE AREA */}
        <div 
          className="relative aspect-square bg-gray-100 select-none touch-none overflow-hidden"
          onMouseDown={() => setIsComparing(true)}
          onMouseUp={() => setIsComparing(false)}
          onMouseLeave={() => setIsComparing(false)}
          onTouchStart={() => setIsComparing(true)}
          onTouchEnd={() => setIsComparing(false)}
        >
          {status === 'loading' && (
            <div className="absolute inset-0 flex flex-col items-center justify-center z-20 bg-white/90">
               {/* Loading Spinner code... */}
               <div className="w-16 h-16 border-4 border-gray-200 border-t-yellow-500 rounded-full animate-spin"></div>
               <p className="text-sm text-gray-600 font-medium mt-4 animate-pulse">Styling your look...</p>
            </div>
          )}

          {status === 'error' && (
            <div className="absolute inset-0 flex flex-col items-center justify-center z-20 p-6 text-center">
               <span className="text-4xl mb-2">😔</span>
               <p className="text-gray-800 font-medium">Couldn't generate the preview.</p>
               <button onClick={onClose} className="mt-4 text-sm text-gray-500 underline">Close</button>
            </div>
          )}

          {/* GENERATED RESULT */}
          {resultImage && (
            <img src={resultImage} alt="Virtual Try-On" className={`absolute inset-0 w-full h-full object-cover transition-opacity duration-200 ${isComparing ? 'opacity-0' : 'opacity-100'}`} />
          )}

          {/* ORIGINAL USER PHOTO */}
          <img src={userImage} alt="Original" className={`absolute inset-0 w-full h-full object-cover transition-opacity duration-200 ${status === 'success' && !isComparing ? 'opacity-0' : 'opacity-100'}`} />
          
          {/* --- NEW: WATERMARK LOGO --- */}
          {/* Only show on Success and when NOT comparing (showing the AI result) */}
          {status === 'success' && !isComparing && theme?.logoUrl && (
            <div className="absolute top-4 left-4 z-10 pointer-events-none opacity-80 mix-blend-multiply">
               <img 
                 src={theme.logoUrl} 
                 alt="Brand Logo" 
                 className="h-8 w-auto object-contain" // Adjust h-8 to size the logo
               />
            </div>
          )}

          {/* COMPARISON BADGE */}
          {status === 'success' && (
            <div className="absolute bottom-3 left-1/2 -translate-x-1/2 z-20 bg-black/50 backdrop-blur-md text-white text-[10px] px-3 py-1 rounded-full pointer-events-none">
              {isComparing ? "Original Photo" : "Hold to Compare"}
            </div>
          )}
        </div>

        {/* FOOTER */}
        <div className="p-5 text-center bg-white border-t border-gray-100">
          <h3 className="font-bold text-gray-900 text-sm line-clamp-1">{product.title}</h3>
          
          {/* NEW DISCLAIMER TEXT */}
          <p className="text-[10px] text-gray-400 mt-2 uppercase tracking-wide">
            Ai-generated image, size may not be accurate.
          </p>
          
          <a href={product.linkUrl} target="_top" className="mt-4 block w-full bg-black text-white py-3 rounded-xl text-sm font-bold hover:bg-gray-800 transition-colors">View Product Details</a>
        </div>
      </div>
    </div>
  );
};

export default TryOnModal;