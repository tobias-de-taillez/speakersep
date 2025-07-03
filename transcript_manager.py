#!/usr/bin/env python3
"""
Meeting Transcript Manager
Converts speaker-separated audio segments to text with interactive speaker assignment
Uses OpenAI Whisper-large-v3 via HuggingFace Transformers for best quality
"""

import json
import logging
import os
import re
import torch
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional

import pandas as pd
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline

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
    
    def __init__(self, whisper_model: str = "openai/whisper-large-v3"):
        """
        Initialize transcript manager
        
        Args:
            whisper_model: Whisper model ID (default: openai/whisper-large-v3)
        """
        self.whisper_model_name = whisper_model
        self.whisper_pipeline = None
        self.device = None
        self.torch_dtype = None
        self.transcripts = {}
        self.speaker_mappings = {}
        
    def _setup_device_and_dtype(self):
        """Setup optimal device and data type for current hardware"""
        if torch.cuda.is_available():
            self.device = "cuda"
            self.torch_dtype = torch.float16
            logger.info("🚀 Using CUDA GPU acceleration")
        elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            self.device = "mps"
            self.torch_dtype = torch.float16
            logger.info("🚀 Using Apple Silicon MPS acceleration")
        else:
            self.device = "cpu"
            self.torch_dtype = torch.float32
            logger.info("💻 Using CPU (no GPU acceleration available)")
        
    def load_whisper_model(self) -> bool:
        """Load Whisper-large-v3 model via HuggingFace Transformers"""
        try:
            self._setup_device_and_dtype()
            
            logger.info(f"🔄 Loading Whisper model: {self.whisper_model_name}")
            logger.info(f"📥 Model size: ~3GB (Whisper-large-v3 with 10-20% better accuracy)")
            logger.info(f"⏳ First time: Downloading model may take 5-15 minutes...")
            logger.info(f"🎯 Note: This is the LATEST and BEST Whisper model for German transcription!")
            
            # Load model and processor
            model = AutoModelForSpeechSeq2Seq.from_pretrained(
                self.whisper_model_name,
                torch_dtype=self.torch_dtype,
                low_cpu_mem_usage=True,
                use_safetensors=True
            )
            model.to(self.device)
            
            processor = AutoProcessor.from_pretrained(self.whisper_model_name)
            
            # Create pipeline with optimized settings
            self.whisper_pipeline = pipeline(
                "automatic-speech-recognition",
                model=model,
                tokenizer=processor.tokenizer,
                feature_extractor=processor.feature_extractor,
                torch_dtype=self.torch_dtype,
                device=self.device,
                return_timestamps=True
            )
            
            logger.info(f"✅ Whisper-large-v3 loaded successfully on {self.device}")
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
        """Transcribe all segments in a session using Whisper-large-v3"""
        if not self.whisper_pipeline:
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
        
        logger.info(f"🎤 Transcribing {len(segment_files)} segments with Whisper-large-v3...")
        logger.info(f"⏳ Estimated time: {len(segment_files) * 3}-{len(segment_files) * 8} seconds (GPU-accelerated)")
        
        import time
        start_time = time.time()
        
        # Prepare generation kwargs for best quality
        generate_kwargs = {
            "language": "german",
            "task": "transcribe",
            "return_timestamps": True,
            "max_new_tokens": 400,  # Reduced from 448 to stay under token limit
            "num_beams": 1,
            "condition_on_prev_tokens": False,
            "compression_ratio_threshold": 1.35,
            "temperature": (0.0, 0.2, 0.4, 0.6, 0.8, 1.0),
            "logprob_threshold": -1.0,
            "no_speech_threshold": 0.6
        }
        
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
                
                # Transcribe segment with Whisper-large-v3
                result = self.whisper_pipeline(
                    str(segment_file),
                    generate_kwargs=generate_kwargs
                )
                
                text = result["text"].strip()
                
                if text:  # Only keep non-empty transcriptions
                    transcripts[segment_file.name] = {
                        'speaker_id': speaker_id,
                        'start_time': start_time,
                        'end_time': end_time,
                        'duration': end_time - start_time,
                        'text': text,
                        'confidence': 1.0,  # Transformers doesn't provide confidence scores
                        'language': 'german',
                        'model': 'whisper-large-v3'
                    }
                    logger.debug(f"✅ {speaker_id}: {text[:50]}...")
                else:
                    logger.debug(f"⚠️ Empty transcription for {segment_file.name}")
                    
            except Exception as e:
                logger.error(f"❌ Failed to transcribe {segment_file.name}: {e}")
        
        logger.info(f"✅ Transcribed {len(transcripts)}/{len(segment_files)} segments with Whisper-large-v3")
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
            'model_used': 'whisper-large-v3',
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
            'model_used': 'whisper-large-v3',
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
        if not transcript or not transcript.get('transcript'):
            logger.warning("⚠️ No transcript data to save")
            return
        
        # JSON format (structured data)
        json_file = output_file.with_suffix('.json')
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(transcript, f, indent=2, ensure_ascii=False)
        logger.info(f"💾 Saved JSON transcript: {json_file}")
        
        # TXT format (human readable)
        txt_file = output_file.with_suffix('.txt')
        with open(txt_file, 'w', encoding='utf-8') as f:
            f.write(f"Meeting Transcript: {transcript['session_name']}\n")
            f.write(f"Generated: {transcript['generated_at']}\n")
            f.write(f"Model: {transcript.get('model_used', 'whisper-large-v3')}\n")
            f.write(f"Speakers: {', '.join(transcript['speakers'])}\n")
            f.write("=" * 50 + "\n\n")
            
            for entry in transcript['transcript']:
                f.write(f"[{entry['timestamp_formatted']}] {entry['speaker']}: {entry['text']}\n")
        logger.info(f"📝 Saved TXT transcript: {txt_file}")
        
        # CSV format (for analysis)
        csv_file = output_file.with_suffix('.csv')
        transcript_df = pd.DataFrame(transcript['transcript'])
        transcript_df.to_csv(csv_file, index=False, encoding='utf-8')
        logger.info(f"📊 Saved CSV transcript: {csv_file}")
    
    def process_session_transcription_only(self, session_path: Path) -> Optional[Path]:
        """Process session for transcription only (no interactive assignment)"""
        session_name = session_path.name
        logger.info(f"🎤 Processing session for transcription: {session_name}")
        
        # Transcribe all segments
        transcripts = self.transcribe_session(session_path)
        
        if not transcripts:
            logger.error(f"❌ No transcripts generated for {session_name}")
            return None
        
        # Save raw transcripts for later assignment
        raw_transcript_file = self.save_raw_transcripts(transcripts, session_path, session_name)
        
        logger.info(f"✅ Session transcription completed: {session_name}")
        logger.info(f"📂 Raw transcripts saved: {raw_transcript_file}")
        logger.info(f"🌅 Next step: Run 'python speaker_assignment.py' for interactive speaker naming")
        
        return raw_transcript_file


