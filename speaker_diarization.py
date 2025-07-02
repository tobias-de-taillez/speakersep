#!/usr/bin/env python3
"""
Speaker Diarization Processing Pipeline
======================================

Processes all audio files in "audio in/" directory using pyannote.audio speaker diarization,
saves results in structured sub-folders in "audio_out/", and moves processed files to "audio_processed/".

Requirements:
- HuggingFace account with access token
- Accept pyannote/segmentation-3.0 user conditions  
- Accept pyannote/speaker-diarization-3.1 user conditions
- pyannote.audio 3.3.2+ installed

Usage:
    export HUGGINGFACE_TOKEN="your_token_here"
    python speaker_diarization.py
"""

import os
import sys
import shutil
import logging
from pathlib import Path
from datetime import datetime
import json
import csv
import tempfile
from typing import List, Dict, Any, Optional

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not available, continue with system env vars

try:
    import torch
    from pyannote.audio import Pipeline
    from pyannote.core import Annotation
    import librosa
    import soundfile as sf
except ImportError as e:
    print(f"❌ Missing required dependency: {e}")
    print("Install with: pip install pyannote.audio librosa soundfile")
    sys.exit(1)

# Video processing for MP4 audio extraction
try:
    import moviepy.editor
    MOVIEPY_AVAILABLE = True
except ImportError:
    MOVIEPY_AVAILABLE = False
    # Logger is not yet configured, will warn later

