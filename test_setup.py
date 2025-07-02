#!/usr/bin/env python3
"""
Test Script für HuggingFace Setup Verification
============================================

Testet ob:
1. .env File korrekt geladen wird
2. HUGGINGFACE_TOKEN verfügbar ist
3. pyannote.audio Pipeline geladen werden kann
4. GPU Support funktioniert

Usage: python test_setup.py
"""

import os
import sys

# Load .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ .env file loaded successfully")
except ImportError:
    print("⚠️ python-dotenv not available, using system environment")
except Exception as e:
    print(f"❌ Error loading .env: {e}")

def test_token():
    """Test HuggingFace token availability"""
    print("\n🔑 Testing HuggingFace Token...")
    
    token = os.getenv('HUGGINGFACE_TOKEN')
    if not token:
        print("❌ HUGGINGFACE_TOKEN not found!")
        print("💡 Make sure your .env file contains:")
        print("   HUGGINGFACE_TOKEN=your_token_here")
        return False
    
    print(f"✅ Token found (length: {len(token)} characters)")
    print(f"   Preview: {token[:8]}...{token[-4:]}")
    return True

def test_dependencies():
    """Test required dependencies"""
    print("\n📦 Testing Dependencies...")
    
    dependencies = [
        ('torch', 'PyTorch'),
        ('pyannote.audio', 'pyannote.audio'),
        ('librosa', 'librosa'), 
        ('soundfile', 'soundfile')
    ]
    
    missing = []
    for module, name in dependencies:
        try:
            __import__(module)
            print(f"✅ {name}")
        except ImportError:
            print(f"❌ {name} - Missing!")
            missing.append(name)
    
    if missing:
        print(f"\n💡 Install missing dependencies:")
        print("pip install " + " ".join(missing))
        return False
    
    return True

def test_gpu_support():
    """Test GPU acceleration support"""
    print("\n🚀 Testing GPU Support...")
    
    try:
        import torch
        
        if torch.backends.mps.is_available():
            print("✅ Apple Silicon MPS acceleration available")
            return "mps"
        elif torch.cuda.is_available():
            print("✅ CUDA GPU acceleration available")  
            return "cuda"
        else:
            print("💻 Using CPU (no GPU acceleration)")
            return "cpu"
    except Exception as e:
        print(f"❌ Error checking GPU support: {e}")
        return None

def test_pipeline_loading():
    """Test pyannote.audio pipeline loading"""
    print("\n🧠 Testing Pipeline Loading...")
    
    token = os.getenv('HUGGINGFACE_TOKEN')
    if not token:
        print("❌ Cannot test pipeline without HuggingFace token")
        return False
    
    try:
        from pyannote.audio import Pipeline
        
        print("🔄 Loading speaker diarization pipeline...")
        print("   This may take a few minutes on first run...")
        
        pipeline = Pipeline.from_pretrained(
            "pyannote/speaker-diarization-3.1",
            use_auth_token=token
        )
        
        print("✅ Pipeline loaded successfully!")
        print("💡 Model will be cached for faster future loading")
        return True
        
    except Exception as e:
        print(f"❌ Pipeline loading failed: {e}")
        
        error_msg = str(e).lower()
        if "repository not found" in error_msg or "access" in error_msg:
            print("\n💡 Troubleshooting:")
            print("1. Accept conditions at: https://hf.co/pyannote/segmentation-3.0")
            print("2. Accept conditions at: https://hf.co/pyannote/speaker-diarization-3.1") 
            print("3. Wait 5-10 minutes after accepting conditions")
            print("4. Verify your token has 'Read' permissions")
        
        return False

def test_directory_structure():
    """Test required directory structure"""
    print("\n📁 Testing Directory Structure...")
    
    directories = [
        ("audio in", "Input directory for audio files"),
        ("audio out", "Output directory for results"), 
        ("audio_processed", "Archive directory for processed files")
    ]
    
    for dir_name, description in directories:
        if os.path.exists(dir_name):
            print(f"✅ {dir_name}/ - {description}")
        else:
            print(f"⚠️ {dir_name}/ - Missing (will be created automatically)")
    
    return True

def main():
    """Run all tests"""
    print("🎵 Speaker Diarization Setup Test")
    print("=" * 50)
    
    tests = [
        ("Token Check", test_token),
        ("Dependencies", test_dependencies), 
        ("GPU Support", test_gpu_support),
        ("Directory Structure", test_directory_structure),
        ("Pipeline Loading", test_pipeline_loading)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except KeyboardInterrupt:
            print(f"\n⏹️ Test interrupted at: {test_name}")
            break
        except Exception as e:
            print(f"❌ Unexpected error in {test_name}: {e}")
            results[test_name] = False
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Ready to process audio files.")
        print("💡 Put audio files in 'audio in/' and run: python speaker_diarization.py")
    else:
        print("\n⚠️ Some tests failed. Please fix issues before processing audio.")
        print("📖 See setup_huggingface.md for detailed instructions")

if __name__ == "__main__":
    main() 