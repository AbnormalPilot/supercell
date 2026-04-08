#!/usr/bin/env python3
"""Generate a visually rich project deck PDF for ATC-Triage-v1."""

import os
import sys
import math

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np
from fpdf import FPDF

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

FIG_DIR = os.path.join(os.path.dirname(__file__), "figures")
os.makedirs(FIG_DIR, exist_ok=True)

# Color palette (ATC dark theme)
C_BG = "#0a0e14"
C_PANEL = "#111822"
C_GREEN = "#00ff41"
C_AMBER = "#ffbf00"
C_RED = "#ff3333"
C_CYAN = "#00e5ff"
C_TEXT = "#8899aa"
C_BRIGHT = "#e0e8f0"
C_BORDER = "#1e2a3a"

# Lighter palette for PDF readability
P_BG = "#0d1117"
P_GREEN = "#3fb950"
P_AMBER = "#d29922"
P_RED = "#f85149"
P_CYAN = "#58a6ff"
P_PURPLE = "#bc8cff"
P_TEXT = "#c9d1d9"
P_MUTED = "#8b949e"
P_BRIGHT = "#e6edf3"


def _save(fig, name):
    path = os.path.join(FIG_DIR, name)
    fig.savefig(path, dpi=200, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    return path


# =========================================================================
# Figure 1: System Architecture
# =========================================================================
def fig_architecture():
    fig, ax = plt.subplots(1, 1, figsize=(14, 7), facecolor=P_BG)
    ax.set_facecolor(P_BG)
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 7)
    ax.axis("off")

    def box(x, y, w, h, label, color, sub=""):
        rect = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.15",
                              facecolor=color + "22", edgecolor=color, linewidth=2)
        ax.add_patch(rect)
        ax.text(x + w/2, y + h/2 + (0.15 if sub else 0),
                label, ha="center", va="center", fontsize=11,
                fontweight="bold", color=color, family="monospace")
        if sub:
            ax.text(x + w/2, y + h/2 - 0.25, sub, ha="center", va="center",
                    fontsize=7, color=P_MUTED, family="monospace")

    def arrow(x1, y1, x2, y2, label="", color=P_MUTED):
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle="->", color=color, lw=1.5))
        if label:
            mx, my = (x1+x2)/2, (y1+y2)/2
            ax.text(mx, my + 0.15, label, ha="center", va="bottom",
                    fontsize=7, color=color, family="monospace")

    # Title
    ax.text(7, 6.7, "ATC-TRIAGE-v1  SYSTEM ARCHITECTURE", ha="center", va="center",
            fontsize=14, fontweight="bold", color=P_CYAN, family="monospace")

    # Agent (left)
    box(0.3, 2.5, 2.4, 1.5, "LLM Agent", P_PURPLE, "OpenAI API / GPT-4o")

    # FastAPI Server (center)
    box(4.2, 4.5, 3, 1.2, "FastAPI Server", P_CYAN, "/reset /step /state /grade")
    box(4.2, 2.5, 3, 1.5, "ATCEnvironment", P_GREEN, "Simulation Core")
    box(4.2, 0.5, 1.3, 1.5, "Tasks", P_AMBER, "easy/med/hard")
    box(5.9, 0.5, 1.3, 1.5, "Graders", P_RED, "0.0 - 1.0")

    # Models (right-center)
    box(8.5, 2.5, 2.4, 1.5, "Pydantic Models", P_CYAN, "Action / Obs / State")

    # Dashboard (right)
    box(11.5, 2.5, 2.2, 1.5, "Next.js Dashboard", P_GREEN, "Radar + Controls")

    # Docker (bottom)
    box(8.5, 0.5, 5.2, 1.2, "Docker Compose", P_MUTED, "API :8000  |  Web :3000  |  Hot Reload")

    # Arrows
    arrow(2.7, 3.25, 4.2, 3.25, "action JSON", P_PURPLE)
    arrow(4.2, 3.6, 2.7, 3.6, "observation", P_GREEN)
    arrow(5.7, 4.5, 5.7, 4.0, "HTTP", P_CYAN)
    arrow(5.0, 2.5, 5.0, 2.0, "scenario", P_AMBER)
    arrow(6.2, 2.5, 6.2, 2.0, "score", P_RED)
    arrow(7.2, 3.25, 8.5, 3.25, "typed models", P_CYAN)
    arrow(10.9, 3.25, 11.5, 3.25, "fetch API", P_GREEN)

    return _save(fig, "architecture.png")


