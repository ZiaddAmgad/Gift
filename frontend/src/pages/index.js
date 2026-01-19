import React from 'react';
import ChatWidget from '../components/ChatWidget';

// --- INLINE ICONS (No installation needed) ---
const MenuIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="4" y1="12" x2="20" y2="12"></line><line x1="4" y1="6" x2="20" y2="6"></line><line x1="4" y1="18" x2="20" y2="18"></line></svg>
);
const SearchIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>
);
const UserIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>
);
const BagIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z"></path><line x1="3" y1="6" x2="21" y2="6"></line><path d="M16 10a4 4 0 0 1-8 0"></path></svg>
);

const Home = () => {
  return (
    <div className="min-h-screen bg-white font-sans text-gray-900 relative">
      
      {/* --- 1. PROFESSIONAL NAVBAR --- */}
      <nav className="border-b border-gray-100 sticky top-0 bg-white/95 backdrop-blur-sm z-40">
        <div className="container mx-auto px-6 h-20 flex items-center justify-between">
          <div className="flex items-center gap-6">
            <span className="text-gray-800 cursor-pointer"><MenuIcon /></span>
            <span className="text-gray-500 cursor-pointer hover:text-black"><SearchIcon /></span>
          </div>
          
          {/* Static, Professional Brand Name */}
          <div className="text-2xl tracking-[0.2em] font-serif font-bold uppercase text-center">
            THE JEWELRY STORE
          </div>

          <div className="flex items-center gap-6">
            <span className="text-gray-500 cursor-pointer hover:text-black"><UserIcon /></span>
            <span className="text-gray-500 cursor-pointer hover:text-black"><BagIcon /></span>
          </div>
        </div>
      </nav>

      {/* --- 2. HERO SECTION (Generic Luxury) --- */}
      <section className="relative h-[650px] bg-[#f8f8f8] flex items-center justify-center">
        <div className="text-center px-4 max-w-3xl">
          <span className="text-xs font-bold tracking-[0.3em] text-gray-400 uppercase mb-6 block">
            Spring / Summer 2025
          </span>
          <h1 className="text-5xl md:text-7xl font-serif mb-8 text-gray-900 leading-tight">
            Modern Heirlooms
          </h1>
          <p className="text-gray-500 mb-10 text-lg font-light max-w-xl mx-auto">
            Crafted with precision, designed for eternity. Explore the new collection of ethically sourced gold and silver.
          </p>
          <button className="bg-black text-white px-10 py-4 text-xs tracking-[0.2em] uppercase hover:bg-gray-800 transition duration-300">
            View Collection
          </button>
        </div>
      </section>

      {/* --- 3. PRODUCT GRID BACKGROUND --- */}
      <section className="container mx-auto px-6 py-24">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-x-8 gap-y-12">
          {[1, 2, 3].map((i) => (
            <div key={i} className="group cursor-pointer">
              <div className="aspect-[3/4] bg-gray-100 mb-6 relative">
                 <div className="absolute inset-0 bg-gray-200 opacity-30"></div>
              </div>
              <h3 className="text-base font-serif mb-2 text-gray-900">Essential Chain {i}</h3>
              <p className="text-sm text-gray-500">$180.00</p>
            </div>
          ))}
        </div>
      </section>

      {/* --- 4. FOOTER --- */}
      <footer className="bg-white border-t border-gray-100 py-12 text-center">
        <p className="text-xs text-gray-400 tracking-widest uppercase">
          © 2025 The Jewelry Store Demo
        </p>
      </footer>

      {/* --- 5. THE WIDGET WRAPPER --- */}
      {/* 
         Fixed Position Overlay: This ensures the widget floats on top of the 
         demo content, just like it would in an iframe on a real site.
         z-index ensures it's above the nav/images.
         pointer-events-none ensures it doesn't block clicks on the store itself.
      */}
      <div className="fixed inset-0 z-[9999] pointer-events-none">
        <ChatWidget />
      </div>
      
    </div>
  );
};

export default Home;