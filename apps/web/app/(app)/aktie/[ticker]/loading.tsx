export default function StockLoading() {
  return (
    <div className="space-y-6 animate-pulse">
      <div className="skeleton h-32 rounded-2xl" />
      <div className="flex gap-2"><div className="skeleton h-8 w-24 rounded-lg" /><div className="skeleton h-8 w-24 rounded-lg" /><div className="skeleton h-8 w-24 rounded-lg" /></div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="skeleton h-80 rounded-2xl" />
        <div className="skeleton h-80 rounded-2xl" />
      </div>
    </div>
  );
}