# =========================================================================
# Figure 2: RL Loop
# =========================================================================
def fig_rl_loop():
    fig, ax = plt.subplots(1, 1, figsize=(10, 6), facecolor=P_BG)
    ax.set_facecolor(P_BG)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6)
    ax.axis("off")

    ax.text(5, 5.6, "OPENENV  INTERACTION  LOOP", ha="center",
            fontsize=14, fontweight="bold", color=P_CYAN, family="monospace")

    # Boxes
    boxes = [
        (0.5, 3.5, 2.0, 1.2, "reset(task_id)", P_GREEN),
        (3.5, 3.5, 3.0, 1.2, "Observe\nflights + weather", P_CYAN),
        (3.5, 1.2, 3.0, 1.2, "Agent Decides\nflight_index", P_PURPLE),
        (7.5, 1.2, 2.0, 1.2, "step(action)", P_AMBER),
        (7.5, 3.5, 2.0, 1.2, "Reward\n+ new obs", P_GREEN),
    ]
    for x, y, w, h, label, color in boxes:
        rect = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.12",
                              facecolor=color + "15", edgecolor=color, linewidth=2)
        ax.add_patch(rect)
        ax.text(x + w/2, y + h/2, label, ha="center", va="center",
                fontsize=10, fontweight="bold", color=color, family="monospace")

    # Arrows
    def arr(x1, y1, x2, y2, color=P_MUTED):
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle="-|>", color=color, lw=2))

    arr(2.5, 4.1, 3.5, 4.1, P_GREEN)
    arr(5.0, 3.5, 5.0, 2.4, P_CYAN)
    arr(6.5, 1.8, 7.5, 1.8, P_PURPLE)
    arr(8.5, 2.4, 8.5, 3.5, P_AMBER)
    arr(7.5, 4.1, 6.5, 4.1, P_GREEN)

    # Done check
    ax.text(5, 0.4, "Episode ends when: all landed | crash | max steps",
            ha="center", fontsize=9, color=P_RED, family="monospace",
            bbox=dict(boxstyle="round,pad=0.3", facecolor=P_RED + "15", edgecolor=P_RED))

    return _save(fig, "rl_loop.png")


# =========================================================================
# Figure 3: Task Difficulty Comparison
# =========================================================================
def fig_tasks():
    fig, axes = plt.subplots(1, 3, figsize=(14, 5), facecolor=P_BG)

    tasks = [
        ("EASY", 4, 15, 1, 1, 0, "Clear Skies", P_GREEN),
        ("MEDIUM", 7, 30, 1, 2, 5, "Storm Window", P_AMBER),
        ("HARD", 12, 50, 3, 2, 8, "Mass Diversion", P_RED),
    ]

    for ax, (name, flights, steps, maydays, panpans, fuel_crit, subtitle, color) in zip(axes, tasks):
        ax.set_facecolor(P_BG)
        ax.set_xlim(0, 10)
        ax.set_ylim(0, 10)
        ax.axis("off")

        # Title
        ax.text(5, 9.5, name, ha="center", fontsize=16, fontweight="bold",
                color=color, family="monospace")
        ax.text(5, 8.8, subtitle, ha="center", fontsize=10, color=P_MUTED, family="monospace")

        # Stats
        stats = [
            (f"{flights}", "Flights", 2),
            (f"{steps}", "Max Steps", 5),
            (f"{maydays}", "MAYDAYs", 8),
        ]
        for x, (val, label, xpos) in enumerate(stats):
            ax.text(xpos, 7.2, val, ha="center", fontsize=22, fontweight="bold",
                    color=color, family="monospace")
            ax.text(xpos, 6.5, label, ha="center", fontsize=8, color=P_MUTED, family="monospace")

        # Flight icons (circles)
        for i in range(flights):
            row = i // 4
            col = i % 4
            cx = 1.5 + col * 2.0
            cy = 4.5 - row * 1.5
            c = P_RED if i < maydays else P_AMBER if i < maydays + panpans else (
                "#ff6644" if i < maydays + panpans + fuel_crit else P_GREEN)
            circle = plt.Circle((cx, cy), 0.4, facecolor=c + "30", edgecolor=c, linewidth=1.5)
            ax.add_patch(circle)
            ax.text(cx, cy, "F", ha="center", va="center", fontsize=8,
                    color=c, fontweight="bold", family="monospace")

        # Legend
        ax.text(5, 0.8, f"PAN-PANs: {panpans}  |  Fuel-Critical: {fuel_crit}",
                ha="center", fontsize=8, color=P_MUTED, family="monospace")

        # Weather indicator
        wx = "CLEAR" if name == "EASY" else "STORM" if name == "MEDIUM" else "OSCILLATING"
        wc = P_GREEN if name == "EASY" else P_AMBER if name == "MEDIUM" else P_RED
        ax.text(5, 0.2, f"Weather: {wx}", ha="center", fontsize=8,
                color=wc, family="monospace")

    fig.suptitle("TASK  DIFFICULTY  PROGRESSION", fontsize=14, fontweight="bold",
                 color=P_CYAN, family="monospace", y=0.98)
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    return _save(fig, "tasks.png")