def main():
    """Main function for command line usage"""
    import sys
    
    transcript_manager = TranscriptManager()
    sessions = transcript_manager.find_processed_sessions()
    
    if not sessions:
        logger.info("📭 No processed sessions found")
        logger.info("💡 Run speaker diarization first: python speaker_diarization.py")
        return
    
    # Show available sessions
    logger.info("📋 Available sessions:")
    for i, session in enumerate(sessions, 1):
        logger.info(f"  {i}. {session.name}")
    
    # Session selection
    if len(sessions) == 1:
        selected_session = sessions[0]
        logger.info(f"🎯 Auto-selected: {selected_session.name}")
    else:
        try:
            choice = input("\nSelect session number (or 'q' to quit): ").strip()
            if choice.lower() == 'q':
                return
            
            session_idx = int(choice) - 1
            if 0 <= session_idx < len(sessions):
                selected_session = sessions[session_idx]
            else:
                logger.error("❌ Invalid session number")
                return
        except (ValueError, KeyboardInterrupt):
            logger.info("👋 Goodbye!")
            return
    
    # Process selected session
    result = transcript_manager.process_session_transcription_only(selected_session)
    
    if result:
        logger.info("🎉 Transcription completed successfully!")
        logger.info("🌅 Run 'python speaker_assignment.py' next for interactive speaker assignment")
    else:
        logger.error("❌ Transcription failed")
        sys.exit(1)


if __name__ == "__main__":
    main() 