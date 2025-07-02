#!/usr/bin/env python3
"""
Master Processor for Overnight Batch Processing
Automatically processes all audio files in "audio in" directory:
1. Speaker Diarization (pyannote.audio)
2. Transcription (OpenAI Whisper)
3. Preparation for morning speaker assignment
"""

import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import List

from speaker_diarization import SpeakerDiarizationProcessor
from transcript_manager import TranscriptManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('overnight_processing.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Directory configuration
AUDIO_INPUT_DIR = Path("audio in")
AUDIO_OUTPUT_DIR = Path("audio out")
AUDIO_PROCESSED_DIR = Path("audio_processed")


class MasterProcessor:
    """Master processor for overnight batch operations"""
    
    def __init__(self):
        """Initialize master processor"""
        self.start_time = None
        self.processed_files = []
        self.failed_files = []
        
        # Initialize sub-processors
        self.diarization_processor = None
        self.transcript_manager = None
        
    def setup_processors(self) -> bool:
        """Setup and validate sub-processors"""
        logger.info("🔧 Setting up processors...")
        
        # Check HuggingFace token
        token = os.getenv('HUGGINGFACE_TOKEN')
        if not token:
            logger.error("❌ HUGGINGFACE_TOKEN environment variable not set!")
            return False
            
        # Initialize diarization processor
        try:
            self.diarization_processor = SpeakerDiarizationProcessor(token)
            if not self.diarization_processor.initialize_pipeline():
                logger.error("❌ Failed to initialize speaker diarization pipeline")
                return False
        except Exception as e:
            logger.error(f"❌ Failed to setup diarization processor: {e}")
            return False
            
        # Initialize transcript manager
        try:
            self.transcript_manager = TranscriptManager()
            if not self.transcript_manager.load_whisper_model():
                logger.error("❌ Failed to load Whisper model")
                return False
        except Exception as e:
            logger.error(f"❌ Failed to setup transcript manager: {e}")
            return False
            
        logger.info("✅ All processors initialized successfully")
        return True
        
    def find_input_files(self) -> List[Path]:
        """Find all audio files in input directory"""
        if not AUDIO_INPUT_DIR.exists():
            logger.warning(f"📭 Input directory not found: {AUDIO_INPUT_DIR}")
            return []
            
        audio_extensions = {'.wav', '.mp3', '.flac', '.m4a', '.aac', '.ogg'}
        audio_files = []
        
        for ext in audio_extensions:
            audio_files.extend(AUDIO_INPUT_DIR.glob(f"*{ext}"))
        
        logger.info(f"📁 Found {len(audio_files)} audio files in input directory")
        for file in audio_files:
            logger.info(f"  • {file.name}")
            
        return audio_files
        
    def process_single_file(self, audio_file: Path) -> bool:
        """Process a single audio file through complete pipeline"""
        logger.info("=" * 80)
        logger.info(f"🎵 PROCESSING: {audio_file.name}")
        logger.info("=" * 80)
        
        file_start_time = time.time()
        
        try:
            # Step 1: Speaker Diarization
            logger.info("🎯 Step 1/2: Speaker Diarization")
            if not self.diarization_processor.process_audio_file(audio_file):
                logger.error(f"❌ Speaker diarization failed for {audio_file.name}")
                return False
                
            # Move processed file to archive
            if not self.diarization_processor.move_processed_file(audio_file):
                logger.warning(f"⚠️ Failed to move {audio_file.name} to archive")
                
            # Step 2: Transcription
            logger.info("🎯 Step 2/2: Speech-to-Text Transcription")
            session_path = AUDIO_OUTPUT_DIR / audio_file.stem
            
            if not session_path.exists():
                logger.error(f"❌ Session directory not found: {session_path}")
                return False
                
            # Transcribe without interactive assignment
            transcripts = self.transcript_manager.transcribe_session(session_path)
            if not transcripts:
                logger.error(f"❌ Transcription failed for {audio_file.name}")
                return False
                
            # Save raw transcripts (without speaker assignment)
            self._save_raw_transcripts(transcripts, session_path, audio_file.stem)
            
            # Success
            file_duration = time.time() - file_start_time
            logger.info(f"✅ Successfully processed {audio_file.name} in {file_duration:.1f}s")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to process {audio_file.name}: {e}")
            return False
            
    def _save_raw_transcripts(self, transcripts: dict, session_path: Path, base_name: str):
        """Save raw transcripts before speaker assignment"""
        import json
        
        metadata_dir = session_path / "metadata"
        raw_transcript_file = metadata_dir / f"{base_name}_raw_transcripts.json"
        
        # Prepare data for speaker assignment
        raw_data = {
            'session_name': base_name,
            'generated_at': datetime.now().isoformat(),
            'total_segments': len(transcripts),
            'speakers_detected': list(set(t['speaker_id'] for t in transcripts.values())),
            'status': 'awaiting_speaker_assignment',
            'transcripts': transcripts
        }
        
        with open(raw_transcript_file, 'w', encoding='utf-8') as f:
            json.dump(raw_data, f, indent=2, ensure_ascii=False)
            
        logger.info(f"💾 Saved raw transcripts: {raw_transcript_file}")
        
    def generate_overnight_summary(self):
        """Generate summary of overnight processing"""
        if not self.start_time:
            return
            
        total_duration = time.time() - self.start_time
        total_files = len(self.processed_files) + len(self.failed_files)
        
        summary = f"""
🌙 OVERNIGHT PROCESSING COMPLETE
{'='*50}
⏱️  Total Time: {total_duration/3600:.1f} hours ({total_duration:.0f} seconds)
📁 Total Files: {total_files}
✅ Successfully Processed: {len(self.processed_files)}
❌ Failed: {len(self.failed_files)}
⚡ Average Time per File: {total_duration/total_files:.1f}s (if > 0)

📋 Successfully Processed Files:
"""
        for file in self.processed_files:
            summary += f"  ✅ {file}\n"
            
        if self.failed_files:
            summary += f"\n❌ Failed Files:\n"
            for file in self.failed_files:
                summary += f"  ❌ {file}\n"
                
        summary += f"""
🌅 NEXT STEPS (Morning Workflow):
1. Run: python speaker_assignment.py
2. Interactive speaker assignment with audio samples
3. Generate final meeting transcripts

📁 Output Location: {AUDIO_OUTPUT_DIR}
📦 Archived Files: {AUDIO_PROCESSED_DIR}
"""

        logger.info(summary)
        
        # Save summary to file
        summary_file = Path("overnight_processing_summary.txt")
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write(summary)
        logger.info(f"📄 Summary saved: {summary_file}")
        
    def run_overnight_processing(self):
        """Main overnight processing pipeline"""
        print("🌙 MASTER PROCESSOR - OVERNIGHT BATCH PROCESSING")
        print("=" * 60)
        print("This will process ALL audio files in 'audio in' directory")
        print("Processing includes: Speaker Diarization + Transcription")
        print("Speaker Assignment will be done interactively tomorrow morning")
        print("=" * 60)
        
        # Confirm start
        confirm = input("\n🚀 Start overnight processing? [y/N]: ").strip().lower()
        if confirm not in ['y', 'yes']:
            print("⏹️ Processing cancelled")
            return
            
        self.start_time = time.time()
        start_datetime = datetime.now()
        logger.info(f"🌙 Starting overnight processing at {start_datetime}")
        
        # Setup processors
        if not self.setup_processors():
            logger.error("❌ Failed to setup processors. Aborting.")
            return
            
        # Find files to process
        audio_files = self.find_input_files()
        if not audio_files:
            logger.info("📭 No audio files found. Nothing to process.")
            return
            
        logger.info(f"🚀 Starting batch processing of {len(audio_files)} files...")
        logger.info(f"⏰ Estimated completion: {len(audio_files) * 10} - {len(audio_files) * 30} minutes")
        
        # Process each file
        for i, audio_file in enumerate(audio_files, 1):
            logger.info(f"\n🎯 File {i}/{len(audio_files)}: {audio_file.name}")
            
            if self.process_single_file(audio_file):
                self.processed_files.append(audio_file.name)
            else:
                self.failed_files.append(audio_file.name)
                
            logger.info(f"📊 Progress: {len(self.processed_files)} success, {len(self.failed_files)} failed")
            
        # Generate final summary
        self.generate_overnight_summary()


def main():
    """Main entry point"""
    try:
        processor = MasterProcessor()
        processor.run_overnight_processing()
    except KeyboardInterrupt:
        print("\n\n⏹️ Processing interrupted by user")
        logger.info("⏹️ Overnight processing interrupted")
    except Exception as e:
        logger.error(f"❌ Unexpected error in master processor: {e}")
        raise


if __name__ == "__main__":
    main() 