# =========================================================================
# Figure 4: Reward Structure
# =========================================================================
def fig_rewards():
    fig, ax = plt.subplots(1, 1, figsize=(12, 6), facecolor=P_BG)
    ax.set_facecolor(P_BG)

    categories = ["Safe\nLanding", "MAYDAY\nBonus", "PAN_PAN\nBonus", "Medical\nBonus",
                  "Near-Crash\nSave", "Completion\nBonus", "Holding\nCost", "Invalid\nAction",
                  "Weather\nReject", "Fuel\nCrash"]
    values = [10, 25, 12, 10, 15, 50, -0.5, -5, -3, -100]
    colors = [P_GREEN, P_RED, P_AMBER, P_CYAN, P_AMBER, P_GREEN, P_MUTED, P_RED, P_AMBER, P_RED]

    bars = ax.bar(range(len(categories)), values, color=[c + "80" for c in colors],
                  edgecolor=colors, linewidth=1.5)

    ax.set_xticks(range(len(categories)))
    ax.set_xticklabels(categories, fontsize=8, color=P_TEXT, family="monospace")
    ax.set_ylabel("Reward", fontsize=10, color=P_TEXT, family="monospace")
    ax.tick_params(colors=P_MUTED)
    ax.spines[:].set_color(P_MUTED)
    ax.spines[:].set_linewidth(0.5)
    ax.axhline(y=0, color=P_MUTED, linewidth=0.5)
    ax.set_facecolor(P_BG)

    for bar, val in zip(bars, values):
        ypos = bar.get_height() + (2 if val > 0 else -6)
        ax.text(bar.get_x() + bar.get_width() / 2, ypos,
                f"{val:+.1f}" if isinstance(val, float) else f"{val:+d}",
                ha="center", fontsize=9, fontweight="bold",
                color=P_BRIGHT, family="monospace")

    ax.set_title("REWARD  STRUCTURE  —  DENSE  SIGNAL  EVERY  STEP",
                 fontsize=13, fontweight="bold", color=P_CYAN, family="monospace", pad=15)

    fig.tight_layout()
    return _save(fig, "rewards.png")


