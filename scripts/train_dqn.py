#!/usr/bin/env python3
"""
PyTorch DQN agent for SUPERCELL ATC Emergency Triage.

Trains directly against ATCEnvironment (no HTTP overhead).
Demonstrates that SUPERCELL is useful for RL research.

Usage:
    uv run python scripts/train_dqn.py              # train easy + hard
    uv run python scripts/train_dqn.py --task easy  # single task
    uv run python scripts/train_dqn.py --episodes 3000
"""
from __future__ import annotations

import argparse
import collections
import os
import random
import sys
from typing import NamedTuple

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim

# ── Path setup ──────────────────────────────────────────────────────────────
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_root, "apps", "api"))

from models import ATCAction
from server.atc_environment import ATCEnvironment

# ── Hyperparameters ──────────────────────────────────────────────────────────
MAX_FLIGHTS    = 20       # padded action/state slots
FLIGHT_FEATS   = 8        # features per flight slot
WEATHER_FEATS  = 5
GLOBAL_FEATS   = 5
STATE_DIM      = MAX_FLIGHTS * FLIGHT_FEATS + WEATHER_FEATS + GLOBAL_FEATS  # 170
ACTION_DIM     = MAX_FLIGHTS

BUFFER_SIZE    = 20_000
BATCH_SIZE     = 64
GAMMA          = 0.99
LR             = 1e-3
EPS_START      = 1.0
EPS_END        = 0.05
EPS_DECAY_EPS  = 1_500   # episodes to decay over
TARGET_UPDATE  = 200     # hard update every N episodes
WARMUP_EPS     = 200     # collect experience before training


