import { Logo } from "@/components/shared/logo";
import { NAV_ITEMS } from "@/features/landing/site-header/nav-items";

export function SiteFooter() {
  return (
    <footer className="border-t border-line bg-background">
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-10 px-5 py-12 sm:px-8 md:flex-row md:items-start md:justify-between md:gap-16 md:py-14">
        <div className="flex max-w-md flex-col items-start gap-4">
          <a
            href="#beranda"
            aria-label="JAGA-KLAIM, kembali ke bagian atas"
            className="rounded-sm outline-none focus-visible:ring-3 focus-visible:ring-ring/50"
          >
            <Logo />
          </a>

          <p className="max-w-sm text-sm leading-6 text-muted-foreground">
            JAGA-KLAIM membantu koder dan verifikator memeriksa kesesuaian kode
            dan bukti pendukung sebelum klaim diajukan. Keputusan akhir tetap
            berada pada manusia yang berwenang.
          </p>

          <p className="max-w-sm text-xs leading-5 text-muted-foreground">
            Informasi pada halaman ini menjelaskan rancangan produk yang
            sedang dikembangkan. Ketersediaan fitur mengikuti implementasi
            aktual.
          </p>
        </div>

        <nav
          aria-label="Navigasi footer"
          className="w-full md:w-auto"
        >
          <h2 className="mb-4 text-sm font-semibold text-foreground">
            Jelajahi JAGA-KLAIM
          </h2>

          <ul className="grid grid-cols-2 gap-x-8 gap-y-3 text-sm sm:grid-cols-3 md:min-w-80">
            {NAV_ITEMS.map((item) => (
              <li key={item.id}>
                <a
                  href={`#${item.id}`}
                  className="inline-flex rounded-sm text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-ring/50 motion-reduce:transition-none"
                >
                  {item.label}
                </a>
              </li>
            ))}
          </ul>
        </nav>
      </div>

      <div className="border-t border-line">
        <div className="mx-auto flex w-full max-w-6xl flex-col gap-2 px-5 py-5 text-xs leading-5 text-muted-foreground sm:px-8 sm:flex-row sm:items-center sm:justify-between">
          <p>
            &copy; {new Date().getFullYear()} JAGA-KLAIM.
          </p>

          <p>
            Asisten pemeriksaan klaim berbasis bukti, dengan keputusan tetap
            pada manusia.
          </p>
        </div>
      </div>
    </footer>
  );
}