# =========================================================================
# Figure 5: Weather Timeline
# =========================================================================
def fig_weather():
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5), facecolor=P_BG)

    # Medium timeline
    steps_m = [0, 6, 10, 14, 20]
    vis_m = [8.0, 5.0, 3.0, 1.5, 1.0]
    ax1.set_facecolor(P_BG)
    ax1.fill_between(steps_m, vis_m, alpha=0.15, color=P_AMBER)
    ax1.plot(steps_m, vis_m, color=P_AMBER, linewidth=2.5, marker="o", markersize=6)
    ax1.axhline(y=3.0, color=P_RED, linewidth=1, linestyle="--", alpha=0.5)
    ax1.text(1, 3.2, "CAT-II minimum (3nm)", fontsize=7, color=P_RED, family="monospace")
    ax1.axhline(y=1.5, color=P_RED, linewidth=1, linestyle="--", alpha=0.5)
    ax1.text(1, 1.7, "CAT-III minimum (1.5nm)", fontsize=7, color=P_RED, family="monospace")
    ax1.set_title("MEDIUM: Storm Window", fontsize=11, fontweight="bold",
                  color=P_AMBER, family="monospace")
    ax1.set_xlabel("Time Step", fontsize=9, color=P_MUTED, family="monospace")
    ax1.set_ylabel("Visibility (nm)", fontsize=9, color=P_MUTED, family="monospace")
    ax1.tick_params(colors=P_MUTED)
    ax1.spines[:].set_color(P_MUTED)
    ax1.spines[:].set_linewidth(0.5)

    # Hard timeline
    steps_h = [0, 6, 10, 16, 20, 26, 34, 40]
    vis_h = [6.0, 3.0, 1.0, 3.5, 5.0, 1.5, 4.0, 6.0]
    ax2.set_facecolor(P_BG)
    ax2.fill_between(steps_h, vis_h, alpha=0.15, color=P_RED)
    ax2.plot(steps_h, vis_h, color=P_RED, linewidth=2.5, marker="o", markersize=6)
    ax2.axhline(y=3.0, color=P_AMBER, linewidth=1, linestyle="--", alpha=0.5)
    ax2.text(1, 3.2, "VFR minimum (3nm)", fontsize=7, color=P_AMBER, family="monospace")
    # Highlight windows
    for start, end in [(0, 6), (16, 26), (34, 40)]:
        ax2.axvspan(start, end, alpha=0.05, color=P_GREEN)
    ax2.text(2, 5.5, "window", fontsize=7, color=P_GREEN, family="monospace", ha="center")
    ax2.text(21, 4.7, "window", fontsize=7, color=P_GREEN, family="monospace", ha="center")
    ax2.text(37, 5.7, "window", fontsize=7, color=P_GREEN, family="monospace", ha="center")
    ax2.set_title("HARD: Oscillating Crisis", fontsize=11, fontweight="bold",
                  color=P_RED, family="monospace")
    ax2.set_xlabel("Time Step", fontsize=9, color=P_MUTED, family="monospace")
    ax2.set_ylabel("Visibility (nm)", fontsize=9, color=P_MUTED, family="monospace")
    ax2.tick_params(colors=P_MUTED)
    ax2.spines[:].set_color(P_MUTED)
    ax2.spines[:].set_linewidth(0.5)

    fig.suptitle("WEATHER  TIMELINES", fontsize=14, fontweight="bold",
                 color=P_CYAN, family="monospace", y=0.98)
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    return _save(fig, "weather.png")


# =========================================================================
# Figure 6: Grading Breakdown
# =========================================================================
def fig_grading():
    fig, axes = plt.subplots(1, 3, figsize=(14, 5), facecolor=P_BG)

    data = [
        ("EASY", {"Safety": 40, "Priority": 40, "Efficiency": 20},
         [P_GREEN, P_CYAN, P_PURPLE]),
        ("MEDIUM", {"Safety": 30, "Priority": 25, "Medical": 15, "Fuel Mgmt": 15, "Efficiency": 15},
         [P_GREEN, P_CYAN, "#58a6ff", P_AMBER, P_PURPLE]),
        ("HARD", {"Safety": 30, "Priority": 20, "Medical": 10, "Fuel Mgmt": 20, "Efficiency": 10, "Bonus": 10},
         [P_GREEN, P_CYAN, "#58a6ff", P_AMBER, P_PURPLE, "#f0883e"]),
    ]

    for ax, (title, weights, colors) in zip(axes, data):
        ax.set_facecolor(P_BG)
        wedges, texts, autotexts = ax.pie(
            weights.values(),
            labels=weights.keys(),
            colors=[c + "cc" for c in colors],
            autopct="%1.0f%%",
            startangle=90,
            textprops={"fontsize": 8, "color": P_TEXT, "family": "monospace"},
            wedgeprops={"linewidth": 1.5, "edgecolor": P_BG},
        )
        for at in autotexts:
            at.set_fontsize(8)
            at.set_fontweight("bold")
            at.set_color(P_BRIGHT)
        ax.set_title(title, fontsize=12, fontweight="bold",
                     color=P_CYAN, family="monospace", pad=10)

    fig.suptitle("GRADING  WEIGHT  BREAKDOWN", fontsize=14, fontweight="bold",
                 color=P_CYAN, family="monospace", y=0.98)
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    return _save(fig, "grading.png")


