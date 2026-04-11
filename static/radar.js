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
        taskId = id;
        selectedIndex = null;
        trails.clear();
        prevCrashed = 0;
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

    async function autoTriage() {
        if (!observation || observation.done) return;
        const landable = observation.flights
            .map((f, i) => ({ f, i }))
            .filter(({ f }) => f.can_land_now);
        if (!landable.length) {
            selectFlight(0);
            await clearToLand();
            return;
        }
        const priority = { MAYDAY: 0, PAN_PAN: 1, NONE: 2 };
        landable.sort((a, b) =>
            (priority[a.f.emergency] - priority[b.f.emergency]) ||
            (a.f.fuel_minutes - b.f.fuel_minutes)
        );
        selectFlight(landable[0].i);
        await clearToLand();
    }

    async function gradeEpisode() {
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

    // Kick off render loop
    requestAnimationFrame(render);
    logLine("[SYSTEM] SUPERCELL tower online. Press 1, 2, or 3 to load a scenario.", "sys");
})();
