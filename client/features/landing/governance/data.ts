import {
  FlaskConicalIcon,
  LockIcon,
  ScrollTextIcon,
  TrendingUpIcon,
  type LucideIcon,
} from "lucide-react";

export type GovernanceBlock = {
  icon: LucideIcon;
  title: string;
  surface: string;
  points: string[];
  note?: string;
};

export const GOVERNANCE_BLOCKS: GovernanceBlock[] = [
  {
    icon: ScrollTextIcon,
    title: "Tata kelola dan audit",
    surface: "bg-bento-lavender",
    points: [
      "Riwayat investigasi dan bukti dapat ditelusuri.",
      "Setiap pemeriksaan merekam versi aturan dan tingkat intervensi.",
      "Verdict manusia dapat menjadi dasar usulan perubahan aturan.",
      "Perubahan aturan membutuhkan persetujuan komite governance.",
      "Versi aturan sebelumnya tetap dapat ditinjau.",
    ],
  },
  {
    icon: LockIcon,
    title: "Privasi dan keamanan data",
    surface: "bg-bento-sky",
    points: [
      "Pemrosesan dilakukan dalam batas fasilitas kesehatan.",
      "Akses data dibatasi sesuai kewenangan.",
      "Data pasien diminimalkan dan dipseudonimkan sesuai kebutuhan.",
      "Sumber data yang diakses harus diizinkan.",
    ],
    note: "Integrasi dan penggunaan data riil harus memenuhi persyaratan legal, etis, dan pelindungan data yang relevan.",
  },
  {
    icon: TrendingUpIcon,
    title: "Dampak yang diharapkan",
    surface: "bg-bento-mint",
    points: [
      "Membantu koder mengidentifikasi kebutuhan koreksi lebih awal.",
      "Membantu verifikator menelaah temuan berdasarkan bukti.",
      "Berpotensi mengurangi pekerjaan klarifikasi pada tahap berikutnya.",
      "Mendukung tata kelola klaim yang lebih terukur dan dapat diaudit.",
    ],
    note: "Ini adalah manfaat yang diharapkan, bukan hasil yang sudah terbukti.",
  },
  {
    icon: FlaskConicalIcon,
    title: "Validasi dan kesiapan",
    surface: "bg-bento-sun",
    points: [
      "Status saat ini: tahap perancangan dan pengembangan awal.",
      "Belum diuji di lingkungan rumah sakit.",
      "Validasi yang direncanakan, belum dilaksanakan: evaluasi dengan data sintetis atau terpseudonimkan, penelaahan oleh koder dan verifikator, serta pilot terbatas setelah persyaratan legal dan etis terpenuhi.",
    ],
    note: "Halaman ini tidak menampilkan klaim akurasi, efisiensi, atau penghematan karena belum terbukti.",
  },
];
