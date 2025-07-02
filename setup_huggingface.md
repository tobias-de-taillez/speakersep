# HuggingFace Setup für Speaker Diarization

## Voraussetzungen
Das Speaker Diarization Script benötigt Zugang zu den pyannote.audio Modellen auf HuggingFace.

## Setup-Schritte

### 1. HuggingFace Account erstellen
- Gehe zu https://huggingface.co
- Erstelle einen kostenlosen Account

### 2. Access Token generieren  
- Besuche https://huggingface.co/settings/tokens
- Erstelle einen neuen Token mit "Read" Berechtigung
- **WICHTIG**: Aktiviere "Access to public gated repositories" ✅
- **Token sicher aufbewahren!**

### 3. Model User Conditions akzeptieren
**Wichtig**: Du musst die Nutzungsbedingungen für beide Modelle akzeptieren:

#### Segmentation Model:
- Gehe zu https://huggingface.co/pyannote/segmentation-3.0
- Klicke auf "Agree and access repository"
- Akzeptiere die Bedingungen

#### Speaker Diarization Model:
- Gehe zu https://huggingface.co/pyannote/speaker-diarization-3.1  
- Klicke auf "Agree and access repository"
- Akzeptiere die Bedingungen

### 4. Token konfigurieren

#### Option A: Environment Variable (empfohlen)
```bash
export HUGGINGFACE_TOKEN="your_token_here"
```

#### Option B: In ~/.bashrc oder ~/.zshrc dauerhaft setzen
```bash
echo 'export HUGGINGFACE_TOKEN="your_token_here"' >> ~/.zshrc
source ~/.zshrc
```

#### Option C: .env Datei (für lokale Entwicklung)
```bash
echo "HUGGINGFACE_TOKEN=your_token_here" > .env
```

## Verification
Nach dem Setup kannst du testen:

```bash
python -c "
import os
from pyannote.audio import Pipeline
token = os.getenv('HUGGINGFACE_TOKEN')
pipeline = Pipeline.from_pretrained('pyannote/speaker-diarization-3.1', use_auth_token=token)
print('✅ Setup erfolgreich!')
"
```

## Troubleshooting

### "Repository not found" Error
- Stelle sicher, dass du die User Conditions für **beide** Modelle akzeptiert hast
- Überprüfe, dass dein Token korrekt gesetzt ist

### "Invalid token" Error  
- Generiere einen neuen Token
- Stelle sicher, dass der Token "Read" Berechtigung hat

### "Access denied" Error
- Akzeptiere die Model-Bedingungen erneut
- Warte 5-10 Minuten nach der Akzeptierung

### "403 Forbidden" oder "gated repositories" Error
- **Häufigster Fehler!** Token braucht spezielle Berechtigung
- Gehe zu https://huggingface.co/settings/tokens
- Klicke auf deinen Token → Scroll zu "Permissions"
- Aktiviere "Access to public gated repositories" ✅
- Speichere die Änderungen

## Nächste Schritte
Nach erfolgreichem Setup:
```bash
python speaker_diarization.py
``` 