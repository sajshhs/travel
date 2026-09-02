import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { Download, Eye, Loader2, RotateCcw, Send } from "lucide-react";
import apiClient from "@/services/apiClient";
import { LoadingState, EmptyState, ErrorState } from "@/components/shared/DataStates";
import { formatCurrency, formatDate } from "@/utils/formatters";
import { downloadPdf, openPdf, safeName } from "./docUtils";

export function RefundNoteRow({ note, onChanged, compact = false }) {
  const [busy, setBusy] = useState(false);
  const sendWa = async () => {
    setBusy(true);
    try {
      const r = await apiClient.post(`/documents/refund-notes/${note.id}/send-wa`);
      toast.success(`Nota refund ${r.data?.number || ""} terkirim via WhatsApp`);
      onChanged && onChanged();
    } catch (e) { toast.error(e?.response?.data?.detail || "Gagal mengirim nota refund via WhatsApp"); } finally { setBusy(false); }
  };
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-3" data-testid={`refund-note-${note.id}`}>
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-mono text-[12.5px] font-semibold text-[#1C1C1E]" data-testid={`refund-note-number-${note.id}`}>{note.number}</span>
          <span className="rounded-full bg-[#FDECEA] px-2 py-0.5 text-[10.5px] font-semibold text-[#A8221A]">Refund</span>
          {Number(note.cancellation_fee) > 0 ? <span className="rounded-full bg-[#F1F1F4] px-2 py-0.5 text-[10.5px] text-[#6B6B73]">denda {formatCurrency(note.cancellation_fee)}</span> : null}
          {note.sent_count ? <span className="text-[10.5px] text-[#127A36]">WA terkirim {note.sent_count}×</span> : null}
        </div>
        <p className="mt-0.5 truncate text-[12px] text-[#6B6B73]">{compact ? "" : `${note.customer_name} · ${note.booking_code} · `}dibatalkan {formatDate(note.cancelled_at)}{note.reason ? ` · ${note.reason}` : ""}</p>
      </div>
      <span className="text-[13.5px] font-bold tabular-nums text-[#A8221A]" data-testid={`refund-note-amount-${note.id}`}>{formatCurrency(note.refund_amount)}</span>
      <div className="flex items-center gap-1.5">
        <button className="icon-button !h-8 !w-8" title="Lihat PDF" onClick={() => openPdf(`/documents/refund-notes/${note.id}/pdf?inline=true`)} data-testid={`refund-note-view-${note.id}`}><Eye size={14} /></button>
        <button className="icon-button !h-8 !w-8" title="Unduh PDF" onClick={() => downloadPdf(`/documents/refund-notes/${note.id}/pdf`, safeName(note.number, "nota-refund"))} data-testid={`refund-note-pdf-${note.id}`}><Download size={14} /></button>
        <button className="secondary-button !px-2 !py-1 !text-[12px] !text-[#127A36]" disabled={busy} onClick={sendWa} data-testid={`refund-note-wa-${note.id}`}>
          {busy ? <Loader2 size={13} className="animate-spin" /> : <Send size={13} />} Kirim WA
        </button>
      </div>
    </div>
  );
}

export default function RefundNotesTab() {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const load = useCallback(() => {
    setLoading(true);
    apiClient.get("/documents/refund-notes").then((r) => { setRows(Array.isArray(r.data) ? r.data : []); setError(null); })
      .catch(() => setError("Gagal memuat nota refund")).finally(() => setLoading(false));
  }, []);
  useEffect(() => { load(); }, [load]);
  return (
    <div className="space-y-3" data-testid="refund-notes-panel">
      {loading ? <LoadingState testId="refund-notes-loading" /> : error ? <ErrorState message={error} onRetry={load} />
        : rows.length === 0 ? <EmptyState title="Belum ada nota refund" description="Nota refund terbit otomatis saat booking dibatalkan dengan pengembalian dana." testId="refund-notes-empty" /> : (
          <section className="section-card">
            <div className="section-head"><div className="flex items-center gap-2"><RotateCcw size={16} className="text-[#007AFF]" /><h2>Daftar Nota Refund</h2></div><span className="text-[12px] text-[#8E8E93]">{rows.length} nota</span></div>
            <div className="divide-y divide-[#F2F2F5]" data-testid="refund-notes-list">{rows.map((n) => <RefundNoteRow key={n.id} note={n} onChanged={load} />)}</div>
          </section>
        )}
    </div>
  );
}
