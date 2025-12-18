import ChatWidget from '../components/ChatWidget';

export default function EmbedPage() {
  return (
    // Only the widget should render. No background colors here.
    <div className="w-full h-full bg-transparent flex items-end justify-end">
      <ChatWidget />
    </div>
  );
}