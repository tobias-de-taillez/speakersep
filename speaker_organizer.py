#!/usr/bin/env python3
"""
Speaker Organizer for Fine-Tuning Preparation
Organizes speaker segments by speaker name across all completed sessions
Prepares data for fine-tuning speaker diarization on recurring company speakers
"""

import json
import logging
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Set
from datetime import datetime
import pandas as pd

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Directory configuration
AUDIO_OUTPUT_DIR = Path("audio out")
SPEAKERS_DIR = AUDIO_OUTPUT_DIR / "speakers"


class SpeakerOrganizer:
    """Organizes speaker segments by speaker name for fine-tuning"""
    
    def __init__(self):
        """Initialize speaker organizer"""
        self.completed_sessions = []
        self.speaker_segments = {}  # {speaker_name: [segment_info]}
        self.speaker_stats = {}     # {speaker_name: stats}
        
    def find_completed_sessions(self, use_raw_transcripts: bool = False) -> List[Path]:
        """Find all completed sessions with transcripts"""
        sessions = []
        
        if not AUDIO_OUTPUT_DIR.exists():
            logger.info("📭 No audio output directory found")
            return sessions
            
        for session_dir in AUDIO_OUTPUT_DIR.iterdir():
            if not session_dir.is_dir() or session_dir.name == "speakers":
                continue
                
            metadata_dir = session_dir / "metadata"
            
            if use_raw_transcripts:
                # Check for raw transcripts (SPEAKER_XX format)
                raw_transcript_file = metadata_dir / f"{session_dir.name}_raw_transcripts.json"
                if raw_transcript_file.exists():
                    sessions.append(session_dir)
            else:
                # Check for final transcript (real speaker names)
                final_transcript_file = metadata_dir / f"{session_dir.name}_final_transcript.json"
                if final_transcript_file.exists():
                    sessions.append(session_dir)
                
        session_type = "raw transcript" if use_raw_transcripts else "final transcript"
        logger.info(f"📁 Found {len(sessions)} sessions with {session_type}")
        return sessions
        
    def load_session_speaker_mappings(self, session_path: Path, use_raw_transcripts: bool = False) -> Optional[Dict]:
        """Load speaker mappings from transcript file"""
        try:
            metadata_dir = session_path / "metadata"
            
            if use_raw_transcripts:
                # Load from raw transcripts (SPEAKER_XX format)
                transcript_file = metadata_dir / f"{session_path.name}_raw_transcripts.json"
                with open(transcript_file, 'r', encoding='utf-8') as f:
                    transcript_data = json.load(f)
                
                # Create identity mappings for SPEAKER_XX
                speakers_detected = transcript_data.get('speakers_detected', [])
                speaker_mappings = {speaker: speaker for speaker in speakers_detected}
                
                # Convert raw transcripts to final transcript format
                sorted_transcripts = sorted(
                    transcript_data['transcripts'].items(),
                    key=lambda x: x[1]['start_time']
                )
                
                transcript_entries = []
                for segment_file, data in sorted_transcripts:
                    entry = {
                        'timestamp': data['start_time'],
                        'timestamp_formatted': f"{int(data['start_time']//60):02d}:{int(data['start_time']%60):02d}",
                        'duration': data['duration'],
                        'speaker': data['speaker_id'],  # Use SPEAKER_XX as name
                        'text': data['text']
                    }
                    transcript_entries.append(entry)
                
                final_transcript_data = {
                    'session_name': session_path.name,
                    'speaker_mappings': speaker_mappings,
                    'transcript': transcript_entries
                }
                
                logger.info(f"✅ Loaded {len(speaker_mappings)} speakers from raw transcripts: {session_path.name}")
                
            else:
                # Load from final transcript (real speaker names)
                transcript_file = metadata_dir / f"{session_path.name}_final_transcript.json"
                with open(transcript_file, 'r', encoding='utf-8') as f:
                    final_transcript_data = json.load(f)
                
                speaker_mappings = final_transcript_data.get('speaker_mappings', {})
                if not speaker_mappings:
                    logger.warning(f"⚠️ No speaker mappings found in {session_path.name}")
                    return None
                    
                logger.info(f"✅ Loaded {len(speaker_mappings)} speaker mappings from final transcript: {session_path.name}")
            
            return {
                'session_name': session_path.name,
                'speaker_mappings': speaker_mappings,
                'transcript_data': final_transcript_data
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to load transcript data from {session_path.name}: {e}")
            return None
            
    def collect_speaker_segments(self, session_data: Dict) -> bool:
        """Collect all segments for each speaker from a session"""
        try:
            session_name = session_data['session_name']
            speaker_mappings = session_data['speaker_mappings']
            transcript_data = session_data['transcript_data']
            
            # Get session path
            session_path = AUDIO_OUTPUT_DIR / session_name
            segments_dir = session_path / "segments"
            
            if not segments_dir.exists():
                logger.warning(f"⚠️ No segments directory found for {session_name}")
                return False
                
            # Process each transcript entry
            for entry in transcript_data.get('transcript', []):
                speaker_id = None
                speaker_name = entry.get('speaker', '')
                
                # Find corresponding speaker_id for this speaker_name
                for sid, sname in speaker_mappings.items():
                    if sname == speaker_name:
                        speaker_id = sid
                        break
                        
                if not speaker_id:
                    logger.warning(f"⚠️ Could not find speaker_id for {speaker_name} in {session_name}")
                    continue
                    
                # Find matching segment files
                segment_pattern = f"*_{speaker_id}_*_{entry['timestamp']:.1f}s-*.wav"
                matching_segments = list(segments_dir.glob(segment_pattern))
                
                if not matching_segments:
                    # Try alternative pattern matching
                    segment_pattern = f"*_{speaker_id}_*.wav"
                    all_speaker_segments = list(segments_dir.glob(segment_pattern))
                    
                    # Filter by timestamp
                    matching_segments = []
                    for seg in all_speaker_segments:
                        if f"{entry['timestamp']:.1f}s" in seg.name:
                            matching_segments.append(seg)
                
                # Add segments to speaker collection
                for segment_file in matching_segments:
                    if speaker_name not in self.speaker_segments:
                        self.speaker_segments[speaker_name] = []
                        
                    segment_info = {
                        'session_name': session_name,
                        'speaker_id': speaker_id,
                        'file_path': segment_file,
                        'timestamp': entry['timestamp'],
                        'duration': entry['duration'],
                        'text': entry['text']
                    }
                    
                    self.speaker_segments[speaker_name].append(segment_info)
                    
            logger.info(f"✅ Collected segments from {session_name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to collect segments from {session_data['session_name']}: {e}")
            return False
            
    def organize_speaker_directories(self) -> bool:
        """Create speaker directories and copy segments"""
        try:
            # Create speakers directory
            SPEAKERS_DIR.mkdir(exist_ok=True)
            logger.info(f"📁 Created speakers directory: {SPEAKERS_DIR}")
            
            for speaker_name, segments in self.speaker_segments.items():
                # Create speaker directory
                speaker_dir = SPEAKERS_DIR / speaker_name
                speaker_dir.mkdir(exist_ok=True)
                
                logger.info(f"👤 Organizing {len(segments)} segments for {speaker_name}")
                
                # Copy segments to speaker directory
                copied_count = 0
                for segment_info in segments:
                    source_file = segment_info['file_path']
                    
                    if not source_file.exists():
                        logger.warning(f"⚠️ Source file not found: {source_file}")
                        continue
                        
                    # Create new filename with session info
                    new_filename = f"{segment_info['session_name']}_{source_file.name}"
                    dest_file = speaker_dir / new_filename
                    
                    # Copy file if it doesn't exist
                    if not dest_file.exists():
                        try:
                            shutil.copy2(source_file, dest_file)
                            copied_count += 1
                        except Exception as e:
                            logger.warning(f"⚠️ Failed to copy {source_file.name}: {e}")
                    else:
                        logger.debug(f"📄 Already exists: {new_filename}")
                        
                logger.info(f"✅ Copied {copied_count} new segments for {speaker_name}")
                
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to organize speaker directories: {e}")
            return False
            
    def generate_speaker_profiles(self) -> bool:
        """Generate speaker profiles with statistics"""
        try:
            for speaker_name, segments in self.speaker_segments.items():
                # Calculate statistics
                total_segments = len(segments)
                total_duration = sum(seg['duration'] for seg in segments)
                sessions_involved = set(seg['session_name'] for seg in segments)
                
                # Average duration
                avg_duration = total_duration / total_segments if total_segments > 0 else 0
                
                # Session breakdown
                session_stats = {}
                for session_name in sessions_involved:
                    session_segments = [seg for seg in segments if seg['session_name'] == session_name]
                    session_stats[session_name] = {
                        'segments': len(session_segments),
                        'duration': sum(seg['duration'] for seg in session_segments)
                    }
                
                # Create speaker profile
                speaker_profile = {
                    'speaker_name': speaker_name,
                    'generated_at': datetime.now().isoformat(),
                    'total_segments': total_segments,
                    'total_duration_seconds': total_duration,
                    'total_duration_minutes': total_duration / 60,
                    'average_segment_duration': avg_duration,
                    'sessions_involved': len(sessions_involved),
                    'session_breakdown': session_stats,
                    'sessions_list': sorted(list(sessions_involved))
                }
                
                # Save speaker profile
                speaker_dir = SPEAKERS_DIR / speaker_name
                profile_file = speaker_dir / f"{speaker_name}_profile.json"
                
                with open(profile_file, 'w', encoding='utf-8') as f:
                    json.dump(speaker_profile, f, indent=2, ensure_ascii=False)
                    
                self.speaker_stats[speaker_name] = speaker_profile
                logger.info(f"📊 Generated profile for {speaker_name}: {total_segments} segments, {total_duration:.1f}s")
                
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to generate speaker profiles: {e}")
            return False
            
    def generate_overall_summary(self) -> bool:
        """Generate overall summary of speaker organization"""
        try:
            total_speakers = len(self.speaker_segments)
            total_segments = sum(len(segments) for segments in self.speaker_segments.values())
            total_duration = sum(
                sum(seg['duration'] for seg in segments) 
                for segments in self.speaker_segments.values()
            )
            
            # Create summary
            summary = {
                'generated_at': datetime.now().isoformat(),
                'total_speakers': total_speakers,
                'total_segments': total_segments,
                'total_duration_seconds': total_duration,
                'total_duration_minutes': total_duration / 60,
                'total_duration_hours': total_duration / 3600,
                'sessions_processed': len(self.completed_sessions),
                'speakers_summary': {}
            }
            
            # Add per-speaker summary
            for speaker_name, profile in self.speaker_stats.items():
                summary['speakers_summary'][speaker_name] = {
                    'segments': profile['total_segments'],
                    'duration_minutes': profile['total_duration_minutes'],
                    'sessions': profile['sessions_involved']
                }
                
            # Save summary
            summary_file = SPEAKERS_DIR / "speakers_summary.json"
            with open(summary_file, 'w', encoding='utf-8') as f:
                json.dump(summary, f, indent=2, ensure_ascii=False)
                
            # Log summary
            logger.info(f"📊 SPEAKER ORGANIZATION SUMMARY:")
            logger.info(f"👥 Total Speakers: {total_speakers}")
            logger.info(f"🎵 Total Segments: {total_segments}")
            logger.info(f"⏱️ Total Duration: {total_duration/60:.1f} minutes ({total_duration/3600:.1f} hours)")
            logger.info(f"📁 Sessions Processed: {len(self.completed_sessions)}")
            logger.info(f"💾 Summary saved: {summary_file}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to generate overall summary: {e}")
            return False
            
    def organize_all_speakers(self, use_raw_transcripts: bool = False) -> bool:
        """Main method to organize all speakers"""
        transcript_type = "raw transcripts (SPEAKER_XX)" if use_raw_transcripts else "final transcripts (real names)"
        logger.info(f"🗂️ Starting speaker organization using {transcript_type}...")
        
        # Find completed sessions
        self.completed_sessions = self.find_completed_sessions(use_raw_transcripts)
        if not self.completed_sessions:
            if use_raw_transcripts:
                logger.info("📭 No sessions with raw transcripts found. Run master_processor.py first.")
            else:
                logger.info("📭 No sessions with final transcripts found. Run speaker_assignment.py first.")
            return False
            
        # Process each session
        for session_path in self.completed_sessions:
            session_data = self.load_session_speaker_mappings(session_path, use_raw_transcripts)
            if session_data:
                self.collect_speaker_segments(session_data)
                
        if not self.speaker_segments:
            logger.warning("⚠️ No speaker segments collected")
            return False
            
        # Organize directories
        if not self.organize_speaker_directories():
            return False
            
        # Generate profiles
        if not self.generate_speaker_profiles():
            return False
            
        # Generate overall summary
        if not self.generate_overall_summary():
            return False
            
        logger.info("🎉 Speaker organization completed successfully!")
        logger.info(f"📁 Organized speakers available in: {SPEAKERS_DIR}")
        logger.info("🤖 Ready for fine-tuning preparation!")
        
        return True


def main():
    """Main function for command line usage"""
    organizer = SpeakerOrganizer()
    
    # Check what transcript types are available
    final_sessions = organizer.find_completed_sessions(use_raw_transcripts=False)
    raw_sessions = organizer.find_completed_sessions(use_raw_transcripts=True)
    
    print("🗂️ SPEAKER ORGANIZER")
    print("=" * 50)
    print("Organize speaker segments for fine-tuning preparation")
    print("=" * 50)
    
    if not final_sessions and not raw_sessions:
        logger.error("❌ No sessions found with transcripts")
        logger.info("💡 Run master_processor.py first to process audio files")
        return 1
    
    # Show available options
    print(f"📊 Available Sessions:")
    print(f"   • Final transcripts (real names): {len(final_sessions)} sessions")
    print(f"   • Raw transcripts (SPEAKER_XX): {len(raw_sessions)} sessions")
    
    use_raw_transcripts = False
    
    if final_sessions and raw_sessions:
        # User can choose
        print(f"\n🎯 Choose transcript type:")
        print(f"   1. Final transcripts (real speaker names)")
        print(f"   2. Raw transcripts (SPEAKER_XX format)")
        
        while True:
            try:
                choice = input(f"\nSelect option (1-2): ").strip()
                if choice == "1":
                    use_raw_transcripts = False
                    break
                elif choice == "2":
                    use_raw_transcripts = True
                    break
                else:
                    print("❌ Please enter 1 or 2")
            except (ValueError, KeyboardInterrupt):
                print("\n👋 Goodbye!")
                return 0
                
    elif raw_sessions and not final_sessions:
        # Only raw transcripts available
        use_raw_transcripts = True
        print(f"\n🎯 Using raw transcripts (SPEAKER_XX format)")
        print(f"💡 Run speaker_assignment.py to create real speaker names")
        
    elif final_sessions and not raw_sessions:
        # Only final transcripts available
        use_raw_transcripts = False
        print(f"\n🎯 Using final transcripts (real speaker names)")
    
    # Execute organization
    success = organizer.organize_all_speakers(use_raw_transcripts)
    
    if success:
        logger.info("✅ Speaker organization completed successfully!")
        logger.info("🎯 Next steps:")
        logger.info("   1. Review speaker directories in 'audio out/speakers/'")
        logger.info("   2. Use organized samples for fine-tuning speaker diarization")
        if use_raw_transcripts:
            logger.info("   3. Consider running speaker_assignment.py for real speaker names")
        logger.info("   4. Run this tool again after processing new sessions")
    else:
        logger.error("❌ Speaker organization failed")
        return 1
        
    return 0


if __name__ == "__main__":
    exit(main()) 