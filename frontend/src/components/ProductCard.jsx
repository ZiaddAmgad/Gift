import React from 'react';

const ProductCard = ({ product, theme }) => {
  
  // 1. Fallback Generator (Only used if product.handle is missing)
  const generateHandle = (title) => {
    return title
      .toLowerCase()
      .replace(/'/g, '')           
      .replace(/’/g, '')           
      .replace(/[^a-z0-9]+/g, '-') 
      .replace(/^-+|-+$/g, '');    
  };

  // 2. PREFER THE REAL HANDLE FROM PINECONE
  const handle = product.handle || generateHandle(product.title || "");
  
  // --- BASE URL GENERATION ---
  const baseUrl = theme?.storeUrl || "https://koaysilver.com"; 
  
  // 3. Construct the URL
  // If we have a full URL in metadata, use it. Otherwise, build it with the handle.
  const rawUrl = product.product_url || `${baseUrl}/products/${handle}`;

  // --- ANALYTICS INJECTION (UTM TAGS) ---
  const utmSource = "utm_source=Leeki_AI"; 
  const utmMedium = "utm_medium=concierge_widget";
  const utmCampaign = "utm_campaign=recommendation";
  
  const separator = rawUrl.includes('?') ? '&' : '?';
  const linkUrl = `${rawUrl}${separator}${utmSource}&${utmMedium}&${utmCampaign}`;

  return (
    <a 
      href={linkUrl} 
      target="_blank" 
      rel="noopener noreferrer"
      className="block bg-white rounded-lg shadow-md overflow-hidden border border-gray-100 mb-4 transition-transform hover:scale-[1.02] hover:shadow-lg no-underline group"
    >
      {/* IMAGE SECTION */}
      <div className="relative h-48 bg-gray-100">
        <img 
          src={product.image_url || 'https://placehold.co/400x300?text=Jewelry'} 
          alt={product.title}
          className="w-full h-full object-cover"
          onError={(e) => {e.target.src = 'https://placehold.co/400x300?text=No+Image'}}
        />
      </div>
      
      {/* DETAILS SECTION */}
      <div className="p-4">
        {/* TITLE */}
        <div className="mb-2">
          <h3 className="font-bold text-gray-800 text-sm line-clamp-2">{product.title}</h3>
        </div>
        
        {/* DESCRIPTION */}
        <p className="text-xs text-gray-500 mb-3 line-clamp-2">
          {product.description}
        </p>
        
        {/* BUTTON */}
        <div className="w-full bg-[var(--brand-color)] text-white py-2 rounded text-center text-sm font-medium group-hover:bg-[var(--brand-hover)] transition-colors">
          View Product
        </div>
      </div>
    </a>
  );
};

export default ProductCard;