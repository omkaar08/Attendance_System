/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        surface: '#f3f7fb',
        brand: {
          50: '#eff8ff',
          100: '#dbeffd',
          600: '#1d6f93',
          700: '#15587a',
          800: '#133754',
          900: '#102742',
        },
      },
      fontFamily: {
        sans: ['Manrope', 'sans-serif'],
        display: ['Sora', 'sans-serif'],
      },
      boxShadow: {
        soft: '0 20px 45px -24px rgba(16, 39, 66, 0.35)',
      },
    },
  },
  plugins: [],
}

