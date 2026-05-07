"use client";

import { useState, useEffect, useRef } from "react";

const API_URL = "/api/v1/hantavirus";

// Equirectangular projection: top = (90 - lat) / 180 * 100, left = (lon + 180) / 360 * 100
function latLonToPercent(lat: number, lon: number) {
  return {
    top: ((90 - lat) / 180) * 100,
    left: ((lon + 180) / 360) * 100,
  };
}

const MARKER_POSITIONS = {
  vessel: latLonToPercent(-60, -55),
  CH: latLonToPercent(47, 8),
  AR: latLonToPercent(-35, -65),
  ZA: latLonToPercent(-30, 25),
  SN: latLonToPercent(14, -14),
};

const STATUS_COLORS: Record<string, string> = {
  ACTIVE: "#ef4444",
  CONFIRMED: "#f97316",
  "SOURCE REGION": "#a855f7",
  RESPONDING: "#3b82f6",
};

type AffectedEntry = {
  id: string;
  name: string;
  region: string;
  flag: string;
  lat: number;
  lon: number;
  cases: number | null;
  confirmed: number | null;
  deaths: number;
  status: string;
  detail: string;
};

type Outbreak = {
  name: string;
  subtype: string;
  origin_event: string;
  status: string;
  risk_level: string;
  total_cases: number;
  confirmed_cases: number;
  deaths: number;
  last_updated: string;
  source: string;
  source_url: string;
  transmission: {
    type: string;
    vector: string;
    person_to_person: boolean;
    person_to_person_note: string;
    incubation_days: string;
    historical_cfr_pct: number;
    severity: string;
    symptoms: string[];
  };
  affected: AffectedEntry[];
  organizations: string[];
};

type NewsItem = {
  title: string;
  url: string;
  source: string;
  published_at: string;
  summary: string;
};

type OutbreakData = {
  success: boolean;
  outbreak: Outbreak;
  news: NewsItem[];
  fetched_at: string;
};

