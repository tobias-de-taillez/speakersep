#!/usr/bin/env python3
"""
Test script for pyannote.audio installation
Verifies basic functionality without requiring audio files or HuggingFace tokens
"""

def test_imports():
    """Test that all core modules can be imported"""
    try:
        import pyannote.audio
        print(f"✅ pyannote.audio version: {pyannote.audio.__version__}")
        
        from pyannote.audio import Pipeline
        print("✅ Pipeline import successful")
        
        from pyannote.core import Segment, Timeline
        print("✅ Core classes import successful")
        
        import torch
        print(f"✅ PyTorch version: {torch.__version__}")
        
        # Check if CUDA/MPS available
        if torch.cuda.is_available():
            print("✅ CUDA available")
        elif torch.backends.mps.is_available():
            print("✅ MPS (Apple Silicon) available")
        else:
            print("ℹ️  Running on CPU")
            
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def test_basic_functionality():
    """Test basic pyannote functionality without external dependencies"""
    try:
        from pyannote.core import Segment, Timeline
        
        # Test Segment creation
        segment = Segment(start=0.0, end=5.0)
        print(f"✅ Created segment: {segment}")
        
        # Test Timeline creation
        timeline = Timeline([
            Segment(0.0, 2.0),
            Segment(3.0, 5.0)
        ])
        print(f"✅ Created timeline with {len(timeline)} segments")
        
        # Test timeline operations
        duration = timeline.duration()
        print(f"✅ Timeline duration: {duration:.1f}s")
        
        return True
        
    except Exception as e:
        print(f"❌ Functionality test error: {e}")
        return False

def main():
    print("=== pyannote.audio Installation Test ===\n")
    
    print("1. Testing imports...")
    imports_ok = test_imports()
    
    print("\n2. Testing basic functionality...")
    functionality_ok = test_basic_functionality()
    
    print(f"\n=== Test Summary ===")
    if imports_ok and functionality_ok:
        print("✅ All tests passed! pyannote.audio is ready to use.")
        print("\nNext steps:")
        print("- Get HuggingFace access token for pretrained models")
        print("- Test with actual audio files")
        print("- Explore speaker diarization pipeline")
        return 0
    else:
        print("❌ Some tests failed. Check installation.")
        return 1

if __name__ == "__main__":
    exit(main()) 