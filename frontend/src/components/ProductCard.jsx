import React from 'react';

const ProductCard = ({ product }) => {
  
  const generateHandle = (title) => {
    return title
      .toLowerCase()
      .trim()
      .replace(/[^\w\s-]/g, '') 
      .replace(/[\s_-]+/g, '-') 
      .replace(/^-+|-+$/g, ''); 
  };

  const handle = generateHandle(product.title || "");
  const linkUrl = product.product_url || `https://koaysilver.com/products/${handle}`;

  return (
    <a 
      href={linkUrl} 
      target="_blank" 
      rel="noopener noreferrer"
      className="block bg-white rounded-lg shadow-md overflow-hidden border border-gray-100 mb-4 transition-transform hover:scale-[1.02] hover:shadow-lg no-underline"
    >
      <div className="relative h-48 bg-gray-100">
        <img 
          src={product.image_url || 'https://placehold.co/400x300?text=Jewelry'} 
          alt={product.title}
          className="w-full h-full object-cover"
          onError={(e) => {e.target.src = 'https://placehold.co/400x300?text=No+Image'}}
        />
      </div>
      
      <div className="p-4">
        <div className="flex justify-between items-start mb-2">
          <h3 className="font-bold text-gray-800 text-sm line-clamp-2">{product.title}</h3>
          <span className="font-bold text-blue-600 whitespace-nowrap ml-2">
            {product.price?.toLocaleString()} EGP
          </span>
        </div>
        
        <p className="text-xs text-gray-500 mb-3 line-clamp-2">
          {product.description}
        </p>
        
        {/* VIEW BUTTON: Updated to Green */}
        <div className="w-full bg-[#154027] text-white py-2 rounded text-center text-sm font-medium group-hover:bg-[#1e5736] transition-colors">
          View Product
        </div>
      </div>
    </a>
  );
};

export default ProductCard;