import { QuoteIcon } from "lucide-react";

const ROWS = [
  {
    dot: "bg-brand",
    title: "Expected evidence",
    text: "Hasil laboratorium yang mendukung diagnosis",
  },
  {
    dot: "bg-mint",
    title: "Observed evidence",
    text: "Tidak ditemukan pada sumber yang diizinkan",
  },
  {
    dot: "bg-orange",
    title: "Delta",
    text: "1 bukti tidak ditemukan, diserahkan untuk diperiksa manusia",
  },
] as const;

export function EvidenceComparison() {
  return (
    <figure className="m-0">
      <div className="rounded-3xl bg-white p-6 ring-1 ring-line sm:p-8">
        <ul className="flex flex-col gap-5">
          {ROWS.map((row) => (
            <li key={row.title} className="flex items-start gap-4">
              <span
                aria-hidden="true"
                className={`mt-1.5 size-3 shrink-0 rounded-full ${row.dot}`}
              />
              <div>
                <p className="text-sm font-semibold text-ink">{row.title}</p>
                <p className="mt-0.5 text-[0.95rem] leading-relaxed text-muted-foreground">
                  {row.text}
                </p>
              </div>
            </li>
          ))}
        </ul>
        <p className="mt-6 flex items-start gap-3 rounded-2xl bg-surface-2 p-4 text-sm leading-relaxed text-ink">
          <QuoteIcon className="mt-0.5 size-4 shrink-0 text-brand" aria-hidden="true" />
          <span>
            Sitasi: catatan laboratorium pada sumber yang diizinkan, lengkap dengan
            kutipan dan hash buktinya.
          </span>
        </p>
      </div>
      <figcaption className="mt-3 text-sm text-muted-foreground">
        Contoh ilustrasi, bukan data nyata. Bukti yang tidak ditemukan tidak
        otomatis membuktikan bahwa pelayanan tidak pernah dilakukan.
      </figcaption>
    </figure>
  );
}
