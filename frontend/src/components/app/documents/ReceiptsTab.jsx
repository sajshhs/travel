import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { Download, Eye, Loader2, Receipt, Send } from "lucide-react";
import apiClient from "@/services/apiClient";
import { LoadingState, EmptyState, ErrorState } from "@/components/shared/DataStates";
import { formatCurrency, formatDateTime } from "@/utils/formatters";
import { downloadPdf, openPdf, safeName } from "./docUtils";

const METHOD = { transfer: "Transfer", cash: "Tunai", qris: "QRIS" };

export function ReceiptRow({ rcp, onChanged, compact = false }) {
  const [busy, setBusy] = useState(false);
  const sendWa = async () => {
    setBusy(true);
    try {
      const r = await apiClient.post(`/documents/receipts/${rcp.id}/send-wa`);
      toast.success(`Kwitansi ${r.data?.number || ""} terkirim via WhatsApp`);
      onChanged && onChanged();
    } catch (e) { toast.error(e?.response?.data?.detail || "Gagal mengirim kwitansi via WhatsApp"); } finally { setBusy(false); }
  };
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-3" data-testid={`receipt-${rcp.id}`}>
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-mono text-[12.5px] font-semibold text-[#1C1C1E]" data-testid={`receipt-number-${rcp.id}`}>{rcp.number}</span>
          <span className="rounded-full bg-[#E8F7EC] px-2 py-0.5 text-[10.5px] font-semibold text-[#126E2C]">{rcp.payment_type === "dp" ? "DP" : "Pelunasan"}</span>
          <span className="rounded-full bg-[#F1F1F4] px-2 py-0.5 text-[10.5px] text-[#6B6B73]">{METHOD[rcp.method] || rcp.method}</span>
          {rcp.sent_count ? <span className="text-[10.5px] text-[#127A36]">WA terkirim {rcp.sent_count}×</span> : null}
        </div>
        <p className="mt-0.5 truncate text-[12px] text-[#6B6B73]">{compact ? "" : `${rcp.customer_name} · ${rcp.booking_code} · `}{formatDateTime(rcp.paid_at)} · sisa {formatCurrency(rcp.remaining_after)}</p>
      </div>
      <span className="text-[13.5px] font-bold tabular-nums text-[#126E2C]" data-testid={`receipt-amount-${rcp.id}`}>{formatCurrency(rcp.amount)}</span>
      <div className="flex items-center gap-1.5">
        <button className="icon-button !h-8 !w-8" title="Lihat PDF" onClick={() => openPdf(`/documents/receipts/${rcp.id}/pdf?inline=true`)} data-testid={`receipt-view-${rcp.id}`}><Eye size={14} /></button>
        <button className="icon-button !h-8 !w-8" title="Unduh PDF" onClick={() => downloadPdf(`/documents/receipts/${rcp.id}/pdf`, safeName(rcp.number, "kwitansi"))} data-testid={`receipt-pdf-${rcp.id}`}><Download size={14} /></button>
        <button className="secondary-button !px-2 !py-1 !text-[12px] !text-[#127A36]" disabled={busy} onClick={sendWa} data-testid={`receipt-wa-${rcp.id}`}>
          {busy ? <Loader2 size={13} className="animate-spin" /> : <Send size={13} />} Kirim WA
        </button>
      </div>
    </div>
  );
}

export default function ReceiptsTab() {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const load = useCallback(() => {
    setLoading(true);
    apiClient.get("/documents/receipts").then((r) => { setRows(Array.isArray(r.data) ? r.data : []); setError(null); })
      .catch(() => setError("Gagal memuat kwitansi")).finally(() => setLoading(false));
  }, []);
  useEffect(() => { load(); }, [load]);
  return (
    <div className="space-y-3" data-testid="receipts-panel">
      {loading ? <LoadingState testId="receipts-loading" /> : error ? <ErrorState message={error} onRetry={load} />
        : rows.length === 0 ? <EmptyState title="Belum ada kwitansi" description="Kwitansi terbit otomatis saat pembayaran dicatat (bisa diatur di Pengaturan Dokumen)." testId="receipts-empty" /> : (
          <section className="section-card">
            <div className="section-head"><div className="flex items-center gap-2"><Receipt size={16} className="text-[#007AFF]" /><h2>Daftar Kwitansi</h2></div><span className="text-[12px] text-[#8E8E93]">{rows.length} kwitansi</span></div>
            <div className="divide-y divide-[#F2F2F5]" data-testid="receipts-list">{rows.map((r) => <ReceiptRow key={r.id} rcp={r} onChanged={load} />)}</div>
          </section>
        )}
    </div>
  );
}
