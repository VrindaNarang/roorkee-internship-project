/// <reference types="vitest/config" />
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
// https://vite.dev/config/
export default defineConfig({
    plugins: [react()],
    build: {
        rollupOptions: {
            output: {
                // Manual chunking (Milestone 11 — bundle-size optimization): vendor
                // libraries change far less often than app code, so splitting them
                // into their own chunks lets browsers cache them across deploys
                // instead of invalidating one giant bundle on every app change.
                manualChunks: {
                    'vendor-react': ['react', 'react-dom', 'react-router-dom'],
                    'vendor-mui': ['@mui/material', '@mui/icons-material', '@emotion/react', '@emotion/styled'],
                    'vendor-charts': ['recharts'],
                    'vendor-query': ['@tanstack/react-query'],
                },
            },
        },
    },
    test: {
        environment: 'jsdom',
        globals: true,
        setupFiles: ['./src/test/setup.ts'],
        css: false,
    },
});
