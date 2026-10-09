# Installation und Einrichtung

## Systemvoraussetzungen

- **Betriebssystem:** Windows 11 (64-bit)
- **Python:** 3.8 oder höher
- **Browser:** Moderne Browser (Chrome, Firefox, Edge, Safari)
- **Bildschirm:** Mindestens 1024x768 Pixel

## Python-Empfänger Installation

### 1. Python installieren

1. Laden Sie die neueste Python-Version von [python.org](https://www.python.org/downloads/) herunter
2. Führen Sie den Installer aus
3. **Wichtig:** Aktivieren Sie die Option "Add Python to PATH"
4. Klicken Sie auf "Install Now"
5. Nach der Installation öffnen Sie eine neue Eingabeaufforderung (cmd) und überprüfen Sie die Installation:
   ```bash
   python --version
   pip --version
   ```

### 2. Projekt herunterladen

#### Option A: Git Clone (empfohlen)

```bash
cd C:\Projekte
git clone https://github.com/ThiloBerger/Optische-Datenuebertragung.git
cd Optische-Datenuebertragung
```

#### Option B: ZIP-Download

1. Laden Sie das Repository als ZIP-Datei von GitHub herunter
2. Extrahieren Sie die Datei in ein Verzeichnis Ihrer Wahl
3. Öffnen Sie die Eingabeaufforderung in diesem Verzeichnis

### 3. Abhängigkeiten installieren

Navigieren Sie zum `receiver`-Verzeichnis und installieren Sie die Abhängigkeiten:

```bash
cd receiver
pip install -r requirements.txt
```

#### Alternative: Einzelne Pakete installieren

```bash
pip install mss opencv-python pyzbar rich crc32c
```

### 4. Installation überprüfen

Führen Sie einen kurzen Test durch:

```bash
python -c "import cv2; import mss; import pyzbar; print('Alle Abhängigkeiten installiert!')"
```

## Browser-Sender Einrichtung

### 1. Dateien kopieren

Der Browser-Sender benötigt keine Installation. Kopieren Sie einfach die Dateien aus dem `sender`-Verzeichnis:

1. `index.html`
2. `sender.js`

### 2. Lokale Nutzung

Öffnen Sie die `index.html` direkt in Ihrem Browser:

- **Windows:** Doppelklick auf die Datei
- **Mac/Linux:** `open index.html` oder `xdg-open index.html`

### 3. Webserver (optional)

Für bessere Performance können Sie einen lokalen Webserver starten:

```bash
cd sender
python -m http.server 8000
```

Öffnen Sie dann `http://localhost:8000` in Ihrem Browser.

## Konfiguration

### Python-Empfänger Konfiguration

Der Empfänger kann über Kommandozeilenparameter konfiguriert werden:

```bash
# Standard-Konfiguration
python receiver.py

# Benutzerdefinierter Erfassungsbereich (top, left, width, height)
python receiver.py --area "100,100,400,400"

# Kürzeres Erfassungsintervall (Sekunden)
python receiver.py --interval 0.3

# Benutzerdefiniertes Transfer-Verzeichnis
python receiver.py --transfer-dir ./meine_transfers

# Interaktiver Modus
python receiver.py --interactive

# Alle Optionen
python receiver.py --help
```

#### Erfassungsbereich bestimmen

1. Öffnen Sie den Browser-Sender und zeigen Sie einen QR-Code an
2. Notieren Sie sich die Position und Größe des QR-Codes auf Ihrem Bildschirm
3. Verwenden Sie ein Tool wie "Screen Ruler" oder "PixelRuler", um die genauen Koordinaten zu bestimmen
4. Passen Sie die Parameter mit `--area "top,left,width,height"` an

**Beispiel:**
- QR-Code erscheint bei (200, 300) mit einer Größe von 400x400 Pixeln
- Parameter: `--area "200,300,400,400"`

### Browser-Sender Konfiguration

Die Konfiguration erfolgt direkt in der Weboberfläche:

- **Blockgröße:** Wählen Sie aus vordefinierten Werten (1 KB - 16 KB)
- **Anzeigedauer:** Wählen Sie die Dauer pro Block (0,5 - 2 Sekunden)

## Erste Schritte

### 1. Empfänger starten

Öffnen Sie eine Eingabeaufforderung und starten Sie den Empfänger:

```bash
cd C:\Projekte\Optische-Datenuebertragung\receiver
python receiver.py --area "100,100,400,400"
```

### 2. Sender vorbereiten

1. Öffnen Sie die `index.html` in Ihrem Browser
2. Wählen Sie eine Datei aus
3. Konfigurieren Sie Blockgröße und Anzeigedauer
4. Klicken Sie auf "Übertragung starten"

### 3. Übertragung durchführen

1. Positionieren Sie das Browser-Fenster so, dass der QR-Code im Erfassungsbereich des Empfängers liegt
2. Der Empfänger sollte den QR-Code erkennen und die Daten verarbeiten
3. Fortschritt wird in der Konsole angezeigt

### 4. Transfer überprüfen

Nach Abschluss der Übertragung:

```bash
# Liste aller Transfers anzeigen
python receiver.py --interactive
list

# Fehlende Blöcke anzeigen
missing <transfer_id>

# Datei-Integrität überprüfen
verify <transfer_id>
```

## Problembehandlung

### Häufige Probleme

#### 1. QR-Codes werden nicht erkannt

**Mögliche Ursachen:**
- Erfassungsbereich ist falsch konfiguriert
- Bildschirmhelligkeit oder Kontrast ist zu niedrig
- QR-Code ist zu klein

**Lösungen:**
- Passen Sie den Erfassungsbereich mit `--area` an
- Erhöhen Sie die Anzeigedauer im Sender
- Vergrößern Sie das Browser-Fenster

#### 2. Langsame Übertragung

**Mögliche Ursachen:**
- Große Blockgröße
- Lange Anzeigedauer
- Hardware-Leistung

**Lösungen:**
- Reduzieren Sie die Blockgröße (z.B. auf 2 KB)
- Reduzieren Sie die Anzeigedauer (z.B. auf 0,5 Sekunden)
- Schließen Sie andere Programme, die CPU-Ressourcen verbrauchen

#### 3. Prüfsummenfehler

**Mögliche Ursachen:**
- Bildschirmskalierung (z.B. 125%, 150%)
- Anti-Aliasing-Effekte
- Bildschirmaufnahme-Probleme

**Lösungen:**
- Stellen Sie die Bildschirmskalierung auf 100% ein
- Verwenden Sie einen anderen Browser
- Testen Sie mit kleineren Blockgrößen

#### 4. Python-Module können nicht installiert werden

**Mögliche Ursachen:**
- pip ist veraltet
- Berechtigungsprobleme
- Python-Version nicht kompatibel

**Lösungen:**
```bash
# pip aktualisieren
python -m pip install --upgrade pip

# Mit Administratorrechten installieren
pip install --user -r requirements.txt

# Virtuelle Umgebung verwenden
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### Fehlerprotokollierung

Der Empfänger protolliert alle Aktivitäten in der Datei `receiver.log`. Diese Datei kann hilfreich sein, um Probleme zu diagnostizieren:

```bash
# Log-Datei anzeigen
type receiver.log

# Letzte 100 Zeilen anzeigen
more +%((Get-Content receiver.log).Count - 100) receiver.log
```

## Leistungsoptimierung

### Durchsatz maximieren

1. **Blockgröße optimieren:**
   - Größere Blöcke = weniger Overhead
   - Kleinere Blöcke = schnellere Übertragung bei Fehlern
   - Empfohlen: 4 KB - 8 KB

2. **Anzeigedauer anpassen:**
   - Kürzere Dauer = höherer Durchsatz
   - Längere Dauer = bessere Erkennungsrate
   - Empfohlen: 0,5 - 1 Sekunde

3. **Erfassungsbereich minimieren:**
   - Kleinerer Bereich = schnellere Verarbeitung
   - Nur den QR-Code-Bereich erfassen

### Hardware-Empfehlungen

- **CPU:** Mindestens 2 Kerne, 2 GHz
- **RAM:** 4 GB oder mehr
- **Grafikkarte:** Nicht kritisch (CPU-basierte Verarbeitung)
- **Bildschirm:** 1080p oder höher für bessere QR-Code-Erkennung

## Sicherheit

### Wichtige Sicherheitshinweise

1. **Bildschirmerfassung:**
   - Der Empfänger erfasst nur den explizit definierten Bereich
   - Keine anderen Fenster oder Inhalte werden erfasst
   - Überprüfen Sie immer den Erfassungsbereich

2. **Dateiausführung:**
   - Empfangene Dateien werden NICHT automatisch ausgeführt
   - Überprüfen Sie immer die Datei-Herkunft
   - Verwenden Sie Antiviren-Software

3. **Datenintegrität:**
   - Der Empfänger überprüft die Integrität jeder Datei
   - Nur Dateien mit gültigem SHA-256 Hash werden als erfolgreich markiert

4. **Temporäre Dateien:**
   - Alle Transfer-Daten werden im `transfers`-Verzeichnis gespeichert
   - Sie können dieses Verzeichnis regelmäßig bereinigen

### Berechtigungen

Der Empfänger benötigt folgende Berechtigungen:

- **Lesezugriff:** Auf den Bildschirm (für die Erfassung)
- **Schreibzugriff:** Auf das Transfer-Verzeichnis
- **Netzwerkzugriff:** Keiner (lokaler Betrieb)

## Deinstallation

### Python-Empfänger

1. Löschen Sie das Projektverzeichnis
2. Optional: Deinstallieren Sie die Python-Pakete
   ```bash
   pip uninstall mss opencv-python pyzbar rich crc32c
   ```

### Browser-Sender

Einfach die Dateien `index.html` und `sender.js` löschen.

## Unterstützte Browser

- Google Chrome (empfohlen)
- Mozilla Firefox
- Microsoft Edge
- Safari
- Opera

## Unterstützte Betriebssysteme

- **Primär:** Windows 11 (64-bit)
- **Getestet:** Windows 10 (64-bit)
- **Experimentell:** macOS, Linux (Bildschirmerfassung kann abweichen)

## Nächste Schritte

Nach erfolgreicher Installation:

1. Lesen Sie das [Protokoll-Dokument](PROTOKOLL.md) für technische Details
2. Testen Sie mit kleinen Dateien (< 1 MB)
3. Experimentieren Sie mit verschiedenen Einstellungen
4. Dokumentieren Sie Ihre Ergebnisse
5. Für große Dateien (> 50 MB): Planen Sie ausreichend Zeit ein
