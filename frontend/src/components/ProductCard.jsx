import React from 'react';

const ProductCard = ({ product, theme, onTryOn, hasUserPhoto }) => {
  
  // 1. Fallback Handle Generator
  const generateHandle = (title) => {
    return title
      .toLowerCase()
      .replace(/'/g, '')           
      .replace(/’/g, '')           
      .replace(/[^a-z0-9]+/g, '-') 
      .replace(/^-+|-+$/g, '');    
  };

  const handle = product.handle ? product.handle : generateHandle(product.title || "");
  const baseUrl = theme?.storeUrl || "https://artsysilver.co"; 
  const rawUrl = `${baseUrl}/products/${handle}`;

  // UTM Tags
  const utmSource = "utm_source=Leeki_AI"; 
  const utmMedium = "utm_medium=gift_assistant_widget";
  const utmCampaign = "utm_campaign=recommendation";
  const separator = rawUrl.includes('?') ? '&' : '?';
  const linkUrl = `${rawUrl}${separator}${utmSource}&${utmMedium}&${utmCampaign}`;

  // Pass URL to modal if needed later
  product.linkUrl = linkUrl; 

  return (
    <div className="block bg-white rounded-lg shadow-md overflow-hidden border border-gray-100 mb-4 transition-transform hover:scale-[1.01] hover:shadow-lg group">
      
      {/* CLICKABLE AREA (Image + Title) */}
      <a href={linkUrl} target="_self" rel="noopener noreferrer" className="block no-underline">
        {/* IMAGE SECTION */}
        <div className="relative h-48 bg-gray-100 overflow-hidden">
          <img 
            src={product.image_url || 'https://placehold.co/400x300?text=Jewelry'} 
            alt={product.title}
            className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
            onError={(e) => {e.target.src = 'https://placehold.co/400x300?text=No+Image'}}
          />
        </div>
        
        {/* TEXT DETAILS */}
        <div className="p-4 pb-2">
          <div className="mb-1">
            <h3 className="font-bold text-gray-800 text-sm line-clamp-2 leading-tight">{product.title}</h3>
          </div>
          <p className="text-xs text-gray-500 mb-2 line-clamp-2">
            {product.description}
          </p>
        </div>
      </a>

      {/* ACTION BUTTONS */}
      <div className="px-4 pb-4 flex gap-2">
        {/* Standard Button */}
        <a 
          href={linkUrl} 
          className="flex-1 bg-[var(--brand-color)] text-white py-2.5 rounded-lg text-center text-xs font-bold uppercase tracking-wide hover:bg-[var(--brand-hover)] transition-colors flex items-center justify-center"
        >
          View Details
        </a>

        {/* Try On Button - Only visible if we have a user photo */}
        {hasUserPhoto && (
          <button 
            onClick={() => onTryOn(product)}
            className="flex-1 bg-gradient-to-r from-yellow-600 via-yellow-500 to-yellow-600 bg-[length:200%_auto] hover:bg-right transition-all duration-500 text-white py-2.5 rounded-lg text-xs font-bold uppercase tracking-wide flex items-center justify-center gap-1 shadow-sm"
          >
            <span>✨</span> Try On
          </button>
        )}
      </div>
    </div>
  );
};

export default ProductCard;