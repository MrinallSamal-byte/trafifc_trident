# 🚦 Traffic-Mind: AI-Powered Traffic Light Controller

## 🏆 Built for Trident Academy Hackathon

---

### The Problem

Traffic lights today are **timer-based**. They cycle on fixed intervals regardless of actual traffic conditions, causing unnecessary congestion at intersections. During peak hours, some directions pile up with dozens of waiting cars while the light stays green for an empty road.

### Our Solution

**Traffic-Mind** is an AI Agent that **controls traffic lights in real-time** based on vehicle density, using **Deep Q-Network (DQN) Reinforcement Learning**. It doesn't just predict traffic — it actively **fixes** it.

The AI observes queue lengths, average wait times, and vehicle counts in all four directions, then decides which direction should get the green light to maximise throughput and minimise congestion.

---

## ✨ Key Features

| Feature | Description |
|---------|-------------|
| 🎮 **Real-time Simulation** | Beautiful PyGame traffic sim with cars, lights, and a dark-themed UI |
| 🤖 **DQN Reinforcement Learning** | Deep Q-Network agent trained to minimise wait times |
| 📊 **Live Dashboard** | Real-time stats overlay: throughput, queue bars, CO₂ emissions, FPS |
| 🚑 **Emergency Green Corridor** | Auto-detects emergency vehicles and forces green light priority |
| 🌿 **CO₂ Eco Impact Monitoring** | Real-time CO₂ emission tracking for idle and moving vehicles |
| 🛡️ **Runtime Fail-safe** | DQN automatically falls back to timer mode on AI errors |
| 🔧 **Arduino Hardware** | Physical LED traffic lights + IR sensors via serial communication |
| 📈 **3-Way Comparison** | Side-by-side: Timer vs Rule-Based vs AI with improvement percentages |
| 🏆 **One-Click Demo** | `python demo.py` runs a scripted 3-act presentation |

---

## 🛠️ Tech Stack

- **Language**: Python 3.10+
- **Simulation**: PyGame 2.5+
- **AI Engine**: PyTorch 2.0+ (DQN)
- **Hardware**: Arduino UNO (C++), 12 LEDs, 4 IR Sensors
- **Analytics**: NumPy, Matplotlib

---

## 🚀 Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Train the AI (optional but recommended)

```bash
python train.py --episodes 500
```

A training curve chart is saved to `models/training_curve.png`.

### 3. Run the simulation

```bash
python main.py
```

### 4. Hackathon demo (one click!)

```bash
python demo.py
```

---

## 🎮 Controls

| Key | Action |
|-----|--------|
| `1` | Switch to **Timer** mode (dumb baseline) |
| `2` | Switch to **Smart** mode (rule-based) |
| `3` | Switch to **AI** mode (DQN — requires trained model) |
| `+` / `-` | Increase / decrease traffic density |
| `R` | Reset simulation |
| `H` | Toggle Arduino hardware sync |
| `Esc` | Quit |

---

## 📂 Project Structure

```
traffic-mind/
├── config/settings.py          # All constants & hyperparameters
├── simulation/
│   ├── road_network.py         # Lane, Road, Intersection geometry
│   ├── vehicle.py              # Vehicle physics, rendering, spawner
│   ├── traffic_light.py        # Light state machine & base controller
│   └── environment.py          # Gym-compatible training environment
├── controllers/
│   ├── timer_controller.py     # Fixed-timer baseline
│   ├── rule_based_controller.py # Density-aware switching
│   └── dqn_controller.py       # RL agent controller
├── ai/
│   ├── dqn_network.py          # Neural network architecture
│   ├── replay_buffer.py        # Experience replay memory
│   └── trainer.py              # Training loop with logging
├── hardware/
│   ├── arduino_bridge.py       # Python ↔ Arduino serial bridge
│   └── traffic_light.ino       # Arduino LED + sensor code
├── visualization/
│   ├── renderer.py             # PyGame rendering engine
│   └── dashboard.py            # Live metrics tracker
├── analytics/metrics.py        # Performance metrics & comparisons
├── main.py                     # Interactive simulation
├── train.py                    # DQN training script
└── demo.py                     # Hackathon demo (3 acts)
```

---

## 📊 Results

| Metric | Timer | AI (DQN) | Improvement |
|--------|-------|----------|-------------|
| Throughput | ~12/min | ~22/min | **+83%** |
| Avg Wait | ~34 frames | ~8 frames | **-76%** |
| Max Wait | ~89 frames | ~15 frames | **-83%** |

> *Results measured on heavy-traffic scenario (spawn rate = 0.08)*

---

## 🔧 Arduino Wiring

```
North Light: Pin 2 (R), 3 (Y), 4 (G)
South Light: Pin 5 (R), 6 (Y), 7 (G)
East Light:  Pin 8 (R), 9 (Y), 10 (G)
West Light:  Pin 11 (R), 12 (Y), 13 (G)
IR Sensors:  A0 (N), A1 (S), A2 (E), A3 (W)
```

---

## 👥 Team

- Built with ❤️ for Trident Academy Hackathon

---

## 📜 License

MIT License — feel free to use, modify, and present.