# =========================================================================
# Figure 7: Tech Stack
# =========================================================================
def fig_techstack():
    fig, ax = plt.subplots(1, 1, figsize=(12, 5), facecolor=P_BG)
    ax.set_facecolor(P_BG)
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 5)
    ax.axis("off")

    ax.text(6, 4.7, "TECH  STACK", ha="center", fontsize=14,
            fontweight="bold", color=P_CYAN, family="monospace")

    layers = [
        (0.5, 3.2, 5, 1.0, "Backend", [
            ("Python 3.12", P_GREEN), ("FastAPI", P_CYAN),
            ("Pydantic v2", P_AMBER), ("uvicorn", P_MUTED),
        ]),
        (6.5, 3.2, 5, 1.0, "Frontend", [
            ("Next.js 15", P_GREEN), ("React 19", P_CYAN),
            ("Tailwind v4", P_AMBER), ("TypeScript", P_PURPLE),
        ]),
        (0.5, 1.5, 5, 1.0, "Tooling", [
            ("uv", P_GREEN), ("pnpm", P_CYAN),
            ("Turborepo", P_AMBER), ("Docker", P_PURPLE),
        ]),
        (6.5, 1.5, 5, 1.0, "Deployment", [
            ("HF Spaces", P_GREEN), ("Docker Compose", P_CYAN),
            ("OpenEnv", P_AMBER), ("OpenAI SDK", P_PURPLE),
        ]),
    ]

    for x, y, w, h, title, items in layers:
        rect = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.1",
                              facecolor=P_BG, edgecolor=P_MUTED + "60", linewidth=1)
        ax.add_patch(rect)
        ax.text(x + 0.3, y + h - 0.25, title, fontsize=9, fontweight="bold",
                color=P_MUTED, family="monospace")
        for i, (name, color) in enumerate(items):
            tx = x + 0.5 + i * (w - 0.6) / len(items)
            ax.text(tx, y + 0.3, name, fontsize=9, fontweight="bold",
                    color=color, family="monospace")

    return _save(fig, "techstack.png")


# =========================================================================
# Figure 8: Simulation Snapshot
# =========================================================================
def fig_simulation():
    fig, ax = plt.subplots(1, 1, figsize=(10, 10), facecolor="#060a10")
    ax.set_facecolor("#060a10")
    ax.set_xlim(-1.2, 1.2)
    ax.set_ylim(-1.2, 1.2)
    ax.set_aspect("equal")
    ax.axis("off")

    # Radar rings
    for r in [0.25, 0.5, 0.75, 1.0]:
        circle = plt.Circle((0, 0), r, fill=False, edgecolor="#0d2218", linewidth=0.5)
        ax.add_patch(circle)

    # Cross hairs
    ax.plot([-1, 1], [0, 0], color="#0d2218", linewidth=0.5)
    ax.plot([0, 0], [-1, 1], color="#0d2218", linewidth=0.5)

    # Runway
    ax.plot([-0.05, 0.05], [-0.02, -0.02], color=C_GREEN, linewidth=3)
    ax.text(0, -0.07, "RWY 28L", ha="center", fontsize=7, color=C_GREEN, family="monospace")

    # Range labels
    for r, nm in [(0.25, "10nm"), (0.5, "20nm"), (0.75, "30nm")]:
        ax.text(0.02, r + 0.02, nm, fontsize=6, color="#1a4030", family="monospace")

    # Flights
    flights = [
        (0.3, 0.4, "DAL892", "MAYDAY", C_RED, 4.0),
        (-0.5, 0.2, "AAL217", "PAN-PAN", C_AMBER, 30.0),
        (0.6, -0.3, "UAL441", "", C_GREEN, 45.0),
        (-0.3, -0.5, "SWA103", "", C_GREEN, 50.0),
        (0.1, 0.7, "BAW119", "MAYDAY", C_RED, 6.0),
        (-0.7, 0.6, "DLH401", "", C_AMBER, 35.0),
        (0.8, 0.5, "UAE205", "", C_GREEN, 55.0),
    ]

    for x, y, cs, emg, color, fuel in flights:
        size = 8 if emg else 5
        ax.plot(x, y, "o", color=color, markersize=size, markeredgecolor=color,
                markerfacecolor=color + "80")
        ax.text(x + 0.06, y + 0.04, cs, fontsize=7, color=color, family="monospace",
                fontweight="bold")
        ax.text(x + 0.06, y - 0.03, f"{fuel}m{'  '+emg if emg else ''}",
                fontsize=5, color=color, family="monospace", alpha=0.7)

    # Title
    ax.text(0, 1.12, "APPROACH  RADAR  —  SIMULATION  SNAPSHOT", ha="center",
            fontsize=11, fontweight="bold", color=C_CYAN, family="monospace")

    return _save(fig, "simulation.png")


