# Optische Datenübertragung

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Status: Entwicklung](https://img.shields.io/badge/status-Entwicklung-orange.svg)]()

**Optische Datenübertragung zwischen Browser und lokalem Python-Empfänger**

Dieses Projekt implementiert einen Prototyp für die Übertragung von Dateien über optische Signale (Bildschirm zu Kamera) zwischen einem Browser-Sender und einem Python-Empfänger.

## 📋 Übersicht

### Architektur

```
┌─────────────────────┐         ┌─────────────────────┐
│   Browser-Sender     │         │   Python-Empfänger   │
│  (HTML/JS)           │         │                     │
│                     │         │                     │
│  • Dateiauswahl      │◄───────►│  • Bildschirmerfassung│
│  • Blockaufteilung   │  QR-   │  • QR-Code Erkennung │
│  • QR-Code Generierung│  Code  │  • Datenrekonstruktion│
│  • Anzeige           │         │  • Integritätsprüfung│
└─────────────────────┘         └─────────────────────┘
```

### Hauptmerkmale

- **Browser-basierter Sender:** Keine Installation erforderlich, funktioniert in jedem modernen Browser
- **Python-Empfänger:** Erfasst Bildschirmbereich und dekodiert QR-Codes
- **Robustes Protokoll:** Fehlererkennung, Prüfsummen, Wiederherstellung
- **Skalierbar:** Unterstützt Dateien von wenigen Bytes bis zu mehreren Gigabytes
- **Sicher:** Integritätsprüfung mit SHA-256 und CRC-32

## 🚀 Schnellstart

### 1. Python-Empfänger einrichten

```bash
# Repository klonen
cd /path/to/project
git clone https://github.com/ThiloBerger/Optische-Datenuebertragung.git
cd Optische-Datenuebertragung

# Abhängigkeiten installieren
cd receiver
pip install -r requirements.txt

# Empfänger starten
python receiver.py --area "100,100,400,400"
```

### 2. Browser-Sender öffnen

Öffnen Sie die Datei `sender/index.html` in Ihrem Browser oder starten Sie einen lokalen Webserver:

```bash
cd sender
python -m http.server 8000
# Dann öffnen: http://localhost:8000
```

### 3. Übertragung starten

1. Wählen Sie eine Datei im Browser-Sender aus
2. Konfigurieren Sie Blockgröße und Anzeigedauer
3. Positionieren Sie das Browser-Fenster so, dass der QR-Code im Erfassungsbereich des Empfängers liegt
4. Klicken Sie auf "Übertragung starten"

## 📁 Projektstruktur

```
Optische-Datenuebertragung/
├── sender/
│   ├── index.html          # Browser-Sender UI
│   └── sender.js           # Sender-Logik (QR-Code Generierung, Blockaufteilung)
│
├── receiver/
│   ├── receiver.py         # Haupt-Empfänger-Programm
│   ├── requirements.txt    # Python-Abhängigkeiten
│   └── transfers/          # Gespeicherte Transfer-Daten (wird erstellt)
│
├── docs/
│   ├── INSTALLATION.md     # Installationsanleitung
│   ├── PROTOKOLL.md        # Protokoll-Spezifikation
│   └── BEDIENUNG.md        # Bedienungsanleitung (geplant)
│
├── tests/
│   ├── test_protocol.py    # Python-Tests für das Protokoll
│   └── test_sender.html    # Browser-Tests für den Sender
│
└── README.md               # Dieses Dokument
```

## 🔧 Konfiguration

### Browser-Sender

| Parameter | Beschreibung | Standardwert | Empfohlene Werte |
|-----------|--------------|---------------|------------------|
| Blockgröße | Größe der Datenblöcke | 4 KB | 1 KB - 16 KB |
| Anzeigedauer | Dauer pro Block | 1 Sekunde | 0,5 - 2 Sekunden |

### Python-Empfänger

| Parameter | Beschreibung | Standardwert |
|-----------|--------------|---------------|
| `--area` | Erfassungsbereich (top,left,width,height) | "100,100,400,400" |
| `--interval` | Erfassungsintervall (Sekunden) | 0.5 |
| `--transfer-dir` | Verzeichnis für Transfer-Daten | "./transfers" |

**Beispiel:**
```bash
# Erfassungsbereich anpassen
python receiver.py --area "200,300,500,500"

# Kürzeres Intervall für bessere Performance
python receiver.py --interval 0.3

# Interaktiver Modus
python receiver.py --interactive
```

## 📊 Protokoll-Spezifikation

Jeder QR-Code enthält die folgenden Daten:

```
OTP:1.0:{transfer_id}:{block_number}:{total_blocks}:{data_length}:{data_base64}:{checksum}
```

### Feldbeschreibungen

| Feld | Typ | Beschreibung |
|------|-----|--------------|
| `OTP` | String | Protokoll-Präfix |
| `1.0` | String | Protokollversion |
| `transfer_id` | UUID | Eindeutige Transfer-Kennung |
| `block_number` | Integer | Blocknummer (1-basiert) |
| `total_blocks` | Integer | Gesamtzahl der Blöcke |
| `data_length` | Integer | Länge der Nutzdaten |
| `data_base64` | Base64 | Nutzdaten (Base64-kodiert) |
| `checksum` | Integer | CRC-32 Prüfsumme |

### Fehlererkennung

- **CRC-32:** Pro Block für Übertragungsfehler
- **SHA-256:** Für die gesamte Datei nach Rekonstruktion
- **Duplikaterkennung:** Doppelt empfangene Blöcke werden ignoriert
- **Fehlende Blöcke:** Werden protolliert und können manuell angefordert werden

## 🎯 Leistungsdaten

### Theoretischer Durchsatz

| Blockgröße | QR-Code Kapazität | Effektiver Durchsatz (1s/Block) |
|------------|-------------------|----------------------------------|
| 1 KB | ~700 Bytes | ~0.7 KB/s |
| 2 KB | ~1.4 KB | ~1.4 KB/s |
| 4 KB | ~2.8 KB | ~2.8 KB/s |
| 8 KB | ~2.8 KB | ~2.8 KB/s |

### Praktische Übertragungsdauer

| Dateigröße | Blockgröße | Geschätzte Blöcke | Dauer (1s/Block) |
|------------|-------------|-------------------|------------------|
| 1 MB | 4 KB | 256 | ~4,3 Minuten |
| 10 MB | 4 KB | 2.560 | ~43 Minuten |
| 50 MB | 4 KB | 12.800 | ~3,6 Stunden |
| 100 MB | 8 KB | 12.800 | ~3,6 Stunden |

### Optimierungsmöglichkeiten

1. **Kürzere Anzeigedauer:** 0,5 Sekunden pro Block verdoppelt den Durchsatz
2. **Größere Blöcke:** 8 KB Blöcke reduzieren den Overhead
3. **Bessere Erkennung:** Optimierte Bildschirmposition und -größe
4. **Eigenes Rasterformat:** Höhere Datendichte als QR-Codes (zukünftig)

## ✅ Unterstützte Funktionen

### Phase 1: Machbarkeitsnachweis ✅

- [x] Browser-Sender mit Dateiauswahl
- [x] Dateiaufteilung in Blöcke
- [x] QR-Code Generierung pro Block
- [x] Python-Empfänger mit Bildschirmerfassung
- [x] QR-Code Erkennung und Dekodierung
- [x] Grundlegende Fehlererkennung (CRC-32)

### Phase 2: Protokoll und Fehlerbehandlung ✅

- [x] Blocknummerierung und -verfolgung
- [x] CRC-32 Prüfsummen pro Block
- [x] SHA-256 Hash für Dateiintegrität
- [x] Erkennung von Duplikaten
- [x] Behandlung fehlender Blöcke
- [x] Dauerhafte Speicherung des Transfer-Zustands
- [x] Wiederaufnahme unterbrochener Transfers

### Phase 3: Dateirekonstruktion ✅

- [x] Datei aus Blöcken rekonstruieren
- [x] Integritätsprüfung der rekonstruierten Datei
- [x] Unterstützung für ZIP-Archive
- [x] Export fehlender Blöcke

### Phase 4: Leistungsoptimierung 🔄

- [x] Durchsatzmessung
- [ ] Vergleich mit eigenem Rasterformat
- [ ] Adaptive Blockgröße
- [ ] Parallele Verarbeitung

### Phase 5: Dokumentation ✅

- [x] Installationsanleitung
- [x] Protokoll-Spezifikation
- [x] Bedienungsanleitung
- [ ] API-Dokumentation

## 🧪 Tests

### Python-Tests ausführen

```bash
cd receiver
python -m pytest ../tests/test_protocol.py -v
```

### Browser-Tests

Öffnen Sie `tests/test_sender.html` in Ihrem Browser und führen Sie die verschiedenen Testkategorien aus:

1. **Grundlegende Funktionstests:** Transfer-ID, CRC-32, Block-Erstellung, QR-Format
2. **Dateiverarbeitungstests:** Kleine, mittlere und große Dateien
3. **Fehlerbehandlungstests:** Ungültige Blocknummern, Duplikate
4. **Durchsatztests:** Performance-Messungen
5. **Protokolltests:** Version, Metadaten, Prüfsummen
6. **Integritätstests:** Datenintegrität, SHA-256, Rekonstruktion

## 📦 Abhängigkeiten

### Browser-Sender

- Keine externen Abhängigkeiten
- Benötigt nur einen modernen Browser
- Verwendet CDN für QR-Code Bibliothek (qrcode.js)

### Python-Empfänger

| Paket | Version | Zweck |
|-------|---------|-------|
| `mss` | >= 9.0.0 | Bildschirmerfassung |
| `opencv-python` | >= 4.8.0 | Bildverarbeitung |
| `pyzbar` | >= 0.1.9 | QR-Code Erkennung |
| `rich` | >= 13.7.0 | Schöne Konsolenausgabe |
| `crc32c` | >= 2.2 | CRC-32 Prüfsummen |

## 🔒 Sicherheit

### Datenschutz

- **Keine automatische Ausführung:** Empfangene Dateien werden nicht automatisch ausgeführt
- **Lokale Verarbeitung:** Alle Daten bleiben auf Ihrem lokalen Rechner
- **Keine Serververbindung:** Das System funktioniert vollständig offline

### Integrität

- **CRC-32:** Jeder Block wird auf Übertragungsfehler geprüft
- **SHA-256:** Die gesamte Datei wird nach der Rekonstruktion geprüft
- **Prüfsummen:** Alle Daten werden validiert, bevor sie gespeichert werden

## 📝 Lizenz

Dieses Projekt steht unter der [MIT-Lizenz](LICENSE).

## 🤝 Beitrag

Beiträge sind willkommen! Bitte beachten Sie die folgenden Schritte:

1. Forken Sie das Repository
2. Erstellen Sie einen Feature-Branch (`git checkout -b feature/neue-funktion`)
3. Commiten Sie Ihre Änderungen (`git commit -m 'Neue Funktion hinzugefügt'`)
4. Pushen Sie zum Branch (`git push origin feature/neue-funktion`)
5. Erstellen Sie einen Pull Request

## 📞 Support

Bei Fragen oder Problemen:

1. Lesen Sie die [Dokumentation](docs/)
2. Überprüfen Sie die [Issues](https://github.com/ThiloBerger/Optische-Datenuebertragung/issues)
3. Erstellen Sie ein neues Issue mit einer detaillierten Beschreibung

## 🎉 Nächste Schritte

### Kurzfristig

- [ ] Performance-Optimierung für große Dateien
- [ ] Bessere Fehlerbehandlung und -meldungen
- [ ] GUI für den Empfänger (optional)

### Mittelfristig

- [ ] Eigenes Schwarz-Weiß-Raster für höheren Durchsatz
- [ ] Adaptive Blockgröße basierend auf Erkennungsrate
- [ ] Bidirektionale Kommunikation (Rückkanal)

### Langfristig

- [ ] Unterstützung für mehrere Dateien gleichzeitig
- [ ] Verschlüsselung der übertragenen Daten
- [ ] Komprimierung der Nutzdaten
- [ ] Mobile Empfänger-App (Android/iOS)

---

**Hinweis:** Dieses Projekt befindet sich in der aktiven Entwicklung. Die API und das Protokoll können sich noch ändern.

© 2024 Thilo Berger - Optische Datenübertragung
