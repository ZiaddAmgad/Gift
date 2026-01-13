import React from 'react';

const ProductCard = ({ product, theme }) => {
  
  const generateHandle = (title) => {
    return title
      .toLowerCase()
      .replace(/'/g, '')           // 1. Remove apostrophes (Queen's -> Queens)
      .replace(/’/g, '')           // 1b. Remove smart quotes
      .replace(/[^a-z0-9]+/g, '-') // 2. Replace ALL non-alphanumeric chars (spaces, brackets, commas) with a single dash
      .replace(/^-+|-+$/g, '');    // 3. Trim dashes from start and end
  };

  const handle = generateHandle(product.title || "");
  
  // --- MULTI-TENANT LINK GENERATION ---
  const baseUrl = theme?.storeUrl || "https://koaysilver.com"; 
  const linkUrl = product.product_url || `${baseUrl}/products/${handle}`;

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
        {/* TITLE ONLY (Price removed) */}
        <div className="mb-2">
          <h3 className="font-bold text-gray-800 text-sm line-clamp-2">{product.title}</h3>
        </div>
        
        {/* DESCRIPTION */}
        <p className="text-xs text-gray-500 mb-3 line-clamp-2">
          {product.description}
        </p>
        
        {/* DYNAMIC BUTTON COLOR */}
        <div className="w-full bg-[var(--brand-color)] text-white py-2 rounded text-center text-sm font-medium group-hover:bg-[var(--brand-hover)] transition-colors">
          View Product
        </div>
      </div>
    </a>
  );
};

export default ProductCard;