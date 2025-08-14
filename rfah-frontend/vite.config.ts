import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  base: '/static/',       // مهم: لكي تظهر الصور والأصول من السيرفر نفسه
  build: { outDir: 'dist' }
})
