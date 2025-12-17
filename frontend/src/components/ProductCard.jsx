import React from 'react';

const ProductCard = ({ product }) => {
  // Fallback if product_url isn't in your DB yet. 
  // It links to a demo page with the ID.
  const linkUrl = product.product_url || `/products/${product.id}`;

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
        {/* Match Score Badge */}
        {product.score && (
          <div className="absolute top-2 right-2 bg-white/90 backdrop-blur px-2 py-1 rounded text-xs font-bold text-blue-800 shadow-sm">
            {Math.round(product.score * 100)}% Match
          </div>
        )}
      </div>
      
      <div className="p-4">
        <div className="flex justify-between items-start mb-2">
          <h3 className="font-bold text-gray-800 text-sm line-clamp-2">{product.title}</h3>
          <span className="font-bold text-blue-600 whitespace-nowrap ml-2">
            {/* EGP Currency Format */}
            {product.price?.toLocaleString()} EGP
          </span>
        </div>
        
        <p className="text-xs text-gray-500 mb-3 line-clamp-2">
          {product.description}
        </p>
        
        <div className="flex gap-2 text-xs mb-3">
            <span className="bg-gray-100 px-2 py-1 rounded text-gray-600 uppercase tracking-wide text-[10px]">
              {product.style}
            </span>
        </div>

        <div className="w-full bg-black text-white py-2 rounded text-center text-sm font-medium group-hover:bg-gray-800 transition-colors">
          View Product
        </div>
      </div>
    </a>
  );
};

export default ProductCard;