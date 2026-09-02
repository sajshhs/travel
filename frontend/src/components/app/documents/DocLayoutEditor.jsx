import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { Eye, Loader2, RotateCcw, Save, Upload, X } from "lucide-react";
import apiClient from "@/services/apiClient";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { LoadingState } from "@/components/shared/DataStates";
import { fetchPdfBlobUrl } from "./docUtils";

export function Field({ label, children, hint }) {
  return (
    <div className="space-y-1.5">
      <Label className="text-[12px]">{label}</Label>
      {children}
      {hint ? <p className="text-[11px] text-[#8E8E93]">{hint}</p> : null}
    </div>
  );
}

export function Toggle({ label, checked, onChange, testId, hint }) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-[10px] border border-[#E2E3E7] px-3 py-2">
      <div><p className="text-[12.5px] font-semibold text-[#1C1C1E]">{label}</p>{hint ? <p className="text-[11px] text-[#6B6B73]">{hint}</p> : null}</div>
      <Switch checked={Boolean(checked)} onCheckedChange={onChange} data-testid={testId} />
    </div>
  );
}

/** Pratinjau PDF inline (iframe) memakai mesin cetak yang sama dengan dokumen nyata. */
export function PreviewPane({ code, draft, script }) {
  const [url, setUrl] = useState("");
  const [busy, setBusy] = useState(false);
  const refresh = useCallback(async () => {
    setBusy(true);
    try {
      const res = await apiClient.post(`/documents/layouts/${code}/preview`, { ...(draft || {}), script: script || undefined }, { responseType: "blob" });
      setUrl((old) => { if (old) window.URL.revokeObjectURL(old); return window.URL.createObjectURL(new Blob([res.data], { type: "application/pdf" })); });
    } catch (e) { toast.error("Gagal membuat pratinjau"); } finally { setBusy(false); }
  }, [code, draft, script]);
  useEffect(() => { refresh(); }, [code]); // eslint-disable-line react-hooks/exhaustive-deps
  return (
    <div className="space-y-2" data-testid="doc-preview-pane">
      <div className="flex items-center justify-between">
        <p className="text-[12px] font-semibold text-[#6B6B73]">Pratinjau (data contoh)</p>
        <button className="secondary-button !px-2.5 !py-1 !text-[12px]" onClick={refresh} disabled={busy} data-testid="doc-preview-refresh">{busy ? <Loader2 size={13} className="animate-spin" /> : <Eye size={13} />} Perbarui pratinjau</button>
      </div>
      {url ? <iframe title="Pratinjau dokumen" src={`${url}#toolbar=0&view=FitH`} className="h-[640px] w-full rounded-[12px] border border-[#E2E3E7] bg-white" data-testid="doc-preview-frame" />
        : <div className="flex h-[640px] items-center justify-center rounded-[12px] border border-dashed border-[#E2E3E7] text-[12px] text-[#8E8E93]">Memuat pratinjau…</div>}
      {url ? <p className="text-[11px] text-[#8E8E93]">Pratinjau tidak tampil? <button type="button" className="font-semibold text-[#007AFF]" onClick={() => window.open(url, "_blank", "noopener")} data-testid="doc-preview-open">Buka PDF di tab baru</button></p> : null}
    </div>
  );
}

export function DocCodeSelect({ value, onChange, targets, includeDefault = true }) {
  return (
    <Select value={value} onValueChange={onChange}>
      <SelectTrigger className="w-full sm:w-[340px]" data-testid="doc-code-select"><SelectValue /></SelectTrigger>
      <SelectContent>{targets.filter((t) => includeDefault || t.code !== "__default__").map((t) => <SelectItem key={t.code} value={t.code}>{t.label}{t.customized || t.script_customized ? " ●" : ""}</SelectItem>)}</SelectContent>
    </Select>
  );
}

const PAPERS = ["A4", "LETTER", "LEGAL"];

