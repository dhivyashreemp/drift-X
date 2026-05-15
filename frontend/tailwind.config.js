/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        navy: {
          950: '#050d1f',
          900: '#091a38',
          800: '#0e2347',
          700: '#163060',
          600: '#1d3f7a',
        },
        neon: {
          400: '#7fff14',
          500: '#39FF14',
          600: '#28cc0f',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
