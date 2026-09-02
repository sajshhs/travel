import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { Archive, Clock, Database, Download, FileSpreadsheet, HardDrive, History, Loader2, RotateCcw, Trash2, Upload } from "lucide-react";
import apiClient from "@/services/apiClient";
import { useAuth } from "@/context/AuthContext";
import { LoadingState, ErrorState } from "@/components/shared/DataStates";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { formatDateTime } from "@/utils/formatters";
import RestoreDialog from "@/components/app/data/RestoreDialog";
import ExportFilterDialog from "@/components/app/data/ExportFilterDialog";
import MasterImportPanel from "@/components/app/data/MasterImportPanel";

const KIND_TONE = { manual: "bg-[#EAF2FF] text-[#0058CC]", auto: "bg-[#E8F7EC] text-[#126E2C]", pre_restore: "bg-[#FFF4E5] text-[#B45309]", uploaded: "bg-[#F1F1F4] text-[#3C3C43]" };

function Stat({ icon: Icon, label, value, sub, testId }) {
  return (
    <div className="rounded-[14px] border border-[#E2E3E7] bg-white px-4 py-3" data-testid={testId}>
      <div className="flex items-center gap-2 text-[11.5px] font-semibold uppercase tracking-wide text-[#8E8E93]"><Icon size={13} /> {label}</div>
      <p className="mt-1 text-[20px] font-bold tabular-nums text-[#1C1C1E]">{value}</p>
      {sub ? <p className="text-[11.5px] text-[#6B6B73]">{sub}</p> : null}
    </div>
  );
}