# Configuration
AUDIO_INPUT_DIR = Path("audio in")
AUDIO_OUTPUT_DIR = Path("audio out") 
AUDIO_PROCESSED_DIR = Path("audio_processed")
SUPPORTED_FORMATS = {'.wav', '.mp3', '.flac', '.m4a', '.aac', '.ogg', '.webm', '.mp4'}

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('speaker_diarization.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class SpeakerDiarizationProcessor:
    """Main processor for speaker diarization pipeline"""
    
    def __init__(self, huggingface_token: Optional[str] = None):
        self.hf_token = huggingface_token or os.getenv('HUGGINGFACE_TOKEN')
        self.pipeline = None
        self.device = self._setup_device()
        
        if not self.hf_token:
            logger.error("❌ HuggingFace token required!")
            logger.error("Set HUGGINGFACE_TOKEN environment variable or pass as parameter")
            logger.error("Get token at: https://huggingface.co/settings/tokens")
            sys.exit(1)
    
    def _setup_device(self) -> torch.device:
        """Setup optimal device (MPS > CUDA > CPU)"""
        if torch.backends.mps.is_available():
            logger.info("🚀 Using Apple Silicon MPS acceleration")
            return torch.device("mps")
        elif torch.cuda.is_available():
            logger.info("🚀 Using CUDA GPU acceleration")  
            return torch.device("cuda")
        else:
            logger.info("💻 Using CPU (consider GPU for faster processing)")
            return torch.device("cpu")
    
    def initialize_pipeline(self) -> bool:
        """Initialize pyannote.audio speaker diarization pipeline"""
        try:
            logger.info("🔄 Loading speaker diarization pipeline...")
            logger.info("📋 Required: Accept conditions at https://hf.co/pyannote/segmentation-3.0")
            logger.info("📋 Required: Accept conditions at https://hf.co/pyannote/speaker-diarization-3.1")
            
            self.pipeline = Pipeline.from_pretrained(
                "pyannote/speaker-diarization-3.1",
                use_auth_token=self.hf_token
            )
            
            # Move pipeline to optimal device
            self.pipeline.to(self.device)
            logger.info(f"✅ Pipeline loaded on {self.device}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize pipeline: {e}")
            if "Repository not found" in str(e):
                logger.error("💡 Make sure you have accepted the user conditions:")
                logger.error("   - https://hf.co/pyannote/segmentation-3.0")
                logger.error("   - https://hf.co/pyannote/speaker-diarization-3.1")
            return False
    
    def get_audio_files(self) -> List[Path]:
        """Get all supported audio files from input directory"""
        if not AUDIO_INPUT_DIR.exists():
            logger.error(f"❌ Input directory '{AUDIO_INPUT_DIR}' not found")
            return []
        
        audio_files = []
        for file_path in AUDIO_INPUT_DIR.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in SUPPORTED_FORMATS:
                audio_files.append(file_path)
        
        logger.info(f"📁 Found {len(audio_files)} audio files to process")
        return sorted(audio_files)
    
    def extract_audio_from_video(self, video_file: Path) -> Optional[Path]:
        """Extract audio from MP4 video file"""
        if not MOVIEPY_AVAILABLE:
            logger.error("❌ moviepy not available. Cannot extract audio from MP4.")
            logger.error("Install with: pip install moviepy")
            return None
            
        if video_file.suffix.lower() != '.mp4':
            return video_file  # Not a video file, return as-is
            
        try:
            logger.info(f"🎬 Extracting audio from MP4: {video_file.name}")
            
            # Create temporary audio file
            temp_audio = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
            temp_audio_path = Path(temp_audio.name)
            temp_audio.close()
            
            # Extract audio using moviepy
            from moviepy.editor import VideoFileClip
            video_clip = VideoFileClip(str(video_file))
            audio_clip = video_clip.audio
            
            if audio_clip is None:
                logger.error(f"❌ No audio track found in {video_file.name}")
                video_clip.close()
                return None
                
            # Write audio to temporary file
            audio_clip.write_audiofile(str(temp_audio_path), verbose=False, logger=None)
            
            # Cleanup
            audio_clip.close()
            video_clip.close()
            
            logger.info(f"✅ Audio extracted to temporary file: {temp_audio_path.name}")
            return temp_audio_path
            
        except Exception as e:
            logger.error(f"❌ Failed to extract audio from {video_file.name}: {e}")
            return None
    
    def create_output_structure(self, audio_file: Path) -> Path:
        """Create output directory structure for audio file"""
        # Use filename without extension as folder name
        folder_name = audio_file.stem
        output_folder = AUDIO_OUTPUT_DIR / folder_name
        
        # Create sub-directories
        output_folder.mkdir(parents=True, exist_ok=True)
        (output_folder / "segments").mkdir(exist_ok=True)
        (output_folder / "metadata").mkdir(exist_ok=True)
        
        return output_folder
    
    def process_audio_file(self, audio_file: Path) -> bool:
        """Process single audio file with speaker diarization"""
        logger.info(f"🎵 Processing: {audio_file.name}")
        
        temp_audio_file = None
        try:
            # Handle MP4 video files by extracting audio
            if audio_file.suffix.lower() == '.mp4':
                audio_file_for_processing = self.extract_audio_from_video(audio_file)
                if audio_file_for_processing is None:
                    return False
                temp_audio_file = audio_file_for_processing
            else:
                audio_file_for_processing = audio_file
            
            # Create output structure (using original filename)
            output_folder = self.create_output_structure(audio_file)
            
            # Apply speaker diarization
            logger.info("🧠 Applying speaker diarization...")
            diarization = self.pipeline(str(audio_file_for_processing))
            
            # Save results in multiple formats and get meaningful segments
            meaningful_segments = self._save_diarization_results(diarization, audio_file, output_folder)
            
            # Extract speaker segments (only meaningful ones)
            self._extract_speaker_segments(audio_file_for_processing, diarization, output_folder, meaningful_segments)
            
            # Generate summary
            self._generate_summary(diarization, audio_file, output_folder)
            
            logger.info(f"✅ Successfully processed: {audio_file.name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to process {audio_file.name}: {e}")
            return False
        finally:
            # Cleanup temporary audio file if created
            if temp_audio_file and temp_audio_file != audio_file:
                try:
                    temp_audio_file.unlink()
                    logger.debug(f"🗑️ Cleaned up temporary file: {temp_audio_file.name}")
                except Exception as e:
                    logger.warning(f"⚠️ Failed to cleanup temporary file: {e}")
    
    def _save_diarization_results(self, diarization: Annotation, audio_file: Path, output_folder: Path) -> List[tuple]:
        """Save diarization results in multiple formats"""
        base_name = audio_file.stem
        
        # 1. Save as RTTM (Rich Transcription Time Marked) format
        rttm_file = output_folder / "metadata" / f"{base_name}.rttm"
        with open(rttm_file, 'w') as f:
            diarization.write_rttm(f)
        
        # Filter meaningful segments (≥1s) for all processing
        meaningful_segments = []
        all_segments = list(diarization.itertracks(yield_label=True))
        
        for item in all_segments:
            if len(item) == 3:
                turn, _, speaker = item
            elif len(item) == 2:
                turn, speaker = item
            else:
                logger.warning(f"Unexpected diarization format: {item}")
                continue
                
            if turn.duration >= 1.0:
                meaningful_segments.append((turn, speaker))
            else:
                logger.debug(f"Filtered short segment: {turn.duration:.2f}s ({speaker})")
        
        logger.info(f"📊 Kept {len(meaningful_segments)} segments ≥1s (filtered {len(all_segments) - len(meaningful_segments)} short segments)")
        
        # 2. Save as CSV for easy analysis
        csv_file = output_folder / "metadata" / f"{base_name}_timeline.csv"
        with open(csv_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['start_time', 'end_time', 'duration', 'speaker'])
            
            for turn, speaker in meaningful_segments:
                writer.writerow([
                    f"{turn.start:.2f}",
                    f"{turn.end:.2f}", 
                    f"{turn.duration:.2f}",
                    speaker
                ])
        
        # 3. Save as JSON for programmatic access (only meaningful segments)
        json_file = output_folder / "metadata" / f"{base_name}_diarization.json"
        timeline_data = []
        total_duration = 0
        
        for turn, speaker in meaningful_segments:
            timeline_data.append({
                'start': turn.start,
                'end': turn.end,
                'duration': turn.duration,
                'speaker': speaker
            })
            total_duration = max(total_duration, turn.end)
        
        with open(json_file, 'w') as f:
            json.dump({
                'audio_file': audio_file.name,
                'processed_at': datetime.now().isoformat(),
                'num_speakers': len(diarization.labels()),  
                'total_duration': total_duration,
                'timeline': timeline_data
            }, f, indent=2)
        
        return meaningful_segments
    
    def _extract_speaker_segments(self, audio_file: Path, diarization: Annotation, output_folder: Path, meaningful_segments: List[tuple]):
        """Extract individual speaker segments as separate audio files"""
        try:
            # Load original audio
            audio, sr = librosa.load(str(audio_file), sr=None)
            
            segments_folder = output_folder / "segments"
            base_name = audio_file.stem
            
            # Extract each meaningful speaker segment (≥1s only)
            for i, (turn, speaker) in enumerate(meaningful_segments):
                start_sample = int(turn.start * sr)
                end_sample = int(turn.end * sr)
                
                # Extract segment
                segment_audio = audio[start_sample:end_sample]
                
                # Save segment
                segment_filename = f"{base_name}_{speaker}_{i:03d}_{turn.start:.1f}s-{turn.end:.1f}s.wav"
                segment_path = segments_folder / segment_filename
                
                sf.write(str(segment_path), segment_audio, sr)
            
            logger.info(f"🎯 Extracted {len(meaningful_segments)} speaker segments")
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to extract segments: {e}")
    
    def _generate_summary(self, diarization: Annotation, audio_file: Path, output_folder: Path):
        """Generate processing summary and statistics"""
        speakers = list(diarization.labels())
        # Calculate total duration safely
        total_duration = 0
        if diarization:
            for item in diarization.itertracks(yield_label=True):
                if len(item) >= 2:
                    turn = item[0]  # First element is always the segment
                    total_duration = max(total_duration, turn.end)
        
        # Calculate speaker statistics
        speaker_stats = {}
        for speaker in speakers:
            speaker_segments = []
            for item in diarization.itertracks(yield_label=True):
                if len(item) == 3:
                    turn, _, spk = item
                elif len(item) == 2:
                    turn, spk = item
                else:
                    continue
                if spk == speaker:
                    speaker_segments.append(turn)
            
            total_speech_time = sum(turn.duration for turn in speaker_segments)
            speaker_stats[speaker] = {
                'segments': len(speaker_segments),
                'total_speech_time': total_speech_time,
                'speech_ratio': total_speech_time / total_duration if total_duration > 0 else 0
            }
        
        # Create summary
        summary = {
            'file': audio_file.name,
            'processed_at': datetime.now().isoformat(),
            'total_duration': total_duration,
            'num_speakers': len(speakers),
            'speakers': speakers,
            'speaker_statistics': speaker_stats,
            'total_segments': len(list(diarization.itertracks())),
        }
        
        # Save summary
        summary_file = output_folder / "metadata" / f"{audio_file.stem}_summary.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        # Log summary
        logger.info(f"📊 Summary: {len(speakers)} speakers, {len(list(diarization.itertracks()))} segments, {total_duration:.1f}s duration")
    
    def move_processed_file(self, audio_file: Path) -> bool:
        """Move processed file to processed directory"""
        try:
            AUDIO_PROCESSED_DIR.mkdir(exist_ok=True)
            destination = AUDIO_PROCESSED_DIR / audio_file.name
            
            # Handle file name conflicts
            counter = 1
            while destination.exists():
                name_parts = audio_file.stem, counter, audio_file.suffix
                destination = AUDIO_PROCESSED_DIR / f"{name_parts[0]}_{name_parts[1]}{name_parts[2]}"
                counter += 1
            
            shutil.move(str(audio_file), str(destination))
            logger.info(f"📦 Moved to: {destination}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to move {audio_file.name}: {e}")
            return False
    
    def process_all_files(self):
        """Process all audio files in input directory"""
        if not self.initialize_pipeline():
            return
        
        audio_files = self.get_audio_files()
        if not audio_files:
            logger.info("📭 No audio files to process")
            return
        
        # Ensure output directories exist
        AUDIO_OUTPUT_DIR.mkdir(exist_ok=True)
        AUDIO_PROCESSED_DIR.mkdir(exist_ok=True)
        
        success_count = 0
        total_files = len(audio_files)
        
        logger.info(f"🚀 Starting batch processing of {total_files} files...")
        start_time = datetime.now()
        
        for i, audio_file in enumerate(audio_files, 1):
            logger.info(f"📋 Progress: {i}/{total_files}")
            
            if self.process_audio_file(audio_file):
                if self.move_processed_file(audio_file):
                    success_count += 1
            
            logger.info("-" * 50)
        
        # Final summary
        end_time = datetime.now() 
        duration = end_time - start_time
        
        logger.info("=" * 50)
        logger.info("🎉 BATCH PROCESSING COMPLETE")
        logger.info(f"✅ Successfully processed: {success_count}/{total_files}")
        logger.info(f"⏱️ Total time: {duration}")
        logger.info(f"📁 Results saved in: {AUDIO_OUTPUT_DIR}")
        logger.info(f"📦 Processed files moved to: {AUDIO_PROCESSED_DIR}")


def main():
    """Main entry point"""
    print("🎵 Speaker Diarization Processing Pipeline")
    print("=" * 50)
    
    # Check HuggingFace token
    token = os.getenv('HUGGINGFACE_TOKEN')
    if not token:
        print("❌ HUGGINGFACE_TOKEN environment variable not set!")
        print("📝 Steps to setup:")
        print("1. Create account at https://huggingface.co")
        print("2. Get access token at https://hf.co/settings/tokens")
        print("3. Accept conditions at https://hf.co/pyannote/segmentation-3.0")
        print("4. Accept conditions at https://hf.co/pyannote/speaker-diarization-3.1")
        print("5. Set token: export HUGGINGFACE_TOKEN='your_token_here'")
        return
    
    # Initialize and run processor
    processor = SpeakerDiarizationProcessor(token)
    processor.process_all_files()


if __name__ == "__main__":
    main() 