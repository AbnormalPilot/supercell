/* =====================================================================
 * SUPERCELL — VABB Mumbai Tower (Apple-system edition)
 *
 * Canvas radar + UI controller. Uses a restrained Apple-tone palette:
 * navy background, white outlines, Apple Blue for normal traffic,
 * red for MAYDAY, amber for PAN-PAN. No phosphor bloom.
 * ================================================================== */

(function () {
    "use strict";

    // ---------- Canvas + geometry ----------
    const canvas = document.getElementById("radar-canvas");
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    const W = canvas.width;
    const H = canvas.height;
    const CX = W / 2;
    const CY = H / 2;
    const RADAR_R = Math.min(W, H) / 2 - 24;
    const RANGE_NM = 40;

    const COLOR_RING    = "rgba(255, 255, 255, 0.18)";
    const COLOR_RING_2  = "rgba(255, 255, 255, 0.10)";
    const COLOR_TEXT    = "rgba(255, 255, 255, 0.55)";
    const COLOR_TEXT_BR = "#ffffff";
    const COLOR_RUNWAY  = "#ffffff";
    const COLOR_FIX     = "#7a9cff";
    const COLOR_NORMAL  = "#2997ff"; // bright blue (Apple dark-bg link)
    const COLOR_PANPAN  = "#ffb020";
    const COLOR_MAYDAY  = "#ff453a";
    const COLOR_SELECT  = "#ffd60a";
    const COLOR_SWEEP   = "rgba(255, 255, 255, 0.22)";

    // VABB STAR fix geometry (approximate bearings from airport)
    const FIXES = [
        { name: "PARAR", bearing: 90,  nm: 32 },
        { name: "GUDOM", bearing: 45,  nm: 35 },
        { name: "NOMUS", bearing: 135, nm: 34 },
        { name: "LEKIT", bearing: 315, nm: 32 },
    ];

    // VABB runways: 09/27 (primary), 14/32 (crossing secondary)
    const RUNWAYS = [
        { headingDeg: 90,  lengthNm: 2.1, primary: true  },
        { headingDeg: 135, lengthNm: 1.7, primary: false },
    ];

    // ---------- State ----------
    let sweepAngle = -Math.PI / 2;
    let observation = null;
    let taskId = null;
    let selectedIndex = null;
    let prevCrashed = 0;
    const trails = new Map();
    /** @type {{step:number, reward:number, cumulative:number}[]} */
    const rewardHistory = [];

    function polarToXY(bearingDeg, nm) {
        const rad = ((bearingDeg - 90) * Math.PI) / 180;
        const r = (nm / RANGE_NM) * RADAR_R;
        return { x: CX + Math.cos(rad) * r, y: CY + Math.sin(rad) * r };
    }

    function zuluClock() {
        const d = new Date();
        const p = (n) => String(n).padStart(2, "0");
        return `${p(d.getUTCHours())}:${p(d.getUTCMinutes())}:${p(d.getUTCSeconds())}`;
    }

    // ---------- Rendering ----------
    function drawBackground() {
        ctx.clearRect(0, 0, W, H);

        // Outer ring
        ctx.strokeStyle = COLOR_RING;
        ctx.lineWidth = 1.5;
        ctx.beginPath();
        ctx.arc(CX, CY, RADAR_R, 0, Math.PI * 2);
        ctx.stroke();

        // Range rings — three dashed concentric rings
        ctx.strokeStyle = COLOR_RING_2;
        ctx.setLineDash([2, 5]);
        for (let i = 1; i < 4; i++) {
            ctx.beginPath();
            ctx.arc(CX, CY, (RADAR_R * i) / 4, 0, Math.PI * 2);
            ctx.stroke();
        }
        ctx.setLineDash([]);

        // Crosshairs
        ctx.strokeStyle = COLOR_RING_2;
        ctx.beginPath();
        ctx.moveTo(CX - RADAR_R, CY);
        ctx.lineTo(CX + RADAR_R, CY);
        ctx.moveTo(CX, CY - RADAR_R);
        ctx.lineTo(CX, CY + RADAR_R);
        ctx.stroke();

        // Compass labels
        ctx.fillStyle = COLOR_TEXT;
        ctx.font = "11px 'SF Pro Text', monospace";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText("N", CX, CY - RADAR_R - 10);
        ctx.fillText("S", CX, CY + RADAR_R + 10);
        ctx.textAlign = "left";
        ctx.fillText("E", CX + RADAR_R + 8, CY);
        ctx.textAlign = "right";
        ctx.fillText("W", CX - RADAR_R - 8, CY);

        // Range ring labels
        ctx.textAlign = "left";
        ctx.fillStyle = "rgba(255, 255, 255, 0.28)";
        ctx.font = "9px 'SF Mono', monospace";
        for (let i = 1; i <= 4; i++) {
            const nm = (RANGE_NM * i) / 4;
            ctx.fillText(`${nm.toFixed(0)}NM`, CX + 4, CY - (RADAR_R * i) / 4);
        }
    }

    function drawRunways() {
        RUNWAYS.forEach((rw) => {
            const halfLen = (rw.lengthNm / RANGE_NM) * RADAR_R;
            const rad = ((rw.headingDeg - 90) * Math.PI) / 180;
            const dx = Math.cos(rad) * halfLen;
            const dy = Math.sin(rad) * halfLen;
            ctx.strokeStyle = rw.primary
                ? COLOR_RUNWAY
                : "rgba(255, 255, 255, 0.35)";
            ctx.lineWidth = 2.5;
            ctx.lineCap = "round";
            ctx.beginPath();
            ctx.moveTo(CX - dx, CY - dy);
            ctx.lineTo(CX + dx, CY + dy);
            ctx.stroke();
        });

        // Airport marker — small filled square
        ctx.fillStyle = COLOR_RUNWAY;
        ctx.fillRect(CX - 3, CY - 3, 6, 6);

        ctx.fillStyle = "rgba(255, 255, 255, 0.55)";
        ctx.font = "10px 'SF Pro Text', monospace";
        ctx.textAlign = "left";
        ctx.fillText("VABB", CX + 8, CY + 16);
    }

    function drawFixes() {
        FIXES.forEach((f) => {
            const p = polarToXY(f.bearing, f.nm);

            // Airway from fix → airport
            ctx.setLineDash([1, 4]);
            ctx.strokeStyle = "rgba(122, 156, 255, 0.18)";
            ctx.lineWidth = 1;
            ctx.beginPath();
            ctx.moveTo(p.x, p.y);
            ctx.lineTo(CX, CY);
            ctx.stroke();
            ctx.setLineDash([]);

            // Triangle waypoint
            ctx.strokeStyle = COLOR_FIX;
            ctx.fillStyle = "rgba(122, 156, 255, 0.16)";
            ctx.lineWidth = 1;
            ctx.beginPath();
            ctx.moveTo(p.x, p.y - 5);
            ctx.lineTo(p.x + 5, p.y + 4);
            ctx.lineTo(p.x - 5, p.y + 4);
            ctx.closePath();
            ctx.fill();
            ctx.stroke();

            ctx.fillStyle = "rgba(122, 156, 255, 0.9)";
            ctx.font = "10px 'SF Pro Text', monospace";
            ctx.textAlign = "center";
            ctx.fillText(f.name, p.x, p.y + 16);
        });
    }

    function drawSweep() {
        // Soft wedge sweep — minimal, no neon bloom
        const span = 0.5;
        const grad = ctx.createConicGradient(sweepAngle, CX, CY);
        grad.addColorStop(0, COLOR_SWEEP);
        grad.addColorStop(span / (Math.PI * 2), "rgba(255, 255, 255, 0)");
        ctx.fillStyle = grad;
        ctx.beginPath();
        ctx.moveTo(CX, CY);
        ctx.arc(CX, CY, RADAR_R, sweepAngle, sweepAngle + span);
        ctx.closePath();
        ctx.fill();

        // Leading edge line
        ctx.strokeStyle = "rgba(255, 255, 255, 0.55)";
        ctx.lineWidth = 1.5;
        ctx.beginPath();
        ctx.moveTo(CX, CY);
        ctx.lineTo(
            CX + Math.cos(sweepAngle) * RADAR_R,
            CY + Math.sin(sweepAngle) * RADAR_R
        );
        ctx.stroke();
    }

    function drawFlights() {
        if (!observation || !observation.flights) return;
        observation.flights.forEach((f, i) => {
            const bearing = typeof f.bearing_deg === "number" ? f.bearing_deg : 90;
            const nm = Math.min(RANGE_NM - 2, Math.max(4, f.distance_nm || 20));
            const p = polarToXY(bearing, nm);

            // Short trail — 6 recent positions
            const trail = trails.get(f.callsign) || [];
            trail.push(p);
            if (trail.length > 6) trail.shift();
            trails.set(f.callsign, trail);

            for (let t = 0; t < trail.length - 1; t++) {
                const a = (t / trail.length) * 0.3;
                ctx.strokeStyle = `rgba(255, 255, 255, ${a})`;
                ctx.lineWidth = 1;
                ctx.beginPath();
                ctx.moveTo(trail[t].x, trail[t].y);
                ctx.lineTo(trail[t + 1].x, trail[t + 1].y);
                ctx.stroke();
            }

            // Blip colour by priority
            let color = COLOR_NORMAL;
            if (f.emergency === "MAYDAY") color = COLOR_MAYDAY;
            else if (f.emergency === "PAN_PAN") color = COLOR_PANPAN;

            // Blip
            ctx.fillStyle = color;
            ctx.beginPath();
            ctx.arc(p.x, p.y, i === selectedIndex ? 5.5 : 4, 0, Math.PI * 2);
            ctx.fill();

            // Selection ring
            if (i === selectedIndex) {
                ctx.strokeStyle = COLOR_SELECT;
                ctx.lineWidth = 1.5;
                ctx.beginPath();
                ctx.arc(p.x, p.y, 10, 0, Math.PI * 2);
                ctx.stroke();
            }

            // Data block
            const lx = p.x + 9;
            const ly = p.y - 9;
            ctx.font = "10px 'SF Pro Text', monospace";
            ctx.fillStyle = color;
            ctx.textAlign = "left";
            ctx.fillText(f.callsign, lx, ly);

            ctx.fillStyle = "rgba(255, 255, 255, 0.65)";
            ctx.font = "9px 'SF Pro Text', monospace";
            ctx.fillText(
                `${Math.round(f.fuel_minutes)}F · ${Math.round(nm)}NM`,
                lx,
                ly + 10
            );
        });
    }

    function render() {
        drawBackground();
        drawFixes();
        drawRunways();
        drawFlights();
        drawSweep();

        sweepAngle += 0.022;
        if (sweepAngle > Math.PI * 2) sweepAngle -= Math.PI * 2;

        const deg = Math.round(((sweepAngle * 180) / Math.PI + 90 + 360) % 360);
        const el = document.getElementById("sweep-deg");
        if (el) el.textContent = String(deg).padStart(3, "0") + "°";

        requestAnimationFrame(render);
    }

    // ---------- UI updaters ----------
    function renderStrips() {
        const stack = document.getElementById("flight-strips");
        const count = document.getElementById("strip-count");
        if (!stack) return;

        if (!observation || !observation.flights || observation.flights.length === 0) {
            stack.innerHTML = '<div class="sk-strip-empty">No inbound traffic.</div>';
            if (count) count.textContent = "0 airborne";
            return;
        }
        if (count) count.textContent = `${observation.flights.length} airborne`;

        stack.innerHTML = "";
        observation.flights.forEach((f, i) => {
            const div = document.createElement("div");
            const classes = ["sk-strip"];
            if (f.emergency === "MAYDAY") classes.push("mayday");
            if (f.emergency === "PAN_PAN") classes.push("panpan");
            if (!f.can_land_now) classes.push("blocked");
            if (i === selectedIndex) classes.push("selected");
            div.className = classes.join(" ");

            const fuelClass =
                f.fuel_minutes < 5 ? "critical" :
                f.fuel_minutes < 10 ? "low" : "";

            let tag = "";
            if (f.emergency === "MAYDAY") {
                tag = '<span class="sk-strip-tag sk-strip-tag-mayday">MAYDAY</span>';
            } else if (f.emergency === "PAN_PAN") {
                tag = '<span class="sk-strip-tag sk-strip-tag-panpan">PAN-PAN</span>';
            }
            const medTag = f.medical_onboard
                ? '<span class="sk-strip-tag sk-strip-tag-med">MED</span>'
                : "";

            div.innerHTML = `
                <div class="sk-strip-idx">${i}</div>
                <div>
                    <div class="sk-strip-callsign">${f.callsign} ${tag}${medTag}</div>
                    <div class="sk-strip-sub">
                        ${f.aircraft_type} · ${f.approach_fix || "—"} ·
                        ${Math.round(f.distance_nm)} NM ·
                        ${f.can_land_now ? "clear" : "blocked"}
                    </div>
                </div>
                <div class="sk-strip-right">
                    <div class="sk-strip-fuel ${fuelClass}">${Math.round(f.fuel_minutes)}m</div>
                    <div>pax ${f.passengers}</div>
                </div>
            `;
            div.addEventListener("click", () => selectFlight(i));
            stack.appendChild(div);
        });
    }

    // ---------- Reward signal graph ----------
    function recordReward(step, reward) {
        const prev = rewardHistory.length
            ? rewardHistory[rewardHistory.length - 1].cumulative
            : 0;
        rewardHistory.push({ step, reward, cumulative: prev + reward });
        renderRewardGraph();
    }

    function clearRewardGraph() {
        rewardHistory.length = 0;
        renderRewardGraph();
    }

    /**
     * Build a smooth SVG `d` string from a list of [x,y] points using a
     * Catmull-Rom → cubic Bézier conversion. Gives a silky curve without
     * overshoots, mirroring the reference area-chart aesthetic.
     */
    function smoothPath(points, tension = 0.5) {
        if (points.length === 0) return "";
        if (points.length === 1) {
            return `M ${points[0][0]} ${points[0][1]}`;
        }
        let d = `M ${points[0][0]} ${points[0][1]}`;
        for (let i = 0; i < points.length - 1; i++) {
            const p0 = points[i - 1] || points[i];
            const p1 = points[i];
            const p2 = points[i + 1];
            const p3 = points[i + 2] || p2;
            const c1x = p1[0] + ((p2[0] - p0[0]) * tension) / 6;
            const c1y = p1[1] + ((p2[1] - p0[1]) * tension) / 6;
            const c2x = p2[0] - ((p3[0] - p1[0]) * tension) / 6;
            const c2y = p2[1] - ((p3[1] - p1[1]) * tension) / 6;
            d += ` C ${c1x.toFixed(2)} ${c1y.toFixed(2)}, ${c2x.toFixed(2)} ${c2y.toFixed(2)}, ${p2[0].toFixed(2)} ${p2[1].toFixed(2)}`;
        }
        return d;
    }

    /** Pick "nice" round-number tick marks for a Y range. */
    function niceTicks(minV, maxV, count = 4) {
        const range = Math.max(1e-9, maxV - minV);
        const rawStep = range / count;
        const mag = Math.pow(10, Math.floor(Math.log10(rawStep)));
        const norm = rawStep / mag;
        let step;
        if (norm < 1.5) step = mag;
        else if (norm < 3) step = 2 * mag;
        else if (norm < 7) step = 5 * mag;
        else step = 10 * mag;
        const ticks = [];
        const start = Math.ceil(minV / step) * step;
        for (let v = start; v <= maxV + 1e-9; v += step) ticks.push(v);
        return ticks;
    }

    function renderRewardGraph() {
        const svg = document.getElementById("reward-graph");
        if (!svg) return;

        const W = svg.clientWidth || 760;
        const H = svg.clientHeight || 200;
        const pad = { top: 30, right: 58, bottom: 28, left: 16 };
        const plotW = Math.max(1, W - pad.left - pad.right);
        const plotH = Math.max(1, H - pad.top - pad.bottom);

        if (rewardHistory.length === 0) {
            svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
            svg.innerHTML =
                `<text x="${W / 2}" y="${H / 2}" text-anchor="middle" ` +
                `fill="rgba(0,0,0,0.32)" font-size="13">` +
                `No data yet — load a scenario and play a step</text>`;
            return;
        }

        // Y range covers 0, per-step rewards, and cumulative trace, padded a bit.
        const all = [0];
        rewardHistory.forEach((d) => {
            all.push(d.reward);
            all.push(d.cumulative);
        });
        let minY = Math.min(...all);
        let maxY = Math.max(...all);
        const span = Math.max(1, maxY - minY);
        minY -= span * 0.08;
        maxY += span * 0.12;  // extra headroom for the tooltip pill

        const n = rewardHistory.length;
        const xAt = (i) => pad.left + (n <= 1 ? plotW / 2 : (i * plotW) / (n - 1));
        const yAt = (v) => pad.top + plotH - ((v - minY) / (maxY - minY)) * plotH;

        const zeroY = yAt(0);
        const ticks = niceTicks(minY, maxY, 4);

        const parts = [];

        // -- defs: gradients, drop shadow, clip --
        parts.push(`
<defs>
    <linearGradient id="rewardFillPos" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="#0071e3" stop-opacity="0.42"/>
        <stop offset="55%" stop-color="#0071e3" stop-opacity="0.14"/>
        <stop offset="100%" stop-color="#0071e3" stop-opacity="0"/>
    </linearGradient>
    <linearGradient id="rewardFillNeg" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="#e30000" stop-opacity="0"/>
        <stop offset="100%" stop-color="#e30000" stop-opacity="0.28"/>
    </linearGradient>
    <filter id="rewardTipShadow" x="-40%" y="-40%" width="180%" height="180%">
        <feDropShadow dx="0" dy="2" stdDeviation="3" flood-color="#0071e3" flood-opacity="0.35"/>
    </filter>
    <filter id="rewardLineShadow" x="-10%" y="-10%" width="120%" height="140%">
        <feDropShadow dx="0" dy="1" stdDeviation="1.2" flood-color="#000" flood-opacity="0.18"/>
    </filter>
</defs>`);

        // -- Horizontal grid lines with right-side labels --
        ticks.forEach((t) => {
            const y = yAt(t).toFixed(2);
            parts.push(
                `<line x1="${pad.left}" y1="${y}" x2="${pad.left + plotW}" y2="${y}" ` +
                `stroke="rgba(0,0,0,0.07)" stroke-width="1"/>`
            );
            parts.push(
                `<text x="${pad.left + plotW + 8}" y="${(+y + 4).toFixed(2)}" ` +
                `font-family="SF Pro Text, -apple-system, sans-serif" font-size="11" ` +
                `fill="rgba(0,0,0,0.45)" text-anchor="start">${t.toFixed(0)}</text>`
            );
        });

        // -- Emphasized zero baseline --
        parts.push(
            `<line x1="${pad.left}" y1="${zeroY.toFixed(2)}" x2="${pad.left + plotW}" y2="${zeroY.toFixed(2)}" ` +
            `stroke="rgba(0,0,0,0.22)" stroke-width="1" stroke-dasharray="3,4"/>`
        );

        // -- Per-step reward bars (thin, behind the line) --
        const barW = n <= 1 ? 10 : Math.max(2, (plotW / n) * 0.55);
        rewardHistory.forEach((d, i) => {
            const cx = xAt(i);
            const barTop = Math.min(zeroY, yAt(d.reward));
            const barH = Math.abs(yAt(d.reward) - zeroY);
            const color = d.reward >= 0 ? "#0071e3" : "#e30000";
            parts.push(
                `<rect x="${(cx - barW / 2).toFixed(2)}" y="${barTop.toFixed(2)}" ` +
                `width="${barW.toFixed(2)}" height="${Math.max(1, barH).toFixed(2)}" ` +
                `rx="2" fill="${color}" opacity="0.38"/>`
            );
        });

        // -- Cumulative area (gradient fill) + smooth line --
        const points = rewardHistory.map((d, i) => [xAt(i), yAt(d.cumulative)]);
        const linePath = smoothPath(points, 0.6);

        if (points.length >= 2) {
            const firstX = points[0][0].toFixed(2);
            const lastX = points[points.length - 1][0].toFixed(2);
            const areaPath = `${linePath} L ${lastX} ${zeroY.toFixed(2)} L ${firstX} ${zeroY.toFixed(2)} Z`;
            // Pick fill gradient based on whether the ending sits above or below zero
            const fillId = rewardHistory[n - 1].cumulative >= 0 ? "rewardFillPos" : "rewardFillNeg";
            parts.push(`<path d="${areaPath}" fill="url(#${fillId})"/>`);
        }

        parts.push(
            `<path d="${linePath}" fill="none" stroke="#1d1d1f" stroke-width="2.5" ` +
            `stroke-linecap="round" stroke-linejoin="round" filter="url(#rewardLineShadow)"/>`
        );

        // -- Latest point — white ring with dark core --
        const last = rewardHistory[n - 1];
        const lastPt = points[points.length - 1];
        parts.push(
            `<circle cx="${lastPt[0].toFixed(2)}" cy="${lastPt[1].toFixed(2)}" r="6" ` +
            `fill="#ffffff" stroke="#1d1d1f" stroke-width="2"/>`
        );
        parts.push(
            `<circle cx="${lastPt[0].toFixed(2)}" cy="${lastPt[1].toFixed(2)}" r="2.5" ` +
            `fill="#0071e3"/>`
        );

        // -- Tooltip pill with the cumulative total --
        const tipLabel = `\u03A3 ${last.cumulative >= 0 ? "+" : ""}${last.cumulative.toFixed(1)}`;
        const tipW = Math.max(56, tipLabel.length * 8 + 18);
        const tipH = 26;
        let tipX = lastPt[0] - tipW / 2;
        let tipY = lastPt[1] - tipH - 14;
        // Clamp to plot area
        tipX = Math.max(pad.left, Math.min(pad.left + plotW - tipW, tipX));
        // If clipping above, flip below the point
        if (tipY < 2) tipY = Math.min(pad.top + plotH - tipH - 4, lastPt[1] + 14);

        // Tail anchor (small triangle) pointing from pill toward the point
        const tailBase = Math.max(tipX + 12, Math.min(tipX + tipW - 12, lastPt[0]));
        const tailTipY = lastPt[1] > tipY ? tipY + tipH : tipY;
        const tailDir = lastPt[1] > tipY ? 5 : -5;

        parts.push(`
<g filter="url(#rewardTipShadow)">
    <rect x="${tipX.toFixed(2)}" y="${tipY.toFixed(2)}" width="${tipW}" height="${tipH}" rx="13" ry="13" fill="#0071e3"/>
    <polygon points="${(tailBase - 4).toFixed(2)},${tailTipY.toFixed(2)} ${(tailBase + 4).toFixed(2)},${tailTipY.toFixed(2)} ${tailBase.toFixed(2)},${(tailTipY + tailDir).toFixed(2)}" fill="#0071e3"/>
    <text x="${(tipX + tipW / 2).toFixed(2)}" y="${(tipY + tipH / 2 + 4).toFixed(2)}" ` +
        `text-anchor="middle" font-family="SF Pro Display, -apple-system, sans-serif" ` +
        `font-size="13" font-weight="600" fill="#ffffff">${tipLabel}</text>
</g>`);

        // -- X-axis endpoints --
        parts.push(
            `<text x="${xAt(0).toFixed(2)}" y="${(H - 6).toFixed(2)}" text-anchor="start" ` +
            `font-family="SF Pro Text, -apple-system, sans-serif" font-size="10" ` +
            `fill="rgba(0,0,0,0.45)">step 1</text>`
        );
        if (n > 1) {
            parts.push(
                `<text x="${xAt(n - 1).toFixed(2)}" y="${(H - 6).toFixed(2)}" text-anchor="end" ` +
                `font-family="SF Pro Text, -apple-system, sans-serif" font-size="10" ` +
                `fill="rgba(0,0,0,0.45)">step ${n}</text>`
            );
        }

        svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
        svg.innerHTML = parts.join("");
    }

    window.addEventListener("resize", renderRewardGraph);

    function updateStatus() {
        if (!observation) return;
        const g = (id) => document.getElementById(id);
        const set = (id, v) => { const el = g(id); if (el) el.textContent = v; };

        set("task-name", (observation.task_name || observation.task_id || "—"));
        set("time-step", `${String(observation.time_step).padStart(2, "0")} / ${String(observation.max_time_steps).padStart(2, "0")}`);
        set("vis-value", `${observation.weather.visibility_nm.toFixed(1)} nm`);
        set("wind-value", `${Math.round(observation.weather.wind_knots)} kt`);
        set("mayday-count", observation.flights.filter((f) => f.emergency === "MAYDAY").length);
        set("landed-count", observation.landed_safely);
        set("crashed-count", observation.crashed);
        set("episode-reward", (observation.episode_reward ?? 0).toFixed(1));

        // METAR-style weather line
        const w = observation.weather;
        const visMeters = Math.round(w.visibility_nm * 1852);
        const metar =
            `METAR VABB ${zuluClock().replace(/:/g, "").slice(0, 4)}Z ` +
            `24012KT ${String(visMeters).padStart(4, "0")}M ` +
            `${(w.precipitation || "").toUpperCase()} ` +
            `BKN${Math.round(w.ceiling_feet / 100)} TREND ${(w.trend || "").toUpperCase()}`;
        set("metar-line", metar);
    }

    function selectFlight(i) {
        selectedIndex = i;
        const f = observation && observation.flights[i];
        const el = document.getElementById("selected-flight");
        if (el) el.textContent = f ? f.callsign : "—";
        renderStrips();
    }

    /**
     * Pick the best default selection: highest-priority landable flight,
     * tie-broken by lowest fuel. Falls back to index 0 if nothing can land.
     * Returns null if there are no flights.
     */
    function bestDefaultIndex() {
        if (!observation || !observation.flights || !observation.flights.length) {
            return null;
        }
        const priority = { MAYDAY: 0, PAN_PAN: 1, NONE: 2 };
        const landable = observation.flights
            .map((f, i) => ({ f, i }))
            .filter(({ f }) => f.can_land_now);
        const pool = landable.length ? landable : observation.flights.map((f, i) => ({ f, i }));
        pool.sort((a, b) =>
            (priority[a.f.emergency] - priority[b.f.emergency]) ||
            (a.f.fuel_minutes - b.f.fuel_minutes)
        );
        return pool[0].i;
    }

    function autoSelectBest() {
        const i = bestDefaultIndex();
        if (i === null) {
            selectedIndex = null;
            const el = document.getElementById("selected-flight");
            if (el) el.textContent = "—";
            renderStrips();
        } else {
            selectFlight(i);
        }
    }

    // ---------- Event log ----------
    function logLine(text, cls) {
        const log = document.getElementById("event-log");
        if (!log) return;
        const line = document.createElement("div");
        line.className = "sk-log-line " + (cls ? "sk-log-" + cls : "");
        line.textContent = text;
        log.appendChild(line);
        log.scrollTop = log.scrollHeight;
        while (log.childElementCount > 80) log.removeChild(log.firstChild);
    }

    // ---------- API ----------
    async function api(path, body) {
        const opt = {
            method: body ? "POST" : "GET",
            headers: { "Content-Type": "application/json" },
        };
        if (body) opt.body = JSON.stringify(body);
        const res = await fetch(path, opt);
        if (!res.ok) throw new Error(`${path} → ${res.status}`);
        return res.json();
    }

    async function resetTask(id) {
        // If auto-play is running, stop it first so we don't step on the new episode.
        autoPlaying = false;
        setAutoButton("Auto Triage");
        taskId = id;
        selectedIndex = null;
        trails.clear();
        prevCrashed = 0;
        clearRewardGraph();
        try {
            const data = await api("/reset", { episode_id: id });
            observation = data.observation;
            document.querySelectorAll(".sk-scenario-row").forEach((b) =>
                b.classList.toggle("active", b.dataset.task === id)
            );
            logLine(
                `[SYSTEM] ${observation.task_name} loaded · ${observation.total_flights} inbound`,
                "sys"
            );
            logLine(
                `[TWR] All aircraft on approach, expect vectors for ILS RWY 27. Current vis ${observation.weather.visibility_nm.toFixed(1)} nm.`,
                "tower"
            );
            observation.flights.forEach((f) => {
                if (f.emergency === "MAYDAY") {
                    logLine(
                        `[${f.callsign}] MAYDAY MAYDAY MAYDAY. Fuel critical ${Math.round(f.fuel_minutes)} minutes. Request immediate landing.`,
                        "alert"
                    );
                }
            });
            renderStrips();
            updateStatus();
            autoSelectBest();
        } catch (e) {
            logLine(`[ERROR] ${e.message}`, "crash");
        }
    }

    async function clearToLand() {
        // If nothing is selected, pick the best default so the button "just works".
        if (selectedIndex === null || !observation || !observation.flights[selectedIndex]) {
            const i = bestDefaultIndex();
            if (i === null) {
                logLine("[TWR] No inbound traffic. Load a scenario first.", "sys");
                return;
            }
            selectFlight(i);
        }
        const prev = observation.flights[selectedIndex];
        try {
            const data = await api("/step", { action: { flight_index: selectedIndex } });
            observation = data.observation;

            // Plot the per-step reward on the live graph.
            recordReward(observation.time_step, Number(data.reward) || 0);

            if (data.reward >= 10) {
                logLine(
                    `[TWR] ${prev.callsign}, cleared to land runway 27, wind 240 at 14. Welcome to Mumbai.`,
                    "tower"
                );
                logLine(
                    `[${prev.callsign}] Cleared to land 27, ${prev.callsign}.`,
                    "pilot"
                );
            } else if (data.reward <= -3) {
                logLine(
                    `[TWR] Negative ${prev.callsign}, visibility below your minima. Maintain hold, expect vectors.`,
                    "tower"
                );
            } else if (data.reward < 0) {
                logLine(
                    `[TWR] ${prev.callsign}, runway still occupied. Continue approach.`,
                    "tower"
                );
            }

            if (observation.crashed > prevCrashed) {
                logLine(
                    `[EMRG] Fuel exhaustion event · ${observation.crashed - prevCrashed} aircraft lost`,
                    "crash"
                );
            }
            prevCrashed = observation.crashed;

            renderStrips();
            updateStatus();
            // Auto-advance selection to the next highest-priority flight so
            // the user can keep pressing Clear to Land without re-selecting.
            autoSelectBest();

            if (observation.done) {
                logLine("[SYSTEM] Episode terminated · request grade", "sys");
            }
        } catch (e) {
            logLine(`[ERROR] ${e.message}`, "crash");
        }
    }

    // ---------- Auto triage (play-to-done) ----------
    // autoPlaying is a toggle: first click starts the loop, second click stops it.
    // The loop plays one step, waits AUTO_STEP_DELAY_MS so the user can read the
    // tower voice log line, then plays the next step, until the episode finishes.
    const AUTO_STEP_DELAY_MS = 650;
    let autoPlaying = false;

    function setAutoButton(label) {
        const el = document.getElementById("btn-auto");
        if (el) el.textContent = label;
    }

    function sleep(ms) {
        return new Promise((res) => setTimeout(res, ms));
    }

    /**
     * Run the heuristic loop until the episode terminates. Does NOT grade at
     * the end — callers decide when to fetch the score. Pure play loop.
     */
    async function playAutoLoop() {
        while (
            autoPlaying
            && observation
            && !observation.done
            && observation.flights.length > 0
        ) {
            const i = bestDefaultIndex();
            if (i === null) break;
            selectFlight(i);
            await clearToLand();
            if (!observation.done) {
                await sleep(AUTO_STEP_DELAY_MS);
            }
        }
    }

    async function autoTriage() {
        // Second click → stop the running loop.
        if (autoPlaying) {
            autoPlaying = false;
            return;
        }

        if (!observation || observation.done) {
            logLine("[SYSTEM] Episode already finished. Load a scenario to continue.", "sys");
            return;
        }

        autoPlaying = true;
        setAutoButton("Stop Auto");
        logLine("[SYSTEM] Auto triage engaged — heuristic agent flying the tower.", "sys");

        try {
            await playAutoLoop();
        } finally {
            autoPlaying = false;
            setAutoButton("Auto Triage");
        }

        // Auto-grade at the end so the final score is shown without extra clicks.
        if (observation && observation.done) {
            logLine("[SYSTEM] Episode complete — computing final score.", "sys");
            await fetchAndLogGrade();
        }
    }

    /**
     * Fetch the score from /grade and log it. Does not play any steps —
     * callers should ensure the episode is played before calling if they
     * want a meaningful score.
     */
    async function fetchAndLogGrade() {
        try {
            // /grade is a POST endpoint — pass {} so api() sends POST, not GET.
            const data = await api("/grade", {});
            const el = document.getElementById("score-display");
            if (el) el.textContent = data.score.toFixed(3);

            logLine(
                `[SCORE] ${data.task_id.toUpperCase()} · ${data.score.toFixed(3)} · ` +
                `landed ${data.landing_log.length} · crashed ${data.crash_log.length} · ` +
                `reward ${data.episode_reward.toFixed(1)}`,
                "score"
            );
        } catch (e) {
            logLine(`[ERROR] ${e.message}`, "crash");
        }
    }

    /**
     * Grade Episode button handler.
     *
     * - If no scenario has been loaded: tell the user.
     * - If the episode is fresh (no steps taken yet): auto-play with the
     *   heuristic, then grade. Matches the user's mental model of "click
     *   and see the score".
     * - If the episode has been partially played manually: grade the
     *   current state without continuing auto-play.
     * - If the episode is already done: just grade it.
     */
    async function gradeEpisode() {
        if (!observation) {
            logLine("[SYSTEM] No scenario loaded. Pick one on the left first.", "sys");
            return;
        }

        const fresh = !observation.done && observation.time_step === 0;
        if (fresh) {
            // Episode is un-played — run auto triage to completion first,
            // then fall through to grading.
            if (autoPlaying) {
                // Already running; just wait for it to finish by returning.
                return;
            }
            autoPlaying = true;
            setAutoButton("Stop Auto");
            logLine("[SYSTEM] No steps played yet — running heuristic agent to completion.", "sys");
            try {
                await playAutoLoop();
            } finally {
                autoPlaying = false;
                setAutoButton("Auto Triage");
            }
            if (!observation || !observation.done) {
                // User stopped the loop early — grade the partial state anyway.
                logLine("[SYSTEM] Auto triage stopped before completion.", "sys");
            } else {
                logLine("[SYSTEM] Episode complete — computing final score.", "sys");
            }
        }

        await fetchAndLogGrade();
    }

    // ---------- Wiring ----------
    document.querySelectorAll(".sk-scenario-row").forEach((b) =>
        b.addEventListener("click", () => resetTask(b.dataset.task))
    );
    const clearBtn = document.getElementById("btn-clear-land");
    const autoBtn = document.getElementById("btn-auto");
    const gradeBtn = document.getElementById("btn-grade");
    if (clearBtn) clearBtn.addEventListener("click", clearToLand);
    if (autoBtn) autoBtn.addEventListener("click", autoTriage);
    if (gradeBtn) gradeBtn.addEventListener("click", gradeEpisode);

    // Keyboard shortcuts
    window.addEventListener("keydown", (ev) => {
        if (ev.target.tagName === "INPUT" || ev.target.tagName === "TEXTAREA") return;
        if (ev.key === " " || ev.key === "Enter") {
            ev.preventDefault();
            clearToLand();
        } else if (ev.key.toLowerCase() === "a") {
            autoTriage();
        } else if (ev.key === "1") resetTask("easy");
        else if (ev.key === "2") resetTask("medium");
        else if (ev.key === "3") resetTask("hard");
        else if (ev.key === "4") resetTask("extra_hard");
        else if (ev.key === "ArrowDown" && observation && observation.flights.length) {
            selectFlight(((selectedIndex ?? -1) + 1) % observation.flights.length);
        } else if (ev.key === "ArrowUp" && observation && observation.flights.length) {
            const len = observation.flights.length;
            selectFlight(((selectedIndex ?? 0) - 1 + len) % len);
        }
    });

    // Kick off render loop and paint the empty reward graph.
    requestAnimationFrame(render);
    renderRewardGraph();
    logLine("[SYSTEM] SUPERCELL tower online. Press 1, 2, or 3 to load a scenario.", "sys");
})();
