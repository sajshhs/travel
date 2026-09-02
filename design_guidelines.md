{
  "brand": {
    "name": "RahazaTrans",
    "tone": [
      "premium",
      "percaya diri",
      "hangat",
      "konversi-cepat ala OTA (Traveloka/tiket.com)"
    ],
    "language": "id-ID",
    "non_negotiables": [
      "Pertahankan glassmorphism + hero foto + serif display (Fraunces).",
      "Readability wajib (WCAG AA) di light & dark, terutama di atas foto hero.",
      "Tidak boleh mock data/angka fiktif; semua section baru harus pakai endpoint publik yang tersedia.",
      "Tidak menambah item navbar publik.",
      "Semua elemen interaktif & info penting wajib punya data-testid (kebab-case)."
    ]
  },

  "executive_summary": {
    "what_to_fix": [
      "Glass surfaces saat ini terlalu ‘putih’ di dark mode (glass-modal pakai background putih !important) → teks putih jadi hilang.",
      "Glass-3d di atas hero foto terang memakai refraction overlay (mix-blend-mode: screen) terlalu kuat → label/placeholder/judul tersapu.",
      "CTA panel blog rusak karena Tailwind arbitrary value to-[color:var(--primary)] invalid (var berisi triplet HSL).",
      "ChatWidget panel/FAB terlalu tinggi pada viewport pendek dan menabrak header/announcement.",
      "Halaman Fleet/Destinations/Trip Calculator terasa sepi saat data sedikit → perlu section berbasis data nyata + empty/loading states." 
    ],
    "design_strategy": [
      "Jadikan glass sebagai ‘surface’ yang theme-aware: selalu punya base tint yang mengikuti --card/--background, plus scrim khusus saat berada di atas foto.",
      "Pisahkan ‘decorative refraction’ dari area teks/form: refraction hanya boleh di pinggir/atas (mask), opacity rendah, dan non-screen blend di light mode.",
      "CTA band harus selalu memakai background solid/tinted berbasis token (bukan gradient Tailwind yang mengandalkan var triplet).",
      "Floating elements memakai sistem offset berbasis CSS variables agar tidak tabrakan dengan StickyMobileCTA dan aman di viewport pendek." 
    ]
  },

  "typography": {
    "font_pairing": {
      "display": {
        "name": "Fraunces",
        "usage": "Hero headline, section heading utama, CTA headline",
        "class": "font-fraunces"
      },
      "body": {
        "name": "Plus Jakarta Sans",
        "usage": "Body, label form, navigasi, tabel harga",
        "token": "--font-public"
      },
      "numbers": {
        "usage": "Harga, total, breakdown",
        "classes": "tabular-nums"
      }
    },
    "scale": {
      "h1": "text-4xl sm:text-5xl lg:text-6xl",
      "h2": "text-base md:text-lg",
      "body": "text-sm md:text-base",
      "small": "text-xs md:text-sm"
    },
    "readability_rules": [
      "Di atas foto/hero: gunakan scrim (underlay) + text-shadow halus untuk heading saja (bukan body panjang).",
      "Label/placeholder form di glass: gunakan warna berbasis --foreground dengan opacity tinggi (>=0.82) dan jangan pernah putih di atas surface terang.",
      "Gunakan leading-relaxed untuk paragraf narasi/FAQ; gunakan max-w-prose untuk teks panjang." 
    ]
  },

  "color_system": {
    "constraints": [
      "Jangan ubah struktur token yang sudah ada (HSL triplet).",
      "Tidak hardcode hex untuk warna brand; semua via token.",
      "Tidak membuat palet baru; boleh menambah token turunan khusus surface-on-hero / scrim / cta-band jika diperlukan." 
    ],
    "token_additions_allowed": {
      "purpose": "Token turunan untuk readability di atas foto & untuk CTA band yang aman",
      "new_tokens": {
        "--surface-on-hero": "HSL/alpha yang lebih stabil untuk card di atas foto (light & dark)",
        "--surface-on-hero-border": "border hairline untuk surface-on-hero",
        "--scrim-hero": "overlay gradient untuk menstabilkan kontras hero",
        "--scrim-panel": "overlay untuk panel/modal di atas konten",
        "--cta-band-bg": "background CTA band (solid/tinted) yang valid",
        "--cta-band-fg": "foreground CTA band",
        "--cta-band-border": "border CTA band"
      }
    }
  },

  "readability_on_glass_rules_executable": {
    "goal": "Glass tetap premium (rim/bevel/depth) tapi teks/form selalu terbaca di light/dark dan di atas foto hero.",

    "core_principles": [
      "1) Glass base harus mengikuti mode: di dark mode base-nya gelap (bukan putih).",
      "2) Di atas foto hero: selalu ada scrim/underlay sebelum glass (stabilkan luminance).",
      "3) Refraction/sheen tidak boleh ‘menyapu’ area teks: batasi dengan mask + opacity rendah.",
      "4) mix-blend-mode hanya untuk dekorasi kecil; default-nya normal/soft-light agar aman." 
    ],

    "css_patch_plan": {
      "file": "/app/frontend/src/index.css",
      "what_to_change": {
        "glass_modal": {
          "problem": "background putih !important membuat teks putih hilang di dark mode",
          "fix": [
            "Hapus hardcoded hsla(0 0% 100% / 0.94) !important.",
            "Gunakan hsla(var(--glass-bg-strong)) sebagai base + gradient edge/tint.",
            "Tambahkan scrim internal tipis (pseudo-element) untuk memastikan kontras teks." 
          ],
          "recommended_values": {
            "background": "linear-gradient(180deg, hsla(var(--glass-edge)) 0%, hsla(var(--glass-tint)) 18%, hsla(var(--glass-bg-strong)) 100%)",
            "backdrop_blur": "blur(26px) saturate(1.45)",
            "border": "1px solid hsla(var(--glass-rim))",
            "shadow": "var(--shadow-glass-3d-strong)",
            "internal_scrim": "::before { background: linear-gradient(180deg, hsla(var(--background) / 0.10), hsla(var(--background) / 0.22)); opacity: 1; mix-blend-mode: normal; }"
          }
        },

        "glass_3d": {
          "problem": "::before refraction (screen 0.55) + white radial terlalu kuat di atas hero terang",
          "fix": [
            "Turunkan opacity refraction ke 0.18–0.28 (default 0.22).",
            "Ganti mix-blend-mode dari screen → soft-light (light mode) dan normal (dark mode) untuk mencegah washout.",
            "Batasi refraction hanya di area atas/tepi dengan mask-image agar tidak menimpa label/form.",
            "Tambahkan varian ‘surface-on-hero’ untuk TripEstimatorInline: base lebih opaque + border lebih tegas." 
          ],
          "recommended_values": {
            "glass_3d_background": "linear-gradient(180deg, hsla(var(--glass-edge-soft)) 0%, hsla(var(--glass-tint)) 18%, hsla(var(--glass-bg)) 100%)",
            "refraction_opacity": "0.22",
            "refraction_blend_light": "soft-light",
            "refraction_blend_dark": "normal",
            "mask": "mask-image: radial-gradient(120% 70% at 50% 0%, black 0%, black 45%, transparent 78%);"
          }
        },

        "glass_and_glass_strong": {
          "problem": "Glass base kadang terlalu terang/kurang stabil di atas foto",
          "fix": [
            "Pastikan --glass-bg dan --glass-bg-strong di preset dark benar-benar gelap (di public-themes.css).",
            "Tambahkan utilitas .glass-on-hero untuk kasus di atas foto: background lebih opaque + border lebih kontras + blur sedikit lebih tinggi." 
          ],
          "recommended_values": {
            "glass_on_hero": ".glass-on-hero { background: hsla(var(--surface-on-hero)); border-color: hsla(var(--surface-on-hero-border)); -webkit-backdrop-filter: blur(26px) saturate(1.35); backdrop-filter: blur(26px) saturate(1.35); }"
          }
        },

        "scrim_underlay_pattern": {
          "where": [
            "Hero sections dengan foto terang",
            "Kartu estimator di hero",
            "Modal/CTA panel di atas konten yang ramai"
          ],
          "pattern": {
            "structure": "<div className='relative'> <img/> <div className='absolute inset-0 hero-scrim'/> <div className='relative z-10 glass-on-hero'>...</div></div>",
            "css": ".hero-scrim{ background: var(--scrim-hero); }",
            "recommended_scrim": "linear-gradient(180deg, hsla(var(--primary) / 0.55) 0%, hsla(var(--primary) / 0.22) 42%, hsla(var(--background) / 0.10) 100%)"
          }
        },

        "mix_blend_mode_rules": {
          "allowed": [
            "Hanya untuk dekorasi non-teks (orb, highlight kecil, sheen) dan harus opacity <= 0.22",
            "Tidak boleh pada container yang berisi form fields/label"
          ],
          "disallowed": [
            "screen pada overlay full-card di light mode",
            "overlay yang menutupi 100% area card tanpa mask"
          ]
        }
      }
    }
  },

  "cta_band_safe_pattern": {
    "problem": "CTA blog rusak karena Tailwind gradient memakai var triplet HSL (invalid).",
    "rule": "Jangan pernah pakai to-[color:var(--primary)] atau from-[color:var(--primary)] untuk gradient. Gunakan token gradient yang sudah ada (var(--gradient-cta)) atau background solid hsla(var(--primary) / alpha).",
    "recommended_component": {
      "name": "CtaBand",
      "usage": [
        "Blog detail (/blog/:slug)",
        "/fleet",
        "/destinations",
        "/trip-calculator"
      ],
      "visual": "Band full-width dengan background solid/tinted + border hairline + 1 primary CTA + 1 secondary link",
      "tailwind_classes": {
        "wrapper": "relative overflow-hidden rounded-2xl border p-5 md:p-7",
        "bg": "bg-[hsla(var(--cta-band-bg))] text-[hsl(var(--cta-band-fg))] border-[hsla(var(--cta-band-border))]",
        "decor": "before:absolute before:inset-0 before:bg-[var(--gradient-accent)] before:opacity-30 before:pointer-events-none",
        "layout": "flex flex-col gap-4 md:flex-row md:items-center md:justify-between"
      },
      "button": {
        "primary": "Button (shadcn) variant=default + className='cta-shine glow-focus'",
        "secondary": "Button variant=ghost (atau link) dengan underline halus"
      },
      "data_testids": {
        "primary": "cta-band-primary-button",
        "secondary": "cta-band-secondary-link"
      }
    }
  },

  "floating_elements_placement_rules": {
    "goal": "ChatWidget, StickyMobileCTA, ResumeBookingChip, ConsentBanner tidak saling tabrak; aman di viewport pendek.",
    "z_index_system": {
      "announcement_bar": 40,
      "public_header": 50,
      "sticky_mobile_cta": 60,
      "chat_fab": 70,
      "chat_panel": 70,
      "modal_overlay": 80,
      "modal_content": 90,
      "toasts": 100
    },
    "offset_tokens": {
      "file": "/app/frontend/src/index.css",
      "css_vars": {
        "--header-h": "90px",
        "--announce-h": "varies (set by component; fallback 0px)",
        "--sticky-cta-h": "72px (mobile bar height incl safe-area)",
        "--fab-gap": "16px",
        "--fab-bottom": "calc(env(safe-area-inset-bottom) + var(--sticky-cta-h) + var(--fab-gap))",
        "--panel-bottom": "calc(env(safe-area-inset-bottom) + var(--sticky-cta-h) + var(--fab-gap) + 56px)"
      }
    },
    "chatwidget_rules": {
      "fab": {
        "position": "fixed",
        "bottom": "var(--fab-bottom)",
        "right": "16px",
        "zIndex": "var(--z-chat, 70)",
        "mobile": "keep above StickyMobileCTA",
        "data_testid": "chat-fab-button"
      },
      "panel": {
        "position": "fixed",
        "bottom": "var(--panel-bottom)",
        "right": "16px",
        "maxHeight": "min(520px, calc(100dvh - var(--header-h) - 24px))",
        "height": "clamp(360px, 62dvh, 520px)",
        "width": "min(380px, calc(100vw - 32px))",
        "overflow": "hidden",
        "data_testid": "chat-panel"
      },
      "viewport_short_cases": {
        "390x640": "panel height turun otomatis via clamp + maxHeight; tidak boleh melewati header",
        "1920x800": "panel tetap 520px max; bottom offset aman"
      }
    },
    "consent_banner": {
      "rule": "Jika ConsentBanner fixed bottom, maka StickyMobileCTA harus naik di atasnya (stacking). Gunakan CSS var --consent-h untuk offset.",
      "data_testid": "consent-banner"
    }
  },

  "page_blueprints": {
    "fleet": {
      "page": "/fleet",
      "primary_goal": "Konversi ke /booking (sewa harian / airport transfer) atau WhatsApp; tetap terasa ‘penuh’ walau unit cuma 3.",
      "data_sources": [
        "GET /api/public/fleet",
        "GET /api/public/booking/config (vehicle_types, services)",
        "GET /api/public/promos",
        "GET /api/public/stats",
        "GET /api/public/testimonials"
      ],
      "sections": [
        {
          "order": 1,
          "name": "Hero + Quick Actions",
          "purpose": "Jelaskan value (armada premium Bandung) + 2 CTA (Booking Online, Minta Penawaran)",
          "components": ["PageHero", "TripEstimatorInline (optional compact)", "Button"],
          "notes": "Hero pakai scrim + glass-on-hero untuk estimator agar label terbaca di foto terang.",
          "data_testids": ["fleet-hero-booking-button", "fleet-hero-quotation-button"]
        },
        {
          "order": 2,
          "name": "Fleet Grid (existing) + Filter Type",
          "purpose": "Browse cepat; tetap ada empty/loading",
          "components": ["FleetCard", "Select (shadcn)", "Skeleton"],
          "data": "fleet[] + booking/config.vehicle_types[]",
          "empty_state": "Jika fleet kosong: tampilkan CTA ke /quotation + WhatsApp + jelaskan layanan tetap tersedia (airport transfer / paket)."
        },
        {
          "order": 3,
          "name": "Perbandingan Tipe Armada (Value Table)",
          "purpose": "Mengisi halaman saat unit sedikit; bantu user memilih",
          "components": ["Table (shadcn)", "Badge", "IconChip"],
          "data": "booking/config.vehicle_types[] (from_price, max_capacity, units)",
          "a11y": "Harga pakai tabular-nums; table punya caption; loading skeleton."
        },
        {
          "order": 4,
          "name": "Promo Aktif (Carousel/Stack)",
          "purpose": "Dorong urgency tanpa angka palsu",
          "components": ["Carousel (shadcn)", "GlassCard"],
          "data": "promos[]",
          "empty_state": "Jika tidak ada promo: tampilkan ‘Harga transparan + DP 30%’ dari booking/config.dp_percent."
        },
        {
          "order": 5,
          "name": "Booking Online CTA (Band)",
          "purpose": "Konversi utama",
          "components": ["CtaBand"],
          "data": "booking/config.dp_percent + hold_hours",
          "copy": "Tekankan DP 30% & hold 2 jam (real)."
        },
        {
          "order": 6,
          "name": "Testimoni + Trust Signals",
          "purpose": "Social proof",
          "components": ["Testimonials section existing", "StatCounter"],
          "data": "testimonials[] + stats"
        }
      ],
      "mobile_notes": [
        "Grid jadi 1 kolom; perbandingan tipe armada jadi cards (Table → stacked rows) untuk readability.",
        "CTA band sticky tidak boleh; gunakan StickyMobileCTA existing saja." 
      ]
    },

    "destinations": {
      "page": "/destinations",
      "primary_goal": "Buat user yakin memilih destinasi + langsung lanjut booking/paket.",
      "data_sources": [
        "GET /api/public/destinations",
        "GET /api/public/packages",
        "GET /api/public/stats",
        "GET /api/public/articles"
      ],
      "sections": [
        {
          "order": 1,
          "name": "Hero + Region Filter",
          "purpose": "Entry point + filter cepat",
          "components": ["PageHero", "Select (shadcn)", "DestCard"],
          "data_testids": ["destinations-region-filter"]
        },
        {
          "order": 2,
          "name": "Bento Grid Destinasi (existing) + Empty/Loading",
          "purpose": "Browse",
          "components": ["DestCard", "Skeleton"],
          "data": "destinations[]"
        },
        {
          "order": 3,
          "name": "Fun Facts (Data-driven)",
          "purpose": "Mengisi halaman + edukasi ringan tanpa angka palsu",
          "components": ["GlassCard", "Badge", "Separator"],
          "data": "destinations[].highlights + best_time (ambil 3–6 item teratas dari destinasi populer)",
          "copy_rule": "Fun fact harus berasal dari highlight/itinerary/best_time; jangan bikin fakta baru." 
        },
        {
          "order": 4,
          "name": "Paket Wisata Populer",
          "purpose": "Konversi ke paket (price_from real)",
          "components": ["Carousel", "Card"],
          "data": "packages[]",
          "a11y": "Harga tabular-nums; empty state: arahkan ke /quotation." 
        },
        {
          "order": 5,
          "name": "FAQ Destinasi (Accordion)",
          "purpose": "Jawab keberatan umum",
          "components": ["Accordion (shadcn)", "SectionHeading"],
          "data": "destinations[].faqs (gabungkan 6–10 Q/A dari destinasi populer)",
          "data_testids": ["destinations-faq-accordion"]
        },
        {
          "order": 6,
          "name": "Narasi + CTA Penutup",
          "purpose": "Storytelling singkat + ajak booking",
          "components": ["ScrollStory (existing) atau Reveal", "CtaBand"],
          "data": "stats + booking/config (dp_percent, hold_hours) jika diperlukan",
          "copy": "Narasi 2–3 paragraf max, berakhir CTA: ‘Mulai Booking Online’ + ‘Konsultasi via WhatsApp’."
        }
      ],
      "mobile_notes": [
        "Fun facts jadi stack cards 1 kolom.",
        "FAQ accordion full-width; CTA band setelah FAQ agar natural." 
      ]
    },

    "trip_calculator": {
      "page": "/trip-calculator",
      "primary_goal": "Buat kalkulator terasa bernilai bahkan sebelum hasil; dorong lanjut ke /booking.",
      "data_sources": [
        "POST /api/public/trip-estimate",
        "GET /api/public/booking/config",
        "GET /api/public/promos",
        "GET /api/public/routes"
      ],
      "sections": [
        {
          "order": 1,
          "name": "Hero + Trust Microcopy",
          "purpose": "Jelaskan harga dihitung server-side; transparan",
          "components": ["PageHero", "StatCounter (mini)"]
        },
        {
          "order": 2,
          "name": "Calculator Workspace (Form | Result)",
          "purpose": "Interaksi utama",
          "components": ["Card/GlassCard", "Form (shadcn)", "Select (shadcn)", "Skeleton"],
          "layout": "Desktop 2 kolom; mobile 1 kolom (result collapsible).",
          "empty_state": "Sebelum submit: tampilkan ‘contoh breakdown’ berbasis aturan nyata (DP 30%, hold 2 jam) tanpa angka harga; tampilkan tips memilih tipe armada dari booking/config.vehicle_types.",
          "data_testids": ["trip-calculator-submit-button", "trip-calculator-form"]
        },
        {
          "order": 3,
          "name": "Promo yang Bisa Dipakai",
          "purpose": "Dorong konversi",
          "components": ["Carousel", "Badge"],
          "data": "promos[]",
          "empty_state": "Jika kosong: tampilkan ‘Harga terbaik otomatis’ + CTA booking." 
        },
        {
          "order": 4,
          "name": "CTA Band: Lanjut Booking",
          "purpose": "Konversi",
          "components": ["CtaBand"],
          "data": "booking/config.dp_percent + hold_hours"
        }
      ],
      "mobile_notes": [
        "Result panel jadi Drawer/Collapsible agar tidak makan layar.",
        "Gunakan Skeleton saat loading estimate; tampilkan error state jelas (Alert shadcn)." 
      ]
    }
  },

  "component_path": {
    "shadcn_ui": {
      "button": "/app/frontend/src/components/ui/button.jsx",
      "card": "/app/frontend/src/components/ui/card.jsx",
      "dialog": "/app/frontend/src/components/ui/dialog.jsx",
      "drawer": "/app/frontend/src/components/ui/drawer.jsx",
      "accordion": "/app/frontend/src/components/ui/accordion.jsx",
      "select": "/app/frontend/src/components/ui/select.jsx",
      "carousel": "/app/frontend/src/components/ui/carousel.jsx",
      "skeleton": "/app/frontend/src/components/ui/skeleton.jsx",
      "table": "/app/frontend/src/components/ui/table.jsx",
      "alert": "/app/frontend/src/components/ui/alert.jsx",
      "sonner": "/app/frontend/src/components/ui/sonner.jsx"
    },
    "existing_public_components_to_reuse": [
      "PageHero",
      "SectionHeading",
      "Reveal",
      "GlassCard",
      "StatCounter",
      "FleetCard",
      "DestCard",
      "TripEstimatorInline",
      "BookingStepsSection",
      "FleetSpecGrid",
      "PhotoSphereTour",
      "Lightbox",
      "RouteMapInteractive",
      "MegaMenu",
      "StickyMobileCTA",
      "ScrollStory"
    ]
  },

  "image_urls": {
    "note": "Tidak mengambil gambar baru karena repo sudah memakai hero foto dari data destinasi (hero_image) dan paket (image_url). Gunakan itu sebagai sumber utama agar tidak mock.",
    "categories": [
      {
        "category": "destination-hero",
        "source": "GET /api/public/destinations[].hero_image",
        "usage": "Hero /destinations dan detail destinasi"
      },
      {
        "category": "package-card",
        "source": "GET /api/public/packages[].image_url",
        "usage": "Carousel paket wisata"
      },
      {
        "category": "fleet-gallery",
        "source": "GET /api/public/fleet[].photos[] / gallery[]",
        "usage": "Fleet cards + lightbox"
      }
    ]
  },

  "motion_microinteractions": {
    "principles": [
      "Gunakan Reveal/Framer Motion untuk entrance ringan (opacity + y 8px) dengan prefers-reduced-motion fallback.",
      "Hover lift hanya pada card clickable (FleetCard/DestCard/promo card).",
      "CTA shine hanya pada primary CTA (booking) dan tidak pada semua tombol." 
    ],
    "durations": {
      "fast": "var(--motion-fast)",
      "base": "var(--motion-base)",
      "slow": "var(--motion-slow)"
    }
  },

  "accessibility": {
    "requirements": [
      "Kontras teks minimal WCAG AA (utama keluhan user).",
      "Focus-visible ring sudah ada; pastikan komponen baru tidak menimpa outline.",
      "Dialog/Drawer: aria-label, aria-describedby, ESC close.",
      "Loading + empty state wajib untuk list/table (gate strict).",
      "Tidak pakai <select> native; gunakan shadcn Select.",
      "Harga selalu tabular-nums." 
    ]
  },

  "instructions_to_main_agent": {
    "priority_order": [
      "1) Patch index.css: glass-modal & glass-3d refraction + tambah .glass-on-hero + scrim tokens.",
      "2) Fix CTA panel blog: ganti gradient invalid dengan CtaBand pattern (bg token-based).",
      "3) Reposition ChatWidget: gunakan offset vars + clamp height + z-index system.",
      "4) Implement section blueprint /fleet, /destinations, /trip-calculator dengan data nyata + loading/empty.",
      "5) Global rename brand ke RahazaTrans (navbar/footer/chat/SEO/WA text)." 
    ],
    "implementation_notes_js": [
      "Repo pakai .js (bukan .tsx). Pastikan semua contoh komponen ditulis React .js.",
      "Tambahkan data-testid pada setiap Button/Link/Input baru (kebab-case).",
      "Untuk CTA band: gunakan style berbasis CSS var (bg-[hsla(var(--cta-band-bg))]) bukan Tailwind gradient var triplet.",
      "Untuk hero estimator: bungkus dengan scrim overlay + class .glass-on-hero agar label/placeholder tidak washout." 
    ]
  },

  "appendix_general_ui_ux_design_guidelines": "<General UI UX Design Guidelines>  \n    - You must **not** apply universal transition. Eg: `transition: all`. This results in breaking transforms. Always add transitions for specific interactive elements like button, input excluding transforms\n    - You must **not** center align the app container, ie do not add `.App { text-align: center; }` in the css file. This disrupts the human natural reading flow of text\n   - NEVER: use AI assistant Emoji characters like`🤖🧠💭💡🔮🎯📚🎭🎬🎪🎉🎊🎁🎀🎂🍰🎈🎨🎰💰💵💳🏦💎🪙💸🤑📊📈📉💹🔢🏆🥇 etc for icons. Always use **FontAwesome cdn** or **lucid-react** library already installed in the package.json\n\n **GRADIENT RESTRICTION RULE**\nNEVER use dark/saturated gradient combos (e.g., purple/pink) on any UI element.  Prohibited gradients: blue-500 to purple 600, purple 500 to pink-500, green-500 to blue-500, red to pink etc\nNEVER use dark gradients for logo, testimonial, footer etc\nNEVER let gradients cover more than 20% of the viewport.\nNEVER apply gradients to text-heavy content or reading areas.\nNEVER use gradients on small UI elements (<100px width).\nNEVER stack multiple gradient layers in the same viewport.\n\n**ENFORCEMENT RULE:**\n    • Id gradient area exceeds 20% of viewport OR affects readability, **THEN** use solid colors\n\n**How and where to use:**\n   • Section backgrounds (not content backgrounds)\n   • Hero section header content. Eg: dark to light to dark color\n   • Decorative overlays and accent elements only\n   • Hero section with 2-3 mild color\n   • Gradients creation can be done for any angle say horizontal, vertical or diagonal\n\n- For AI chat, voice application, **do not use purple color. Use color like light green, ocean blue, peach orange etc**\n\n</Font Guidelines>\n\n- Every interaction needs micro-animations - hover states, transitions, parallax effects, and entrance animations. Static = dead. \n   \n- Use 2-3x more spacing than feels comfortable. Cramped designs look cheap.\n\n- Subtle grain textures, noise overlays, custom cursors, selection states, and loading animations: separates good from extraordinary.\n   \n- Before generating UI, infer the visual style from the problem statement (palette, contrast, mood, motion) and immediately instantiate it by setting global design tokens (primary, secondary/accent, background, foreground, ring, state colors), rather than relying on any library defaults. Don't make the background dark as a default step, always understand problem first and define colors accordingly\n    Eg: - if it implies playful/energetic, choose a colorful scheme\n           - if it implies monochrome/minimal, choose a black–white/neutral scheme\n\n**Component Reuse:**\n\t- Prioritize using pre-existing components from src/components/ui when applicable\n\t- Create new components that match the style and conventions of existing components when needed\n\t- Examine existing components to understand the project's component patterns before creating new ones\n\n**IMPORTANT**: Do not use HTML based component like dropdown, calendar, toast etc. You **MUST** always use `/app/frontend/src/components/ui/ ` only as a primary components as these are modern and stylish component\n\n**Best Practices:**\n\t- Use Shadcn/UI as the primary component library for consistency and accessibility\n\t- Import path: ./components/[component-name]\n\n**Export Conventions:**\n\t- Components MUST use named exports (export const ComponentName = ...)\n\t- Pages MUST use default exports (export default function PageName() {...})\n\n**Toasts:**\n  - Use `sonner` for toasts\"\n  - Sonner component are located in `/app/src/components/ui/sonner.tsx`\n\nUse 2–4 color gradients, subtle textures/noise overlays, or CSS-based noise to avoid flat visuals.\n</General UI UX Design Guidelines>"
}
