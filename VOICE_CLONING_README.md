# 🎤 Voice Cloning Setup für M4 Pro MacBook

## 🚀 Schnellstart

```bash
# 1. Setup ausführen
./setup_voice_cloning.sh

# 2. Demo starten
python voice_cloning_demo.py
```

## 📋 Voraussetzungen

- ✅ **MacBook M4 Pro** (oder andere Apple Silicon)
- ✅ **Python 3.9+** installiert
- ✅ **Tobias Speaker-Samples** in `audio out/speakers/Tobias/`
- ✅ **8GB+ freier RAM** für optimale Performance

## 🎯 Was macht das Setup?

### 🔧 Automatische Installation:
- **PyTorch mit MPS-Support** für Apple Silicon
- **OpenVoice-kompatible Models** (via HuggingFace Transformers)
- **XTTS-v2** als bewährtes Fallback-System
- **Audio-Processing Libraries** (librosa, soundfile)
- **Performance-Monitoring** und Fehlerbehandlung

### 🎬 Demo-Tests:
- **5 verschiedene Texte** mit Tobias-Stimme
- **Qualitäts-Vergleich** zwischen OpenVoice und XTTS-v2
- **Performance-Benchmarks** auf M4 Pro
- **Automatische Tobias-Sample-Auswahl**

## 📊 Erwartete Performance

| **Metric** | **OpenVoice** | **XTTS-v2** |
|------------|---------------|--------------|
| **Synthese-Zeit** | ~2-5s pro Satz | ~3-8s pro Satz |
| **Memory-Usage** | ~2-4GB | ~1-3GB |
| **Qualität** | Exzellent | Sehr gut |
| **Stabilität** | Experimentell | Bewährt |

## 🎤 Verwendung

### Basis-Synthese:
```python
from voice_cloning_demo import VoiceCloningDemo

demo = VoiceCloningDemo()
demo.run_full_demo()
```

### Manueller Test:
```python
# XTTS-v2 (empfohlen für Produktion)
from TTS.api import TTS

tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to("mps")
tts.tts_to_file(
    text="Hallo, das ist meine geklonte Stimme!",
    file_path="output.wav",
    speaker_wav="audio out/speakers/Tobias/best_sample.wav",
    language="de"
)
```

## 📁 Output-Struktur

```
voice_cloning_output/
├── openvoice_output_1234567890.wav      # OpenVoice Synthese
├── xtts_output_1234567890.wav           # XTTS-v2 Synthese
└── voice_cloning_report.json            # Performance-Report
```

## 🔧 Troubleshooting

### ❌ "MPS not available"
```bash
# Prüfe PyTorch Installation
python3 -c "import torch; print(torch.__version__)"

# Neuinstallation
pip install torch torchvision torchaudio
```

### ❌ "No Tobias samples found"
```bash
# Prüfe Tobias-Verzeichnis
ls "audio out/speakers/Tobias/"

# Führe Speaker-Organisation aus
python speaker_organizer.py
```

### ❌ "Out of memory"
```bash
# Reduziere Batch-Size oder schließe andere Apps
# Monitoring:
top -pid $(pgrep Python)
```

## 🎯 Demo-Texte

Das Demo testet folgende Texte:
1. "Hallo, das ist ein Test meiner synthetisierten Stimme mit OpenVoice auf dem M4 Pro."
2. "Künstliche Intelligenz ermöglicht es uns, Stimmen mit nur wenigen Sekunden Audio zu klonen."
3. "Die Qualität der Sprachsynthese ist beeindruckend und wird immer besser."
4. "Dies ist ein längerer Text um zu testen, wie konsistent die Stimme über mehrere Sätze bleibt."
5. "Guten Tag! Ich hoffe, die Stimm-Synthese klingt natürlich und authentisch."

## 📈 Performance-Optimierung

### M4 Pro spezifische Tips:
- ✅ **MPS-Acceleration nutzen** für GPU-Beschleunigung
- ✅ **Unified Memory** effizient nutzen
- ✅ **Andere Apps schließen** für optimale Performance
- ✅ **Activity Monitor** für Memory-Monitoring

### Code-Optimierungen:
```python
import torch

# Memory-Cleanup nach jeder Synthese
if torch.backends.mps.is_available():
    torch.mps.empty_cache()

# Batch-Size reduzieren bei Memory-Problemen
batch_size = 1  # Statt 4 oder 8
```

## 🎛️ Erweiterte Konfiguration

### Custom Demo-Texte:
```python
demo = VoiceCloningDemo()
demo.demo_texts = [
    "Ihr eigener Text hier",
    "Weitere Texte für Tests"
]
demo.run_full_demo()
```

### Andere Sprecher:
```python
demo = VoiceCloningDemo()
demo.speaker_dir = Path("audio out/speakers/Elisabeth")
demo.run_full_demo()
```

## 🚨 Bekannte Limitierungen

- **OpenVoice**: Experimentelle Technologie, könnte instabil sein
- **XTTS-v2**: Benötigt mindestens 6-Sekunden-Audio-Clips
- **Memory**: Kann bei langen Texten viel RAM verbrauchen
- **Deutsch**: Möglicherweise weniger optimiert als Englisch

## 🆘 Support

Bei Problemen:
1. **Logs prüfen**: Detaillierte Fehlermeldungen im Terminal
2. **System-Check**: `python3 -c "import torch; print(torch.backends.mps.is_available())"`
3. **Fallback nutzen**: XTTS-v2 wenn OpenVoice Probleme macht
4. **Memory-Monitor**: Activity Monitor für RAM-Usage

## 🎉 Erfolg!

Nach erfolgreichem Setup können Sie:
- ✅ **Ihre eigene Stimme klonen** mit wenigen Sekunden Audio
- ✅ **Beliebige Texte** in Ihrer Stimme synthetisieren
- ✅ **Performance-optimiert** auf M4 Pro nutzen
- ✅ **Qualitäts-Vergleiche** zwischen verschiedenen Models

**Happy Voice Cloning! 🎤** 