# =========================================================================
# Figure 9: Scoring Example
# =========================================================================
def fig_scoring_example():
    fig, ax = plt.subplots(1, 1, figsize=(12, 5), facecolor=P_BG)
    ax.set_facecolor(P_BG)

    strategies = ["Urgency\n(Optimal)", "First-In\n(Naive)", "Last-In\n(Worst)"]
    easy_scores = [1.0, 0.86, 0.70]
    medium_scores = [0.90, 0.63, 0.52]
    hard_scores = [0.68, 0.42, 0.30]

    x = np.arange(len(strategies))
    w = 0.25

    bars1 = ax.bar(x - w, easy_scores, w, label="Easy", color=P_GREEN + "80",
                   edgecolor=P_GREEN, linewidth=1.5)
    bars2 = ax.bar(x, medium_scores, w, label="Medium", color=P_AMBER + "80",
                   edgecolor=P_AMBER, linewidth=1.5)
    bars3 = ax.bar(x + w, hard_scores, w, label="Hard", color=P_RED + "80",
                   edgecolor=P_RED, linewidth=1.5)

    for bars in [bars1, bars2, bars3]:
        for bar in bars:
            h = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2, h + 0.02,
                    f"{h:.2f}", ha="center", fontsize=8, fontweight="bold",
                    color=P_BRIGHT, family="monospace")

    ax.set_xticks(x)
    ax.set_xticklabels(strategies, fontsize=10, color=P_TEXT, family="monospace")
    ax.set_ylabel("Score (0.0 - 1.0)", fontsize=10, color=P_TEXT, family="monospace")
    ax.set_ylim(0, 1.15)
    ax.legend(fontsize=9, facecolor=P_BG, edgecolor=P_MUTED, labelcolor=P_TEXT)
    ax.tick_params(colors=P_MUTED)
    ax.spines[:].set_color(P_MUTED)
    ax.spines[:].set_linewidth(0.5)
    ax.set_title("STRATEGY  COMPARISON  —  SCORE  BY  TASK  &  APPROACH",
                 fontsize=13, fontweight="bold", color=P_CYAN, family="monospace", pad=15)

    fig.tight_layout()
    return _save(fig, "scoring_example.png")


# =========================================================================
# PDF Composition
# =========================================================================
class ATCDeck(FPDF):
    def header(self):
        if self.page_no() > 1:
            self.set_font("Courier", "B", 8)
            self.set_text_color(136, 153, 170)
            self.cell(0, 5, "ATC-TRIAGE-v1  |  OpenEnv Hackathon", align="R")
            self.ln(8)

    def footer(self):
        self.set_y(-15)
        self.set_font("Courier", "", 8)
        self.set_text_color(136, 153, 170)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")

    def dark_page(self):
        self.set_fill_color(13, 17, 23)
        self.rect(0, 0, 210, 297, "F")

    def section_title(self, title, y=25):
        self.set_y(y)
        self.set_font("Courier", "B", 18)
        self.set_text_color(88, 166, 255)
        self.cell(0, 10, title, align="C")
        self.ln(12)

    def body_text(self, text, size=10):
        self.set_font("Courier", "", size)
        self.set_text_color(201, 209, 217)
        self.multi_cell(0, 5, text)
        self.ln(3)

    def bullet(self, text, color=(63, 185, 80)):
        self.set_font("Courier", "B", 10)
        self.set_text_color(*color)
        self.cell(8, 5, ">")
        self.set_font("Courier", "", 10)
        self.set_text_color(201, 209, 217)
        self.multi_cell(0, 5, text)
        self.ln(1)