export default function DataManagement() {
  const { user } = useAuth();
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState("");
  const [note, setNote] = useState("");
  const [restoreTarget, setRestoreTarget] = useState(null);
  const [sched, setSched] = useState(null);
  const [exports, setExports] = useState([]);
  const [exporting, setExporting] = useState("");
  const [exportFilter, setExportFilter] = useState(null);

  const load = useCallback(() => {
    apiClient.get("/data/overview").then((r) => { setData(r.data); setSched(r.data.schedule); setError(null); }).catch(() => setError("Gagal memuat data backup"));
    apiClient.get("/data/exports").then((r) => setExports(Array.isArray(r.data) ? r.data : [])).catch(() => {});
  }, []);
  useEffect(() => { load(); }, [load]);

  const exportTable = async (t) => {
    setExporting(t.key);
    try {
      const res = await apiClient.get(`/data/exports/${t.key}.xlsx`, { responseType: "blob" });
      const url = window.URL.createObjectURL(new Blob([res.data], { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" }));
      const a = document.createElement("a"); a.href = url; a.download = `${t.key}_${new Date().toISOString().slice(0, 10)}.xlsx`; document.body.appendChild(a); a.click(); a.remove(); window.URL.revokeObjectURL(url);
      toast.success(`Excel ${t.label} (${res.headers["x-row-count"] ?? t.count} baris) diunduh`);
    } catch (e) { toast.error(e?.response?.data?.detail || `Gagal mengekspor ${t.label}`); } finally { setExporting(""); }
  };

  const backupNow = async () => {
    setBusy("backup");
    try { const r = await apiClient.post("/data/backups", { note, include_media: true }); toast.success(`Backup selesai · ${r.data.filename} (${r.data.size_label})`); setNote(""); load(); }
    catch (e) { toast.error(e?.response?.data?.detail || "Backup gagal"); } finally { setBusy(""); }
  };
  const upload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setBusy("upload");
    try {
      const fd = new FormData(); fd.append("file", file);
      const r = await apiClient.post("/data/backups/upload", fd, { headers: { "Content-Type": "multipart/form-data" } });
      toast.success(`Arsip ${file.name} terdaftar (${r.data.collections} koleksi, ${r.data.documents} dokumen)`); load();
    } catch (err) { toast.error(err?.response?.data?.detail || "Gagal mengunggah arsip"); } finally { setBusy(""); e.target.value = ""; }
  };
  const download = async (b) => {
    try {
      const res = await apiClient.get(`/data/backups/${b.id}/download`, { responseType: "blob" });
      const url = window.URL.createObjectURL(new Blob([res.data], { type: "application/zip" }));
      const a = document.createElement("a"); a.href = url; a.download = b.filename; document.body.appendChild(a); a.click(); a.remove(); window.URL.revokeObjectURL(url);
    } catch (e) { toast.error("Gagal mengunduh arsip"); }
  };
  const remove = async (b) => {
    if (!window.confirm(`Hapus arsip ${b.filename}? Tindakan ini tidak bisa dibatalkan.`)) return;
    try { await apiClient.delete(`/data/backups/${b.id}`); toast.success("Arsip dihapus"); load(); } catch (e) { toast.error(e?.response?.data?.detail || "Gagal menghapus"); }
  };
  const saveSchedule = async (patch) => {
    const next = { ...sched, ...patch };
    setSched(next);
    try { const r = await apiClient.patch("/data/schedule", patch); setSched(r.data); toast.success("Jadwal backup disimpan"); } catch (e) { toast.error(e?.response?.data?.detail || "Gagal menyimpan jadwal"); }
  };

  if (error) return <ErrorState message={error} onRetry={load} />;
  if (!data) return <LoadingState testId="data-loading" />;
  const backups = data.backups || [];
  const last = backups.find((b) => b.kind !== "pre_restore") || backups[0];
  const totalDocs = (data.collections || []).reduce((s, c) => s + Number(c.count || 0), 0);

  return (
    <div className="space-y-4" data-testid="data-management-page">
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Stat icon={Archive} label="Arsip backup" value={backups.length} sub={`${data.storage.total_label} di server · sisa disk ${data.storage.disk_free_label}`} testId="data-stat-backups" />
        <Stat icon={Clock} label="Backup terakhir" value={last ? formatDateTime(last.created_at) : "—"} sub={last ? `${last.kind_label} · ${last.size_label}` : "Belum pernah backup"} testId="data-stat-last" />
        <Stat icon={Database} label="Data aktif" value={totalDocs.toLocaleString("id-ID")} sub={`${(data.collections || []).length} koleksi/tabel`} testId="data-stat-live" />
        <Stat icon={HardDrive} label="Jadwal harian" value={sched?.enabled ? "Aktif" : "Nonaktif"} sub={sched?.last_run_at ? `Terakhir ${formatDateTime(sched.last_run_at)} · ${String(sched.last_status || "").slice(0, 60)}` : `${sched?.hour_label} · simpan ${sched?.keep_last} terakhir`} testId="data-stat-schedule" />
      </div>

      <section className="section-card">
        <div className="section-head"><div className="flex items-center gap-2"><Archive size={16} className="text-[#007AFF]" /><h2>Backup & Restore</h2></div>
          <div className="flex flex-wrap items-center gap-2">
            <Input value={note} onChange={(e) => setNote(e.target.value)} placeholder="Catatan backup (opsional)" className="h-9 w-[220px]" data-testid="backup-note" />
            <label className="secondary-button cursor-pointer !h-9" data-testid="backup-upload">
              {busy === "upload" ? <Loader2 size={14} className="animate-spin" /> : <Upload size={14} />} Unggah arsip
              <input type="file" accept=".zip,application/zip" className="hidden" onChange={upload} disabled={busy === "upload"} />
            </label>
            <button className="primary-button !h-9" disabled={busy === "backup"} onClick={backupNow} data-testid="backup-now">{busy === "backup" ? <Loader2 size={14} className="animate-spin" /> : <Database size={14} />} Backup Sekarang</button>
          </div>
        </div>
        <div className="section-body">
          <p className="mb-3 text-[12.5px] text-[#6B6B73]">Backup lengkap = seluruh koleksi database + berkas media (logo, foto armada, bukti bayar, CMS) dalam satu ZIP. Restore selalu membuat <b>snapshot otomatis</b> lebih dulu sehingga bisa dikembalikan bila keliru.</p>
          {backups.length === 0 ? <p className="py-6 text-center text-[12.5px] text-[#8E8E93]" data-testid="backups-empty">Belum ada arsip backup. Klik <b>Backup Sekarang</b>.</p> : (
            <div className="overflow-x-auto">
              <table className="w-full text-[12.5px]" data-testid="backups-table">
                <thead><tr className="text-left text-[11px] uppercase tracking-wide text-[#8E8E93]"><th className="pb-2">Waktu</th><th className="pb-2">Jenis</th><th className="pb-2">Isi</th><th className="pb-2 text-right">Ukuran</th><th className="pb-2">Oleh</th><th className="pb-2 text-right">Aksi</th></tr></thead>
                <tbody className="divide-y divide-[#F2F2F5]">
                  {backups.map((b) => (
                    <tr key={b.id} data-testid={`backup-${b.id}`} className={b.available ? "" : "opacity-50"}>
                      <td className="py-2.5 tabular-nums text-[#1C1C1E]">{formatDateTime(b.created_at)}{b.note ? <span className="block max-w-[320px] truncate text-[11px] text-[#8E8E93]" title={b.note}>{b.note}</span> : null}</td>
                      <td className="py-2.5"><span className={`rounded-full px-2 py-0.5 text-[10.5px] font-semibold ${KIND_TONE[b.kind] || KIND_TONE.uploaded}`}>{b.kind_label}</span></td>
                      <td className="py-2.5 text-[#6B6B73]">{b.collections} koleksi · {Number(b.documents).toLocaleString("id-ID")} dokumen · {b.media_files} media</td>
                      <td className="py-2.5 text-right tabular-nums">{b.size_label}</td>
                      <td className="py-2.5 text-[#6B6B73]">{b.created_by_name || "Sistem"}</td>
                      <td className="py-2.5">
                        <div className="flex justify-end gap-1.5">
                          <button className="icon-button !h-8 !w-8" title="Unduh ZIP" disabled={!b.available} onClick={() => download(b)} data-testid={`backup-download-${b.id}`}><Download size={14} /></button>
                          <button className="secondary-button !px-2 !py-1 !text-[12px]" disabled={!b.available} onClick={() => setRestoreTarget(b)} data-testid={`backup-restore-${b.id}`}><RotateCcw size={13} /> Restore</button>
                          <button className="icon-button !h-8 !w-8 !text-[#A8221A]" title="Hapus arsip" onClick={() => remove(b)} data-testid={`backup-delete-${b.id}`}><Trash2 size={14} /></button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </section>

      <section className="section-card">
        <div className="section-head"><div className="flex items-center gap-2"><FileSpreadsheet size={16} className="text-[#007AFF]" /><h2>Ekspor Excel per tabel</h2></div><span className="text-[12px] text-[#8E8E93]">Kolom ramah baca · siap filter di Excel</span></div>
        <div className="section-body grid gap-2 sm:grid-cols-2 lg:grid-cols-4" data-testid="exports-grid">
          {exports.map((t) => (
            <button key={t.key} type="button" disabled={exporting === t.key} onClick={() => (t.filters ? setExportFilter(t) : exportTable(t))} data-testid={`export-${t.key}`}
              className="flex items-center justify-between gap-3 rounded-[12px] border border-[#E2E3E7] bg-white px-4 py-3 text-left transition-colors hover:border-[#B9D5FF] hover:bg-[#F7FAFF] disabled:opacity-60">
              <span>
                <span className="block text-[13px] font-semibold text-[#1C1C1E]">{t.label}</span>
                <span className="block text-[11.5px] text-[#6B6B73]">{Number(t.count).toLocaleString("id-ID")} baris · .xlsx{t.filters ? " · filter tanggal & status" : ""}</span>
              </span>
              {exporting === t.key ? <Loader2 size={16} className="animate-spin text-[#007AFF]" /> : <Download size={16} className="text-[#007AFF]" />}
            </button>
          ))}
        </div>
      </section>

      <MasterImportPanel onDone={load} />

      <div className="grid gap-4 lg:grid-cols-2">
        <section className="section-card">
          <div className="section-head"><div className="flex items-center gap-2"><Clock size={16} className="text-[#007AFF]" /><h2>Jadwal backup otomatis</h2></div></div>
          <div className="section-body space-y-3">
            <div className="flex items-center justify-between gap-3 rounded-[10px] border border-[#E2E3E7] px-3 py-2">
              <div><p className="text-[12.5px] font-semibold text-[#1C1C1E]">Backup harian pukul 02:00 WIB</p><p className="text-[11px] text-[#6B6B73]">Dijalankan oleh penjadwal platform; arsip lama di luar retensi dihapus otomatis.</p></div>
              <Switch checked={Boolean(sched?.enabled)} onCheckedChange={(v) => saveSchedule({ enabled: v })} data-testid="schedule-enabled" />
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <label className="space-y-1.5 text-[12px] text-[#6B6B73]">Simpan N backup otomatis terakhir
                <Input type="number" min={1} max={60} value={sched?.keep_last ?? 7} onChange={(e) => setSched((s) => ({ ...s, keep_last: Number(e.target.value) }))} onBlur={() => saveSchedule({ keep_last: Number(sched.keep_last) || 7 })} data-testid="schedule-keep" />
              </label>
              <div className="flex items-center justify-between gap-3 rounded-[10px] border border-[#E2E3E7] px-3 py-2 self-end">
                <span className="text-[12.5px] font-semibold text-[#1C1C1E]">Sertakan berkas media</span>
                <Switch checked={sched?.include_media !== false} onCheckedChange={(v) => saveSchedule({ include_media: v })} data-testid="schedule-media" />
              </div>
            </div>
            {sched?.last_run_at ? <p className="text-[11.5px] text-[#6B6B73]" data-testid="schedule-last">Terakhir dijalankan {formatDateTime(sched.last_run_at)} — {sched.last_status}</p> : <p className="text-[11.5px] text-[#8E8E93]">Belum pernah dijalankan.</p>}
          </div>
        </section>
        <section className="section-card">
          <div className="section-head"><div className="flex items-center gap-2"><History size={16} className="text-[#007AFF]" /><h2>Riwayat restore</h2></div></div>
          <div className="section-body">
            {(data.restores || []).length === 0 ? <p className="py-4 text-center text-[12.5px] text-[#8E8E93]" data-testid="restores-empty">Belum ada restore.</p> : (
              <div className="divide-y divide-[#F2F2F5]" data-testid="restores-list">
                {data.restores.map((r) => (
                  <div key={r.id} className="py-2.5 text-[12.5px]" data-testid={`restore-${r.id}`}>
                    <p className="font-semibold text-[#1C1C1E]">{r.mode === "full" ? "Restore penuh" : `Restore sebagian (${r.collections.length} koleksi)`} · {formatDateTime(r.finished_at)}</p>
                    <p className="text-[11.5px] text-[#6B6B73]">dari {r.backup_filename} · {Number(r.documents).toLocaleString("id-ID")} dokumen · {r.media_files} media · oleh {r.actor_name}{r.snapshot_id ? " · snapshot tersimpan" : ""}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </section>
      </div>

      <section className="section-card">
        <div className="section-head"><div className="flex items-center gap-2"><Database size={16} className="text-[#007AFF]" /><h2>Koleksi data aktif</h2></div><span className="text-[12px] text-[#8E8E93]">{totalDocs.toLocaleString("id-ID")} dokumen</span></div>
        <div className="section-body grid gap-1.5 sm:grid-cols-3 lg:grid-cols-5" data-testid="collections-grid">
          {(data.collections || []).map((c) => (
            <div key={c.name} className="flex items-center justify-between rounded-[8px] bg-[#F7F8FA] px-2.5 py-1.5 text-[12px]"><span className="truncate font-mono text-[#3C3C43]">{c.name}</span><span className="tabular-nums text-[#6B6B73]">{c.count}</span></div>
          ))}
        </div>
      </section>

      <RestoreDialog backup={restoreTarget} onOpenChange={(v) => !v && setRestoreTarget(null)} onDone={load} actorRole={user?.role} />
      <ExportFilterDialog table={exportFilter} onOpenChange={(v) => !v && setExportFilter(null)} />
    </div>
  );
}