export function LayoutEditor({ code, canEdit, onSaved }) {
  const [layout, setLayout] = useState(null);
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);
  const load = useCallback(() => { apiClient.get(`/documents/layouts/${code}`).then((r) => setLayout(r.data)).catch(() => toast.error("Gagal memuat tampilan dokumen")); }, [code]);
  useEffect(() => { setLayout(null); load(); }, [load]);
  if (!layout) return <LoadingState testId="doc-layout-loading" />;
  const b = layout.brand || {}, o = layout.options || {}, t = layout.table || {};
  const bf = (k, v) => setLayout((l) => ({ ...l, brand: { ...l.brand, [k]: v } }));
  const of = (k, v) => setLayout((l) => ({ ...l, options: { ...l.options, [k]: v } }));
  const tf = (k, v) => setLayout((l) => ({ ...l, table: { ...l.table, [k]: v } }));
  const sf = (i, k, v) => setLayout((l) => ({ ...l, signatures: l.signatures.map((s, idx) => idx === i ? { ...s, [k]: v } : s) }));
  const secf = (key, v) => setLayout((l) => ({ ...l, sections: l.sections.map((s) => s.key === key ? { ...s, visible: v } : s) }));
  const draft = { brand: b, options: o, table: t, signatures: layout.signatures, sections: layout.sections };

  const save = async () => {
    setSaving(true);
    try { const r = await apiClient.put(`/documents/layouts/${code}`, draft); setLayout(r.data); toast.success("Tampilan dokumen disimpan"); onSaved && onSaved(); }
    catch (e) { toast.error(e?.response?.data?.detail || "Gagal menyimpan"); } finally { setSaving(false); }
  };
  const reset = async () => {
    if (!window.confirm("Kembalikan tampilan dokumen ini ke bawaan?")) return;
    try { const r = await apiClient.delete(`/documents/layouts/${code}`); setLayout(r.data); toast.success("Dikembalikan ke bawaan"); onSaved && onSaved(); }
    catch (e) { toast.error(e?.response?.data?.detail || "Gagal mereset"); }
  };
  const uploadLogo = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      const fd = new FormData(); fd.append("file", file); fd.append("alt", "Logo dokumen"); fd.append("source", "doc_layout");
      const r = await apiClient.post("/media", fd, { headers: { "Content-Type": "multipart/form-data" } });
      setLayout((l) => ({ ...l, brand: { ...l.brand, logo_media_id: r.data?.id, logo_url: r.data?.url } }));
      toast.success("Logo diunggah — klik Simpan untuk menerapkan");
    } catch (err) { toast.error(err?.response?.data?.detail || "Gagal mengunggah logo"); } finally { setUploading(false); }
  };

  return (
    <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]" data-testid="doc-layout-editor">
      <div className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <p className="text-[12.5px] text-[#6B6B73]">{code === "__default__" ? "Identitas & gaya ini dipakai SEMUA dokumen." : layout.overridden ? "Dokumen ini punya pengaturan sendiri (override bawaan)." : "Mengikuti bawaan — ubah di sini bila dokumen ini perlu tampil berbeda."}</p>
          {canEdit ? (
            <div className="flex gap-2">
              <button className="secondary-button !px-2.5 !py-1 !text-[12px]" onClick={reset} data-testid="doc-layout-reset"><RotateCcw size={13} /> Bawaan</button>
              <button className="primary-button !px-3 !py-1.5 !text-[12.5px]" onClick={save} disabled={saving} data-testid="doc-layout-save">{saving ? <Loader2 size={13} className="animate-spin" /> : <Save size={13} />} Simpan</button>
            </div>
          ) : null}
        </div>

        <fieldset disabled={!canEdit} className="space-y-4 disabled:cursor-not-allowed disabled:opacity-60">
          <div className="space-y-3 rounded-[12px] border border-[#E2E3E7] p-3">
            <p className="text-[12.5px] font-bold text-[#1C1C1E]">Kop surat & identitas</p>
            <div className="flex items-center gap-3">
              {b.logo_url ? <img src={b.logo_url} alt="Logo" className="h-12 max-w-[140px] rounded border border-[#E2E3E7] bg-white object-contain px-1" data-testid="doc-logo-preview" /> : <div className="flex h-12 w-24 items-center justify-center rounded border border-dashed border-[#E2E3E7] text-[10.5px] text-[#8E8E93]">Tanpa logo</div>}
              <label className="secondary-button cursor-pointer !px-2.5 !py-1 !text-[12px]" data-testid="doc-logo-upload">
                <Upload size={13} /> {uploading ? "Mengunggah…" : b.logo_media_id ? "Ganti logo" : "Unggah logo"}
                <input type="file" accept="image/*" className="hidden" onChange={uploadLogo} disabled={uploading} />
              </label>
              {b.logo_media_id ? <button className="icon-button !h-8 !w-8" title="Hapus logo" onClick={() => { bf("logo_media_id", null); bf("logo_url", null); }} data-testid="doc-logo-remove"><X size={13} /></button> : null}
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <Field label="Nama perusahaan"><Input value={b.company_name || ""} onChange={(e) => bf("company_name", e.target.value)} data-testid="doc-brand-name" /></Field>
              <Field label="Tagline"><Input value={b.tagline || ""} onChange={(e) => bf("tagline", e.target.value)} data-testid="doc-brand-tagline" /></Field>
              <Field label="Telepon / WhatsApp"><Input value={b.phone || ""} onChange={(e) => bf("phone", e.target.value)} data-testid="doc-brand-phone" /></Field>
              <Field label="Email"><Input value={b.email || ""} onChange={(e) => bf("email", e.target.value)} data-testid="doc-brand-email" /></Field>
              <Field label="Website"><Input value={b.website || ""} onChange={(e) => bf("website", e.target.value)} data-testid="doc-brand-website" /></Field>
              <Field label="NPWP"><Input value={b.npwp || ""} onChange={(e) => bf("npwp", e.target.value)} data-testid="doc-brand-npwp" /></Field>
            </div>
            <Field label="Alamat"><Textarea rows={2} value={b.address || ""} onChange={(e) => bf("address", e.target.value)} data-testid="doc-brand-address" /></Field>
            <div className="grid gap-3 sm:grid-cols-3">
              <Field label="Mode kop"><Select value={b.header_mode || "system"} onValueChange={(v) => bf("header_mode", v)}><SelectTrigger data-testid="doc-header-mode"><SelectValue /></SelectTrigger><SelectContent><SelectItem value="system">Dirakit sistem (logo + identitas)</SelectItem><SelectItem value="none">Tanpa kop (kertas berkop sendiri)</SelectItem></SelectContent></Select></Field>
              <Field label="Mode footer"><Select value={b.footer_mode || "system"} onValueChange={(v) => bf("footer_mode", v)}><SelectTrigger data-testid="doc-footer-mode"><SelectValue /></SelectTrigger><SelectContent><SelectItem value="system">Identitas ringkas</SelectItem><SelectItem value="none">Tanpa footer</SelectItem></SelectContent></Select></Field>
              <Field label="Kertas"><Select value={b.paper || "A4"} onValueChange={(v) => bf("paper", v)}><SelectTrigger data-testid="doc-paper"><SelectValue /></SelectTrigger><SelectContent>{PAPERS.map((p) => <SelectItem key={p} value={p}>{p}</SelectItem>)}</SelectContent></Select></Field>
            </div>
            <Field label="Teks footer (kosong = identitas otomatis)"><Input value={b.footer_text || ""} onChange={(e) => bf("footer_text", e.target.value)} data-testid="doc-footer-text" /></Field>
          </div>

          <div className="space-y-3 rounded-[12px] border border-[#E2E3E7] p-3">
            <p className="text-[12.5px] font-bold text-[#1C1C1E]">Gaya & watermark</p>
            <div className="grid gap-3 sm:grid-cols-2">
              <Field label="Warna aksen"><div className="flex items-center gap-2"><input type="color" value={b.accent_color || "#0F6E56"} onChange={(e) => bf("accent_color", e.target.value)} className="h-9 w-12 rounded border border-[#E2E3E7]" data-testid="doc-accent-color" /><Input value={b.accent_color || ""} onChange={(e) => bf("accent_color", e.target.value)} className="font-mono" /></div></Field>
              <Field label="Warna teks judul"><div className="flex items-center gap-2"><input type="color" value={b.text_color || "#1C1C1E"} onChange={(e) => bf("text_color", e.target.value)} className="h-9 w-12 rounded border border-[#E2E3E7]" data-testid="doc-text-color" /><Input value={b.text_color || ""} onChange={(e) => bf("text_color", e.target.value)} className="font-mono" /></div></Field>
              <Field label="Teks watermark (mis. LUNAS / DRAFT)"><Input value={b.watermark_text || ""} onChange={(e) => bf("watermark_text", e.target.value)} data-testid="doc-watermark" /></Field>
              <Field label="Kepekatan watermark (%)"><Input type="number" min={0} max={60} value={b.watermark_opacity ?? 8} onChange={(e) => bf("watermark_opacity", Number(e.target.value))} data-testid="doc-watermark-opacity" /></Field>
            </div>
            <div className="grid gap-3 sm:grid-cols-4">
              {[["margin_top_mm", "Margin atas"], ["margin_bottom_mm", "Margin bawah"], ["margin_left_mm", "Margin kiri"], ["margin_right_mm", "Margin kanan"]].map(([k, l]) => (
                <Field key={k} label={`${l} (mm)`}><Input type="number" value={b[k] ?? ""} onChange={(e) => bf(k, Number(e.target.value))} data-testid={`doc-${k}`} /></Field>
              ))}
            </div>
            <div className="grid gap-3 sm:grid-cols-3">
              <Field label="Garis tabel"><Select value={t.grid || "horizontal"} onValueChange={(v) => tf("grid", v)}><SelectTrigger data-testid="doc-table-grid"><SelectValue /></SelectTrigger><SelectContent><SelectItem value="full">Kotak penuh</SelectItem><SelectItem value="horizontal">Garis horizontal</SelectItem><SelectItem value="none">Transparan</SelectItem></SelectContent></Select></Field>
              <Field label="Ukuran huruf tabel"><Input type="number" step="0.5" value={t.font_size ?? 9} onChange={(e) => tf("font_size", Number(e.target.value))} data-testid="doc-table-font" /></Field>
              <div className="space-y-2 pt-5">
                <Toggle label="Kepala tabel berwarna" checked={t.header_fill !== false} onChange={(v) => tf("header_fill", v)} testId="doc-table-header-fill" />
              </div>
            </div>
            <div className="grid gap-2 sm:grid-cols-2">
              <Toggle label="Baris tabel belang" checked={t.zebra !== false} onChange={(v) => tf("zebra", v)} testId="doc-table-zebra" />
              <Toggle label="Sorot baris total" checked={t.total_highlight !== false} onChange={(v) => tf("total_highlight", v)} testId="doc-table-total" />
              <Toggle label="Nomor halaman di footer" checked={b.show_page_numbers !== false} onChange={(v) => bf("show_page_numbers", v)} testId="doc-page-numbers" />
              <Toggle label="Catatan 'diterbitkan elektronik'" checked={o.show_generated_note !== false} onChange={(v) => of("show_generated_note", v)} testId="doc-generated-note" />
            </div>
          </div>

          <div className="space-y-3 rounded-[12px] border border-[#E2E3E7] p-3">
            <p className="text-[12.5px] font-bold text-[#1C1C1E]">Bagian yang tercetak</p>
            <div className="grid gap-2 sm:grid-cols-2" data-testid="doc-sections">
              {(layout.sections || []).map((s) => <Toggle key={s.key} label={s.label} checked={s.visible !== false} onChange={(v) => secf(s.key, v)} testId={`doc-section-${s.key}`} />)}
            </div>
          </div>

          <div className="space-y-3 rounded-[12px] border border-[#E2E3E7] p-3">
            <div className="flex items-center justify-between">
              <p className="text-[12.5px] font-bold text-[#1C1C1E]">Kolom tanda tangan</p>
              <button className="secondary-button !px-2.5 !py-1 !text-[12px]" disabled={(layout.signatures || []).length >= 3} onClick={() => setLayout((l) => ({ ...l, signatures: [...(l.signatures || []), { title: "Pihak", name: "", position: "", auto_from_issuer: false }] }))} data-testid="doc-sig-add">+ Kolom</button>
            </div>
            {(layout.signatures || []).map((s, i) => (
              <div key={i} className="grid gap-2 rounded-[10px] bg-[#F7F8FA] p-2.5 sm:grid-cols-[1fr_1fr_1fr_auto]" data-testid={`doc-sig-${i}`}>
                <Input placeholder="Judul (mis. Hormat kami)" value={s.title || ""} onChange={(e) => sf(i, "title", e.target.value)} data-testid={`doc-sig-title-${i}`} />
                <Input placeholder="Nama (kosong = penerbit)" value={s.name || ""} onChange={(e) => sf(i, "name", e.target.value)} data-testid={`doc-sig-name-${i}`} />
                <Input placeholder="Jabatan" value={s.position || ""} onChange={(e) => sf(i, "position", e.target.value)} data-testid={`doc-sig-position-${i}`} />
                <div className="flex items-center gap-2">
                  <label className="flex items-center gap-1 text-[11px] text-[#6B6B73]"><Switch checked={Boolean(s.auto_from_issuer)} onCheckedChange={(v) => sf(i, "auto_from_issuer", v)} data-testid={`doc-sig-auto-${i}`} /> Nama penerbit</label>
                  <button className="icon-button !h-8 !w-8" onClick={() => setLayout((l) => ({ ...l, signatures: l.signatures.filter((_, idx) => idx !== i) }))} data-testid={`doc-sig-del-${i}`}><X size={13} /></button>
                </div>
              </div>
            ))}
            <div className="grid gap-3 sm:grid-cols-2">
              <Field label="Tempat (tempat, tanggal di atas ttd)"><Input value={o.place || ""} onChange={(e) => of("place", e.target.value)} placeholder="mis. Bandung" data-testid="doc-place" /></Field>
              <div className="space-y-2 pt-5"><Toggle label="Tampilkan tempat & tanggal" checked={o.show_place_date !== false} onChange={(v) => of("show_place_date", v)} testId="doc-show-place-date" /></div>
              <Toggle label="Tampilkan nomor dokumen" checked={o.show_doc_number !== false} onChange={(v) => of("show_doc_number", v)} testId="doc-show-number" />
              <Toggle label="Catatan materai pada kolom pertama" checked={Boolean(o.show_materai)} onChange={(v) => of("show_materai", v)} testId="doc-show-materai" />
            </div>
          </div>
        </fieldset>
      </div>
      <PreviewPane code={code} draft={draft} />
    </div>
  );
}

