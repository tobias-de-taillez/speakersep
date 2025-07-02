#!/usr/bin/env python3
"""
Meeting Transcript Manager
Converts speaker-separated audio segments to text with interactive speaker assignment
"""

import json
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional

import whisper
import pandas as pd

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Directory configuration
AUDIO_OUTPUT_DIR = Path("audio out")


class TranscriptManager:
    """Manages transcription and speaker assignment for meeting audio"""
    
    def __init__(self, whisper_model: str = "large"):
        """
        Initialize transcript manager
        
        Args:
            whisper_model: Whisper model size (tiny, base, small, medium, large)
        """
        self.whisper_model_name = whisper_model
        self.whisper_model = None
        self.transcripts = {}
        self.speaker_mappings = {}
        
    def load_whisper_model(self) -> bool:
        """Load Whisper model for transcription"""
        try:
            logger.info(f"🔄 Loading Whisper model: {self.whisper_model_name}")
            model_sizes = {"tiny": "17MB", "base": "140MB", "small": "460MB", "medium": "1.4GB", "large": "3GB"}
            size = model_sizes.get(self.whisper_model_name, "unknown")
            logger.info(f"📥 First time: Downloading model (~{size})")
            logger.info(f"⏳ This may take 2-20 minutes depending on model size and internet connection...")
            logger.info(f"🚀 Note: 'large' model provides the BEST German transcription quality available!")
            
            self.whisper_model = whisper.load_model(self.whisper_model_name)
            logger.info(f"✅ Model loaded successfully")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to load Whisper model: {e}")
            return False
    
    def find_processed_sessions(self) -> List[Path]:
        """Find all processed audio sessions in output directory"""
        sessions = []
        if not AUDIO_OUTPUT_DIR.exists():
            logger.info("📭 No audio output directory found")
            return sessions
            
        for item in AUDIO_OUTPUT_DIR.iterdir():
            if item.is_dir() and (item / "segments").exists():
                sessions.append(item)
        
        logger.info(f"📁 Found {len(sessions)} processed sessions")
        return sessions
    
    def transcribe_session(self, session_path: Path) -> Dict:
        """Transcribe all segments in a session"""
        if not self.whisper_model:
            if not self.load_whisper_model():
                return {}
        
        segments_dir = session_path / "segments"
        metadata_dir = session_path / "metadata"
        
        # Load existing timeline for timing information
        timeline_file = metadata_dir / f"{session_path.name}_timeline.csv"
        if not timeline_file.exists():
            logger.error(f"❌ Timeline file not found: {timeline_file}")
            return {}
        
        timeline_df = pd.read_csv(timeline_file)
        
        transcripts = {}
        segment_files = sorted(segments_dir.glob("*.wav"))
        
        logger.info(f"🎤 Transcribing {len(segment_files)} segments...")
        logger.info(f"⏳ Estimated time: {len(segment_files) * 5}-{len(segment_files) * 15} seconds (with 'tiny' model)")
        
        import time
        start_time = time.time()
        
        for i, segment_file in enumerate(segment_files, 1):
            elapsed = time.time() - start_time
            avg_time_per_segment = elapsed / i if i > 1 else 0
            remaining_segments = len(segment_files) - i
            estimated_remaining = remaining_segments * avg_time_per_segment if avg_time_per_segment > 0 else 0
            
            logger.info(f"📋 Progress: {i}/{len(segment_files)} - {segment_file.name}")
            if estimated_remaining > 0:
                logger.info(f"⏱️ Estimated remaining time: {estimated_remaining:.1f} seconds")
            
            try:
                # Extract timing info from filename
                # Format: basename_SPEAKER_XX_001_9.1s-9.2s.wav
                filename_pattern = r"(.+)_(SPEAKER_\d+)_(\d+)_(\d+\.\d+)s-(\d+\.\d+)s\.wav"
                match = re.match(filename_pattern, segment_file.name)
                
                if not match:
                    logger.warning(f"⚠️ Could not parse filename: {segment_file.name}")
                    continue
                
                base_name, speaker_id, segment_num, start_time, end_time = match.groups()
                start_time, end_time = float(start_time), float(end_time)
                
                # Transcribe segment
                result = self.whisper_model.transcribe(str(segment_file))
                text = result["text"].strip()
                
                if text:  # Only keep non-empty transcriptions
                    transcripts[segment_file.name] = {
                        'speaker_id': speaker_id,
                        'start_time': start_time,
                        'end_time': end_time,
                        'duration': end_time - start_time,
                        'text': text,
                        'confidence': result.get('confidence', 0.0),
                        'language': result.get('language', 'unknown')
                    }
                    logger.debug(f"✅ {speaker_id}: {text[:50]}...")
                else:
                    logger.debug(f"⚠️ Empty transcription for {segment_file.name}")
                    
            except Exception as e:
                logger.error(f"❌ Failed to transcribe {segment_file.name}: {e}")
        
        logger.info(f"✅ Transcribed {len(transcripts)}/{len(segment_files)} segments")
        return transcripts
    
    def save_raw_transcripts(self, transcripts: Dict, session_path: Path, session_name: str) -> Path:
        """Save raw transcripts for later speaker assignment"""
        metadata_dir = session_path / "metadata"
        raw_transcript_file = metadata_dir / f"{session_name}_raw_transcripts.json"
        
        # Prepare data for speaker assignment
        raw_data = {
            'session_name': session_name,
            'generated_at': datetime.now().isoformat(),
            'total_segments': len(transcripts),
            'speakers_detected': list(set(t['speaker_id'] for t in transcripts.values())),
            'status': 'awaiting_speaker_assignment',
            'transcripts': transcripts
        }
        
        with open(raw_transcript_file, 'w', encoding='utf-8') as f:
            json.dump(raw_data, f, indent=2, ensure_ascii=False)
            
        logger.info(f"💾 Saved raw transcripts: {raw_transcript_file}")
        logger.info(f"🌅 Next: Run 'python speaker_assignment.py' for interactive speaker assignment")
        
        return raw_transcript_file
    
    def generate_final_transcript(self, transcripts: Dict, speaker_mappings: Dict, session_name: str) -> Dict:
        """Generate final transcript with speaker names and timestamps"""
        if not transcripts:
            return {}
        
        # Sort transcripts by start time
        sorted_transcripts = sorted(
            transcripts.items(),
            key=lambda x: x[1]['start_time']
        )
        
        final_transcript = {
            'session_name': session_name,
            'generated_at': datetime.now().isoformat(),
            'total_segments': len(sorted_transcripts),
            'speakers': list(speaker_mappings.values()),
            'speaker_mappings': speaker_mappings,
            'transcript': []
        }
        
        for segment_file, data in sorted_transcripts:
            speaker_name = speaker_mappings.get(data['speaker_id'], data['speaker_id'])
            
            entry = {
                'timestamp': data['start_time'],
                'timestamp_formatted': f"{int(data['start_time']//60):02d}:{int(data['start_time']%60):02d}",
                'duration': data['duration'],
                'speaker': speaker_name,
                'text': data['text']
            }
            
            final_transcript['transcript'].append(entry)
        
        return final_transcript
    
    def save_transcript(self, transcript: Dict, output_file: Path):
        """Save transcript in multiple formats"""
        base_path = output_file.parent / output_file.stem
        
        # 1. Save as JSON (complete data)
        json_file = base_path.with_suffix('.json')
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(transcript, f, indent=2, ensure_ascii=False)
        logger.info(f"💾 Saved JSON transcript: {json_file}")
        
        # 2. Save as readable text format
        txt_file = base_path.with_suffix('.txt')
        with open(txt_file, 'w', encoding='utf-8') as f:
            f.write(f"Meeting Transcript: {transcript['session_name']}\n")
            f.write(f"Generated: {transcript['generated_at']}\n")
            f.write(f"Speakers: {', '.join(transcript['speakers'])}\n")
            f.write("=" * 80 + "\n\n")
            
            for entry in transcript['transcript']:
                f.write(f"[{entry['timestamp_formatted']}] {entry['speaker']}: {entry['text']}\n\n")
        
        logger.info(f"📄 Saved text transcript: {txt_file}")
        
        # 3. Save as CSV for analysis
        csv_file = base_path.with_suffix('.csv')
        transcript_df = pd.DataFrame(transcript['transcript'])
        transcript_df.to_csv(csv_file, index=False, encoding='utf-8')
        logger.info(f"📊 Saved CSV transcript: {csv_file}")
        
        return {
            'json': json_file,
            'txt': txt_file,
            'csv': csv_file
        }
    
    def process_session_transcription_only(self, session_path: Path) -> Optional[Path]:
        """Transcription-only processing (speaker assignment done separately)"""
        logger.info(f"🎬 Transcribing session: {session_path.name}")
        
        # Transcribe all segments
        transcripts = self.transcribe_session(session_path)
        if not transcripts:
            logger.error("❌ No transcripts generated")
            return None
        
        # Save raw transcripts for later speaker assignment
        raw_transcript_file = self.save_raw_transcripts(transcripts, session_path, session_path.name)
        
        logger.info(f"✅ Transcription complete! Raw transcripts saved.")
        logger.info(f"🌅 Next: Use 'python speaker_assignment.py' for interactive speaker assignment")
        
        return raw_transcript_file


