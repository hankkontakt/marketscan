export default function AppLoading() {
  return (
    <div className="max-w-4xl mx-auto space-y-6 animate-pulse">
      <div className="skeleton h-8 w-48 rounded-lg" />
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        <div className="skeleton h-48 rounded-2xl" />
        <div className="skeleton h-48 rounded-2xl" />
      </div>
      <div className="skeleton h-64 rounded-2xl" />
    </div>
  );
}