export function ScriptEditor({ code, canEdit, onSaved }) {
  const [s, setS] = useState(null);
  const [saving, setSaving] = useState(false);
  const load = useCallback(() => { apiClient.get(`/documents/layouts/${code}/script`).then((r) => setS(r.data)).catch(() => toast.error("Gagal memuat naskah")); }, [code]);
  useEffect(() => { setS(null); load(); }, [load]);
  if (!s) return <LoadingState testId="doc-script-loading" />;
  const f = (k, v) => setS((x) => ({ ...x, [k]: v }));
  const unknown = (txt) => [...String(txt || "").matchAll(/\{\{\s*([a-zA-Z0-9_]+)\s*\}\}/g)].map((m) => m[1]).filter((t) => !s.placeholders.some((p) => p.token === t));
  const bad = [...new Set([...unknown(s.intro), ...unknown(s.closing), ...unknown(s.terms)])];
  const save = async () => {
    setSaving(true);
    try { const r = await apiClient.put(`/documents/layouts/${code}/script`, { intro: s.intro, closing: s.closing, terms: s.terms }); setS(r.data); toast.success("Naskah disimpan"); onSaved && onSaved(); }
    catch (e) { toast.error(e?.response?.data?.detail || "Gagal menyimpan naskah"); } finally { setSaving(false); }
  };
  const reset = async () => {
    try { const r = await apiClient.delete(`/documents/layouts/${code}/script`); setS(r.data); toast.success("Naskah dikembalikan ke bawaan"); onSaved && onSaved(); } catch (e) { toast.error("Gagal mereset"); }
  };
  const insert = (tok) => f("intro", `${s.intro || ""}{{${tok}}}`);
  return (
    <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]" data-testid="doc-script-editor">
      <div className="space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <p className="text-[12.5px] text-[#6B6B73]">Naskah {s.label}. Placeholder <code>{"{{token}}"}</code> diganti data nyata saat cetak. {s.customized ? "● disesuaikan" : "mengikuti bawaan"}</p>
          {canEdit ? <div className="flex gap-2"><button className="secondary-button !px-2.5 !py-1 !text-[12px]" onClick={reset} data-testid="doc-script-reset"><RotateCcw size={13} /> Bawaan</button><button className="primary-button !px-3 !py-1.5 !text-[12.5px]" onClick={save} disabled={saving || bad.length > 0} data-testid="doc-script-save">{saving ? <Loader2 size={13} className="animate-spin" /> : <Save size={13} />} Simpan</button></div> : null}
        </div>
        {bad.length ? <p className="rounded-[10px] bg-[#FFF5F4] px-3 py-2 text-[12px] text-[#A8221A]" data-testid="doc-script-unknown">Placeholder tidak dikenal: {bad.map((t) => `{{${t}}}`).join(", ")} — tidak akan terisi saat cetak.</p> : null}
        <fieldset disabled={!canEdit} className="space-y-3 disabled:cursor-not-allowed disabled:opacity-60">
          <Field label="Kalimat pembuka (di atas rincian)"><Textarea rows={4} value={s.intro || ""} onChange={(e) => f("intro", e.target.value)} data-testid="doc-script-intro" /></Field>
          <Field label="Kalimat penutup (di bawah rincian)"><Textarea rows={3} value={s.closing || ""} onChange={(e) => f("closing", e.target.value)} data-testid="doc-script-closing" /></Field>
          <Field label="Syarat & ketentuan (satu baris = satu poin)"><Textarea rows={5} value={s.terms || ""} onChange={(e) => f("terms", e.target.value)} data-testid="doc-script-terms" /></Field>
        </fieldset>
        <div>
          <p className="mb-1.5 text-[11.5px] font-semibold text-[#6B6B73]">Placeholder tersedia (klik untuk menambah ke pembuka):</p>
          <div className="flex flex-wrap gap-1.5" data-testid="doc-script-placeholders">
            {s.placeholders.map((p) => <button key={p.token} type="button" disabled={!canEdit} onClick={() => insert(p.token)} title={`${p.label} — contoh: ${p.sample}`} className="rounded-full border border-[#E2E3E7] bg-white px-2 py-0.5 font-mono text-[11px] text-[#3C3C43] hover:border-[#B9D5FF]" data-testid={`doc-ph-${p.token}`}>{`{{${p.token}}}`}</button>)}
          </div>
        </div>
      </div>
      <PreviewPane code={code} script={{ intro: s.intro, closing: s.closing, terms: s.terms }} />
    </div>
  );
}

export { fetchPdfBlobUrl };
