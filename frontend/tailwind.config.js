/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './app/**/*.{js,ts,jsx,tsx}',
    './components/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        jarvis: {
          bg: '#050b14',
          text: '#c8d8ef',
          muted: '#5a7a9a',
        },
      },
    },
  },
  plugins: [],
}
