import React from 'react';

const ProductCard = ({ product, theme }) => {
  
  // 1. Fallback Generator (Only runs if Pinecone handle is missing)
  const generateHandle = (title) => {
    return title
      .toLowerCase()
      .replace(/'/g, '')           
      .replace(/’/g, '')           
      .replace(/[^a-z0-9]+/g, '-') 
      .replace(/^-+|-+$/g, '');    
  };

  // 2. GET THE HANDLE
  // Priority A: The correct handle saved in Pinecone (metadata)
  // Priority B: Generate one from title (Emergency backup)
  const handle = product.handle ? product.handle : generateHandle(product.title || "");
  
  // 3. BUILD THE URL DYNAMICALLY
  // We do NOT use product.product_url here because we want to ensure
  // it uses the correct domain from themes.js
  const baseUrl = theme?.storeUrl || "https://artsysilver.co"; 
  const rawUrl = `${baseUrl}/products/${handle}`;

  // 4. ADD ANALYTICS (UTM TAGS)
  const utmSource = "utm_source=Leeki_AI"; 
  const utmMedium = "utm_medium=gift_assistant_widget";
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