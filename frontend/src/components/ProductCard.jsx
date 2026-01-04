import React from 'react';

const ProductCard = ({ product }) => {
  
  // 1. Generate Shopify Handle from Title
  const generateHandle = (title) => {
    return title
      .toLowerCase()
      .trim()
      .replace(/[^\w\s-]/g, '') 
      .replace(/[\s_-]+/g, '-') 
      .replace(/^-+|-+$/g, ''); 
  };

  const handle = generateHandle(product.title || "");
  // Use the live store URL structure
  const linkUrl = product.product_url || `https://koaysilver.com/products/${handle}`;

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
        
        {/* DESCRIPTION (Keeps it from looking bland) */}
        <p className="text-xs text-gray-500 mb-3 line-clamp-2">
          {product.description}
        </p>
        
        {/* BUTTON */}
        <div className="w-full bg-[#154027] text-white py-2 rounded text-center text-sm font-medium group-hover:bg-[#1e5736] transition-colors">
          View Product
        </div>
      </div>
    </a>
  );
};

export default ProductCard;