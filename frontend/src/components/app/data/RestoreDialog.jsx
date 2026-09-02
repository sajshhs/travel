import { useEffect, useState } from "react";
import { toast } from "sonner";
import { AlertTriangle, Loader2, RotateCcw } from "lucide-react";
import apiClient from "@/services/apiClient";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { formatDateTime } from "@/utils/formatters";

export default function RestoreDialog({ backup, onOpenChange, onDone }) {
  const open = Boolean(backup);
  const [manifest, setManifest] = useState(null);
  const [mode, setMode] = useState("full");
  const [selected, setSelected] = useState([]);
  const [includeMedia, setIncludeMedia] = useState(true);
  const [confirm, setConfirm] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!open) return;
    setManifest(null); setMode("full"); setSelected([]); setConfirm(""); setIncludeMedia(Boolean(backup.include_media));
    apiClient.get(`/data/backups/${backup.id}/manifest`).then((r) => setManifest(r.data.manifest)).catch((e) => toast.error(e?.response?.data?.detail || "Gagal membaca isi arsip"));
  }, [open, backup]);

  const cols = manifest?.collections || [];
  const toggle = (n) => setSelected((s) => s.includes(n) ? s.filter((x) => x !== n) : [...s, n]);
  const canSubmit = confirm.trim().toUpperCase() === "RESTORE" && (mode === "full" || selected.length > 0) && !busy;

  const submit = async () => {
    setBusy(true);
    try {
      const r = await apiClient.post("/data/restore", { backup_id: backup.id, collections: mode === "full" ? null : selected, include_media: includeMedia, confirm });
      toast.success(`Restore selesai · ${r.data.documents} dokumen, ${r.data.media_files} media dipulihkan · snapshot sebelum restore tersimpan`);
      onOpenChange(false); onDone && onDone();
    } catch (e) { toast.error(e?.response?.data?.detail || "Restore gagal"); } finally { setBusy(false); }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-2xl" data-testid="restore-dialog">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2"><RotateCcw size={17} className="text-[#007AFF]" /> Restore dari backup</DialogTitle>
          <DialogDescription>{backup?.filename} · dibuat {backup ? formatDateTime(backup.source_created_at || backup.created_at) : ""} · {backup?.size_label}</DialogDescription>
        </DialogHeader>
        <div className="space-y-3">
          <div className="flex items-start gap-2 rounded-[10px] border border-[#F5C6A5] bg-[#FFF7F0] px-3 py-2 text-[12px] text-[#8A4B08]" data-testid="restore-warning">
            <AlertTriangle size={15} className="mt-0.5 flex-shrink-0" />
            <span>Data pada koleksi yang dipilih akan <b>DIGANTI</b> seluruhnya dengan isi arsip. Sistem otomatis membuat snapshot data saat ini sebelum restore sehingga bisa dipulihkan kembali dari daftar arsip.</span>
          </div>
          <div className="grid gap-2 sm:grid-cols-2">
            {[["full", "Restore penuh", "Semua koleksi dalam arsip"], ["partial", "Pilih koleksi", "Hanya tabel tertentu, mis. pelanggan & booking"]].map(([v, l, d]) => (
              <button type="button" key={v} onClick={() => setMode(v)} data-testid={`restore-mode-${v}`}
                className={`rounded-[10px] border px-3 py-2 text-left ${mode === v ? "border-[#007AFF] bg-[#EAF2FF]" : "border-[#E2E3E7] bg-white hover:border-[#B9D5FF]"}`}>
                <span className="block text-[12.5px] font-semibold text-[#1C1C1E]">{l}</span><span className="block text-[11px] text-[#6B6B73]">{d}</span>
              </button>
            ))}
          </div>
          {!manifest ? <p className="text-[12px] text-[#8E8E93]">Membaca isi arsip…</p> : (
            <div className="rounded-[10px] border border-[#E2E3E7] p-2.5">
              <div className="mb-1.5 flex items-center justify-between text-[11.5px] text-[#6B6B73]">
                <span>{cols.length} koleksi · {cols.reduce((s, c) => s + Number(c.count || 0), 0).toLocaleString("id-ID")} dokumen · {manifest.media_files} media</span>
                {mode === "partial" ? <span className="flex gap-2"><button type="button" className="font-semibold text-[#007AFF]" onClick={() => setSelected(cols.map((c) => c.name))} data-testid="restore-select-all">Pilih semua</button><button type="button" className="font-semibold text-[#6B6B73]" onClick={() => setSelected([])} data-testid="restore-select-none">Kosongkan</button></span> : null}
              </div>
              <div className="grid max-h-[220px] gap-1 overflow-y-auto sm:grid-cols-3" data-testid="restore-collections">
                {cols.map((c) => (
                  <label key={c.name} className={`flex items-center justify-between gap-2 rounded-[8px] px-2 py-1 text-[12px] ${mode === "full" ? "bg-[#F7F8FA] text-[#6B6B73]" : "cursor-pointer hover:bg-[#F7F8FA]"}`}>
                    <span className="flex items-center gap-2 truncate">
                      <input type="checkbox" className="accent-[#007AFF]" disabled={mode === "full"} checked={mode === "full" || selected.includes(c.name)} onChange={() => toggle(c.name)} data-testid={`restore-col-${c.name}`} />
                      <span className="truncate font-mono">{c.name}</span>
                    </span>
                    <span className="tabular-nums text-[#8E8E93]">{c.count}</span>
                  </label>
                ))}
              </div>
            </div>
          )}
          <div className="flex items-center justify-between gap-3 rounded-[10px] border border-[#E2E3E7] px-3 py-2">
            <div><p className="text-[12.5px] font-semibold text-[#1C1C1E]">Pulihkan berkas media juga</p><p className="text-[11px] text-[#6B6B73]">Logo, foto armada, bukti bayar, CMS ({manifest?.media_files ?? backup?.media_files ?? 0} berkas dalam arsip).</p></div>
            <Switch checked={includeMedia} onCheckedChange={setIncludeMedia} disabled={!backup?.include_media} data-testid="restore-media" />
          </div>
          <label className="block space-y-1.5 text-[12px] text-[#6B6B73]">Ketik <b>RESTORE</b> untuk mengonfirmasi
            <Input value={confirm} onChange={(e) => setConfirm(e.target.value)} placeholder="RESTORE" className="font-mono uppercase" data-testid="restore-confirm" />
          </label>
        </div>
        <DialogFooter className="mt-2">
          <button className="secondary-button" onClick={() => onOpenChange(false)} data-testid="restore-cancel">Batal</button>
          <button className="primary-button !bg-[#A8221A] hover:!bg-[#8E1B14]" disabled={!canSubmit} onClick={submit} data-testid="restore-submit">{busy ? <Loader2 size={14} className="animate-spin" /> : <RotateCcw size={14} />} Jalankan Restore</button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
