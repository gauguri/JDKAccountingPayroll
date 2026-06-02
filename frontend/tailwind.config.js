/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontSize: {
        // Senior-friendly: bump the base scale up.
        base: ["18px", "1.6"],
        lg: ["22px", "1.5"],
        xl: ["26px", "1.4"],
        "2xl": ["32px", "1.3"],
        "3xl": ["40px", "1.2"],
      },
    },
  },
  plugins: [],
};
