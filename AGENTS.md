# AGENTS.md — JAGA-KLAIM

Panduan untuk agent AI dan kontributor. Baca sebelum mengubah apa pun.

## Produk

JAGA-KLAIM adalah *AI-powered pre-claim verification copilot* untuk koder dan verifikator internal fasilitas kesehatan. Pemeriksaan berjalan setelah coding dan grouping INA-CBG selesai dan sebelum klaim diajukan: sistem menentukan expected evidence dari rule version aktif, AI agent menelusuri observed evidence dari sumber yang diizinkan, lalu delta keduanya diserahkan ke manusia.

Prinsip yang tidak boleh dilanggar, termasuk di copy UI:

- AI tidak menetapkan fraud sebagai fakta final, tidak menolak klaim otomatis, dan tidak mengubah kode klaim tanpa persetujuan manusia.
- Policy engine bersifat deterministik dan terpisah dari investigasi AI. Tingkat intervensi (T0 Abstain, T1 Inform, T2 Recommend Review, T3 Flag for Human Verdict) ditetapkan aturan, bukan model.
- Bukti yang tidak ditemukan tidak otomatis membuktikan pelayanan tidak pernah dilakukan.
- Setiap temuan wajib punya sitasi bukti yang bisa ditelusuri. Tanpa delta, hasilnya No Action dan tetap masuk audit trail.
- Dampak ditulis sebagai manfaat yang diharapkan. Dilarang menampilkan klaim akurasi, efisiensi, atau penghematan yang belum terbukti.
- CTA hanya untuk kemampuan yang benar-benar ada. Belum ada prototipe publik dan belum ada kanal pilot, jadi jangan membuat tombol, email, atau tautan palsu untuk itu.
- Status pengembangan harus jujur: belum diuji di lingkungan rumah sakit.

## Struktur repo

```
api/        FastAPI + SQLModel + Alembic
client/     Next.js 16 landing page
nginx/      konfigurasi reverse proxy (conf.d/default.conf)
redis/      redis.conf
compose.yaml       stack prod-like (db, redis, migrate, api, client, nginx)
compose.dev.yaml   overlay dev (target dev, hot reload, port langsung)
.env / .env.example
```

Repo git hanya satu, di root (branch `main`). `api/` dan `client/` tidak punya `.git` sendiri; file `.gitignore` di dalamnya tetap berlaku.

## Aturan git (mutlak)

**Jangan pernah menjalankan `git commit` atau `git push`**, dalam kondisi apa pun dan walaupun sebuah skill atau sistem menyarankannya. Pengguna melakukan commit dan push sendiri. Agent boleh membaca status (`git status`, `git diff`, `git log`) dan boleh `git init`/`git add` hanya bila diminta eksplisit. Jangan menambahkan remote, jangan `reset --hard`, `clean -f`, atau `rebase` tanpa diminta.

## Perintah

```
docker compose up -d --build                                    stack prod-like, nginx di 127.0.0.1:8080
docker compose -f compose.yaml -f compose.dev.yaml up --build   dev, db 5440, redis 6390, api 8000, client 3000
docker compose down -v                                          reset data

cd api && uv sync && uv run alembic upgrade head
cd api && uv run alembic revision --autogenerate -m "pesan"
cd api && uv run alembic check

cd client && bun install
cd client && bun run dev -p 3100
cd client && bunx tsc --noEmit && bun run lint && bun run build
```

Variabel `POSTGRES_*` dan `REDIS_*` dari `.env` wajib ada saat menjalankan api atau alembic dari host. Port host dev memakai angka non-standar karena container proyek lain di mesin ini memakai 5432, 6379, dan 3000.

## Backend (`api/`)