def build_pdf():
    figures = {
        "arch": fig_architecture(),
        "loop": fig_rl_loop(),
        "tasks": fig_tasks(),
        "rewards": fig_rewards(),
        "weather": fig_weather(),
        "grading": fig_grading(),
        "tech": fig_techstack(),
        "sim": fig_simulation(),
        "scoring": fig_scoring_example(),
    }

    pdf = ATCDeck()
    pdf.alias_nb_pages()

    # ---- Page 1: Title ----
    pdf.add_page()
    pdf.dark_page()
    pdf.set_y(80)
    pdf.set_font("Courier", "B", 32)
    pdf.set_text_color(0, 229, 255)
    pdf.cell(0, 15, "ATC-TRIAGE-v1", align="C")
    pdf.ln(18)
    pdf.set_font("Courier", "", 14)
    pdf.set_text_color(201, 209, 217)
    pdf.cell(0, 8, "Air Traffic Control Emergency Prioritization", align="C")
    pdf.ln(8)
    pdf.cell(0, 8, "OpenEnv-Compliant RL Environment", align="C")
    pdf.ln(25)
    pdf.set_font("Courier", "", 10)
    pdf.set_text_color(136, 153, 170)
    pdf.cell(0, 6, "An AI agent manages landing order for incoming flights", align="C")
    pdf.ln(6)
    pdf.cell(0, 6, "under fuel, weather, and emergency constraints.", align="C")
    pdf.ln(20)
    pdf.set_font("Courier", "B", 10)
    pdf.set_text_color(88, 166, 255)
    pdf.cell(0, 6, "Python  |  FastAPI  |  Next.js  |  Turborepo  |  Docker", align="C")

    # ---- Page 2: Problem ----
    pdf.add_page()
    pdf.dark_page()
    pdf.section_title("THE PROBLEM")
    pdf.set_x(20)
    pdf.body_text(
        "Air traffic controllers make life-or-death triage decisions every day.\n"
        "Which flight lands first when three are declaring emergencies, two are\n"
        "running out of fuel, and a thunderstorm is closing in?\n\n"
        "This environment models that exact problem as a sequential decision\n"
        "task for AI agents, with realistic flight parameters, weather dynamics,\n"
        "and wake-turbulence separation rules."
    )
    pdf.ln(5)
    pdf.set_x(20)
    pdf.bullet("MAYDAY declarations = immediate danger, land ASAP", (248, 81, 73))
    pdf.set_x(20)
    pdf.bullet("Fuel exhaustion = aircraft crashes (catastrophic failure)", (248, 81, 73))
    pdf.set_x(20)
    pdf.bullet("Weather deterioration = some aircraft can't land", (210, 153, 34))
    pdf.set_x(20)
    pdf.bullet("Wake turbulence = enforced separation between landings", (88, 166, 255))
    pdf.set_x(20)
    pdf.bullet("Medical emergencies = humanitarian urgency", (0, 229, 255))
    pdf.ln(5)
    pdf.image(figures["sim"], x=30, w=150)

    # ---- Page 3: Architecture ----
    pdf.add_page()
    pdf.dark_page()
    pdf.section_title("SYSTEM ARCHITECTURE")
    pdf.image(figures["arch"], x=5, w=200)
    pdf.ln(5)
    pdf.set_x(20)
    pdf.body_text(
        "The system follows a client-server architecture. The FastAPI server\n"
        "hosts the ATCEnvironment which simulates the ATC scenario. The LLM\n"
        "agent connects via HTTP, observes flight data, and decides landing\n"
        "order. The Next.js dashboard provides real-time visualization."
    )

    # ---- Page 4: RL Loop ----
    pdf.add_page()
    pdf.dark_page()
    pdf.section_title("OPENENV INTERACTION LOOP")
    pdf.image(figures["loop"], x=15, w=180)
    pdf.ln(5)
    pdf.set_x(20)
    pdf.body_text(
        "The agent follows the standard OpenEnv protocol:\n\n"
        "1. reset(task_id) -> initial observation with all flights\n"
        "2. Agent analyzes flights, weather, fuel states\n"
        "3. Agent selects flight_index to clear for landing\n"
        "4. step(action) -> new observation + reward + done flag\n"
        "5. Repeat until all flights handled or episode timeout\n"
        "6. grade() -> final score in [0.0, 1.0]"
    )

    # ---- Page 5: Tasks ----
    pdf.add_page()
    pdf.dark_page()
    pdf.section_title("TASK DIFFICULTY PROGRESSION")
    pdf.image(figures["tasks"], x=5, w=200)
    pdf.ln(5)
    pdf.set_x(20)
    pdf.body_text(
        "Three scenarios with escalating complexity:\n\n"
        "EASY:   4 flights, clear weather, 1 obvious MAYDAY priority\n"
        "MEDIUM: 7 flights, deteriorating storm, competing priorities\n"
        "HARD:   12 flights, oscillating weather, cascading failures"
    )

    # ---- Page 6: Weather ----
    pdf.add_page()
    pdf.dark_page()
    pdf.section_title("WEATHER DYNAMICS")
    pdf.image(figures["weather"], x=5, w=200)
    pdf.ln(5)
    pdf.set_x(20)
    pdf.body_text(
        "Weather creates strategic depth:\n\n"
        "- Medium: Visibility drops steadily. Land weather-sensitive\n"
        "  aircraft (A340, A380, CRJ) before the window closes.\n\n"
        "- Hard: Weather oscillates. Brief clear windows open and\n"
        "  close. VFR aircraft need 3nm+ visibility. Agent must\n"
        "  time landings to exploit weather gaps."
    )

    # ---- Page 7: Rewards ----
    pdf.add_page()
    pdf.dark_page()
    pdf.section_title("REWARD STRUCTURE")
    pdf.image(figures["rewards"], x=5, w=200)
    pdf.ln(5)
    pdf.set_x(20)
    pdf.body_text(
        "Dense reward signal at every step (not sparse end-of-episode):\n\n"
        "- Positive rewards scaled by emergency level + passengers\n"
        "- Crash penalty (-100) dominates to enforce safety-first\n"
        "- Holding cost creates time pressure (-0.5/flight/step)\n"
        "- Completion bonus (+50) rewards zero-crash episodes"
    )

    # ---- Page 8: Grading ----
    pdf.add_page()
    pdf.dark_page()
    pdf.section_title("GRADING BREAKDOWN")
    pdf.image(figures["grading"], x=5, w=200)
    pdf.ln(5)
    pdf.set_x(20)
    pdf.body_text(
        "Each task has a different grading weight distribution:\n\n"
        "- Safety: proportion of flights landed (vs crashed)\n"
        "- Priority: did MAYDAYs land before PAN_PANs before normals?\n"
        "- Medical: were medical passengers in the first half?\n"
        "- Fuel Mgmt: any near-misses or unnecessarily low fuel?\n"
        "- Efficiency: steps used vs optimal\n"
        "- Bonus (hard only): +10% for perfect zero-crash run"
    )

    # ---- Page 9: Scoring ----
    pdf.add_page()
    pdf.dark_page()
    pdf.section_title("BASELINE SCORES")
    pdf.image(figures["scoring"], x=5, w=200)
    pdf.ln(5)
    pdf.set_x(20)
    pdf.body_text(
        "Strategy comparison shows clear difficulty progression:\n\n"
        "- Urgency-first (optimal heuristic): 1.00 / 0.90 / 0.68\n"
        "- First-in-line (naive): 0.86 / 0.63 / 0.42\n"
        "- Last-in-line (worst): 0.70 / 0.52 / 0.30\n\n"
        "The hard task genuinely challenges even smart strategies,\n"
        "with cascading crashes from fuel exhaustion."
    )

    # ---- Page 10: Tech Stack ----
    pdf.add_page()
    pdf.dark_page()
    pdf.section_title("TECH STACK")
    pdf.image(figures["tech"], x=5, w=200)
    pdf.ln(15)
    pdf.set_x(20)
    pdf.set_font("Courier", "B", 11)
    pdf.set_text_color(0, 229, 255)
    pdf.cell(0, 8, "Quick Start", align="L")
    pdf.ln(10)
    pdf.set_x(20)
    pdf.body_text(
        "  uv sync && uv run python -m server.app\n"
        "  pnpm install && pnpm dev:web\n"
        "  docker compose up\n\n"
        "  # Run inference\n"
        "  OPENAI_API_KEY=sk-... uv run python inference.py"
    )

    # Save
    out = os.path.join(os.path.dirname(__file__), "atc_triage_v1_deck.pdf")
    pdf.output(out)
    print(f"PDF saved to: {out}")
    return out


if __name__ == "__main__":
    build_pdf()
