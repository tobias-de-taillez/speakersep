#!/usr/bin/env python3
"""
🎤 Simple but FUNCTIONAL Voice Cloning with XTTS-v2
No bullshit - this actually works!
"""

import os
import time
import logging
from pathlib import Path
from typing import Optional
import sys

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

def find_speaker_audio(speaker_name: str = "Tobias") -> Optional[Path]:
    """Find speaker audio file"""
    speaker_dir = Path("audio out/speakers") / speaker_name
    
    if not speaker_dir.exists():
        logger.error(f"❌ Speaker directory not found: {speaker_dir}")
        return None
    
    # Look for audio files
    for ext in ['.wav', '.mp3', '.m4a']:
        files = list(speaker_dir.glob(f"*{ext}"))
        if files:
            best_file = max(files, key=lambda f: f.stat().st_size)
            logger.info(f"✅ Found speaker audio: {best_file}")
            return best_file
    
    logger.error(f"❌ No audio files found in {speaker_dir}")
    return None

def main():
    """Main function that does actual voice cloning"""
    
    try:
        # NUCLEAR OPTION: Fix PyTorch 2.6 weights_only issue by monkey patching torch.load
        import torch
        
        logger.info("🔧 Applying NUCLEAR FIX for PyTorch 2.6 compatibility...")
        
        # Save original torch.load
        original_torch_load = torch.load
        
        def patched_torch_load(*args, **kwargs):
            """Patched torch.load that sets weights_only=False"""
            # Force weights_only=False for TTS compatibility
            kwargs['weights_only'] = False
            return original_torch_load(*args, **kwargs)
        
        # Monkey patch torch.load
        torch.load = patched_torch_load
        logger.info("✅ PyTorch 2.6 compatibility NUCLEAR FIX applied!")
        
        # Import TTS
        from TTS.api import TTS
        logger.info("✅ TTS imported successfully")
        
        # Initialize XTTS-v2
        logger.info("🔧 Loading XTTS-v2 model...")
        tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2")
        logger.info("✅ XTTS-v2 model loaded")
        
        # Find speaker audio
        speaker_audio = find_speaker_audio("Tobias")
        if not speaker_audio:
            logger.error("❌ No speaker audio found")
            return
        
        # Create output directory
        output_dir = Path("voice_cloning_output_simple")
        output_dir.mkdir(exist_ok=True)
        
        # Test texts
        test_texts = [
            "Hallo, das ist ein Test der funktionierenden Voice Cloning Technologie.",
            "Künstliche Intelligenz kann jetzt realistische Stimmen synthetisieren.",
            "Dies ist ein ehrlicher Test ohne Dummy-Code oder Kopien."
        ]
        
        # Generate audio for each text
        for i, text in enumerate(test_texts, 1):
            logger.info(f"🎯 Generating audio {i}/{len(test_texts)}")
            logger.info(f"📝 Text: {text}")
            
            start_time = time.time()
            
            # Generate speech
            output_path = output_dir / f"output_{i}_{int(time.time())}.wav"
            
            tts.tts_to_file(
                text=text,
                file_path=str(output_path),
                speaker_wav=str(speaker_audio),
                language="de"
            )
            
            synthesis_time = time.time() - start_time
            
            logger.info(f"✅ Audio generated in {synthesis_time:.2f}s")
            logger.info(f"📁 Output: {output_path}")
            
            # Check if file was actually created
            if output_path.exists():
                size_mb = output_path.stat().st_size / (1024 * 1024)
                logger.info(f"📊 File size: {size_mb:.2f} MB")
            else:
                logger.error(f"❌ File was not created: {output_path}")
        
        logger.info("🎉 Voice cloning completed successfully!")
        
    except ImportError as e:
        logger.error(f"❌ Failed to import TTS: {e}")
        logger.error("Make sure you're using the correct virtual environment")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Voice cloning failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 