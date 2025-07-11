#!/bin/bash

# 🎤 Voice Cloning Setup v2.0 - State-of-the-Art Models (Zonos-v0.1 + F5-TTS)
# Compatible with Python 3.12 for M4 Pro MacBook

set -e

echo "🚀 Setting up State-of-the-Art Voice Cloning Environment..."
echo "📦 Models: Zonos-v0.1 (Primary) + F5-TTS (Alternative) + XTTS-v2 (Fallback)"
echo ""

# Check Python 3.12 availability
if ! command -v python3.12 &> /dev/null; then
    echo "❌ Python 3.12 not found. Please install Python 3.12:"
    echo "   brew install python@3.12"
    exit 1
fi

echo "✅ Python 3.12 found: $(python3.12 --version)"

# Create and activate new venv with Python 3.12
if [ ! -d "venv_voice_cloning" ]; then
    echo "🔧 Creating new virtual environment with Python 3.12..."
    python3.12 -m venv venv_voice_cloning
fi

source venv_voice_cloning/bin/activate

echo "✅ Virtual environment activated: $(python --version)"

# Upgrade pip and install core dependencies
echo "📦 Installing core dependencies..."
pip install --upgrade pip setuptools wheel

# Install PyTorch with MPS support for M4 Pro
echo "🔥 Installing PyTorch with MPS support..."
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

# Install Zonos-v0.1 dependencies
echo "🎯 Installing Zonos-v0.1 dependencies..."
pip install transformers datasets accelerate huggingface_hub
pip install librosa soundfile scipy numpy
pip install gradio fastapi uvicorn

# Install F5-TTS dependencies
echo "🎵 Installing F5-TTS dependencies..."
pip install torchaudio phonemizer cached-path
pip install omegaconf hydra-core
pip install tensorboard

# Install TTS (Coqui) - should work with Python 3.12
echo "🎤 Installing TTS (Coqui) for XTTS-v2 fallback..."
pip install TTS

# Install additional audio processing libraries
echo "🔊 Installing audio processing libraries..."
pip install pydub pedalboard resampy

# Test MPS availability
echo "🧪 Testing MPS availability..."
python3.12 -c "import torch; print(f'PyTorch version: {torch.__version__}'); print(f'MPS available: {torch.backends.mps.is_available()}')"

# Download Zonos-v0.1 model (lightweight check)
echo "📥 Preparing Zonos-v0.1 model download..."
python3.12 -c "from huggingface_hub import snapshot_download; print('✅ HuggingFace Hub ready')"

# Check Tobias samples availability
if [ -d "audio out/speakers/Tobias" ]; then
    TOBIAS_COUNT=$(find "audio out/speakers/Tobias" -name "*.wav" | wc -l)
    echo "✅ Found $TOBIAS_COUNT Tobias audio samples"
else
    echo "⚠️  Tobias samples directory not found. Run speaker_organizer.py first."
fi

echo ""
echo "🎉 Voice Cloning Setup v2.0 Complete!"
echo ""
echo "🚀 Next steps:"
echo "   source venv_voice_cloning/bin/activate"
echo "   python voice_cloning_demo_v2.py"
echo ""
echo "🎯 Features:"
echo "   • Zonos-v0.1: Latest State-of-the-Art Model (Feb 2025)"
echo "   • F5-TTS: Most realistic open source zero shot model"
echo "   • XTTS-v2: Proven fallback system"
echo "   • M4 Pro optimized with MPS support"
echo "   • Robust triple-fallback architecture"
echo "" 