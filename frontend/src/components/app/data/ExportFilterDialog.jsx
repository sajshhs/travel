import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Download, FileSpreadsheet, Loader2 } from "lucide-react";
import apiClient from "@/services/apiClient";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

const OPTION_LABEL = {
  hold: "Hold", confirmed: "Dikonfirmasi", ongoing: "Berjalan", completed: "Selesai", cancelled: "Dibatalkan",
  dp: "DP", settlement: "Pelunasan", refund: "Refund", full: "Penuh", transfer: "Transfer", cash: "Tunai", qris: "QRIS",
  draft: "Draft", sent: "Terkirim", partial: "Sebagian", paid: "Lunas", void: "Batal",
};

export default function ExportFilterDialog({ table, onOpenChange }) {
  const open = Boolean(table);
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [picked, setPicked] = useState({});
  const [busy, setBusy] = useState(false);
  useEffect(() => { if (open) { setFrom(""); setTo(""); setPicked({}); } }, [open, table]);

  const toggle = (fk, v) => setPicked((p) => { const cur = p[fk] || []; return { ...p, [fk]: cur.includes(v) ? cur.filter((x) => x !== v) : [...cur, v] }; });
  const params = new URLSearchParams();
  if (from) params.append("date_from", from);
  if (to) params.append("date_to", to);
  Object.entries(picked).forEach(([fk, vals]) => vals.forEach((v) => params.append(fk, v)));
  const activeCount = (from ? 1 : 0) + (to ? 1 : 0) + Object.values(picked).reduce((s, v) => s + v.length, 0);

  const run = async () => {
    if (from && to && from > to) { toast.error("Tanggal awal harus sebelum tanggal akhir"); return; }
    setBusy(true);
    try {
      const res = await apiClient.get(`/data/exports/${table.key}.xlsx?${params.toString()}`, { responseType: "blob" });
      const url = window.URL.createObjectURL(new Blob([res.data], { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" }));
      const a = document.createElement("a"); a.href = url;
      a.download = `${table.key}${from ? `_${from}` : ""}${to ? `_${to}` : ""}.xlsx`; document.body.appendChild(a); a.click(); a.remove(); window.URL.revokeObjectURL(url);
      toast.success(`Excel ${table.label} (${res.headers["x-row-count"] ?? "?"} baris) diunduh`);
      onOpenChange(false);
    } catch (e) { toast.error(e?.response?.data?.detail || `Gagal mengekspor ${table.label}`); } finally { setBusy(false); }
  };

  if (!table) return null;
  const f = table.filters || {};
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg" data-testid="export-filter-dialog">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2"><FileSpreadsheet size={17} className="text-[#007AFF]" /> Ekspor {table.label} ke Excel</DialogTitle>
          <DialogDescription>Kosongkan filter untuk mengunduh semua ({Number(table.count).toLocaleString("id-ID")} baris).</DialogDescription>
        </DialogHeader>
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5"><Label className="text-[12px]">{f.date_label || "Tanggal"} — dari</Label><Input type="date" value={from} onChange={(e) => setFrom(e.target.value)} data-testid="export-date-from" /></div>
            <div className="space-y-1.5"><Label className="text-[12px]">sampai</Label><Input type="date" value={to} onChange={(e) => setTo(e.target.value)} data-testid="export-date-to" /></div>
          </div>
          {(f.status || []).map((grp) => (
            <div key={grp.key} className="space-y-1.5">
              <Label className="text-[12px]">{grp.label} <span className="font-normal text-[#8E8E93]">(kosong = semua)</span></Label>
              <div className="flex flex-wrap gap-1.5" data-testid={`export-filter-${grp.key}`}>
                {grp.options.map((v) => {
                  const on = (picked[grp.key] || []).includes(v);
                  return (
                    <button type="button" key={v} onClick={() => toggle(grp.key, v)} data-testid={`export-opt-${grp.key}-${v}`}
                      className={`rounded-full border px-3 py-1 text-[12px] font-semibold transition-colors ${on ? "border-[#007AFF] bg-[#EAF2FF] text-[#0058CC]" : "border-[#E2E3E7] bg-white text-[#6B6B73] hover:border-[#B9D5FF]"}`}>
                      {OPTION_LABEL[v] || v}
                    </button>
                  );
                })}
              </div>
            </div>
          ))}
          <p className="text-[11.5px] text-[#8E8E93]" data-testid="export-filter-summary">{activeCount ? `${activeCount} filter aktif` : "Tanpa filter — semua data"}</p>
        </div>
        <DialogFooter className="mt-2">
          <button className="secondary-button" onClick={() => onOpenChange(false)} data-testid="export-cancel">Batal</button>
          <button className="primary-button" disabled={busy} onClick={run} data-testid="export-run">{busy ? <Loader2 size={14} className="animate-spin" /> : <Download size={14} />} Unduh Excel</button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
