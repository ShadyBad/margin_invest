import { ImageResponse } from "next/og"

export const runtime = "edge"

export const alt = "Margin Invest — Deterministic Investment Analysis"
export const size = { width: 1200, height: 630 }
export const contentType = "image/png"

export default async function Image() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          padding: "80px",
          background: "linear-gradient(135deg, #0A0F0D 0%, #111A15 50%, #0A0F0D 100%)",
          fontFamily: "system-ui, sans-serif",
        }}
      >
        {/* Grid pattern overlay */}
        <div
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundImage:
              "linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px)",
            backgroundSize: "64px 64px",
          }}
        />

        {/* Accent glow */}
        <div
          style={{
            position: "absolute",
            top: "30%",
            right: "20%",
            width: "400px",
            height: "400px",
            borderRadius: "50%",
            background: "radial-gradient(circle, rgba(26,122,90,0.15) 0%, transparent 70%)",
          }}
        />

        {/* Live badge */}
        <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "24px" }}>
          <div
            style={{
              width: "10px",
              height: "10px",
              borderRadius: "50%",
              background: "#1A7A5A",
              boxShadow: "0 0 8px #1A7A5A, 0 0 16px rgba(26,122,90,0.3)",
            }}
          />
          <span
            style={{
              fontSize: "14px",
              letterSpacing: "0.15em",
              textTransform: "uppercase" as const,
              color: "#1A7A5A",
              fontWeight: 500,
              fontFamily: "monospace",
            }}
          >
            Live
          </span>
        </div>

        {/* Headline */}
        <div
          style={{
            fontSize: "72px",
            fontWeight: 400,
            color: "#EDE9E3",
            lineHeight: 1.1,
            letterSpacing: "-2px",
            marginBottom: "8px",
          }}
        >
          Discipline.
        </div>
        <div
          style={{
            fontSize: "72px",
            fontWeight: 400,
            color: "#1A7A5A",
            lineHeight: 1.1,
            letterSpacing: "-2px",
            marginBottom: "32px",
            fontStyle: "italic",
          }}
        >
          Engineered.
        </div>

        {/* Subtext */}
        <div
          style={{
            fontSize: "20px",
            color: "#A39E96",
            maxWidth: "600px",
            lineHeight: 1.5,
            marginBottom: "40px",
          }}
        >
          A deterministic capital allocation system. Scoring 3,000+ US equities daily with zero
          human discretion.
        </div>

        {/* Bottom bar */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "24px",
            marginTop: "auto",
          }}
        >
          <span style={{ fontSize: "18px", color: "#EDE9E3", fontWeight: 600 }}>
            margin-invest.com
          </span>
          <div
            style={{
              width: "1px",
              height: "20px",
              background: "rgba(237,233,227,0.2)",
            }}
          />
          <span style={{ fontSize: "14px", color: "#6B6660", fontFamily: "monospace" }}>
            No opinions. No overrides. Just math.
          </span>
        </div>
      </div>
    ),
    { ...size },
  )
}