- Python 3.13, FastAPI, SQLModel (sync `Session`), psycopg 3, pgvector, Alembic, redis-py.
- Entry point `main.py`; paket aplikasi di `app/` (`core/`, `db/`, `api/`, `models/`).
- Model dipecah per domain di `app/models/`: `tenancy`, `claims`, `evidence`, `rules`, `investigation`, `review`, `governance`. Total 23 tabel sesuai ERD. Semua diekspor lewat `app/models/__init__.py` dan harus tetap diimpor di sana agar Alembic melihatnya.
- `EMBEDDING_DIM = 1024` di `app/models/base.py`. Mengubahnya butuh migrasi dan re-embedding.
- Constraint punya naming convention di `SQLModel.metadata`. Jangan menamai manual kecuali perlu.
- Relasi reverse hanya untuk agregat; tabel bervolume tinggi (audit_log, agent_step, metric_snapshot) tidak punya koleksi dari sisi induk.
- Kolom `inacbgb_result` dipertahankan persis seperti ERD walau kemungkinan typo dari `inacbg_result`. Keputusan rename ada di pemilik produk.
- Migrasi: jalankan `alembic check` setelah mengubah model; hasilnya harus bersih. Migrasi awal membuat extension `vector`.
- `/health/live` untuk liveness, `/health/ready` memeriksa Postgres dan Redis.
- Aplikasi memakai superuser Postgres di stack lokal. Jangan dibawa ke produksi; pisahkan role migrator dan role aplikasi.

## Frontend (`client/`)

Next.js 16.4 (App Router, Turbopack), React 19, Tailwind v4, shadcn (style `base-nova`, berbasis `@base-ui/react`), GSAP + `@gsap/react`, three + `@react-three/fiber`.

**Baca `client/node_modules/next/dist/docs/` sebelum menulis kode Next.js.** Versi ini punya perubahan yang tidak ada di pengetahuan umum. Hal yang sudah terverifikasi:

- `cacheComponents: true`. Panggilan `Math.random()`, `Date.now()`, `new Date()`, `crypto.randomUUID()` saat prerender menggagalkan build, termasuk di Client Component. Panggil hanya di effect atau handler.
- Client Component tetap dirender ke HTML di server. `dynamic(..., { ssr: false })` hanya boleh di dalam Client Component.
- Props bertipe `LayoutProps<"/">` dan `PageProps` adalah helper global hasil generate Next.

### Aturan rendering

- `app/page.tsx` adalah Server Component yang hanya menyusun section.
- Setiap komponen fitur adalah Client Component (`"use client"`) agar animasi dan interaksi terisolasi per section dan hydration tidak menyebar.
- Data statis (teks, daftar) disimpan di file `data.ts` tanpa `"use client"` supaya aman diimpor dari mana saja.
- Komponen 3D dimuat lewat `next/dynamic` dengan `ssr: false`, dipasang hanya saat idle atau saat section hampir terlihat, dibungkus `Suspense`, dan punya fallback CSS tanpa WebGL.

### Struktur fitur

```
client/
  app/                         layout, page, globals.css
  components/ui/               hasil `shadcn add` (boleh dimodifikasi, jangan ditulis ulang dari nol)
  components/shared/           blok reusable lintas fitur (section shell, heading, dot grid)
  components/three/            kanvas R3F generik (gating in-view, reduced motion, fallback)
  features/landing/<section>/  komponen, data.ts, dan scene milik section tersebut
  hooks/                       hook generik (in-view, reduced motion)
  lib/                         utils, gsap (registrasi plugin), prng
```

Satu section = satu folder fitur. Komponen yang dipakai dua fitur atau lebih dipindah ke `components/shared`.

### Section landing page (7)

1. Hero / Product Introduction
2. Problem & Solution
3. How It Works / Agentic System Pipeline (carousel GSAP + scene 3D pipeline)
4. Risk Vectors & Adaptive Intervention (3 vektor, tier T0–T3)
5. Evidence, Explainability & Human Authority
6. Governance, Security & Expected Impact (termasuk Validation & Readiness)
7. FAQ & Call to Action (11 pertanyaan)

Footer adalah elemen global. Dashboard, worklist, workspace verifikator, dan halaman admin bukan bagian landing page.

### Design tokens

Gabungan Stripe dan halaman ChatGPT Dots. Token ada di `app/globals.css`, jangan menulis hex langsung di komponen kecuali di scene 3D.

