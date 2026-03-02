export default function Loading() {
  return (
    <div className="flex min-h-[40vh] items-center justify-center">
      <div className="flex flex-col items-center gap-3">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-gray-200 border-t-accent dark:border-slate-700 dark:border-t-indigo-400" />
        <p className="text-sm text-gray-500 dark:text-slate-400">Loading...</p>
      </div>
    </div>
  );
}
