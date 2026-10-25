import React from 'react'

interface IconProps {
  name: string
  size?: number
  stroke?: number
  style?: React.CSSProperties
  className?: string
}

export function Icon({ name, size = 18, stroke = 1.6, style, className }: IconProps) {
  const p = {
    width: size, height: size, viewBox: "0 0 24 24", fill: "none",
    stroke: "currentColor", strokeWidth: stroke, strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const, style, className,
  }
  const paths: Record<string, React.ReactNode> = {
    dashboard: <><rect x="3" y="3" width="7" height="9" rx="1.5"/><rect x="14" y="3" width="7" height="5" rx="1.5"/><rect x="14" y="12" width="7" height="9" rx="1.5"/><rect x="3" y="16" width="7" height="5" rx="1.5"/></>,
    table:    <><rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 9h18M9 9v11M3 14.5h18"/></>,
    sparkle:  <><path d="M12 3l1.9 5.6L19.5 10l-5.6 1.9L12 17.5 10.1 11.9 4.5 10l5.6-1.4L12 3Z"/></>,
    alert:    <><path d="M10.3 4.3 2.6 18a2 2 0 0 0 1.7 3h15.4a2 2 0 0 0 1.7-3L13.7 4.3a2 2 0 0 0-3.4 0Z"/><path d="M12 9v4M12 17h.01"/></>,
    map:      <><path d="M9 4 3 6v14l6-2 6 2 6-2V4l-6 2-6-2Z"/><path d="M9 4v14M15 6v14"/></>,
    shield:   <><path d="M12 3 5 6v5c0 4.5 3 8 7 10 4-2 7-5.5 7-10V6l-7-3Z"/><path d="m9 12 2 2 4-4"/></>,
    search:   <><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></>,
    filter:   <><path d="M3 5h18l-7 8v6l-4 2v-8L3 5Z"/></>,
    download: <><path d="M12 3v12m0 0 4-4m-4 4-4-4"/><path d="M4 17v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2"/></>,
    chevR:    <path d="m9 6 6 6-6 6"/>,
    chevD:    <path d="m6 9 6 6 6-6"/>,
    chevL:    <path d="m15 6-6 6 6 6"/>,
    chevUp:   <path d="m6 15 6-6 6 6"/>,
    close:    <path d="M6 6l12 12M18 6 6 18"/>,
    external: <><path d="M14 4h6v6"/><path d="M20 4 11 13"/><path d="M18 14v4a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4"/></>,
    arrowUp:  <path d="M12 19V5m0 0-6 6m6-6 6 6"/>,
    arrowDn:  <path d="M12 5v14m0 0 6-6m-6 6-6-6"/>,
    send:     <path d="M4 12 20 4l-6 16-3-7-7-1Z"/>,
    check:    <path d="m5 12 4.5 4.5L19 7"/>,
    clock:    <><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></>,
    pin:      <><path d="M12 21s7-6.3 7-12A7 7 0 0 0 5 9c0 5.7 7 12 7 12Z"/><circle cx="12" cy="9" r="2.5"/></>,
    coins:    <><ellipse cx="9" cy="7" rx="6" ry="3"/><path d="M3 7v5c0 1.7 2.7 3 6 3s6-1.3 6-3V7"/><path d="M15 11.5c2.8-.2 6-1.4 6-3.5M9 15v3c0 1.7 2.7 3 6 3s6-1.3 6-3v-6"/></>,
    pulse:    <path d="M3 12h4l2-6 4 14 2-8h6"/>,
    sun:      <><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4 12H2M22 12h-2M5 5l1.5 1.5M17.5 17.5 19 19M19 5l-1.5 1.5M6.5 17.5 5 19"/></>,
    moon:     <path d="M20 14.5A8 8 0 0 1 9.5 4 8 8 0 1 0 20 14.5Z"/>,
    menu:     <path d="M4 7h16M4 12h16M4 17h16"/>,
    bell:     <><path d="M18 8a6 6 0 1 0-12 0c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.5 21a2 2 0 0 1-3 0"/></>,
    user:     <><circle cx="12" cy="8" r="4"/><path d="M5 21a7 7 0 0 1 14 0"/></>,
    bolt:     <path d="M13 2 4 14h6l-1 8 9-12h-6l1-8Z"/>,
    flag:     <><path d="M5 21V4M5 4l6 2 8-2v11l-8 2-6-2"/></>,
    globe:    <><circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c2.5 2.5 3.5 6 3.5 9s-1 6.5-3.5 9c-2.5-2.5-3.5-6-3.5-9s1-6.5 3.5-9Z"/></>,
    scale:    <><path d="M12 3v18M6 7h12"/><path d="m6 7-3 6a3 3 0 0 0 6 0L6 7ZM18 7l-3 6a3 3 0 0 0 6 0l-3-6Z"/><path d="M5 21h14"/></>,
    doc:      <><path d="M6 3h8l4 4v14a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1Z"/><path d="M14 3v4h4M8 13h8M8 17h6"/></>,
    dot:      <circle cx="12" cy="12" r="3.5" fill="currentColor" stroke="none"/>,
  }
  return <svg {...p}>{paths[name] ?? paths.dot}</svg>
}
