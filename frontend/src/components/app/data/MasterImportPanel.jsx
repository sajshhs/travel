import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { AlertTriangle, CheckCircle2, Download, FileUp, Loader2, Upload } from "lucide-react";
import apiClient from "@/services/apiClient";
import { Switch } from "@/components/ui/switch";
import { formatDateTime } from "@/utils/formatters";

export default function MasterImportPanel({ onDone }) {
  const fileRef = useRef(null);
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [busy, setBusy] = useState("");
  const [mode, setMode] = useState("upsert");
  const [snapshot, setSnapshot] = useState(true);
  const [picked, setPicked] = useState([]);
  const [result, setResult] = useState(null);
  const [history, setHistory] = useState([]);
  const [openErr, setOpenErr] = useState({});

  const loadHistory = () => apiClient.get("/data/import/history").then((r) => setHistory(r.data || [])).catch(() => {});
  useEffect(() => { loadHistory(); }, []);

  const downloadTemplate = async () => {
    try {
      const res = await apiClient.get("/data/import/template.xlsx", { responseType: "blob" });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const a = document.createElement("a"); a.href = url; a.download = "template_master_data_rahazatrans.xlsx"; document.body.appendChild(a); a.click(); a.remove(); window.URL.revokeObjectURL(url);
    } catch (e) { toast.error("Gagal mengunduh template"); }
  };
  const onFile = async (e) => {
    const f = e.target.files?.[0];
    if (!f) return;
    setFile(f); setPreview(null); setResult(null); setBusy("preview");
    try {
      const fd = new FormData(); fd.append("file", f);
      const r = await apiClient.post("/data/import/preview", fd, { headers: { "Content-Type": "multipart/form-data" } });
      setPreview(r.data.sheets);
      setPicked(Object.entries(r.data.sheets).filter(([, s]) => s.valid > 0 && !s.missing_columns?.length).map(([k]) => k));
    } catch (err) { toast.error(err?.response?.data?.detail || "Gagal membaca berkas"); setFile(null); } finally { setBusy(""); e.target.value = ""; }
  };
  const run = async () => {
    if (!file || picked.length === 0) return;
    setBusy("commit");
    try {
      const fd = new FormData(); fd.append("file", file); fd.append("mode", mode); fd.append("sheets", picked.join(",")); fd.append("snapshot", String(snapshot));
      const r = await apiClient.post("/data/import/commit", fd, { headers: { "Content-Type": "multipart/form-data" } });
      setResult(r.data); setPreview(null); setFile(null);
      toast.success(`Impor selesai · +${r.data.totals.inserted} baru, ${r.data.totals.updated} diperbarui, ${r.data.totals.skipped} dilewati`);
      loadHistory(); onDone && onDone();
    } catch (err) { toast.error(err?.response?.data?.detail || "Impor gagal"); } finally { setBusy(""); }
  };

  const entries = preview ? Object.entries(preview) : [];
  const totalValid = entries.filter(([k]) => picked.includes(k)).reduce((s, [, v]) => s + v.valid, 0);
  const totalErr = entries.reduce((s, [, v]) => s + v.errors.length, 0);

  return (
    <section className="section-card" data-testid="master-import-panel">
      <div className="section-head">
        <div className="flex items-center gap-2"><FileUp size={16} className="text-[#007AFF]" /><h2>Impor Master Data (migrasi)</h2></div>
        <div className="flex flex-wrap items-center gap-2">
          <button className="secondary-button !h-9" onClick={downloadTemplate} data-testid="import-template"><Download size={14} /> Unduh Template Excel</button>
          <label className="primary-button cursor-pointer !h-9" data-testid="import-upload">
            {busy === "preview" ? <Loader2 size={14} className="animate-spin" /> : <Upload size={14} />} {file ? "Ganti berkas" : "Unggah & Pratinjau"}
            <input ref={fileRef} type="file" accept=".xlsx" className="hidden" onChange={onFile} disabled={Boolean(busy)} />
          </label>
        </div>
      </div>
      <div className="section-body space-y-3">
        <p className="text-[12.5px] text-[#6B6B73]">Satu workbook Excel berisi sheet <b>Pelanggan, Armada, Driver, Kota, Mitra, Add-on</b> — semua diimpor sekaligus. Data lama yang cocok (telepon/plat/nama) diperbarui, sisanya ditambah. Baris error dilewati dan dilaporkan; snapshot backup otomatis dibuat sebelum impor.</p>

        {preview ? (
          <div className="space-y-3" data-testid="import-preview">
            <div className="overflow-x-auto rounded-[12px] border border-[#E2E3E7]">
              <table className="w-full text-[12.5px]">
                <thead><tr className="bg-[#F7F8FA] text-left text-[11px] uppercase tracking-wide text-[#8E8E93]"><th className="px-3 py-2">Impor</th><th className="px-3 py-2">Sheet</th><th className="px-3 py-2 text-right">Baris</th><th className="px-3 py-2 text-right">Akan ditambah</th><th className="px-3 py-2 text-right">Akan diperbarui</th><th className="px-3 py-2 text-right">Error</th><th className="px-3 py-2">Keterangan</th></tr></thead>
                <tbody className="divide-y divide-[#F2F2F5]">
                  {entries.map(([k, s]) => (
                    <tr key={k} data-testid={`import-sheet-${k}`}>
                      <td className="px-3 py-2"><input type="checkbox" className="accent-[#007AFF]" disabled={s.valid === 0 || s.missing_columns?.length > 0} checked={picked.includes(k)} onChange={() => setPicked((p) => p.includes(k) ? p.filter((x) => x !== k) : [...p, k])} data-testid={`import-pick-${k}`} /></td>
                      <td className="px-3 py-2 font-semibold text-[#1C1C1E]">{s.title}</td>
                      <td className="px-3 py-2 text-right tabular-nums">{s.total}</td>
                      <td className="px-3 py-2 text-right tabular-nums text-[#126E2C]">{s.insert}</td>
                      <td className="px-3 py-2 text-right tabular-nums text-[#0058CC]">{mode === "insert_only" ? <span className="text-[#8E8E93]" title="dilewati pada mode hanya-tambah">{s.update} (lewati)</span> : s.update}</td>
                      <td className="px-3 py-2 text-right tabular-nums">{s.errors.length ? <button type="button" className="font-semibold text-[#A8221A] underline" onClick={() => setOpenErr((o) => ({ ...o, [k]: !o[k] }))} data-testid={`import-errors-${k}`}>{s.errors.length}</button> : <span className="text-[#8E8E93]">0</span>}</td>
                      <td className="px-3 py-2 text-[11.5px] text-[#6B6B73]">{s.missing_columns?.length ? <span className="text-[#A8221A]">Kolom wajib hilang: {s.missing_columns.join(", ")}</span> : s.warnings?.length ? `${s.warnings.length} duplikat dalam berkas` : s.valid === 0 ? "kosong" : "siap"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {entries.filter(([k, s]) => openErr[k] && (s.errors.length || s.warnings?.length)).map(([k, s]) => (
              <div key={k} className="rounded-[10px] border border-[#F0C4C0] bg-[#FFF8F7] px-3 py-2 text-[12px]" data-testid={`import-errorlist-${k}`}>
                <p className="mb-1 font-semibold text-[#A8221A]">{s.title} — baris bermasalah (dilewati saat impor)</p>
                <ul className="max-h-[160px] space-y-0.5 overflow-y-auto text-[#6B6B73]">{[...s.errors, ...(s.warnings || [])].map((e, i) => <li key={i}>Baris {e.row}: {e.msg}</li>)}</ul>
              </div>
            ))}
            <div className="flex flex-wrap items-center justify-between gap-3 rounded-[12px] bg-[#F7F8FA] px-3 py-2.5">
              <div className="flex flex-wrap items-center gap-3">
                <div className="flex gap-1.5">
                  {[["upsert", "Tambah + perbarui yang cocok"], ["insert_only", "Hanya tambah baru"]].map(([v, l]) => (
                    <button key={v} type="button" onClick={() => setMode(v)} data-testid={`import-mode-${v}`} className={`rounded-full border px-3 py-1 text-[12px] font-semibold ${mode === v ? "border-[#007AFF] bg-[#EAF2FF] text-[#0058CC]" : "border-[#E2E3E7] bg-white text-[#6B6B73]"}`}>{l}</button>
                  ))}
                </div>
                <label className="flex items-center gap-2 text-[12px] text-[#6B6B73]"><Switch checked={snapshot} onCheckedChange={setSnapshot} data-testid="import-snapshot" /> Snapshot backup dulu</label>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-[12px] text-[#6B6B73]" data-testid="import-summary">{totalValid} baris siap · {totalErr} error dilewati</span>
                <button className="primary-button !h-9" disabled={busy === "commit" || picked.length === 0 || totalValid === 0} onClick={run} data-testid="import-run">{busy === "commit" ? <Loader2 size={14} className="animate-spin" /> : <Upload size={14} />} Impor Semua Sekaligus</button>
              </div>
            </div>
          </div>
        ) : null}

        {result ? (
          <div className="rounded-[12px] border border-[#BFE3C6] bg-[#F1FAF3] px-4 py-3" data-testid="import-result">
            <p className="flex items-center gap-2 text-[13px] font-semibold text-[#126E2C]"><CheckCircle2 size={15} /> Impor selesai — +{result.totals.inserted} baru, {result.totals.updated} diperbarui, {result.totals.skipped} dilewati, {result.totals.errors} error{result.snapshot_id ? " · snapshot tersimpan di daftar arsip" : ""}</p>
            <div className="mt-1.5 grid gap-1 text-[12px] text-[#3C3C43] sm:grid-cols-3">
              {Object.entries(result.summary).map(([k, s]) => <span key={k}>{s.title}: +{s.inserted} / ↻{s.updated} / ⤼{s.skipped}{s.errors ? ` / ✕${s.errors}` : ""}</span>)}
            </div>
          </div>
        ) : null}

        {history.length ? (
          <details className="text-[12px]" data-testid="import-history">
            <summary className="cursor-pointer font-semibold text-[#6B6B73]">Riwayat impor ({history.length})</summary>
            <ul className="mt-1.5 space-y-1 text-[#6B6B73]">
              {history.map((h) => <li key={h.id}>{formatDateTime(h.finished_at)} · {h.actor_name} · {h.mode === "upsert" ? "tambah+perbarui" : "hanya tambah"} · {Object.values(h.summary || {}).map((s) => `${s.title} +${s.inserted}/↻${s.updated}`).join(", ")}</li>)}
            </ul>
          </details>
        ) : null}
        {!preview && !result ? <p className="flex items-center gap-1.5 text-[11.5px] text-[#8E8E93]"><AlertTriangle size={12} /> Mulai dengan mengunduh template, isi sheet yang dibutuhkan, lalu unggah untuk pratinjau — belum ada data yang ditulis sampai Anda menekan "Impor Semua Sekaligus".</p> : null}
      </div>
    </section>
  );
}
