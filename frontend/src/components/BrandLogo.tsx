type BrandLogoProps = {
  size?: "sm" | "md" | "lg";
  showText?: boolean;
};

const sizeClasses = {
  sm: "h-9 w-9",
  md: "h-11 w-11",
  lg: "h-16 w-16",
};

export default function BrandLogo({
  size = "md",
  showText = false,
}: BrandLogoProps) {
  return (
    <div className="flex items-center gap-3">
      <div
        className={`${sizeClasses[size]} relative grid shrink-0 place-items-center overflow-hidden rounded-2xl border border-indigo-300/20 bg-gradient-to-br from-indigo-400 via-indigo-500 to-violet-700 shadow-lg shadow-indigo-500/20`}
        aria-hidden="true"
      >
        <svg
          viewBox="0 0 64 64"
          className="h-[72%] w-[72%]"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          <circle cx="22" cy="21" r="7" fill="white" />
          <path
            d="M10 43C10 34.7 15.4 30 22 30C28.6 30 34 34.7 34 43"
            stroke="white"
            strokeWidth="6"
            strokeLinecap="round"
          />
          <path
            d="M41 16L44 22L50 25L44 28L41 34L38 28L32 25L38 22L41 16Z"
            fill="#C7D2FE"
          />
          <circle cx="48" cy="43" r="4" fill="#DDD6FE" />
          <path
            d="M35 43H44"
            stroke="#DDD6FE"
            strokeWidth="4"
            strokeLinecap="round"
          />
        </svg>
      </div>

      {showText && (
        <div>
          <p className="text-lg font-bold tracking-tight text-white">
            UserOps AI
          </p>
          <p className="text-xs text-slate-400">Operations, simplified</p>
        </div>
      )}
    </div>
  );
}
