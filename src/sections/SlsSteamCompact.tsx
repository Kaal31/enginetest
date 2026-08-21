import { PanelSection, PanelSectionRow, ButtonItem, Spinner } from "@decky/ui";
import { useEffect, useRef, useState } from "react";
import { callable, toaster } from "@decky/api";
import {
  SlsInstallState,
  SlsStatus,
  getSlssteamStatus,
  installSlssteam,
  getSlssteamInstallStatus,
  reloadSteam,
  getShowReinstallQam,
  systemStatus,
  runClientFix,
  crEnsureInstalled,
  disableForeignEngines,
} from "../api";

const getEngineStatus = callable<[], { success: boolean; selected: "moon" | "luma"; moonInstalled: boolean; lumaInstalled: boolean }>("get_engine_status");
const installLumaEngine = callable<[], { success: boolean; error?: string; installed?: boolean }>("install_luma_engine");
const setEngine = callable<[engine: "moon" | "luma"], { success: boolean; error?: string; selected?: string; restartRequired?: boolean }>("set_engine");

function Chip({ ok, label }: { ok: boolean; label: string }) {
  return (
    <span style={{ display: "inline-block", padding: "1px 8px", marginRight: 6, borderRadius: 10, fontSize: 11, background: ok ? "rgba(88,197,120,0.18)" : "rgba(245,166,35,0.18)", color: ok ? "#58c578" : "#f5a623" }}>
      {ok ? "✓ " : "• "}{label}
    </span>
  );
}

