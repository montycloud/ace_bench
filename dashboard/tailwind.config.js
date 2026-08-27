/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'SFMono-Regular', 'monospace'],
      },
      colors: {
        ink: {
          950: '#0a0c16',
          900: '#0f1220',
          850: '#12162a',
          800: '#171b30',
          700: '#232842',
        },
        brand: {
          blue: '#4f8bff',
          yellow: '#f5c518',
          green: '#34d399',
        },
      },
      boxShadow: {
        glow: '0 0 0 1px rgba(79,139,255,0.15), 0 8px 30px -8px rgba(79,139,255,0.25)',
      },
    },
  },
  plugins: [require('@tailwindcss/typography')],
}