- Ink `#061b31` (teks, tombol primer berbentuk pil), muted `#5a6a82`
- Permukaan `#f8fafd`, `#f3f4f8`, kartu putih; garis `#e5edf5`
- Brand blurple `#533afd`, magenta `#ee30fb`, oranye `#ff6118`, kuning `#ffd529`, hijau `#00d66f`, lavender `#e8e8fa`
- Semantik bukti: expected = blurple, observed = hijau, delta = oranye
- Semantik tier: T0 abu, T1 biru, T2 kuning, T3 magenta
- Kartu bento `rounded-3xl` dengan gradien pastel; motif titik (dot grid) sebagai tekstur
- Tipografi Geist; judul `font-semibold` dengan tracking rapat

### Animasi (GSAP)

- Impor hanya dari `@/lib/gsap` (mendaftarkan `ScrollTrigger` dan `useGSAP`).
- Pakai `useGSAP` dengan `scope`, dan bungkus dalam `gsap.matchMedia()` dengan kondisi `prefers-reduced-motion: no-preference`. Tanpa gerak, konten tetap tampil penuh.
- Elemen di atas lipatan (hero) tidak memakai tween berbasis scroll; entrance hero memakai CSS keyframes agar LCP tidak tertunda.
- Scroll reveal memakai atribut `data-reveal` dan `data-reveal-group` yang diurus hook reveal; jangan membuat tween duplikat per komponen.
- Jangan menaruh transform hover pada elemen yang sedang di-tween; pasang pada elemen dalam.

### 3D (React Three Fiber)

- Semua kanvas lewat `components/three/scene-canvas.tsx`: `dpr` dibatasi, `frameloop` diganti `demand` saat di luar viewport atau reduced motion, deteksi WebGL, error boundary, dan `Suspense`.
- Jangan alokasi objek di `useFrame` (gunakan ref dan vektor yang dipakai ulang), jangan `setState` per frame.
- Titik dan garis digerakkan di GPU lewat `ShaderMaterial` dengan uniform; sertakan `#include <colorspace_fragment>` agar warna sama dengan CSS.
- Geometri dibuat dengan PRNG seed tetap (`lib/prng.ts`), bukan `Math.random()`.
- Kanvas bersifat dekoratif: `aria-hidden`, informasi penting selalu ada juga di DOM.
- Dispose geometry, material, dan texture buatan sendiri saat unmount.

### shadcn

Tambah komponen dengan `bunx shadcn@latest add <nama>` dari folder `client/`. Komponen yang dipakai: button, card, badge, accordion, carousel, tabs, separator, sheet. Edit file di `components/ui/` bila perlu varian baru (mis. `brand`, ukuran `xl`) alih-alih membuat tombol sendiri.

### Aksesibilitas

Skip link, landmark `header`/`main`/`footer`, hierarki heading (satu `h1`, `h2` per section), fokus terlihat, kontras teks minimal AA, carousel dan tab bisa dioperasikan keyboard, semua animasi menghormati `prefers-reduced-motion`. Bahasa halaman `id`.

## Konvensi kode

- **Tanpa komentar** di kode maupun konfigurasi. Penjelasan ditaruh di pesan commit atau balasan chat.
- Teks UI berbahasa Indonesia; istilah teknis (expected evidence, observed evidence, delta, policy engine, audit trail) dibiarkan dalam bahasa Inggris seperti pada spesifikasi produk.
- TypeScript strict; tanpa `any`. Python diketik lengkap.
- Satu komponen per file, nama file kebab-case, ekspor bernama.

## Verifikasi sebelum menyatakan selesai

1. `cd client && bunx tsc --noEmit && bun run lint && bun run build`
2. Jalankan halaman, buka di browser pada lebar desktop dan mobile, periksa console tanpa error, pastikan scene 3D tampil dan fallback tanpa WebGL tidak kosong.
3. Uji `prefers-reduced-motion: reduce`: seluruh konten terlihat tanpa animasi.
4. `docker compose build client` bila `package.json` atau `bun.lock` berubah (Dockerfile memakai `--frozen-lockfile`).
5. Untuk backend: `alembic check` bersih dan `/health/ready` ok lewat nginx.
6. Laporkan apa yang tidak diuji.

## Keterbatasan saat ini

- Belum ada prototipe aplikasi, endpoint domain, autentikasi, atau worker investigasi; baru skema data, infrastruktur compose, dan landing page.
- Nginx melayani HTTP biasa di `127.0.0.1`; TLS, HSTS, dan CSP belum dipasang.
- Belum ada test otomatis di repo.