/** Compact SLSsteam block plus the native engine selector. */
export function SlsSteamCompact() {
  const [status, setStatus] = useState<SlsStatus | null>(null);
  const [inst, setInst] = useState<SlsInstallState | null>(null);
  const [busy, setBusy] = useState(false);
  const [showReinstall, setShowReinstall] = useState(true);
  const [sys, setSys] = useState<{ engineInstalled: boolean; foreignEngine: boolean; foreignName: string; cloudredirect: boolean } | null>(null);
  const [qmsg, setQmsg] = useState("");
  const [engine, setEngineState] = useState<Awaited<ReturnType<typeof getEngineStatus>> | null>(null);
  const [engineBusy, setEngineBusy] = useState(false);
  const poll = useRef<ReturnType<typeof setInterval> | null>(null);

  const refresh = async () => {
    try { setStatus(await getSlssteamStatus()); } catch { /* */ }
    try { const s = await systemStatus(); if (s.success) setSys(s); } catch { /* */ }
    try { const e = await getEngineStatus(); if (e.success) setEngineState(e); } catch { /* */ }
  };

  useEffect(() => {
    refresh();
    getShowReinstallQam().then((r) => setShowReinstall(!!r.enabled)).catch(() => {});
    return () => { if (poll.current) clearInterval(poll.current); };
  }, []);

  const waitInstall = () => new Promise<boolean>((resolve) => {
    const iv = setInterval(async () => {
      try {
        const st = await getSlssteamInstallStatus();
        setInst(st.state || null);
        const s = st.state?.status;
        if (s === "done" || s === "failed") { clearInterval(iv); resolve(s === "done"); }
      } catch { /* keep polling */ }
    }, 1500);
  });

  const quickInstall = async () => {
    setBusy(true); setInst(null);
    try {
      const s = await systemStatus();
      if (s.success && (s.foreignEngine || (s.engineInstalled && s.engine !== "slsteam-moon"))) {
        setQmsg(`Clearing conflicting engine (${s.foreignName || s.engine})…`);
        try {
          const d = await disableForeignEngines();
          if (d.success && (d.disabled || []).length) setQmsg(`Disabled ${d.foreignName || "engine"}. Installing slsteam-moon…`);
        } catch { /* best-effort */ }
      }
      if (!s.engineInstalled || (s.engineInstalled && s.engine !== "slsteam-moon")) {
        setQmsg("Installing slsteam-moon…");
        const r = await installSlssteam();
        if (!r.success) {
          const m = r.missingDeps?.length ? `Cannot unpack: ${r.missingDeps.join(", ")}` : (r.error || "SLSsteam install failed");
          setInst({ status: "failed", error: m }); setBusy(false); return;
        }
        const ok = await waitInstall();
        if (!ok) { setBusy(false); return; }
        setQmsg("Applying client fix…");
        try { await runClientFix(); } catch { /* best-effort */ }
      } else {
        setQmsg("slsteam-moon already installed.");
      }
      setQmsg("Installing CloudRedirect in the background (cloud saves)…");
      crEnsureInstalled().catch(() => {});
      setQmsg("SLSDeck is set up. Reload Steam to finish. (CloudRedirect finishes in the background.)");
      toaster.toast({ title: "SLSDeck", body: "SLSDeck set up" });
      refresh();
      setTimeout(() => reloadSteam().catch(() => {}), 3000);
    } catch (e) {
      setQmsg(`Setup error: ${e}`);
    }
    setBusy(false);
  };

  const watch = () => {
    if (poll.current) clearInterval(poll.current);
    poll.current = setInterval(async () => {
      try {
        const st = await getSlssteamInstallStatus();
        setInst(st.state || null);
        const s = st.state?.status;
        if (s === "done" || s === "failed") {
          if (poll.current) clearInterval(poll.current);
          setBusy(false);
          refresh();
          if (s === "done") {
            toaster.toast({ title: "SLSDeck", body: "SLSsteam installed" });
            if (st.state?.installed) setTimeout(() => reloadSteam(), 3000);
          } else toaster.toast({ title: "SLSDeck", body: st.state?.error || "Failed" });
        }
      } catch { /* keep polling */ }
    }, 1500);
  };

  const install = async () => {
    setBusy(true); setInst({ status: "queued" });
    try {
      const r = await installSlssteam();
      if (!r.success) {
        const msg = r.missingDeps?.length ? `Cannot unpack: ${r.missingDeps.join(", ")}` : r.error || "Could not start install";
        setBusy(false); setInst({ status: "failed", error: msg }); toaster.toast({ title: "SLSDeck", body: msg }); return;
      }
      toaster.toast({ title: "SLSDeck", body: "Installing… (a few min)" }); watch();
    } catch (e) {
      const msg = String((e as any)?.message ?? e); setBusy(false); setInst({ status: "failed", error: `Install error: ${msg}` });
    }
  };

  const installLuma = async () => {
    setEngineBusy(true); setQmsg("Installing ordinary SLSsteam + LumaLinux hooks…");
    try {
      const r = await installLumaEngine();
      if (!r.success) {
        setQmsg(r.error || "LumaLinux installation failed");
        toaster.toast({ title: "EngineTest", body: r.error || "LumaLinux installation failed" });
      } else {
        setQmsg("LumaLinux installed. Moon remains active until you switch engines.");
        toaster.toast({ title: "EngineTest", body: "LumaLinux engine installed" });
        await refresh();
      }
    } catch (e) { setQmsg(`Luma install error: ${e}`); }
    setEngineBusy(false);
  };

  const switchEngine = async (next: "moon" | "luma") => {
    if (!engine || engine.selected === next || engineBusy) return;
    setEngineBusy(true); setQmsg(`Switching to ${next === "moon" ? "SLSsteam-moon" : "SLSsteam + LumaLinux"}…`);
    try {
      const r = await setEngine(next);
      if (!r.success) { setQmsg(r.error || "Engine switch failed"); return; }
      toaster.toast({ title: "EngineTest", body: `Engine set to ${next === "moon" ? "SLSsteam-moon" : "SLSsteam + LumaLinux"}. Restarting Steam…` });
      setEngineState((e) => e ? { ...e, selected: next } : e);
      // This is the same restart surface already used by EngineTest in Gaming
      // Mode. The selected engine is persisted before this call; the next Steam
      // process therefore reads it from the existing Game Mode wrapper.
      setTimeout(() => reloadSteam().catch(() => {}), 1200);
    } catch (e) { setQmsg(`Engine switch error: ${e}`); }
    finally { setEngineBusy(false); }
  };

  const working = busy || inst?.status === "running" || inst?.status === "queued";

  return (
    <PanelSection title="SLSsteam / Engine">
      <PanelSectionRow><div style={{ padding: "2px 0" }}>
        <Chip ok={!!status?.installed} label="Moon payload" />
        <Chip ok={!!status?.injected} label="Injected" />
        {engine && <Chip ok={engine.selected === "moon" ? engine.moonInstalled : engine.lumaInstalled} label={`Active: ${engine.selected === "moon" ? "SLSsteam-moon" : "LumaLinux + SLSsteam"}`} />}
      </div></PanelSectionRow>

      {engine && <>
        <PanelSectionRow><div style={{ fontSize: 12, fontWeight: 600, padding: "3px 0" }}>Engine</div></PanelSectionRow>
        <PanelSectionRow><ButtonItem layout="below" disabled={engineBusy || engine.selected === "moon" || !engine.moonInstalled} onClick={() => switchEngine("moon")}>
          {engine.selected === "moon" ? "✓ SLSsteam-moon (active)" : "Switch to SLSsteam-moon"}
        </ButtonItem></PanelSectionRow>
        <PanelSectionRow>
          {engine.lumaInstalled ? (
            <ButtonItem layout="below" disabled={engineBusy || engine.selected === "luma"} onClick={() => switchEngine("luma")}>
              {engine.selected === "luma" ? "✓ SLSsteam + LumaLinux (active)" : "Switch to SLSsteam + LumaLinux"}
            </ButtonItem>
          ) : (
            <ButtonItem layout="below" disabled={engineBusy || !engine.moonInstalled} onClick={installLuma}>
              {engineBusy ? "Installing LumaLinux…" : "Install LumaLinux engine"}
            </ButtonItem>
          )}
        </PanelSectionRow>
        <PanelSectionRow><div style={{ fontSize: 10, opacity: 0.62, padding: "0 2px 3px" }}>
          Both payloads stay installed. Only the selected hook stack is loaded into the next Steam session. Gaming Mode's existing Steam launch hook is reused; LumaLinux's own systemd launcher is not installed.
        </div></PanelSectionRow>
      </>}

      {working && <PanelSectionRow><div style={{ fontSize: 12, opacity: 0.85, padding: "2px 0" }}><Spinner style={{ width: 14, height: 14, marginRight: 8 }} />{inst?.status === "queued" ? "Starting…" : "Installing…"}{typeof inst?.percent === "number" && inst.percent > 0 ? ` ${inst.percent}%` : ""}</div></PanelSectionRow>}
      {inst?.status === "failed" && inst?.error && <PanelSectionRow><div style={{ fontSize: 11, color: "#f5a623", whiteSpace: "pre-wrap", wordBreak: "break-word" }}>{inst.error}</div></PanelSectionRow>}
      {sys?.foreignEngine && !status?.installed && <PanelSectionRow><div style={{ fontSize: 11, color: "#f5a623", padding: "0 2px" }}>Detected {sys.foreignName || "another engine"} — Install will disable it (reversibly) and set up slsteam-moon.</div></PanelSectionRow>}
      {!working && !status?.installed && <PanelSectionRow><ButtonItem layout="below" onClick={quickInstall}>Install SLSDeck (one-tap setup)</ButtonItem></PanelSectionRow>}
      {!working && !status?.installed && <PanelSectionRow><div style={{ fontSize: 11, opacity: 0.6, padding: "0 2px 4px" }}>Installs slsteam-moon{sys?.foreignEngine ? " (disabling any other engine first)" : ""} + CloudRedirect and applies the client fix, in order.</div></PanelSectionRow>}
      {!working && status?.installed && showReinstall && <PanelSectionRow><ButtonItem layout="below" onClick={install}>Reinstall SLSsteam</ButtonItem></PanelSectionRow>}
      {qmsg ? <PanelSectionRow><div style={{ fontSize: 11, opacity: 0.8, padding: "0 2px", whiteSpace: "pre-wrap" }}>{qmsg}</div></PanelSectionRow> : null}
    </PanelSection>
  );
}
