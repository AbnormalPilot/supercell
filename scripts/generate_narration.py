#!/usr/bin/env python3
"""Generate TTS narration audio for Remotion videos using edge-tts (open source, no API key)."""

import asyncio
import os

import edge_tts

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "apps", "video", "public", "audio")
os.makedirs(OUT_DIR, exist_ok=True)

# Voice: en-US-GuyNeural is a clear male voice; en-US-AriaNeural for female
VOICE = "en-US-GuyNeural"
RATE = "-5%"  # Slightly slower for clarity

# ── Explainer video scenes ──────────────────────────────────────────────
EXPLAINER_SCENES = [
    (
        "explainer_01_title",
        "ATC Triage version one. "
        "An air traffic control emergency prioritization environment. "
        "Built as an OpenEnv compliant reinforcement learning environment.",
    ),
    (
        "explainer_02_problem",
        "Air traffic controllers make life or death triage decisions every day. "
        "Three flights declaring emergencies. Two running out of fuel. "
        "A thunderstorm closing in. Which one lands first? "
        "This environment models that exact problem for AI agents, "
        "with realistic fuel burn, weather dynamics, and wake turbulence separation.",
    ),
    (
        "explainer_03_architecture",
        "The system architecture follows a client server pattern. "
        "An LLM agent connects to a FastAPI server over HTTP. "
        "The server runs the ATC Environment, which simulates the full scenario. "
        "Tasks define the flight configurations. Graders score performance from zero to one. "
        "Pydantic models enforce typed actions and observations on the wire. "
        "A Next.js dashboard provides real time radar visualization.",
    ),
    (
        "explainer_04_loop",
        "The interaction loop follows the OpenEnv protocol. "
        "First, reset with a task ID to initialize the scenario. "
        "The agent observes all pending flights, their fuel, emergencies, and the current weather. "
        "It decides which flight to clear for landing by selecting a flight index. "
        "The environment executes the landing, burns fuel for waiting flights, updates weather, "
        "and returns a reward plus the new observation. "
        "This repeats until all flights are handled or the episode times out.",
    ),
    (
        "explainer_05_tasks",
        "Three tasks with escalating difficulty. "
        "Easy: four flights under clear skies. One obvious MAYDAY fuel emergency. "
        "Medium: seven flights with a storm approaching. Visibility drops from eight nautical miles to one. "
        "Hard: twelve aircraft diverted from a closed hub. Three MAYDAYs, oscillating weather, "
        "and cascading fuel failures. Even smart strategies cause crashes on the hard task.",
    ),
    (
        "explainer_06_scoring",
        "Baseline scoring across three strategies. "
        "The urgency first heuristic scores one point oh on easy, point nine on medium, and point six eight on hard. "
        "A naive first in line strategy scores progressively worse. "
        "And a worst case last in line strategy drops to point three on hard. "
        "This demonstrates genuine difficulty progression that challenges frontier models.",
    ),
    (
        "explainer_07_outro",
        "ATC Triage version one. "
        "Two hundred thirteen tests passing. Three task levels. Seven API endpoints. "
        "Full OpenEnv compliance. Built with Python, FastAPI, Next.js, and Docker. "
        "Ready for the hackathon.",
    ),
]

# ── Simulation video scenes ─────────────────────────────────────────────
SIMULATION_SCENES = [
    (
        "simulation_01_intro",
        "Live simulation. Easy task. Clear skies priority. Four inbound flights.",
    ),
    (
        "simulation_02_decision1",
        "First decision. Clearing Delta eight nine two. "
        "MAYDAY fuel emergency with only four minutes of fuel remaining. "
        "This flight must land immediately or it will crash.",
    ),
    (
        "simulation_03_decision2",
        "Second decision. Clearing American two one seven. "
        "Pan pan with medical passenger on board. Urgent but not immediately life threatening.",
    ),
    (
        "simulation_04_decision3",
        "Third. Clearing United four four one. Normal priority. Forty one minutes of fuel. Safe margin.",
    ),
    (
        "simulation_05_decision4",
        "Final approach. Clearing Southwest one oh three. Last flight. Episode almost complete.",
    ),
    (
        "simulation_06_score",
        "Episode complete. Score: one hundred percent. "
        "All four flights landed safely. Zero crashes. Optimal triage sequence achieved.",
    ),
]


async def generate_audio(name: str, text: str):
    """Generate a single audio file."""
    out_path = os.path.join(OUT_DIR, f"{name}.mp3")
    if os.path.exists(out_path):
        print(f"  [skip] {name}.mp3 (exists)")
        return

    comm = edge_tts.Communicate(text, VOICE, rate=RATE)
    await comm.save(out_path)
    size = os.path.getsize(out_path)
    print(f"  [done] {name}.mp3 ({size // 1024}KB)")


async def main():
    print("Generating explainer narration...")
    for name, text in EXPLAINER_SCENES:
        await generate_audio(name, text)

    print("\nGenerating simulation narration...")
    for name, text in SIMULATION_SCENES:
        await generate_audio(name, text)

    print(f"\nAll audio saved to: {OUT_DIR}")
    print(f"Files: {len(os.listdir(OUT_DIR))}")


if __name__ == "__main__":
    asyncio.run(main())
