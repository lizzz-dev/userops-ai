import BrandLogo from "./BrandLogo";


type HeaderProps = {
  onLogout: () => void;
};

export default function Header({ onLogout }: HeaderProps) {
  return (
    <header className="flex min-h-20 items-center justify-between gap-4 border-b border-white/10 bg-slate-950/80 px-4 py-4 backdrop-blur sm:px-6">
      <div className="flex min-w-0 items-center gap-3">
        <div className="lg:hidden">
          <BrandLogo size="sm" />
        </div>
        <div className="min-w-0">
          <h2 className="truncate text-base font-semibold text-white sm:text-lg">
            UserOps AI Assistant
          </h2>
          <p className="hidden truncate text-sm text-slate-400 sm:block">
            Natural language workspace management
          </p>
        </div>
      </div>

      <button
        type="button"
        onClick={onLogout}
        className="shrink-0 rounded-lg border border-white/10 px-3 py-2 text-sm text-slate-300 transition hover:bg-white/10 hover:text-white lg:hidden"
      >
        Log out
      </button>
    </header>
  );
}