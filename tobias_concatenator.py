#!/usr/bin/env python3
"""
🎤 Tobias Sample Concatenator für Zonos Voice Cloning
Concateniert 3 Minuten der besten Tobias-Samples aus 30.june mit 1s Pausen
"""

import os
import sys
import time
import logging
from pathlib import Path
from typing import List, Tuple
import numpy as np
import soundfile as sf
import librosa
import re

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TobiasConcatenator:
    def __init__(self, base_dir: str = "audio out/30.june/segments"):
        self.base_dir = Path(base_dir)
        self.output_dir = Path("voice_cloning_output_v2")
        self.output_dir.mkdir(exist_ok=True)
        
        # Target concatenation parameters
        self.target_duration = 180  # 3 minutes in seconds
        self.pause_duration = 1.0   # 1 second pause between samples
        self.sample_rate = 16000    # Standard sampling rate
        
        logger.info(f"🎯 Target: {self.target_duration}s with {self.pause_duration}s pauses")
        logger.info(f"📁 Source: {self.base_dir}")
        logger.info(f"📤 Output: {self.output_dir}")
    
    def _parse_segment_info(self, filename: str) -> Tuple[int, float, float]:
        """Parse segment filename to extract segment number and timestamps"""
        # Pattern: tmp0ulopk1k_SPEAKER_01_024_121.2s-126.6s.wav
        pattern = r'tmp0ulopk1k_SPEAKER_01_(\d+)_(\d+\.?\d*)s-(\d+\.?\d*)s\.wav'
        match = re.match(pattern, filename)
        
        if match:
            segment_num = int(match.group(1))
            start_time = float(match.group(2))
            end_time = float(match.group(3))
            return segment_num, start_time, end_time
        else:
            raise ValueError(f"Could not parse filename: {filename}")
    
    def _get_tobias_segments(self) -> List[Tuple[Path, int, float, float, float]]:
        """Get all Tobias (SPEAKER_01) segments sorted by timestamp"""
        segments = []
        
        # Find all SPEAKER_01 files
        for file_path in self.base_dir.glob("*SPEAKER_01*.wav"):
            try:
                segment_num, start_time, end_time = self._parse_segment_info(file_path.name)
                duration = end_time - start_time
                
                # Check if file exists and is readable
                if file_path.exists() and file_path.stat().st_size > 0:
                    segments.append((file_path, segment_num, start_time, end_time, duration))
                    logger.debug(f"📄 {file_path.name}: {duration:.1f}s ({start_time:.1f}s-{end_time:.1f}s)")
                else:
                    logger.warning(f"⚠️ Skipping empty/missing file: {file_path.name}")
                    
            except Exception as e:
                logger.warning(f"⚠️ Could not process {file_path.name}: {e}")
        
        # Sort by start timestamp
        segments.sort(key=lambda x: x[2])
        
        logger.info(f"✅ Found {len(segments)} Tobias segments")
        return segments
    
    def _load_audio_segment(self, file_path: Path) -> np.ndarray:
        """Load and resample audio segment"""
        try:
            # Try multiple audio loading methods
            try:
                audio, sr = librosa.load(str(file_path), sr=self.sample_rate, mono=True)
                logger.debug(f"📊 Loaded with librosa: {file_path.name} ({len(audio)} samples)")
                return audio
            except Exception as e1:
                logger.debug(f"Librosa failed: {e1}")
                
                # Fallback to soundfile
                try:
                    audio, sr = sf.read(str(file_path))
                    if audio.ndim > 1:
                        audio = audio.mean(axis=1)  # Convert to mono
                    if sr != self.sample_rate:
                        audio = librosa.resample(audio, orig_sr=sr, target_sr=self.sample_rate)
                    logger.debug(f"📊 Loaded with soundfile: {file_path.name} ({len(audio)} samples)")
                    return audio
                except Exception as e2:
                    logger.error(f"❌ Both loading methods failed for {file_path.name}: {e1}, {e2}")
                    return None
                    
        except Exception as e:
            logger.error(f"❌ Could not load {file_path.name}: {e}")
            return None
    
    def _select_best_segments(self, segments: List[Tuple[Path, int, float, float, float]]) -> List[Tuple[Path, int, float, float, float]]:
        """Select best segments up to target duration"""
        selected = []
        total_duration = 0
        total_pauses = 0
        
        for segment in segments:
            file_path, segment_num, start_time, end_time, duration = segment
            
            # Calculate total time with pause
            time_with_pause = duration + self.pause_duration
            
            # Check if we can fit this segment
            if total_duration + time_with_pause <= self.target_duration:
                selected.append(segment)
                total_duration += time_with_pause
                total_pauses += self.pause_duration
                
                logger.info(f"✅ Selected: {file_path.name} ({duration:.1f}s) - Total: {total_duration:.1f}s")
            else:
                logger.info(f"⏹️ Stopping at {len(selected)} segments - would exceed target duration")
                break
        
        actual_audio_duration = total_duration - total_pauses
        logger.info(f"📊 Selected {len(selected)} segments:")
        logger.info(f"   🎵 Audio duration: {actual_audio_duration:.1f}s")
        logger.info(f"   ⏸️ Pause duration: {total_pauses:.1f}s")
        logger.info(f"   📈 Total duration: {total_duration:.1f}s")
        
        return selected
    
    def concatenate_tobias_samples(self) -> Path:
        """Concatenate Tobias samples with pauses"""
        logger.info("🚀 Starting Tobias sample concatenation...")
        
        # Get all segments
        segments = self._get_tobias_segments()
        if not segments:
            logger.error("❌ No Tobias segments found")
            return None
        
        # Select best segments
        selected_segments = self._select_best_segments(segments)
        if not selected_segments:
            logger.error("❌ No segments selected")
            return None
        
        # Load and concatenate audio
        concatenated_audio = []
        pause_samples = int(self.pause_duration * self.sample_rate)
        silence = np.zeros(pause_samples)
        
        for i, (file_path, segment_num, start_time, end_time, duration) in enumerate(selected_segments):
            logger.info(f"🔄 Processing segment {i+1}/{len(selected_segments)}: {file_path.name}")
            
            # Load audio
            audio = self._load_audio_segment(file_path)
            if audio is None:
                logger.warning(f"⚠️ Skipping segment {file_path.name} - could not load")
                continue
            
            # Add audio to concatenation
            concatenated_audio.append(audio)
            
            # Add pause (except for last segment)
            if i < len(selected_segments) - 1:
                concatenated_audio.append(silence)
                logger.debug(f"⏸️ Added {self.pause_duration}s pause")
        
        # Combine all audio
        if not concatenated_audio:
            logger.error("❌ No audio data to concatenate")
            return None
        
        final_audio = np.concatenate(concatenated_audio)
        final_duration = len(final_audio) / self.sample_rate
        
        # Save concatenated audio
        timestamp = int(time.time())
        output_path = self.output_dir / f"tobias_concatenated_30june_{timestamp}.wav"
        
        sf.write(str(output_path), final_audio, self.sample_rate)
        
        logger.info(f"🎉 Concatenation completed!")
        logger.info(f"📊 Final audio: {final_duration:.1f}s ({len(final_audio)} samples)")
        logger.info(f"📁 Saved to: {output_path}")
        
        return output_path

def main():
    """Main function"""
    try:
        concatenator = TobiasConcatenator()
        output_path = concatenator.concatenate_tobias_samples()
        
        if output_path:
            logger.info(f"✅ SUCCESS: Tobias samples concatenated to {output_path}")
            return output_path
        else:
            logger.error("❌ FAILED: Could not concatenate Tobias samples")
            return None
            
    except Exception as e:
        logger.error(f"❌ Concatenation failed: {e}")
        raise

if __name__ == "__main__":
    result = main()
    sys.exit(0 if result else 1) 