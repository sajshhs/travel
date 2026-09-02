import { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { FileText, Receipt, Palette, ScrollText, Hash, Landmark, RotateCcw } from "lucide-react";
import apiClient from "@/services/apiClient";
import { useAuth } from "@/context/AuthContext";
import InvoicesTab from "@/components/app/documents/InvoicesTab";
import ReceiptsTab from "@/components/app/documents/ReceiptsTab";
import RefundNotesTab from "@/components/app/documents/RefundNotesTab";
import { DocCodeSelect, LayoutEditor, ScriptEditor } from "@/components/app/documents/DocLayoutEditor";
import { ConfigPanel, NumberingPanel } from "@/components/app/documents/DocConfigPanels";

const TABS = [
  ["invoices", "Invoice", FileText],
  ["receipts", "Kwitansi", Receipt],
  ["refunds", "Nota Refund", RotateCcw],
  ["layout", "Kop & Tampilan", Palette],
  ["script", "Naskah", ScrollText],
  ["config", "Rekening, Pajak & WA", Landmark],
  ["numbering", "Penomoran", Hash],
];

export default function Documents() {
  const { user } = useAuth();
  const [params, setParams] = useSearchParams();
  const tab = params.get("tab") || "invoices";
  const setTab = (t) => setParams({ tab: t });
  const canEdit = user?.role === "owner";
  const [targets, setTargets] = useState([]);
  const [code, setCode] = useState("__default__");
  const [scriptCode, setScriptCode] = useState("INVOICE_DP");

  const loadTargets = useCallback(() => { apiClient.get("/documents/layouts").then((r) => setTargets(r.data?.data || [])).catch(() => {}); }, []);
  useEffect(() => { loadTargets(); }, [loadTargets]);

  return (
    <div className="space-y-4" data-testid="documents-page">
      <div className="tab-bar">
        {TABS.map(([k, l, Icon]) => (
          <button key={k} className={`tab-button ${tab === k ? "active" : ""}`} onClick={() => setTab(k)} data-testid={`tab-documents-${k}`}><Icon size={14} /> {l}</button>
        ))}
      </div>
      {!canEdit && ["layout", "script", "config", "numbering"].includes(tab) ? (
        <p className="rounded-[10px] bg-[#FFF8E6] px-3 py-2 text-[12px] text-[#8A5A00]" data-testid="documents-readonly-note">Mode baca — hanya Pemilik (owner) yang dapat mengubah konfigurasi dokumen.</p>
      ) : null}
      {tab === "invoices" && <InvoicesTab />}
      {tab === "receipts" && <ReceiptsTab />}
      {tab === "refunds" && <RefundNotesTab />}
      {tab === "layout" && (
        <section className="section-card"><div className="section-head"><div className="flex items-center gap-2"><Palette size={16} className="text-[#007AFF]" /><h2>Kop surat, gaya & tanda tangan</h2></div><DocCodeSelect value={code} onChange={setCode} targets={targets} /></div>
          <div className="section-body"><LayoutEditor code={code} canEdit={canEdit} onSaved={loadTargets} /></div></section>
      )}
      {tab === "script" && (
        <section className="section-card"><div className="section-head"><div className="flex items-center gap-2"><ScrollText size={16} className="text-[#007AFF]" /><h2>Naskah per jenis dokumen</h2></div><DocCodeSelect value={scriptCode} onChange={setScriptCode} targets={targets} includeDefault={false} /></div>
          <div className="section-body"><ScriptEditor code={scriptCode} canEdit={canEdit} onSaved={loadTargets} /></div></section>
      )}
      {tab === "config" && (
        <section className="section-card"><div className="section-head"><div className="flex items-center gap-2"><Landmark size={16} className="text-[#007AFF]" /><h2>Rekening, pajak, DP & pesan WhatsApp</h2></div></div>
          <div className="section-body"><ConfigPanel canEdit={canEdit} /></div></section>
      )}
      {tab === "numbering" && (
        <section className="section-card"><div className="section-head"><div className="flex items-center gap-2"><Hash size={16} className="text-[#007AFF]" /><h2>Aturan penomoran dokumen</h2></div></div>
          <div className="section-body"><NumberingPanel canEdit={canEdit} /></div></section>
      )}
    </div>
  );
}
