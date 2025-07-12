#!/usr/bin/env python3
"""
🎤 Voice Cloning Demo v2.0 - State-of-the-Art Models
F5-TTS (Primary) + XTTS-v2 (Fallback) + Zonos-v0.1 (Experimental)

Compatible with Python 3.12 and M4 Pro MacBook
Optimized for maximum quality with robust fallback system
"""

import os
import sys
import time
import logging
import random
import warnings
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any
import json
import datetime

# Suppress warnings for cleaner output
warnings.filterwarnings("ignore")

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('voice_cloning_v2.log')
    ]
)
logger = logging.getLogger(__name__)

# Import dependencies with error handling
try:
    import torch
    import torchaudio
    import librosa
    import soundfile as sf
    import numpy as np
    # Fixed import for transformers
    from transformers.pipelines import pipeline
    from transformers import AutoTokenizer, AutoModel
    from huggingface_hub import hf_hub_download, snapshot_download
    # Gradio is optional for this demo
    try:
        import gradio as gr
        HAS_GRADIO = True
    except ImportError:
        HAS_GRADIO = False
        logger.warning("Gradio not available - web interface disabled")
except ImportError as e:
    logger.error(f"Failed to import required libraries: {e}")
    sys.exit(1)

class StateOfTheArtVoiceCloner:
    """
    Voice Cloning with latest State-of-the-Art models:
    1. F5-TTS (Primary) - Most realistic open source
    2. XTTS-v2 (Fallback) - Proven system  
    3. Zonos-v0.1 (Experimental) - Latest Feb 2025 model
    """
    
    def __init__(self, speaker_dir: str = "audio out/speakers/Tobias"):
        self.speaker_dir = Path(speaker_dir)
        self.device = self._setup_device()
        self.output_dir = Path("voice_cloning_output_v2")
        self.output_dir.mkdir(exist_ok=True)
        
        # Performance tracking
        self.performance_data = {
            "session_id": datetime.datetime.now().strftime("%Y%m%d_%H%M%S"),
            "models": [],
            "synthesis_times": [],
            "audio_lengths": [],
            "quality_scores": []
        }
        
        # Demo texts optimized for German and quality testing
        self.demo_texts = [
            "Hallo, das ist eine Demonstration der neuesten F5-TTS Voice Cloning Technologie.",
            "Künstliche Intelligenz revolutioniert die Sprachsynthese. Diese Stimme wurde mit nur wenigen Sekunden Referenz-Audio erstellt.",
            "Die Qualität der modernen Text-zu-Sprache-Modelle ist beeindruckend. F5-TTS erreicht eine neue Stufe des Realismus.",
            "Dies ist ein längerer Test um zu evaluieren, wie konsistent und natürlich die synthetisierte Stimme über mehrere Sätze hinweg klingt.",
            "Guten Tag! Ich hoffe, diese State-of-the-Art Voice Cloning Demonstration mit F5-TTS überzeugt Sie von der Qualität."
        ]
        
        # Initialize models
        self.f5_tts_model = None
        self.xtts_model = None
        self.zonos_model = None
        
        logger.info(f"🚀 State-of-the-Art Voice Cloner initialized")
        logger.info(f"📱 Device: {self.device}")
        logger.info(f"📁 Speaker directory: {self.speaker_dir}")
        logger.info(f"📤 Output directory: {self.output_dir}")
    
    def _setup_device(self) -> torch.device:
        """Setup optimal device for M4 Pro"""
        if torch.backends.mps.is_available():
            logger.info("✅ MPS (Metal Performance Shaders) available")
            return torch.device("mps")
        elif torch.cuda.is_available():
            logger.info("✅ CUDA available")
            return torch.device("cuda")
        else:
            logger.info("⚠️  Using CPU (MPS/CUDA not available)")
            return torch.device("cpu")
    
    def _get_speaker_samples(self) -> List[Path]:
        """Get available speaker samples"""
        if not self.speaker_dir.exists():
            logger.error(f"❌ Speaker directory not found: {self.speaker_dir}")
            return []
        
        # Find all audio files
        audio_extensions = ['.wav', '.mp3', '.m4a', '.flac']
        samples = []
        
        for ext in audio_extensions:
            samples.extend(self.speaker_dir.glob(f"*{ext}"))
        
        logger.info(f"✅ Found {len(samples)} speaker samples")
        return samples
    
    def _select_best_sample(self, samples: List[Path]) -> Optional[Path]:
        """Select best sample based on file size and name patterns"""
        if not samples:
            return None
        
        # Prefer samples with specific keywords
        preferred_keywords = ['clean', 'clear', 'good', 'best', 'quality']
        
        # Sort by preference and file size
        def sample_score(sample: Path) -> float:
            score = 0.0
            name_lower = sample.name.lower()
            
            # Bonus for preferred keywords
            for keyword in preferred_keywords:
                if keyword in name_lower:
                    score += 10.0
            
            # Bonus for reasonable file size (3-30 seconds of audio)
            try:
                size_mb = sample.stat().st_size / (1024 * 1024)
                if 0.1 <= size_mb <= 5.0:  # Reasonable size range
                    score += 5.0
            except:
                pass
            
            # Small bonus for WAV files
            if sample.suffix.lower() == '.wav':
                score += 1.0
            
            return score
        
        best_sample = max(samples, key=sample_score)
        logger.info(f"🎯 Selected best sample: {best_sample.name}")
        return best_sample
    
    def _get_concatenated_tobias_audio(self) -> Optional[Path]:
        """Get the concatenated Tobias audio file for voice cloning"""
        try:
            # Look for concatenated audio files in output directory
            pattern = "tobias_concatenated_30june_*.wav"
            
            concatenated_files = list(self.output_dir.glob(pattern))
            
            if concatenated_files:
                # Get the newest concatenated file
                newest_file = max(concatenated_files, key=lambda x: x.stat().st_mtime)
                
                # Verify file exists and has reasonable size
                if newest_file.exists() and newest_file.stat().st_size > 100000:  # > 100KB
                    logger.info(f"📁 Found concatenated Tobias audio: {newest_file.name}")
                    return newest_file
                else:
                    logger.warning(f"⚠️ Concatenated file too small: {newest_file.name}")
                    return None
            else:
                logger.warning("⚠️ No concatenated Tobias audio found - will use reference audio")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error finding concatenated audio: {e}")
            return None
    
    def _setup_f5_tts_model(self) -> bool:
        """Setup F5-TTS model (Primary)"""
        try:
            logger.info("🎵 Setting up F5-TTS model...")
            
            # Try to use f5-tts-mlx for Apple Silicon optimization
            if self.device.type == "mps":
                try:
                    logger.info("🍎 Attempting MLX optimization for Apple Silicon...")
                    from f5_tts_mlx.generate import generate
                    
                    self.f5_tts_model = {
                        "name": "F5-TTS-MLX",
                        "generate_func": generate,
                        "ready": True,
                        "type": "mlx"
                    }
                    
                    self.performance_data["models"].append("F5-TTS-MLX")
                    logger.info("✅ F5-TTS MLX model ready (Apple Silicon optimized)")
                    return True
                    
                except ImportError:
                    logger.warning("⚠️  f5-tts-mlx not available, falling back to standard F5-TTS")
            
            # Fallback to standard F5-TTS
            try:
                import f5_tts
                from f5_tts.infer.utils_infer import infer_process, load_model, load_vocoder
                from f5_tts.model import CFM
                from huggingface_hub import hf_hub_download
                
                # Download F5-TTS model files from HuggingFace
                logger.info("📥 Downloading F5-TTS model from HuggingFace...")
                ckpt_path = hf_hub_download(
                    repo_id="SWivid/F5-TTS",
                    filename="F5TTS_Base/model_1200000.safetensors"
                )
                vocab_file = hf_hub_download(
                    repo_id="SWivid/F5-TTS",
                    filename="F5TTS_Base/vocab.txt"
                )
                
                # Load F5-TTS model and vocoder
                model_cls = CFM
                model_cfg = {
                    "dim": 1024,
                    "depth": 22, 
                    "heads": 16,
                    "ff_mult": 2,
                    "text_dim": 512,
                    "conv_layers": 4
                }
                
                model = load_model(
                    model_cls=model_cls,
                    model_cfg=model_cfg, 
                    ckpt_path=ckpt_path,
                    vocab_file=vocab_file,
                    device=str(self.device)
                )
                
                vocoder = load_vocoder(
                    vocoder_name="vocos", 
                    is_local=False,
                    device=str(self.device)
                )
                
                self.f5_tts_model = {
                    "name": "F5-TTS",
                    "model": model,
                    "vocoder": vocoder,
                    "infer_func": infer_process,
                    "ready": True,
                    "type": "standard"
                }
                
                self.performance_data["models"].append("F5-TTS")
                logger.info("✅ F5-TTS standard model ready")
                return True
                
            except ImportError:
                logger.error("❌ F5-TTS library not installed. Run: pip install f5-tts")
                return False
                
        except Exception as e:
            logger.error(f"❌ F5-TTS setup failed: {e}")
            return False
    
    def _setup_xtts_model(self) -> bool:
        """Setup XTTS-v2 model (Fallback)"""
        try:
            logger.info("🎤 Setting up XTTS-v2 fallback model...")
            
            # Import TTS with better error handling
            try:
                from TTS.api import TTS
            except ImportError:
                logger.error("❌ TTS library not installed. Run: pip install TTS")
                return False
            
            # Load XTTS-v2 model
            self.xtts_model = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(self.device)
            
            self.performance_data["models"].append("XTTS-v2")
            logger.info("✅ XTTS-v2 model ready")
            return True
            
        except Exception as e:
            logger.error(f"❌ XTTS-v2 setup failed: {e}")
            return False
    
    def _setup_zonos_model(self) -> bool:
        """Setup Zonos-v0.1 model (Experimental)"""
        try:
            logger.info("🎯 Setting up Zonos-v0.1 model...")
            
            # Import Zonos modules
            from zonos.model import Zonos
            from zonos.conditioning import make_cond_dict
            
            # Zonos works best on CPU (MPS has compatibility issues)
            zonos_device = "cpu"
            logger.info("🖥️ Using CPU for Zonos (MPS compatibility issues)")
            
            # Use only the transformer model (hybrid is not supported)
            model_name = "Zyphra/Zonos-v0.1-transformer"
            logger.info(f"🤖 Using {model_name}")
            
            # Load the model
            logger.info(f"📥 Loading {model_name}...")
            model = Zonos.from_pretrained(model_name, device=zonos_device)
            
            self.zonos_model = {
                "name": model_name.split("/")[-1],
                "model": model,
                "make_cond_dict": make_cond_dict,
                "device": zonos_device,
                "ready": True
            }
            
            self.performance_data["models"].append(self.zonos_model["name"])
            logger.info(f"✅ {self.zonos_model['name']} model ready on {zonos_device}")
            return True
            
        except ImportError as e:
            logger.error(f"❌ Zonos library not installed: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Zonos setup failed: {e}")
            return False
    
    def _synthesize_with_f5_tts(self, text: str, reference_audio: Path) -> Optional[Path]:
        """Synthesize speech with F5-TTS"""
        try:
            logger.info("🎵 Synthesizing with F5-TTS...")
            
            start_time = time.time()
            
            timestamp = int(time.time())
            output_path = self.output_dir / f"f5tts_output_{timestamp}.wav"
            
            if self.f5_tts_model and self.f5_tts_model.get("ready"):
                
                if self.f5_tts_model["type"] == "mlx":
                    # Use MLX optimized version
                    generate_func = self.f5_tts_model["generate_func"]
                    
                    # Generate audio with F5-TTS MLX
                    audio = generate_func(
                        text=text,
                        ref_audio=str(reference_audio),
                        ref_text="",  # Auto-transcribe
                        output_path=str(output_path)
                    )
                    
                elif self.f5_tts_model["type"] == "standard":
                    # Use standard F5-TTS
                    infer_func = self.f5_tts_model["infer_func"]
                    model = self.f5_tts_model["model"]
                    vocoder = self.f5_tts_model["vocoder"]
                    
                    # Use F5-TTS inference with correct parameters
                    audio, spectrogram = infer_func(
                        ref_audio=str(reference_audio),
                        ref_text="",  # Auto-transcribe from audio
                        gen_text=text,
                        model_obj=model,
                        vocoder=vocoder,
                        device=str(self.device)
                    )
                    
                    # Save audio to output path
                    import soundfile as sf
                    sf.write(output_path, audio, 24000)
                
                synthesis_time = time.time() - start_time
                self.performance_data["synthesis_times"].append(synthesis_time)
                
                logger.info(f"✅ F5-TTS synthesis completed in {synthesis_time:.2f}s")
                return output_path
            
            return None
            
        except Exception as e:
            logger.error(f"❌ F5-TTS synthesis failed: {e}")
            return None
    
    def _synthesize_with_xtts(self, text: str, reference_audio: Path) -> Optional[Path]:
        """Synthesize speech with XTTS-v2"""
        try:
            logger.info("🎤 Synthesizing with XTTS-v2...")
            
            start_time = time.time()
            
            timestamp = int(time.time())
            output_path = self.output_dir / f"xtts_output_{timestamp}.wav"
            
            # XTTS-v2 synthesis
            if self.xtts_model:
                self.xtts_model.tts_to_file(
                    text=text,
                    file_path=str(output_path),
                    speaker_wav=str(reference_audio),
                    language="de"
                )
                
                synthesis_time = time.time() - start_time
                self.performance_data["synthesis_times"].append(synthesis_time)
                
                logger.info(f"✅ XTTS-v2 synthesis completed in {synthesis_time:.2f}s")
                return output_path
            
            return None
            
        except Exception as e:
            logger.error(f"❌ XTTS-v2 synthesis failed: {e}")
            return None
    
    def _synthesize_with_zonos(self, text: str, reference_audio: Path) -> Optional[Path]:
        """Synthesize speech with Zonos-v0.1 using proper voice cloning"""
        try:
            logger.info("🎯 Synthesizing with Zonos-v0.1 Voice Cloning...")
            
            start_time = time.time()
            
            timestamp = int(time.time())
            output_path = self.output_dir / f"zonos_output_{timestamp}.wav"
            
            if self.zonos_model and self.zonos_model.get("ready"):
                model = self.zonos_model["model"]
                make_cond_dict = self.zonos_model["make_cond_dict"]
                
                # Detect language (Zonos uses 'de' and 'en-us')
                language = "de" if any(char in text.lower() for char in "äöüß") or "ist" in text.lower() else "en-us"
                
                logger.info(f"🌍 Detected language: {language}")
                
                # CRITICAL FIX: Use concatenated Tobias samples for voice cloning
                concatenated_audio_path = self._get_concatenated_tobias_audio()
                
                if concatenated_audio_path:
                    logger.info(f"🎤 Using concatenated Tobias audio: {concatenated_audio_path.name}")
                    
                    # Load concatenated audio and create speaker embedding
                    import torchaudio
                    wav, sr = torchaudio.load(str(concatenated_audio_path))
                    logger.info(f"📊 Loaded concatenated audio: {wav.shape[1]/sr:.1f}s at {sr}Hz")
                    
                    # Generate speaker embedding from concatenated samples
                    logger.info("🧠 Generating speaker embedding from concatenated samples...")
                    speaker_embedding = model.make_speaker_embedding(wav, sr)
                    logger.info(f"✅ Speaker embedding generated: {speaker_embedding.shape}")
                    
                    # Create conditioning dictionary WITH speaker embedding
                    cond_dict = make_cond_dict(
                        text=text,
                        language=language,
                        speaker=speaker_embedding  # ← CRITICAL FIX: Add speaker embedding
                    )
                    
                    logger.info("🎛️ Preparing conditioning with speaker embedding...")
                    conditioning = model.prepare_conditioning(cond_dict)
                    
                else:
                    logger.warning("⚠️ No concatenated audio found, using reference audio")
                    
                    # Fallback to single reference audio
                    import torchaudio
                    wav, sr = torchaudio.load(str(reference_audio))
                    logger.info(f"📊 Loaded reference audio: {wav.shape[1]/sr:.1f}s at {sr}Hz")
                    
                    # Generate speaker embedding from reference audio
                    logger.info("🧠 Generating speaker embedding from reference audio...")
                    speaker_embedding = model.make_speaker_embedding(wav, sr)
                    logger.info(f"✅ Speaker embedding generated: {speaker_embedding.shape}")
                    
                    # Create conditioning dictionary WITH speaker embedding
                    cond_dict = make_cond_dict(
                        text=text,
                        language=language,
                        speaker=speaker_embedding  # ← CRITICAL FIX: Add speaker embedding
                    )
                    
                    logger.info("🎛️ Preparing conditioning with speaker embedding...")
                    conditioning = model.prepare_conditioning(cond_dict)
                
                # Generate audio codes
                logger.info("🔄 Generating audio with Zonos Voice Cloning...")
                codes = model.generate(conditioning)
                
                # Decode to waveform
                logger.info("🔊 Decoding to waveform...")
                wavs = model.autoencoder.decode(codes).cpu()
                
                # Save audio
                import torchaudio
                torchaudio.save(str(output_path), wavs[0], model.autoencoder.sampling_rate)
                
                synthesis_time = time.time() - start_time
                audio_length = wavs[0].shape[1] / model.autoencoder.sampling_rate
                
                self.performance_data["synthesis_times"].append(synthesis_time)
                self.performance_data["audio_lengths"].append(audio_length)
                
                logger.info(f"✅ Zonos Voice Cloning completed in {synthesis_time:.2f}s")
                logger.info(f"📊 Audio length: {audio_length:.2f}s")
                return output_path
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Zonos Voice Cloning failed: {e}")
            return None
    
    def synthesize_speech(self, text: str, reference_audio: Optional[Path] = None) -> List[Tuple[str, Path]]:
        """
        Synthesize speech with all available models
        Returns list of (model_name, output_path) tuples
        """
        if not reference_audio:
            samples = self._get_speaker_samples()
            reference_audio = self._select_best_sample(samples)
            
            if not reference_audio:
                logger.error("❌ No suitable reference audio found")
                return []
        
        logger.info(f"🎙️  Using reference audio: {reference_audio.name}")
        logger.info(f"📝 Text: {text[:100]}...")
        
        results = []
        
        # Try F5-TTS first (Primary)
        if self.f5_tts_model and self.f5_tts_model.get("ready"):
            f5_output = self._synthesize_with_f5_tts(text, reference_audio)
            if f5_output:
                results.append((self.f5_tts_model["name"], f5_output))
        
        # Try XTTS-v2 (Fallback)
        if self.xtts_model:
            xtts_output = self._synthesize_with_xtts(text, reference_audio)
            if xtts_output:
                results.append(("XTTS-v2", xtts_output))
        
        # Try Zonos-v0.1 (Experimental)
        if self.zonos_model and self.zonos_model.get("ready"):
            zonos_output = self._synthesize_with_zonos(text, reference_audio)
            if zonos_output:
                results.append(("Zonos-v0.1", zonos_output))
        
        return results
    
    def run_full_demo(self):
        """Run comprehensive demo with all models"""
        logger.info("🚀 Starting State-of-the-Art Voice Cloning Demo...")
        
        # Setup models
        logger.info("🔧 Setting up models...")
        
        f5_ready = self._setup_f5_tts_model()
        xtts_ready = self._setup_xtts_model()
        zonos_ready = self._setup_zonos_model()
        
        if not (f5_ready or xtts_ready or zonos_ready):
            logger.error("❌ No models could be set up successfully")
            return
        
        # Get speaker samples
        samples = self._get_speaker_samples()
        if not samples:
            logger.error("❌ No speaker samples found")
            return
        
        reference_audio = self._select_best_sample(samples)
        
        # Run demo with all texts
        logger.info("🎬 Running demo with all texts...")
        
        for i, text in enumerate(self.demo_texts, 1):
            logger.info(f"\n🎯 Demo {i}/{len(self.demo_texts)}")
            logger.info(f"📝 Text: {text}")
            
            results = self.synthesize_speech(text, reference_audio)
            
            if results:
                logger.info(f"✅ Generated {len(results)} audio files:")
                for model_name, output_path in results:
                    logger.info(f"   🎵 {model_name}: {output_path.name}")
            else:
                logger.warning(f"⚠️  No audio generated for demo {i}")
        
        # Save performance report
        self._save_performance_report()
        
        logger.info("🎉 Demo completed successfully!")
    
    def _save_performance_report(self):
        """Save performance report to JSON"""
        report_path = self.output_dir / f"performance_report_{self.performance_data['session_id']}.json"
        
        # Calculate statistics
        if self.performance_data["synthesis_times"]:
            avg_time = sum(self.performance_data["synthesis_times"]) / len(self.performance_data["synthesis_times"])
            max_time = max(self.performance_data["synthesis_times"])
            min_time = min(self.performance_data["synthesis_times"])
            
            self.performance_data["statistics"] = {
                "average_synthesis_time": avg_time,
                "max_synthesis_time": max_time,
                "min_synthesis_time": min_time,
                "total_demos": len(self.demo_texts),
                "models_used": len(set(self.performance_data["models"]))
            }
        
        with open(report_path, 'w') as f:
            json.dump(self.performance_data, f, indent=2)
        
        logger.info(f"📊 Performance report saved: {report_path}")

def main():
    """Main function"""
    try:
        # Create voice cloner instance
        cloner = StateOfTheArtVoiceCloner()
        
        # Run full demo
        cloner.run_full_demo()
        
    except KeyboardInterrupt:
        logger.info("⚠️  Demo interrupted by user")
    except Exception as e:
        logger.error(f"❌ Demo failed: {e}")
        raise

if __name__ == "__main__":
    main() 