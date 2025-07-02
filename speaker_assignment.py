#!/usr/bin/env python3
"""
Interactive Speaker Assignment with Audio Playback
Morning workflow tool for assigning real names to detected speakers
"""

import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import pandas as pd
from datetime import datetime

# Audio playback
try:
    import pygame
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False
    print("⚠️ pygame not available. Audio playback disabled.")
    print("💡 Install with: pip install pygame")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Directory configuration
AUDIO_OUTPUT_DIR = Path("audio out")


class SpeakerAssignmentTool:
    """Interactive tool for speaker assignment with audio playback"""
    
    def __init__(self):
        """Initialize speaker assignment tool"""
        self.sessions = []
        self.current_session = None
        self.current_transcripts = {}
        self.current_speaker_mappings = {}
        
        # Initialize audio if available
        if AUDIO_AVAILABLE:
            try:
                pygame.mixer.init()
                logger.info("🔊 Audio playback enabled")
            except Exception as e:
                logger.warning(f"⚠️ Failed to initialize audio: {e}")
                global AUDIO_AVAILABLE
                AUDIO_AVAILABLE = False
        
    def find_sessions_awaiting_assignment(self) -> List[Path]:
        """Find sessions that need speaker assignment"""
        sessions = []
        
        if not AUDIO_OUTPUT_DIR.exists():
            logger.info("📭 No audio output directory found")
            return sessions
            
        for session_dir in AUDIO_OUTPUT_DIR.iterdir():
            if not session_dir.is_dir():
                continue
                
            # Check for raw transcripts file
            metadata_dir = session_dir / "metadata"
            raw_file = metadata_dir / f"{session_dir.name}_raw_transcripts.json"
            
            if raw_file.exists():
                try:
                    with open(raw_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if data.get('status') == 'awaiting_speaker_assignment':
                            sessions.append(session_dir)
                except Exception as e:
                    logger.warning(f"⚠️ Failed to read {raw_file}: {e}")
                    
        logger.info(f"📁 Found {len(sessions)} sessions awaiting speaker assignment")
        return sessions
        
    def load_session_data(self, session_path: Path) -> bool:
        """Load transcripts and session data"""
        try:
            metadata_dir = session_path / "metadata"
            raw_file = metadata_dir / f"{session_path.name}_raw_transcripts.json"
            
            with open(raw_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            self.current_session = session_path
            self.current_transcripts = data['transcripts']
            self.current_speaker_mappings = {}
            
            logger.info(f"✅ Loaded session: {session_path.name}")
            logger.info(f"📊 {len(self.current_transcripts)} segments, {len(data['speakers_detected'])} speakers")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to load session data: {e}")
            return False
            
    def find_audio_samples_for_speaker(self, speaker_id: str) -> List[Tuple[Path, dict]]:
        """Find audio segments for a specific speaker"""
        if not self.current_session:
            return []
            
        segments_dir = self.current_session / "segments"
        speaker_files = []
        
        # Find segments for this speaker with transcript data
        for segment_file, transcript_data in self.current_transcripts.items():
            if transcript_data['speaker_id'] == speaker_id:
                segment_path = segments_dir / segment_file
                if segment_path.exists():
                    speaker_files.append((segment_path, transcript_data))
                    
        # Sort by duration (prefer longer segments first) and limit to 3
        speaker_files.sort(key=lambda x: x[1]['duration'], reverse=True)
        return speaker_files[:3]
        
    def play_audio_sample(self, audio_file: Path) -> bool:
        """Play an audio sample"""
        if not AUDIO_AVAILABLE:
            print("⚠️ Audio playback not available")
            return False
            
        try:
            print(f"🔊 Playing: {audio_file.name}")
            pygame.mixer.music.load(str(audio_file))
            pygame.mixer.music.play()
            
            # Wait for playback to finish or user interrupt
            while pygame.mixer.music.get_busy():
                pygame.time.wait(100)
                # Check for user interrupt (this is basic - could be improved)
                
            return True
            
        except Exception as e:
            print(f"❌ Failed to play audio: {e}")
            return False
            
    def interactive_speaker_assignment(self) -> Dict[str, str]:
        """Interactive CLI for speaker assignment with audio samples"""
        if not self.current_transcripts:
            logger.warning("⚠️ No transcripts available for speaker assignment")
            return {}
            
        # Get unique speakers
        speakers = list(set(t['speaker_id'] for t in self.current_transcripts.values()))
        speakers.sort()  # Consistent ordering
        
        print("\n" + "="*80)
        print("🎭 INTERACTIVE SPEAKER ASSIGNMENT WITH AUDIO SAMPLES")
        print("="*80)
        print("Review text samples and listen to audio before assigning real names")
        print("🔊 Audio controls: Each speaker will have 3 sample audio clips")
        print("💡 Tip: Longer segments usually have clearer voice characteristics")
        print("-"*80)
        
        for speaker_id in speakers:
            print(f"\n🔊 {speaker_id}")
            print("="*40)
            
            # Get audio samples for this speaker
            audio_samples = self.find_audio_samples_for_speaker(speaker_id)
            
            if not audio_samples:
                print(f"⚠️ No audio samples found for {speaker_id}")
                continue
                
            # Show text samples with timing
            print("📝 Text Samples:")
            for i, (audio_file, transcript_data) in enumerate(audio_samples, 1):
                duration = transcript_data['duration']
                start_time = transcript_data['start_time']
                text = transcript_data['text']
                
                print(f"  {i}. [{start_time:.1f}s, {duration:.1f}s] {text[:100]}{'...' if len(text) > 100 else ''}")
                
            # Audio playback options
            if AUDIO_AVAILABLE:
                print(f"\n🎵 Audio Samples Available:")
                for i, (audio_file, transcript_data) in enumerate(audio_samples, 1):
                    print(f"  {i}. {audio_file.name} ({transcript_data['duration']:.1f}s)")
                    
                print(f"\n🎮 Controls:")
                print(f"  • Enter 1-{len(audio_samples)} to play audio sample")
                print(f"  • Enter speaker name when ready")
                print(f"  • Enter 'skip' to use default ID")
                
                while True:
                    user_input = input(f"\n🎯 Play sample (1-{len(audio_samples)}) or enter speaker name: ").strip()
                    
                    # Check if it's a sample number
                    try:
                        sample_num = int(user_input)
                        if 1 <= sample_num <= len(audio_samples):
                            audio_file, _ = audio_samples[sample_num - 1]
                            print(f"\n▶️ Playing sample {sample_num}...")
                            self.play_audio_sample(audio_file)
                            print("✅ Playback finished")
                            continue
                        else:
                            print(f"❌ Please enter a number between 1 and {len(audio_samples)}")
                            continue
                    except ValueError:
                        # Not a number, treat as speaker name
                        real_name = user_input
                        break
            else:
                # No audio available, just ask for name
                real_name = input(f"\n👤 Enter real name for {speaker_id} (or 'skip' for default): ").strip()
                
            # Process speaker name
            if real_name.lower() in ['skip', '']:
                real_name = speaker_id
            elif not real_name.replace(' ', '').replace('-', '').replace('_', '').isalnum():
                print("⚠️ Using letters, numbers, spaces, hyphens, and underscores only")
                real_name = speaker_id
                
            self.current_speaker_mappings[speaker_id] = real_name
            print(f"✅ {speaker_id} → {real_name}")
            
        print("\n" + "="*80)
        print("🎉 Speaker Assignment Complete!")
        for speaker_id, real_name in self.current_speaker_mappings.items():
            print(f"  • {speaker_id} → {real_name}")
        print("="*80)
        
        return self.current_speaker_mappings
        
    def generate_final_transcript(self, speaker_mappings: Dict[str, str], session_name: str) -> Dict:
        """Generate final transcript with speaker names and timestamps"""
        if not self.current_transcripts:
            return {}
            
        # Sort transcripts by start time
        sorted_transcripts = sorted(
            self.current_transcripts.items(),
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
        
    def save_final_transcript(self, transcript: Dict, output_file: Path):
        """Save final transcript in multiple formats"""
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
        
    def process_session(self, session_path: Path) -> bool:
        """Process a single session with speaker assignment"""
        logger.info(f"🎬 Processing session: {session_path.name}")
        
        # Load session data
        if not self.load_session_data(session_path):
            return False
            
        # Interactive speaker assignment
        speaker_mappings = self.interactive_speaker_assignment()
        if not speaker_mappings:
            logger.warning("⚠️ No speaker mappings created")
            return False
            
        # Generate final transcript
        final_transcript = self.generate_final_transcript(speaker_mappings, session_path.name)
        if not final_transcript:
            logger.error("❌ Failed to generate final transcript")
            return False
            
        # Save final transcript
        output_file = session_path / "metadata" / f"{session_path.name}_final_transcript"
        saved_files = self.save_final_transcript(final_transcript, output_file)
        
        # Mark session as completed
        self._mark_session_completed(session_path)
        
        logger.info(f"🎉 Session processing complete!")
        logger.info(f"📁 Files saved: {', '.join(saved_files.keys())}")
        
        return True
        
    def _mark_session_completed(self, session_path: Path):
        """Mark session as completed by updating raw transcript status"""
        try:
            metadata_dir = session_path / "metadata" 
            raw_file = metadata_dir / f"{session_path.name}_raw_transcripts.json"
            
            if raw_file.exists():
                with open(raw_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                data['status'] = 'completed'
                data['completed_at'] = datetime.now().isoformat()
                
                with open(raw_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                    
                logger.info(f"✅ Marked session as completed: {session_path.name}")
                
        except Exception as e:
            logger.warning(f"⚠️ Failed to mark session as completed: {e}")
            
    def run_interactive_assignment(self):
        """Main interactive assignment workflow"""
        print("🎭 SPEAKER ASSIGNMENT TOOL")
        print("=" * 50)
        print("Interactive assignment of real names to detected speakers")
        if AUDIO_AVAILABLE:
            print("🔊 Audio playback: ENABLED")
        else:
            print("⚠️ Audio playback: DISABLED (install pygame for audio)")
        print("=" * 50)
        
        # Find sessions needing assignment
        sessions = self.find_sessions_awaiting_assignment()
        if not sessions:
            print("📭 No sessions found awaiting speaker assignment.")
            print("💡 Run master_processor.py first to process audio files.")
            return
            
        # Show available sessions
        print(f"\n📁 Sessions Awaiting Assignment:")
        for i, session in enumerate(sessions, 1):
            print(f"  {i}. {session.name}")
            
        # Session selection
        while True:
            try:
                choice = input(f"\n🎯 Select session (1-{len(sessions)}, 'all' for all): ").strip().lower()
                
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
                print(f"\n{'='*80}")
                print(f"🎬 SESSION: {session.name}")
                print(f"{'='*80}")
                
                if not self.process_session(session):
                    logger.error(f"❌ Failed to process {session.name}")
                    
            except KeyboardInterrupt:
                print("\n\n⏹️ Processing interrupted by user")
                break
            except Exception as e:
                logger.error(f"❌ Failed to process {session.name}: {e}")
                
        print("\n🎉 Speaker assignment complete!")


def main():
    """Main entry point"""
    try:
        tool = SpeakerAssignmentTool()
        tool.run_interactive_assignment()
    except KeyboardInterrupt:
        print("\n\n⏹️ Assignment interrupted by user")
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        raise


if __name__ == "__main__":
    main() 