export default function CosAALogo() {
  return (
    <div className="flex flex-col items-center gap-4">
      {/* Animated SVG Brain-Hexagon Icon */}
      <div className="relative">
        {/* Outer glow ring */}
        <div className="absolute inset-0 -m-3 rounded-full bg-blue-500/10 blur-xl animate-pulse-slow" />

        <svg
          width="80"
          height="80"
          viewBox="0 0 80 80"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          className="relative drop-shadow-[0_0_25px_rgba(96,165,250,0.6)]"
        >
          <defs>
            <linearGradient id="logo-grad" x1="0" y1="0" x2="80" y2="80" gradientUnits="userSpaceOnUse">
              <stop offset="0%" stopColor="#93c5fd" />
              <stop offset="50%" stopColor="#60a5fa" />
              <stop offset="100%" stopColor="#2563eb" />
            </linearGradient>
            <linearGradient id="logo-grad2" x1="80" y1="0" x2="0" y2="80" gradientUnits="userSpaceOnUse">
              <stop offset="0%" stopColor="#818cf8" />
              <stop offset="100%" stopColor="#3b82f6" />
            </linearGradient>
            <filter id="glow">
              <feGaussianBlur stdDeviation="2" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>

          {/* Outer hexagon — slow rotating */}
          <path
            d="M40 4L72 22v36L40 76 8 58V22L40 4z"
            stroke="url(#logo-grad)"
            strokeWidth="1.5"
            fill="none"
            opacity="0.3"
          >
            <animateTransform
              attributeName="transform"
              type="rotate"
              from="0 40 40"
              to="360 40 40"
              dur="60s"
              repeatCount="indefinite"
            />
          </path>

          {/* Inner hexagon with glow */}
          <path
            d="M40 10L66 25v30L40 70 14 55V25L40 10z"
            stroke="url(#logo-grad)"
            strokeWidth="2"
            fill="none"
            filter="url(#glow)"
          />

          {/* Central brain node — breathing */}
          <circle cx="40" cy="40" r="4.5" fill="url(#logo-grad)" filter="url(#glow)">
            <animate attributeName="r" values="4.5;5.2;4.5" dur="2s" repeatCount="indefinite" />
          </circle>

          {/* Top node */}
          <circle cx="40" cy="22" r="3" fill="url(#logo-grad2)">
            <animate attributeName="opacity" values="0.7;1;0.7" dur="3s" repeatCount="indefinite" />
          </circle>

          {/* Left node */}
          <circle cx="26" cy="34" r="2.5" fill="url(#logo-grad)">
            <animate attributeName="opacity" values="1;0.6;1" dur="2.5s" repeatCount="indefinite" />
          </circle>

          {/* Right node */}
          <circle cx="54" cy="34" r="2.5" fill="url(#logo-grad2)">
            <animate attributeName="opacity" values="0.6;1;0.6" dur="2.8s" repeatCount="indefinite" />
          </circle>

          {/* Bottom-left node */}
          <circle cx="30" cy="52" r="2.5" fill="url(#logo-grad)">
            <animate attributeName="opacity" values="0.8;1;0.8" dur="2.2s" repeatCount="indefinite" />
          </circle>

          {/* Bottom-right node */}
          <circle cx="50" cy="52" r="2.5" fill="url(#logo-grad2)">
            <animate attributeName="opacity" values="1;0.7;1" dur="2.6s" repeatCount="indefinite" />
          </circle>

          {/* Neural connections with glow */}
          <g stroke="url(#logo-grad)" strokeWidth="1.2" opacity="0.5" filter="url(#glow)">
            <line x1="40" y1="22" x2="26" y2="34" />
            <line x1="40" y1="22" x2="54" y2="34" />
            <line x1="40" y1="22" x2="40" y2="40" />
            <line x1="26" y1="34" x2="40" y2="40" />
            <line x1="54" y1="34" x2="40" y2="40" />
            <line x1="40" y1="40" x2="30" y2="52" />
            <line x1="40" y1="40" x2="50" y2="52" />
            <line x1="26" y1="34" x2="30" y2="52" />
            <line x1="54" y1="34" x2="50" y2="52" />
          </g>

          {/* Synapse pulses — traveling dots along connections */}
          <circle r="1.5" fill="#93c5fd" opacity="0.8">
            <animateMotion dur="3s" repeatCount="indefinite" path="M40,22 L40,40 L30,52" />
          </circle>
          <circle r="1.5" fill="#818cf8" opacity="0.8">
            <animateMotion dur="3.5s" repeatCount="indefinite" path="M40,22 L54,34 L40,40" />
          </circle>
          <circle r="1" fill="#60a5fa" opacity="0.6">
            <animateMotion dur="4s" repeatCount="indefinite" path="M26,34 L40,40 L50,52" />
          </circle>
        </svg>
      </div>

      {/* Title with gradient */}
      <h1 className="relative text-4xl font-bold tracking-wide">
        <span className="bg-gradient-to-r from-blue-300 via-blue-400 to-indigo-400 bg-clip-text text-transparent">
          COS-AA
        </span>
      </h1>

      {/* Subtitle */}
      <p className="text-sm text-gray-400/80 text-center tracking-wider uppercase">
        Cognitive Operating System for AI Agents
      </p>
    </div>
  );
}
