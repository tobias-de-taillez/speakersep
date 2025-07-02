# Speaker Separation Library

## Projektziel
Entwicklung einer Library zur automatischen Zerlegung von Meeting-Transkript-Audio-Files in einzelne Sprecher.

## KERN-DIREKTIVE Protokoll
Alle Änderungen folgen dem 3-Phasen-Protokoll:
1. **ANALYZE & PLAN** - Vollständige Analyse, Planung, IN BEARBEITUNG Changelog-Eintrag
2. **EXECUTE & DOCUMENT** - Implementierung mit Dokumentation, Changelog-Update  
3. **REFLECT & UPDATE** - Validierung, Changelog-Finalisierung, master.md Update

## Changelog

### Abgeschlossen
- [INIT] Repository-Initialisierung und Grundstruktur
  - master.md mit KERN-DIREKTIVE Protokoll erstellt
  - Git repository initialisiert 
  - Initial commit erstellt
  - GitHub Repository erstellt: https://github.com/tobias-de-taillez/speakersep
  - Code erfolgreich auf GitHub gepusht

- [SETUP] Development Environment Setup
  - Python 3.12 virtual environment erstellt (Python 3.13 inkompatibel mit sentencepiece)
  - pyannote.audio 3.3.2 erfolgreich installiert mit allen Dependencies
  - Test-Skript erstellt und validiert - alle Core-Features funktional
  - MPS (Apple Silicon) GPU-Support verfügbar
  - Basis für Speaker Diarization Pipeline etabliert
  - Audio Input/Output Ordner struktur erstellt (git-ignore konfiguriert)

- [IMPL] Speaker Diarization Pipeline Implementation
  - speaker_diarization.py - Comprehensive processing pipeline erstellt
  - pyannote.audio 3.1 integration mit state-of-the-art performance
  - Structured output: RTTM, CSV, JSON formats + individual speaker segments
  - Batch processing mit MPS/CUDA GPU acceleration support
  - Comprehensive logging und error handling
  - Audio workflow: "audio in/" → processing → "audio_out/" (results) → "audio_processed/" (archive)
  - setup_huggingface.md - Complete setup guide für HuggingFace integration
  - librosa + soundfile dependencies für Audio segment extraction

### IN BEARBEITUNG
- [TEST] HuggingFace setup und erste Test-Läufe mit echten Audio-Files

## Technische Spezifikation

### Kern-Framework: pyannote.audio
**Gefunden auf: [GitHub](https://github.com/pyannote/pyannote-audio) (7.8k Stars)**
- **Version 3.1**: State-of-the-art speaker diarization (deutlich besser als 2.x)
- **Benchmark Performance**: 9.0-50.0% DER je nach Dataset (siehe GitHub)
- **GPU Support**: CUDA + Apple Silicon MPS acceleration  
- **Pretrained Models**: Verfügbar über HuggingFace Model Hub
- **Requirements**: HuggingFace Token + User Conditions Acceptance

### Pipeline-Architektur
```
Audio Input → pyannote.audio Pipeline → Multi-Format Output
├── "audio in/"           ├── segmentation-3.0      ├── metadata/
│   └── *.wav,mp3,etc    ├── speaker-diarization-3.1  │   ├── *.rttm (standard)
│                        └── MPS/CUDA acceleration     │   ├── *_timeline.csv  
├── Processing                                         │   ├── *_diarization.json
│   ├── Speaker detection                             │   └── *_summary.json
│   ├── Timeline generation                           └── segments/
│   └── Segment extraction                                └── *_speaker_X_*.wav
│
└── Archive: "audio_processed/"
```

### Output-Formate
- **RTTM**: Rich Transcription Time Marked (Industrie-Standard)
- **CSV**: Timeline für Excel/Analyse (start, end, duration, speaker)  
- **JSON**: Programmatischer Zugriff mit Metadata
- **Segments**: Einzelne WAV-Files pro Speaker-Segment
- **Summary**: Statistiken (Sprecher-Anzahl, Redezeit-Verteilung, etc.)

### Performance-Benchmarks (von pyannote.audio)
| Dataset | v2.1 DER | v3.1 DER | Verbesserung |
|---------|----------|----------|--------------|
| Earnings21 | 17.0% | 9.4% | -45% |  
| DIHARD 3 | 26.9% | 21.7% | -19% |
| AMI (SDM) | 27.1% | 22.4% | -17% |
| VoxConverse | 11.2% | 11.3% | ~0% |

## Entwicklungsrichtlinien
- Code und Comments in Englisch
- Präzise, pessimistische Herangehensweise für bessere Iteration
- Technische Details priorisiert über generische Ratschläge
- Direkte, konkrete Lösungsansätze 