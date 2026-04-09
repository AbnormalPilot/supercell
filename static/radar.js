/**
 * CSIA Mumbai ATC Radar Simulation
 * Animated radar with flight tracking and API integration
 */

// Global state
let currentState = null;
let radarAngle = 0;
let flights = [];
let animationId = null;
let sweepSpeed = 2; // degrees per frame

// DOM Elements
const canvas = document.getElementById('radar-canvas');
const ctx = canvas.getContext('2d');
const sweepDegEl = document.getElementById('sweep-deg');
const taskNameEl = document.getElementById('task-name');
const timeStepEl = document.getElementById('time-step');
const weatherStatusEl = document.getElementById('weather-status');
const maydayCountEl = document.getElementById('mayday-count');
const flightStripsEl = document.getElementById('flight-strips');
const metarEl = document.getElementById('metar-display');
const scoreEl = document.getElementById('score-display');
const eventLogEl = document.getElementById('event-log');

// API Client
const API_BASE = '';

async function apiPost(endpoint, payload = {}) {
    const response = await fetch(`${API_BASE}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });
    return response.json();
}

async function apiGet(endpoint) {
    const response = await fetch(`${API_BASE}${endpoint}`);
    return response.json();
}

// Initialize
function init() {
    resizeCanvas();
    window.addEventListener('resize', resizeCanvas);
    startRadarAnimation();
    log('System initialized. Select a scenario to begin.', 'system');
}

function resizeCanvas() {
    const container = canvas.parentElement;
    const size = Math.min(container.clientWidth - 40, container.clientHeight - 100, 600);
    canvas.width = size;
    canvas.height = size;
}

// Radar Animation
function startRadarAnimation() {
    function animate() {
        drawRadar();
        radarAngle = (radarAngle + sweepSpeed) % 360;
        sweepDegEl.textContent = `${Math.floor(radarAngle)}°`;
        animationId = requestAnimationFrame(animate);
    }
    animate();
}

function drawRadar() {
    const centerX = canvas.width / 2;
    const centerY = canvas.height / 2;
    const radius = Math.min(centerX, centerY) - 20;
    
    // Clear canvas
    ctx.fillStyle = '#0a0a0f';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    
    // Draw grid circles
    ctx.strokeStyle = 'rgba(0, 255, 65, 0.2)';
    ctx.lineWidth = 1;
    
    for (let i = 1; i <= 4; i++) {
        ctx.beginPath();
        ctx.arc(centerX, centerY, radius * i / 4, 0, Math.PI * 2);
        ctx.stroke();
    }
    
    // Draw crosshairs
    ctx.beginPath();
    ctx.moveTo(centerX - radius, centerY);
    ctx.lineTo(centerX + radius, centerY);
    ctx.moveTo(centerX, centerY - radius);
    ctx.lineTo(centerX, centerY + radius);
    ctx.stroke();
    
    // Draw angle markers
    ctx.fillStyle = 'rgba(0, 255, 65, 0.5)';
    ctx.font = '10px monospace';
    ctx.textAlign = 'center';
    
    const angles = [0, 45, 90, 135, 180, 225, 270, 315];
    angles.forEach(deg => {
        const rad = (deg - 90) * Math.PI / 180;
        const x = centerX + (radius + 15) * Math.cos(rad);
        const y = centerY + (radius + 15) * Math.sin(rad);
        ctx.fillText(deg.toString().padStart(3, '0'), x, y + 3);
    });
    
    // Draw range rings labels
    ctx.fillStyle = 'rgba(0, 255, 65, 0.4)';
    [10, 20, 30, 40].forEach((range, i) => {
        const y = centerY - radius * (i + 1) / 4;
        ctx.fillText(`${range}nm`, centerX + 5, y - 2);
    });
    
    // Draw flights
    if (currentState && currentState.observation) {
        drawFlights(centerX, centerY, radius);
    }
    
    // Draw radar sweep
    const sweepRad = (radarAngle - 90) * Math.PI / 180;
    const grad = ctx.createRadialGradient(centerX, centerY, 0, centerX, centerY, radius);
    grad.addColorStop(0, 'rgba(0, 255, 65, 0)');
    grad.addColorStop(0.8, 'rgba(0, 255, 65, 0.1)');
    grad.addColorStop(1, 'rgba(0, 255, 65, 0.3)');
    
    ctx.save();
    ctx.translate(centerX, centerY);
    ctx.rotate(sweepRad);
    ctx.beginPath();
    ctx.moveTo(0, 0);
    ctx.arc(0, 0, radius, -0.3, 0.3);
    ctx.closePath();
    ctx.fillStyle = grad;
    ctx.fill();
    ctx.restore();
    
    // Draw center dot
    ctx.beginPath();
    ctx.arc(centerX, centerY, 3, 0, Math.PI * 2);
    ctx.fillStyle = '#00ff41';
    ctx.fill();
}

function drawFlights(centerX, centerY, radius) {
    const flights = currentState.observation.flights || [];
    const weather = currentState.observation.weather || {};
    
    flights.forEach((flight, idx) => {
        // Calculate position based on distance and bearing
        const distance = flight.distance_nm || 20;
        const bearing = (idx * 137.5) % 360; // Golden angle distribution
        const rad = (bearing - 90) * Math.PI / 180;
        const r = (distance / 40) * radius;
        
        const x = centerX + r * Math.cos(rad);
        const y = centerY + r * Math.sin(rad);
        
        // Determine color based on emergency
        let color = '#00ff41';
        let size = 6;
        let pulse = false;
        
        if (flight.emergency === 'MAYDAY') {
            color = '#ff3333';
            size = 10;
            pulse = true;
        } else if (flight.emergency === 'PAN_PAN') {
            color = '#ffbf00';
            size = 8;
        }
        
        // Draw blip
        ctx.beginPath();
        ctx.arc(x, y, size, 0, Math.PI * 2);
        ctx.fillStyle = color;
        ctx.fill();
        
        // Pulse effect for emergencies
        if (pulse) {
            const pulseSize = size + Math.sin(Date.now() / 200) * 4;
            ctx.beginPath();
            ctx.arc(x, y, Math.abs(pulseSize), 0, Math.PI * 2);
            ctx.strokeStyle = `rgba(255, 51, 51, ${0.5 + Math.sin(Date.now() / 200) * 0.3})`;
            ctx.lineWidth = 2;
            ctx.stroke();
        }
        
        // Draw callsign
        ctx.fillStyle = color;
        ctx.font = '11px monospace';
        ctx.textAlign = 'left';
        ctx.fillText(flight.callsign, x + 10, y + 3);
        
        // Draw fuel indicator if low
        if (flight.fuel_minutes < 10) {
            ctx.fillStyle = '#ff3333';
            ctx.fillText(`⚡${flight.fuel_minutes.toFixed(0)}`, x + 10, y + 15);
        }
    });
}

// Actions
async function resetTask(taskId) {
    try {
        log(`Initializing ${taskId} scenario...`, 'system');
        const result = await apiPost('/reset', { episode_id: taskId });
        currentState = result;
        updateUI();
        log(`Scenario loaded: ${result.observation.task_name}`, 'system');
    } catch (err) {
        log(`Error: ${err.message}`, 'crash');
    }
}

async function landFlight() {
    if (!currentState) {
        log('No active scenario. Select a task first.', 'system');
        return;
    }
    
    const index = parseInt(document.getElementById('flight-index').value) || 0;
    
    try {
        const result = await apiPost('/step', { action: { flight_index: index } });
        currentState = result;
        
        const reward = result.reward || 0;
        const flight = result.observation.flights[index];
        const callsign = flight ? flight.callsign : 'unknown';
        
        if (reward > 0) {
            log(`✓ Flight ${callsign} cleared to land`, 'land');
        } else {
            log(`✗ Cannot land flight ${callsign} (weather/runway)`, 'crash');
        }
        
        updateUI();
        
        if (result.done) {
            log('Episode complete!', 'system');
            await gradeEpisode();
        }
    } catch (err) {
        log(`Error: ${err.message}`, 'crash');
    }
}

async function autoLand() {
    if (!currentState) {
        log('No active scenario. Select a task first.', 'system');
        return;
    }
    
    log('Auto-triage initiated...', 'system');
    
    const flights = currentState.observation.flights || [];
    if (flights.length === 0) {
        log('No active flights', 'system');
        return;
    }
    
    // Priority: MAYDAY > PAN-PAN > medical > low fuel
    const priority = { 'MAYDAY': 0, 'PAN_PAN': 1, 'NONE': 2 };
    const sorted = flights.map((f, i) => ({ ...f, originalIndex: i }))
        .sort((a, b) => {
            const pDiff = priority[a.emergency] - priority[b.emergency];
            if (pDiff !== 0) return pDiff;
            return a.fuel_minutes - b.fuel_minutes;
        });
    
    const nextFlight = sorted[0];
    document.getElementById('flight-index').value = nextFlight.originalIndex;
    
    log(`Auto-selected: ${nextFlight.callsign} (${nextFlight.emergency}, ${nextFlight.fuel_minutes.toFixed(0)}min fuel)`, 'system');
    await landFlight();
}

async function gradeEpisode() {
    if (!currentState) {
        log('No active scenario', 'system');
        return;
    }
    
    try {
        const result = await apiPost('/grade');
        const score = result.score || 0;
        scoreEl.textContent = score.toFixed(3);
        
        if (score >= 0.7) {
            scoreEl.style.color = '#00ff41';
            log(`Excellent! Score: ${score.toFixed(3)}`, 'land');
        } else if (score >= 0.4) {
            scoreEl.style.color = '#ffbf00';
            log(`Pass. Score: ${score.toFixed(3)}`, 'weather');
        } else {
            scoreEl.style.color = '#ff3333';
            log(`Fail. Score: ${score.toFixed(3)}`, 'crash');
        }
    } catch (err) {
        log(`Grading error: ${err.message}`, 'crash');
    }
}

// UI Updates
function updateUI() {
    if (!currentState || !currentState.observation) return;
    
    const obs = currentState.observation;
    
    // Header
    taskNameEl.textContent = obs.task_id.toUpperCase();
    timeStepEl.textContent = `${obs.time_step}/${obs.max_time_steps}`;
    
    // Weather
    const w = obs.weather;
    weatherStatusEl.textContent = `${w.visibility_nm.toFixed(1)}nm ${w.precipitation}`;
    
    // MAYDAY count
    const maydays = (obs.flights || []).filter(f => f.emergency === 'MAYDAY').length;
    maydayCountEl.textContent = maydays;
    
    // METAR
    const metar = formatMETAR(w, obs.time_step);
    metarEl.textContent = metar;
    
    // Flight strips
    updateFlightStrips(obs.flights || []);
}

function formatMETAR(weather, time) {
    const day = String(Math.floor(time / 24) + 1).padStart(2, '0');
    const hour = String(time % 24).padStart(2, '0');
    const vis = Math.round(weather.visibility_nm * 1609.34 / 100); // nm to hundreds of meters
    const wind = Math.round(weather.wind_knots);
    
    return `VABB ${day}${hour}00Z ${wind}KT ${vis}00M ${weather.precipitation.toUpperCase()} ${weather.trend.toUpperCase()}`;
}

function updateFlightStrips(flights) {
    if (flights.length === 0) {
        flightStripsEl.innerHTML = '<div class="strip-placeholder">No active flights</div>';
        return;
    }
    
    flightStripsEl.innerHTML = flights.map((f, i) => {
        const emergencyClass = f.emergency.toLowerCase().replace('_', '-');
        const canLandClass = f.can_land_now ? '' : 'cant-land';
        const medical = f.medical_onboard ? '<span class="strip-medical">🏥</span>' : '';
        
        return `
            <div class="flight-strip ${emergencyClass} ${canLandClass}">
                <span class="strip-index">${i}</span>
                <span class="strip-callsign">${f.callsign}</span>
                <span class="strip-type">${f.aircraft_type.substring(0, 6)}</span>
                <span class="strip-emergency">${f.emergency}</span>
                <span class="strip-fuel">${f.fuel_minutes.toFixed(0)}m</span>
                <span class="strip-pax">${f.passengers}</span>
                ${medical}
            </div>
        `;
    }).join('');
}

function log(message, type = 'system') {
    const entry = document.createElement('div');
    entry.className = `log-entry ${type}`;
    entry.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;
    eventLogEl.appendChild(entry);
    eventLogEl.scrollTop = eventLogEl.scrollHeight;
}

// Keyboard shortcuts
document.addEventListener('keydown', (e) => {
    if (e.target.tagName === 'INPUT') return;
    
    switch(e.key) {
        case '1': resetTask('easy'); break;
        case '2': resetTask('medium'); break;
        case '3': resetTask('hard'); break;
        case '4': resetTask('extra_hard'); break;
        case ' ': landFlight(); break;
        case 'a': autoLand(); break;
    }
});

// Initialize
init();
