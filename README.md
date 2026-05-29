O.R.I.O.N. — Real-Time Multimodal AI Orchestration System

O.R.I.O.N. (Omni-directional Real-time Intelligence & Orchestration Network) is a low-latency conversational AI system built from scratch in Python.

Instead of focusing only on adding features, O.R.I.O.N. is heavily optimized around one core idea:

Real-time interaction should feel conversational, not computational.

The project explores:

* ultra-low-latency voice pipelines,
* streaming AI interaction,
* multimodal orchestration,
* adaptive educational systems,
* ambient AI workflows,
* and real-time desktop assistance.

⸻

Core Philosophy

Most AI assistants feel slow because they rely on blocking pipelines:

Speech → STT → LLM → TTS → Playback 

O.R.I.O.N. replaces this with:

* asynchronous orchestration,
* streaming inference,
* incremental audio playback,
* continuous interaction loops,
* and aggressive latency optimization.

The goal is not to build a “chatbot”.

The goal is to build a responsive runtime system that feels alive.

⸻

Performance

Current conversational startup latency (V4 pipeline):

Component	Approx Latency
Wake Word Detection	~50ms
Streaming STT (Groq Whisper Large V3)	~50ms
Intent Routing (Groq LLaMA 3)	~50ms
LLM TTFT (Streaming Response)	~80ms
Streaming TTS Startup	~150ms
Total Conversational Startup	~300–500ms

Latency progression:

* V1 → ~20–30 seconds
* V2 → ~5–6 seconds
* V4 → ~300–500ms startup latency
   *(Note: this can vary depending on the speed of your internet and the speed of your computer)*

⸻

Core Features

Ultra-Low Latency Voice Pipeline

Wake Word Detection → WebRTC VAD → Streaming STT → Intent Routing → Streaming LLM → Streaming TTS → Real-Time Playback

Key optimizations include:

* async orchestration,
* direct streaming audio pipelines,
* byte-stream playback,
* and minimized API overhead.

⸻

Real-Time Streaming Audio System

Instead of downloading full audio files before playback, O.R.I.O.N. streams audio chunks directly into the playback pipeline.

This allows speech playback to begin while the response is still generating.

⸻

Animated Desktop Interface

A PyQt6-based desktop interface featuring:

* animated orb states,
* live transcript streaming,
* conversational status indicators,
* glassmorphic UI elements,
* and real-time assistant feedback.

The UI dynamically reacts to:

* listening,
* thinking,
* speaking,
* and idle states.

⸻

Streaming Web Search (Background RAG)

O.R.I.O.N. can:

* search the web,
* retrieve information,
* summarize results,
* and stream spoken answers

without opening a browser window.

⸻

Screen Understanding & OCR

Using OCR and multimodal vision models, O.R.I.O.N. can:

* analyze screenshots,
* summarize visible content,
* understand on-screen text,
* and assist with contextual desktop workflows.

⸻

AI Study Simulator

A dedicated educational subsystem capable of:

* generating concept explanations,
* synchronized narration,
* visual learning flows,
* interactive educational simulations,
* and adaptive study assistance.

The system is designed around:

* intuition-first teaching,
* progressive difficulty,
* visual understanding,
* and real-time educational interaction.

⸻

Echo Prevention System

O.R.I.O.N. uses a deterministic assistant state system to prevent:

* self-triggering,
* hallucinated loops,
* recursive responses,
* and microphone feedback instability.

Adaptive acoustic echo cancellation is currently under active development.

⸻

Architecture

O.R.I.O.N. is designed as a modular concurrent system.

Primary runtime components:

1. Voice Engine
    Handles:
    * VAD
    * STT
    * LLM orchestration
    * TTS streaming
    * audio routing
2. Desktop UI
    Handles:
    * assistant visualization
    * live transcripts
    * runtime state rendering
3. Study Engine
    Handles:
    * educational orchestration
    * simulation logic
    * synchronized visual lessons

Communication occurs through lightweight asynchronous event pipelines and high-speed local IPC messaging.

⸻

Technology Stack

Core technologies currently used:

* Python
* PyQt6
* Groq API
* LLaMA 3
* Whisper Large V3
* WebRTC VAD
* Edge TTS
* Manim
* Tesseract OCR
* AsyncIO
* FFmpeg / ffplay

⸻

Example Commands

* “Jarvis, what’s happening in the world today?”
* “Jarvis, explain electromagnetic induction visually.”
* “Jarvis, summarize what I’m looking at.”
* “Jarvis, open my coding workspace.”
* “Jarvis, explain this equation step-by-step.”

*(Note: The wake word remains "Jarvis").*

⸻ 

Current Focus

Current development priorities:

* architecture stability,
* orchestration reliability,
* adaptive educational systems,
* improved observability,
* UI refinement,
* and advanced audio engineering.

Future goals include:

* adaptive acoustic echo cancellation,
* dynamic tool orchestration,
* wearable AI integration,
* contextual awareness systems,
* and real-time cognitive assistance workflows.

⸻

Current Limitations

O.R.I.O.N. is still an experimental and actively evolving system.

Some components are currently:

* prototype-level,
* heavily iterative,
* or under active redesign.

Known limitations include:

* experimental orchestration flows,
* imperfect OCR reliability,
* partial echo cancellation implementation,
* and simulation rendering overhead.

⸻

Why This Project Exists

O.R.I.O.N. started as an experiment in reducing conversational latency.

It gradually evolved into a broader exploration of:

* real-time AI interaction,
* multimodal orchestration,
* streaming system design,
* and ambient computing.

The project is primarily built to learn:

* systems engineering,
* applied AI infrastructure,
* interaction design,
* and real-time orchestration architecture.

⸻


## Setup

1. Clone the repository and install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Configure your `.env` file with the necessary API keys:
   ```env
   GROQ_API_KEY=your_key_here
   OPENROUTER_API_KEY=your_key_here
   HF_TOKEN=your_key_here
   PICOVOICE_KEY=your_key_here
   ELEVEN_API_KEY=your_key_here
   TTS_ENGINE=edge  or 'elevenlabs'
   ```
3. Run the system:
   ```bash
   ./run_orion.sh
   ```


---
Built by Shourya