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

### IN BEARBEITUNG
- [ARCH] Speaker separation library Architektur-Definition und Implementierung

## Technische Spezifikation

### Anforderungen
- Audio-Input: Meeting-Aufnahmen (WAV, MP3, etc.)
- Output: Getrennte Audio-Streams pro identifizierten Sprecher
- Unterstützung für variable Sprecheranzahl
- Echtzeit-Verarbeitung optional

### Architektur
*TBD - wird während Entwicklung definiert*

## Entwicklungsrichtlinien
- Code und Comments in Englisch
- Präzise, pessimistische Herangehensweise für bessere Iteration
- Technische Details priorisiert über generische Ratschläge
- Direkte, konkrete Lösungsansätze 