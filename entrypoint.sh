#!/bin/bash

echo "--- Hardware Detection ---"
# Check for NVIDIA
if lspci | grep -i nvidia > /dev/null; then
    echo "Detected: NVIDIA GPU"
    GPU_TYPE="nvidia"
# Check for AMD
elif lspci | grep -i "amd/ati" > /dev/null; then
    echo "Detected: AMD/ATI GPU"
    GPU_TYPE="amd"
else
    echo "Detected: No discrete GPU (CPU ONLY)"
    GPU_TYPE="cpu"
fi

# Start Ollama in the background
echo "Starting Ollama server..."
ollama serve &

# Wait for Ollama to be available
until curl -s http://localhost:11434/api/tags > /dev/null; do
  sleep 2
done

# Perform the Ollama-specific detection check
if ollama ps | grep -q "gpu"; then
    echo "✅ SUCCESS: Ollama has successfully initialized the $GPU_TYPE GPU!"
else
    echo "⚠️  WARNING: $GPU_TYPE detected, but Ollama is using the CPU."
    echo "   (Ensure you have the Drivers and Container Toolkit installed on your PC)"
fi

# Start the application
exec uv run main.py
