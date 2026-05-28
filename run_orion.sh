#!/bin/bash
cd "$(dirname "$0")"
source ~/.zshrc

echo "========================================="
echo "🤖 INITIALIZING ORION MASTER SYSTEM..."
echo "========================================="

# Kill any lingering instances to prevent ghost processes
pkill -f "python3 -m voice.voice_loop"
pkill -f "python3 -m study.run_study"
pkill -f "python3 -m desktop.run"

# 1. Start the Voice Engine (STT, TTS, OCR, Wake Word)
echo "[1/3] 🎙️ Starting ORION Voice & Vision Engine..."
python3 -m voice.voice_loop &
VOICE_PID=$!

sleep 2 # Give it a moment to initialize

# 2. Start the Study Engine (PyQt6 GUI, Manim Renderer)
echo "[2/3] 🎓 Starting ORION AI Study Simulator..."
python3 -m study.run_study &
STUDY_PID=$!

# 3. Start the Desktop UI (Orb + Transcript + Controls)
echo "[3/3] 🖥️  Starting ORION Desktop UI..."
python3 -m desktop.run &
DESKTOP_PID=$!

echo "========================================="
echo "✅ ORION IS FULLY ONLINE!"
echo "Press [Ctrl+C] to gracefully shut down all systems."
echo "========================================="

# Trap Ctrl+C (SIGINT) to kill all processes cleanly
trap "echo -e '\n🛑 Shutting down ORION...'; kill $VOICE_PID $STUDY_PID $DESKTOP_PID 2>/dev/null; exit" SIGINT

# Keep script alive and wait for background processes
wait $VOICE_PID $STUDY_PID $DESKTOP_PID