def main():
    """Main entry point"""
    print("🎤 Meeting Transcript Manager")
    print("=" * 50)
    
    # Initialize manager
    manager = TranscriptManager()
    
    # Find available sessions
    sessions = manager.find_processed_sessions()
    if not sessions:
        print("📭 No processed audio sessions found.")
        print("💡 Run speaker_diarization.py first to process audio files.")
        return
    
    # Show available sessions
    print(f"\n📁 Available Sessions:")
    for i, session in enumerate(sessions, 1):
        print(f"  {i}. {session.name}")
    
    # Session selection
    while True:
        try:
            choice = input(f"\n🎯 Select session to transcribe (1-{len(sessions)}, 'all' for all sessions): ").strip().lower()
            
            if choice == 'all':
                selected_sessions = sessions
                break
            else:
                session_num = int(choice)
                if 1 <= session_num <= len(sessions):
                    selected_sessions = [sessions[session_num - 1]]
                    break
                else:
                    print(f"❌ Please enter a number between 1 and {len(sessions)}")
        except ValueError:
            print("❌ Please enter a valid number or 'all'")
    
    # Process selected sessions
    for session in selected_sessions:
        try:
            manager.process_session_transcription_only(session)
        except KeyboardInterrupt:
            print("\n\n⏹️ Processing interrupted by user")
            break
        except Exception as e:
            logger.error(f"❌ Failed to process {session.name}: {e}")
    
    print("\n🎉 Transcript processing complete!")


if __name__ == "__main__":
    main() 