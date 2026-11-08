import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
// Only in local Vite dev, forward the token via proxy; never inject into browser bundle.
export default defineConfig({ plugins:[react()], server:{ port:5173, proxy: {
  '/api': { target: 'http://127.0.0.1:8005', changeOrigin:true, rewrite:(p)=>p.replace(/^\/api/, ''),
   configure: (proxy)=>proxy.on('proxyReq', (req)=>{ if(process.env.API_TOKEN) req.setHeader('X-API-Key',process.env.API_TOKEN); }) }
} }});
