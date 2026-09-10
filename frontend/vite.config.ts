import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
export default defineConfig({plugins:[react(),tailwindcss()],server:{port:5173,strictPort:true,proxy:{'/api':{target:'http://127.0.0.1:8000',timeout:1260000,proxyTimeout:1260000}}}});
