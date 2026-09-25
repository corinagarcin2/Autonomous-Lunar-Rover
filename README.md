# Autonomous Lunar Excavation Rover Simulator

A Python-based autonomous rover simulation that navigates procedurally
generated lunar environments using A* path planning, detects hazards,
excavates regolith, transports material, and autonomously constructs a berm.

# Demo


## Key Features

- 🧭 A* autonomous path planning
- 🌑 Procedurally generated lunar terrain
- 🪨 Randomized rocks and craters
- 📡 Simulated hazard detection
- 🔄 Dynamic route generation and replanning
- ⛏️ Autonomous regolith excavation
- 🚜 Regolith transportation
- 🏗️ Berm construction
- 🗺️ Real-time navigation minimap
- 📊 Mission telemetry dashboard

# How It Works

Each mission generates a new lunar environment with randomized hazards.
The rover evaluates the terrain and uses A* to calculate a collision-free
route to its target.

The autonomous mission cycle is:

Navigate → Excavate → Transport → Dump → Return → Repeat

Because the environment changes between missions, the rover must calculate
a new navigation path rather than following a predetermined route.

# Technologies

Python • Pygame • A* Search • Procedural Generation •
Finite State Machines • Autonomous Navigation

## Controls

W / S — Drive forward/reverse  
A / D — Steer  
M — Toggle autonomous/manual mode  
R — Generate new mission  
SPACE — Collector control

## Run Locally

Install dependencies: pip install -r requirements.txt

Run:python main.py