# ── Network ──────────────────────────────────────────────────────────────────
class QNetwork(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(STATE_DIM, 256),
            nn.ReLU(),
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Linear(128, ACTION_DIM),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


# ── Replay buffer ────────────────────────────────────────────────────────────
class Transition(NamedTuple):
    state: np.ndarray
    action: int
    reward: float
    next_state: np.ndarray
    done: bool
    mask: np.ndarray        # bool[ACTION_DIM] — valid actions in state
    next_mask: np.ndarray   # bool[ACTION_DIM] — valid actions in next_state


class ReplayBuffer:
    def __init__(self, capacity: int) -> None:
        self._buf: collections.deque[Transition] = collections.deque(maxlen=capacity)

    def push(self, *args) -> None:
        self._buf.append(Transition(*args))

    def sample(self, n: int) -> list[Transition]:
        return random.sample(self._buf, n)

    def __len__(self) -> int:
        return len(self._buf)


# ── Observation → state vector ───────────────────────────────────────────────
_EMERGENCY = {"NONE": 0, "PAN_PAN": 1, "MAYDAY": 2}
_PRECIP    = {"none": 0.0, "rain": 0.33, "snow": 0.67, "thunderstorm": 1.0}
_TREND     = {"deteriorating": 0.0, "stable": 0.5, "improving": 1.0}
_WAKE      = {"LIGHT": 0.25, "MEDIUM": 0.5, "HEAVY": 0.75, "SUPER": 1.0}


def obs_to_tensor(obs) -> tuple[np.ndarray, np.ndarray]:
    """Convert ATCObservation to (state_vec float32[170], valid_mask bool[20])."""
    flights = obs.flights
    weather = obs.weather

    flight_vec = np.zeros(MAX_FLIGHTS * FLIGHT_FEATS, dtype=np.float32)
    mask       = np.zeros(ACTION_DIM, dtype=bool)

    for i, f in enumerate(flights[:MAX_FLIGHTS]):
        b = i * FLIGHT_FEATS
        flight_vec[b]     = _EMERGENCY.get(f.emergency, 0) / 2.0
        flight_vec[b + 1] = min(f.fuel_minutes, 60.0) / 60.0
        flight_vec[b + 2] = min(f.passengers, 500) / 500.0
        flight_vec[b + 3] = float(f.medical_onboard)
        flight_vec[b + 4] = float(f.can_land_now)
        flight_vec[b + 5] = f.min_visibility_nm / 10.0
        flight_vec[b + 6] = _WAKE.get(f.wake_category, 0.5)
        flight_vec[b + 7] = 1.0  # slot occupied
        if f.can_land_now:
            mask[i] = True

    total = max(obs.total_flights, 1)
    state = np.concatenate([
        flight_vec,
        np.array([
            weather.visibility_nm / 10.0,
            weather.wind_knots / 30.0,
            weather.crosswind_knots / 20.0,
            _PRECIP.get(weather.precipitation, 0.0),
            _TREND.get(weather.trend, 0.5),
        ], dtype=np.float32),
        np.array([
            obs.runway_free_in_steps / 5.0,
            obs.time_step / max(obs.max_time_steps, 1),
            obs.landed_safely / total,
            obs.crashed / total,
            len(flights) / total,
        ], dtype=np.float32),
    ])
    return state, mask


# ── Action selection ─────────────────────────────────────────────────────────
def select_action(
    q_net: QNetwork,
    state: np.ndarray,
    mask: np.ndarray,
    epsilon: float,
    device: torch.device,
) -> int:
    valid = np.where(mask)[0]
    if len(valid) == 0:
        return 0  # forced invalid — env will penalise

    if random.random() < epsilon:
        return int(random.choice(valid))

    with torch.no_grad():
        q = q_net(torch.FloatTensor(state).unsqueeze(0).to(device)).squeeze(0).cpu().numpy()
    q[~mask] = -1e9
    return int(np.argmax(q))


# ── Training update ───────────────────────────────────────────────────────────
def update(
    q_net: QNetwork,
    target_net: QNetwork,
    optimizer: optim.Optimizer,
    buffer: ReplayBuffer,
    device: torch.device,
) -> float:
    if len(buffer) < BATCH_SIZE:
        return 0.0

    batch = buffer.sample(BATCH_SIZE)
    states      = torch.FloatTensor(np.stack([t.state      for t in batch])).to(device)
    actions     = torch.LongTensor( [t.action               for t in batch]).to(device)
    rewards     = torch.FloatTensor([t.reward               for t in batch]).to(device)
    next_states = torch.FloatTensor(np.stack([t.next_state for t in batch])).to(device)
    dones       = torch.FloatTensor([float(t.done)          for t in batch]).to(device)
    next_masks  = np.stack([t.next_mask for t in batch])

    # Current Q-values
    q_values = q_net(states).gather(1, actions.unsqueeze(1)).squeeze(1)

    # Target Q-values (masked double-DQN style)
    with torch.no_grad():
        next_q_online = q_net(next_states).cpu().numpy()
        next_q_online[~next_masks] = -1e9
        best_actions = torch.LongTensor(np.argmax(next_q_online, axis=1)).to(device)
        next_q_target = target_net(next_states).gather(1, best_actions.unsqueeze(1)).squeeze(1)
        targets = rewards + GAMMA * next_q_target * (1.0 - dones)

    loss = nn.MSELoss()(q_values, targets)
    optimizer.zero_grad()
    loss.backward()
    nn.utils.clip_grad_norm_(q_net.parameters(), 1.0)
    optimizer.step()
    return loss.item()


# ── Episode runner ────────────────────────────────────────────────────────────
def run_episode(
    env: ATCEnvironment,
    task_id: str,
    q_net: QNetwork,
    buffer: ReplayBuffer,
    epsilon: float,
    device: torch.device,
    train: bool = True,
    optimizer: optim.Optimizer | None = None,
    target_net: QNetwork | None = None,
) -> tuple[float, float, int, int]:
    """Run one episode. Returns (episode_reward, grade_score, landed, crashed)."""
    obs = env.reset(episode_id=task_id)
    state, mask = obs_to_tensor(obs)
    total_reward = 0.0
    steps = 0

    while not obs.done:
        action = select_action(q_net, state, mask, epsilon, device)
        obs = env.step(ATCAction(flight_index=action))
        next_state, next_mask = obs_to_tensor(obs)
        reward = obs.reward or 0.0
        total_reward += reward

        if train:
            buffer.push(state, action, reward, next_state, obs.done, mask, next_mask)
            update(q_net, target_net, optimizer, buffer, device)

        state, mask = next_state, next_mask
        steps += 1
        if steps > 200:  # safety cap
            break

    score = env.grade()
    st = env.state
    return total_reward, score, st.landed_safely, st.crashed


# ── Main training loop ────────────────────────────────────────────────────────
def train_task(
    task_id: str,
    num_episodes: int,
    device: torch.device,
    save_dir: str,
) -> float:
    print(f"\n{'═'*60}")
    print(f"  Training on task: {task_id.upper()}  ({num_episodes} episodes)")
    print(f"{'═'*60}")
    print(f"  {'Ep':>6}  {'ε':>5}  {'Score':>7}  {'Landed':>7}  {'Crashed':>8}  {'100-ep avg':>10}")
    print(f"  {'-'*6}  {'-'*5}  {'-'*7}  {'-'*7}  {'-'*8}  {'-'*10}")

    env        = ATCEnvironment()
    q_net      = QNetwork().to(device)
    target_net = QNetwork().to(device)
    target_net.load_state_dict(q_net.state_dict())
    optimizer  = optim.Adam(q_net.parameters(), lr=LR)
    buffer     = ReplayBuffer(BUFFER_SIZE)

    recent_scores: collections.deque[float] = collections.deque(maxlen=100)

    for ep in range(1, num_episodes + 1):
        eps = max(EPS_END, EPS_START - (EPS_START - EPS_END) * ep / EPS_DECAY_EPS)
        _, score, landed, crashed = run_episode(
            env, task_id, q_net, buffer, eps, device,
            train=(ep > WARMUP_EPS),
            optimizer=optimizer,
            target_net=target_net,
        )
        recent_scores.append(score)

        if ep % TARGET_UPDATE == 0:
            target_net.load_state_dict(q_net.state_dict())

        if ep % 100 == 0:
            avg = sum(recent_scores) / len(recent_scores)
            print(f"  {ep:>6}  {eps:>5.3f}  {score:>7.4f}  {landed:>7}  {crashed:>8}  {avg:>10.4f}")

    # Final evaluation (greedy, no exploration)
    scores = []
    for _ in range(10):
        _, score, _, _ = run_episode(
            env, task_id, q_net, buffer, 0.0, device, train=False,
        )
        scores.append(score)
    final = sum(scores) / len(scores)
    print(f"\n  Final greedy score (avg 10 runs): {final:.4f}")

    # Save checkpoint
    os.makedirs(save_dir, exist_ok=True)
    path = os.path.join(save_dir, f"dqn_{task_id}.pt")
    torch.save({"q_net": q_net.state_dict(), "task_id": task_id, "final_score": final}, path)
    print(f"  Checkpoint saved → {path}")

    return final


def main() -> None:
    parser = argparse.ArgumentParser(description="Train DQN agent on SUPERCELL")
    parser.add_argument("--task",     default="all",  help="easy | medium | hard | all")
    parser.add_argument("--episodes", type=int, default=2000, help="episodes per task")
    parser.add_argument("--save-dir", default="models", help="checkpoint directory")
    args = parser.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"  Device: {device}")

    tasks = ["easy", "medium", "hard"] if args.task == "all" else [args.task]

    results: dict[str, float] = {}
    for task_id in tasks:
        score = train_task(task_id, args.episodes, device, args.save_dir)
        results[task_id] = score

    print(f"\n{'═'*60}")
    print("  TRAINING SUMMARY")
    print(f"{'═'*60}")
    print(f"  {'Task':<10} {'DQN Score':>10}")
    print(f"  {'-'*10} {'-'*10}")
    for tid, score in results.items():
        print(f"  {tid:<10} {score:>10.4f}")
    print()


if __name__ == "__main__":
    main()
