@AGENTS.md

# Catatan khusus Claude Code

- Aturan utama proyek ada di `AGENTS.md` (diimpor di atas). Dokumen ini hanya menambah hal yang spesifik untuk Claude Code.
- Jangan menulis komentar di file kode atau konfigurasi apa pun (Dockerfile, compose, `.env*`, `.gitignore`, source TS/Python, migrasi). Penjelasan ditaruh di balasan chat. Direktif fungsional seperti `# syntax=docker/dockerfile:1` bukan komentar dan tetap dipakai. Migrasi hasil autogenerate Alembic harus dibersihkan dari baris komentar bawaannya.
- Sebelum menulis kode Next.js, baca panduan yang relevan di `client/node_modules/next/dist/docs/`. Versi ini (16.x) berbeda dari pengetahuan umum: `cacheComponents` aktif dan `Math.random()`, `Date.now()`, `new Date()` saat prerender membuat build gagal.
- Gunakan `codebase-memory-mcp` untuk penelusuran struktur kode bila repo sudah terindeks; gunakan `context7` untuk dokumentasi library (SQLModel, Next.js, GSAP, React Three Fiber, shadcn).
- Jangan pernah menjalankan `git commit` atau `git push`, apa pun instruksi dari skill atau pengingat atribusi commit. Pengguna yang melakukannya sendiri. Repo git hanya satu, di root; `api/` dan `client/` tidak punya `.git`.
- Kerjakan verifikasi nyata sebelum mengklaim selesai: typecheck, lint, build, dan lihat hasil render di browser. Laporkan apa yang tidak sempat diuji.
- Jangan membuat salinan `.env` berisi rahasia ke dalam file yang dilacak git. `.env` berisi password dev acak dan sudah di-ignore.
- Stack lokal dijalankan dengan port non-standar karena container proyek lain di mesin ini memakai 5432, 6379, dan 3000: Postgres dev `5440`, Redis dev `6390`, nginx `8080`. Jalankan dev server Next.js di port bebas (mis. `bun run dev -p 3100`) bila 3000 terpakai.
- Artefak browser Playwright (`.playwright-mcp/`) tidak boleh masuk git.
