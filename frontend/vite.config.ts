import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (!id.includes("node_modules")) return undefined;
          if (
            /[\\/]node_modules[\\/](react|react-dom|react-router-dom)[\\/]/.test(
              id,
            )
          ) {
            return "react";
          }
          if (/[\\/]node_modules[\\/]recharts[\\/]/.test(id)) {
            return "charts";
          }
          if (/[\\/]node_modules[\\/]@dnd-kit[\\/]/.test(id)) {
            return "dragdrop";
          }
          if (
            /[\\/]node_modules[\\/](react-markdown|remark-gfm|remark-parse|remark-rehype|unified)[\\/]/.test(
              id,
            )
          ) {
            return "markdown";
          }
          if (/[\\/]node_modules[\\/]@radix-ui[\\/]/.test(id)) {
            return "ui";
          }
          return "vendor";
        },
      },
    },
  },
});