function AnimatedCounter({ value }: { value: number }) {
  const [display, setDisplay] = useState(0);
  const ref = useRef(false);

  useEffect(() => {
    if (ref.current) return;
    ref.current = true;
    const duration = 1200;
    const start = Date.now();
    const tick = () => {
      const elapsed = Date.now() - start;
      const progress = Math.min(elapsed / duration, 1);
      const ease = 1 - Math.pow(1 - progress, 3);
      setDisplay(Math.round(ease * value));
      if (progress < 1) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  }, [value]);

  return <>{display}</>;
}

function WorldMap({ affected }: { affected: AffectedEntry[] }) {
  return (
    <div className="relative w-full rounded-xl overflow-hidden border border-red-900/30 bg-[#03050a]"
      style={{ aspectRatio: "2/1" }}>
      {/* Latitude/longitude grid */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          backgroundImage: `
            linear-gradient(to right, rgba(220,38,38,0.06) 1px, transparent 1px),
            linear-gradient(to bottom, rgba(220,38,38,0.06) 1px, transparent 1px)
          `,
          backgroundSize: "10% 10%",
        }}
      />
      {/* Equator line */}
      <div className="absolute left-0 right-0 border-t border-red-700/20" style={{ top: "50%" }} />
      {/* Prime meridian */}
      <div className="absolute top-0 bottom-0 border-l border-red-700/20" style={{ left: "50%" }} />

      {/* Simplified continent blobs */}
      <svg
        className="absolute inset-0 w-full h-full"
        viewBox="0 0 720 360"
        preserveAspectRatio="none"
      >
        {/* North America */}
        <path
          d="M 60 65 L 215 55 L 225 80 L 230 140 L 200 185 L 165 185 L 130 195 L 100 180 L 75 155 L 60 120 Z"
          fill="#0d1a0d" stroke="#1a3a1a" strokeWidth="1"
        />
        {/* Greenland */}
        <path d="M 215 30 L 255 28 L 265 55 L 230 60 Z" fill="#0d1a0d" stroke="#1a3a1a" strokeWidth="1" />
        {/* South America */}
        <path
          d="M 155 195 L 215 190 L 240 200 L 255 260 L 265 330 L 225 355 L 185 340 L 160 295 L 145 240 Z"
          fill="#0d1a0d" stroke="#1a3a1a" strokeWidth="1"
        />
        {/* Europe */}
        <path
          d="M 330 55 L 395 48 L 420 65 L 430 95 L 415 120 L 390 130 L 360 130 L 335 110 L 320 85 Z"
          fill="#0d1a0d" stroke="#1a3a1a" strokeWidth="1"
        />
        {/* Africa */}
        <path
          d="M 320 130 L 430 125 L 460 155 L 465 225 L 445 295 L 415 345 L 380 355 L 340 330 L 315 270 L 310 200 Z"
          fill="#0d1a0d" stroke="#1a3a1a" strokeWidth="1"
        />
        {/* Asia */}
        <path
          d="M 430 45 L 680 40 L 695 100 L 690 160 L 650 200 L 590 210 L 540 195 L 480 185 L 445 155 L 425 110 Z"
          fill="#0d1a0d" stroke="#1a3a1a" strokeWidth="1"
        />
        {/* Indian Subcontinent */}
        <path d="M 540 195 L 575 210 L 570 255 L 545 260 L 515 230 Z" fill="#0d1a0d" stroke="#1a3a1a" strokeWidth="1" />
        {/* SE Asia peninsula */}
        <path d="M 590 210 L 615 215 L 620 260 L 600 265 L 580 245 Z" fill="#0d1a0d" stroke="#1a3a1a" strokeWidth="1" />
        {/* Australia */}
        <path
          d="M 565 245 L 650 240 L 670 265 L 670 310 L 640 330 L 590 325 L 555 300 L 550 270 Z"
          fill="#0d1a0d" stroke="#1a3a1a" strokeWidth="1"
        />
        {/* Japan */}
        <path d="M 655 95 L 670 90 L 675 115 L 660 120 Z" fill="#0d1a0d" stroke="#1a3a1a" strokeWidth="1" />
        {/* UK */}
        <path d="M 325 68 L 335 65 L 338 80 L 328 82 Z" fill="#0d1a0d" stroke="#1a3a1a" strokeWidth="1" />
      </svg>

      {/* Connection lines between active/confirmed */}
      <svg className="absolute inset-0 w-full h-full pointer-events-none" viewBox="0 0 100 50" preserveAspectRatio="none">
        {affected
          .filter((a) => a.id !== "vessel" && a.cases !== null)
          .map((a) => {
            const from = MARKER_POSITIONS["vessel"];
            const pos = MARKER_POSITIONS[a.id as keyof typeof MARKER_POSITIONS];
            if (!pos) return null;
            return (
              <line
                key={a.id}
                x1={from.left}
                y1={from.top / 2}
                x2={pos.left}
                y2={pos.top / 2}
                stroke="#dc2626"
                strokeWidth="0.15"
                strokeDasharray="0.5 0.5"
                opacity="0.4"
              />
            );
          })}
      </svg>

      {/* Markers */}
      {affected.map((entry) => {
        const pos = MARKER_POSITIONS[entry.id as keyof typeof MARKER_POSITIONS];
        if (!pos) return null;
        const color = STATUS_COLORS[entry.status] || "#6b7280";
        const isActive = entry.status === "ACTIVE" || entry.status === "CONFIRMED";
        return (
          <div
            key={entry.id}
            className="absolute -translate-x-1/2 -translate-y-1/2 group cursor-default"
            style={{ top: `${pos.top}%`, left: `${pos.left}%` }}
            title={`${entry.name}: ${entry.detail}`}
          >
            {isActive && (
              <div
                className="absolute w-6 h-6 rounded-full -translate-x-1/2 -translate-y-1/2 top-1/2 left-1/2 animate-ping opacity-60"
                style={{ backgroundColor: color }}
              />
            )}
            <div
              className="relative w-3 h-3 rounded-full border border-white/20 shadow-lg z-10"
              style={{ backgroundColor: color, boxShadow: `0 0 8px ${color}88` }}
            />
            <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1 px-2 py-1 bg-[#0a0a18] border border-white/10 rounded text-[10px] text-white whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-20">
              {entry.flag} {entry.name}
              {entry.cases !== null && <span className="text-red-400 ml-1">· {entry.cases} case{entry.cases !== 1 ? "s" : ""}</span>}
            </div>
          </div>
        );
      })}

      {/* Legend */}
      <div className="absolute bottom-2 right-2 flex flex-col gap-1">
        {Object.entries(STATUS_COLORS).map(([label, color]) => (
          <div key={label} className="flex items-center gap-1.5">
            <div className="w-2 h-2 rounded-full" style={{ backgroundColor: color }} />
            <span className="text-[9px] font-mono" style={{ color }}>{label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function HantavirusPage() {
  const [data, setData] = useState<OutbreakData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    document.title = "Hantavirus Outbreak Tracker — Solvr Intel";
  }, []);

  useEffect(() => {
    fetch(API_URL)
      .then((r) => r.json())
      .then((d: OutbreakData) => {
        if (d.success) setData(d);
        else setError("Failed to load outbreak data");
      })
      .catch(() => setError("Network error — please refresh"))
      .finally(() => setLoading(false));
  }, []);

  const outbreak = data?.outbreak;
  const news = data?.news ?? [];

  return (
    <div
      className="min-h-screen text-gray-100"
      style={{ background: "linear-gradient(135deg, #030308 0%, #060a08 50%, #03060a 100%)" }}
    >
      {/* Biohazard watermark */}
      <div
        className="fixed inset-0 pointer-events-none select-none flex items-center justify-center opacity-[0.025]"
        aria-hidden
      >
        <span style={{ fontSize: "60vw", lineHeight: 1 }}>☣</span>
      </div>

      <div className="relative max-w-6xl mx-auto px-4 py-10">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-3">
            <span className="text-2xl select-none">☣</span>
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-mono uppercase tracking-widest text-red-400 bg-red-500/10 border border-red-500/30 rounded px-2 py-0.5 animate-pulse">
                OUTBREAK ACTIVE
              </span>
              <span className="text-[10px] font-mono text-gray-500">
                FREE INTEL · POWERED BY SOLVR
              </span>
            </div>
          </div>
          <h1 className="text-4xl md:text-5xl font-black tracking-tight text-white mb-1">
            Andes{" "}
            <span className="text-red-500">Hantavirus</span>
          </h1>
          <p className="text-gray-400 text-sm">
            {(outbreak as unknown as Record<string, unknown>)?.live_data
              ? "Live WHO DON RSS · Case counts auto-updated"
              : "WHO DON snapshot · Live news feed"}{" "}
            · Last updated {outbreak?.last_updated ?? "…"}
          </p>
        </div>

        {loading && (
          <div className="flex items-center gap-3 text-gray-400 text-sm py-20 justify-center">
            <div className="w-5 h-5 border-2 border-red-700/40 border-t-red-500 rounded-full animate-spin" />
            Loading outbreak data…
          </div>
        )}

        {error && (
          <div className="bg-red-900/20 border border-red-500/30 rounded-xl px-6 py-4 text-red-300 text-sm">
            {error}
          </div>
        )}

        {outbreak && (
          <>
            {/* Stats row */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
              {[
                { label: "TOTAL CASES", value: outbreak.total_cases, color: "#ef4444", sub: "reported" },
                { label: "CONFIRMED", value: outbreak.confirmed_cases, color: "#f97316", sub: "lab-verified" },
                { label: "DEATHS", value: outbreak.deaths, color: "#6b7280", sub: "current" },
                { label: "COUNTRIES", value: outbreak.affected.filter((a) => a.cases !== null).length, color: "#a855f7", sub: "with cases" },
              ].map((stat) => (
                <div
                  key={stat.label}
                  className="rounded-xl border border-white/5 bg-white/[0.03] px-5 py-4 text-center"
                  style={{ borderColor: `${stat.color}22` }}
                >
                  <div className="text-3xl font-black mb-0.5" style={{ color: stat.color }}>
                    <AnimatedCounter value={stat.value} />
                  </div>
                  <div className="text-[10px] font-mono uppercase tracking-widest text-gray-400">{stat.label}</div>
                  <div className="text-[10px] text-gray-600 mt-0.5">{stat.sub}</div>
                </div>
              ))}
            </div>

            {/* Live data badge */}
            {!!(outbreak as unknown as Record<string, unknown>)?.live_data && (
              <div className="flex items-center gap-2 mb-4 text-[10px] font-mono text-green-400">
                <div className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
                LIVE — case counts parsed from WHO Disease Outbreak News RSS
              </div>
            )}

            {/* Threat level */}
            <div className="flex items-center gap-4 mb-6 bg-white/[0.03] border border-red-900/20 rounded-xl px-5 py-3">
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-yellow-400 animate-pulse" />
                <span className="text-xs font-mono text-gray-400 uppercase tracking-widest">WHO Risk Level</span>
              </div>
              <div className="flex gap-2">
                {["VERY LOW", "LOW", "MODERATE", "HIGH", "VERY HIGH"].map((level) => (
                  <div
                    key={level}
                    className="text-[10px] font-mono px-2 py-0.5 rounded"
                    style={
                      level === outbreak.risk_level
                        ? { background: "#f97316", color: "#000", fontWeight: 700 }
                        : { background: "rgba(255,255,255,0.05)", color: "#555" }
                    }
                  >
                    {level}
                  </div>
                ))}
              </div>
              <div className="ml-auto text-[10px] text-gray-500 font-mono">
                Global: {outbreak.who_global_risk} · Regional: {outbreak.risk_level}
              </div>
            </div>

            {/* Main 2-column layout */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-5 mb-6">
              {/* World map — takes 2/3 */}
              <div className="lg:col-span-2">
                <div className="text-[10px] font-mono uppercase tracking-widest text-gray-500 mb-2">
                  GLOBAL SPREAD MAP
                </div>
                <WorldMap affected={outbreak.affected} />
                <div className="mt-2 text-[10px] text-gray-600 text-center">
                  Hover markers for details · Equirectangular projection
                </div>
              </div>

              {/* Affected regions list — 1/3 */}
              <div>
                <div className="text-[10px] font-mono uppercase tracking-widest text-gray-500 mb-2">
                  AFFECTED REGIONS
                </div>
                <div className="space-y-2">
                  {outbreak.affected.map((entry) => {
                    const color = STATUS_COLORS[entry.status] || "#6b7280";
                    return (
                      <div
                        key={entry.id}
                        className="rounded-xl border bg-white/[0.03] px-4 py-3"
                        style={{ borderColor: `${color}33` }}
                      >
                        <div className="flex items-center justify-between mb-1">
                          <div className="flex items-center gap-2">
                            <span className="text-base">{entry.flag}</span>
                            <span className="text-sm font-semibold text-white">{entry.name}</span>
                          </div>
                          <span
                            className="text-[9px] font-mono px-1.5 py-0.5 rounded"
                            style={{ background: `${color}20`, color }}
                          >
                            {entry.status}
                          </span>
                        </div>
                        <div className="text-xs text-gray-500 leading-relaxed">{entry.detail}</div>
                        {entry.cases !== null && (
                          <div className="mt-1.5 flex gap-3 text-[11px]">
                            <span className="text-red-400 font-mono">{entry.cases} cases</span>
                            {entry.confirmed !== null && (
                              <span className="text-orange-400 font-mono">{entry.confirmed} confirmed</span>
                            )}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>

            {/* Transmission info */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-5 mb-6">
              <div className="bg-white/[0.03] border border-white/5 rounded-xl px-5 py-4">
                <div className="text-[10px] font-mono uppercase tracking-widest text-gray-500 mb-3">TRANSMISSION</div>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-500">Type</span>
                    <span className="text-white text-right max-w-[60%]">{outbreak.transmission.type}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">Vector</span>
                    <span className="text-white text-right max-w-[60%] text-xs">{outbreak.transmission.vector}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">Person-to-person</span>
                    <span className="text-red-400 font-semibold">YES ⚠</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">Incubation</span>
                    <span className="text-white">{outbreak.transmission.incubation_days}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">Historical CFR</span>
                    <span className="text-red-400 font-bold">{outbreak.transmission.historical_cfr_pct}%</span>
                  </div>
                </div>
              </div>

              <div className="bg-white/[0.03] border border-white/5 rounded-xl px-5 py-4">
                <div className="text-[10px] font-mono uppercase tracking-widest text-gray-500 mb-3">SYMPTOMS</div>
                <div className="flex flex-wrap gap-2">
                  {outbreak.transmission.symptoms.map((s) => (
                    <span
                      key={s}
                      className="text-xs px-2.5 py-1 rounded-full border border-red-900/40 text-red-300 bg-red-900/10"
                    >
                      {s}
                    </span>
                  ))}
                </div>
                <div className="mt-4">
                  <div className="text-[10px] font-mono uppercase tracking-widest text-gray-500 mb-2">RESPONDING ORGS</div>
                  <div className="space-y-1">
                    {outbreak.organizations.map((org) => (
                      <div key={org} className="text-xs text-gray-400 flex items-center gap-1.5">
                        <div className="w-1 h-1 rounded-full bg-blue-400 flex-shrink-0" />
                        {org}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>

            {/* Warning banner */}
            <div className="mb-6 bg-red-950/30 border border-red-800/40 rounded-xl px-5 py-4 text-sm">
              <div className="flex items-start gap-3">
                <span className="text-red-400 text-lg flex-shrink-0">⚠</span>
                <div>
                  <div className="font-semibold text-red-300 mb-1">Person-to-Person Transmission Warning</div>
                  <div className="text-red-400/80 text-xs leading-relaxed">
                    {outbreak.transmission.person_to_person_note}. WHO is coordinating international contact tracing for all
                    passengers and crew of the MV Hondius. Anyone with potential exposure should monitor for symptoms and seek
                    medical attention immediately.
                  </div>
                </div>
              </div>
            </div>

            {/* News feed */}
            <div className="mb-6">
              <div className="text-[10px] font-mono uppercase tracking-widest text-gray-500 mb-3">
                LIVE INTELLIGENCE FEED
              </div>
              {news.length === 0 ? (
                <div className="text-gray-500 text-sm bg-white/[0.02] border border-white/5 rounded-xl px-5 py-4">
                  No recent news articles found. Check back soon.
                </div>
              ) : (
                <div className="space-y-3">
                  {news.map((item, i) => (
                    <a
                      key={i}
                      href={item.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="block bg-white/[0.03] border border-white/5 hover:border-red-900/40 rounded-xl px-5 py-4 transition-colors group"
                    >
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex-1 min-w-0">
                          <div className="text-sm font-medium text-white group-hover:text-red-300 transition-colors mb-1 line-clamp-2">
                            {item.title}
                          </div>
                          {item.summary && (
                            <div className="text-xs text-gray-500 line-clamp-2">{item.summary}</div>
                          )}
                        </div>
                        <div className="text-[10px] font-mono text-gray-600 flex-shrink-0 text-right">
                          <div>{item.source}</div>
                          {item.published_at && (
                            <div className="text-gray-700 mt-0.5">
                              {new Date(item.published_at.endsWith("Z") ? item.published_at : item.published_at + "Z").toLocaleDateString()}
                            </div>
                          )}
                        </div>
                      </div>
                    </a>
                  ))}
                </div>
              )}
            </div>

            {/* Free API callout */}
            <div className="mb-6 bg-[#050a18] border border-blue-900/30 rounded-xl px-5 py-5">
              <div className="flex items-start justify-between gap-4 flex-wrap">
                <div>
                  <div className="text-[10px] font-mono uppercase tracking-widest text-blue-400 mb-1">FREE API ENDPOINT</div>
                  <div className="font-mono text-sm text-white mb-2">
                    GET <span className="text-[#00d4ff]">https://solvrbot.com/api/v1/hantavirus</span>
                  </div>
                  <div className="text-xs text-gray-500">
                    No authentication required. Free tier. Returns outbreak data, affected countries, transmission details + live news.
                  </div>
                </div>
                <div className="flex gap-2 flex-wrap items-center">
                  <span className="text-[9px] font-mono px-2 py-0.5 rounded bg-green-500/15 text-green-400">FREE</span>
                  <span className="text-[9px] font-mono px-2 py-0.5 rounded bg-blue-500/15 text-blue-400">OPEN</span>
                  <a
                    href="https://solvrbot.com/api-docs"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs text-[#00d4ff] hover:underline"
                  >
                    API Docs →
                  </a>
                </div>
              </div>
              <div className="mt-3 bg-black/40 rounded-lg px-4 py-3 font-mono text-xs text-gray-400 overflow-x-auto">
                <span className="text-yellow-400">curl</span>{" "}
                <span className="text-green-400">https://solvrbot.com/api/v1/hantavirus</span>
              </div>
            </div>

            {/* Attribution */}
            <div className="text-center text-[10px] text-gray-600 space-y-1">
              <div>
                Data sourced from{" "}
                <a
                  href={outbreak.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-gray-500 hover:text-white underline"
                >
                  {outbreak.source}
                </a>
                {" "}· Cached 2h · Last updated {outbreak.last_updated}
              </div>
              <div>
                Intelligence powered by{" "}
                <a href="https://solvrbot.com" target="_blank" rel="noopener noreferrer" className="text-[#00d4ff] hover:underline">
                  Solvr
                </a>
                {" "}· Free public data for global health awareness
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
