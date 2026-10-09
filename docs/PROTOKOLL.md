# Optisches Übertragungsprotokoll

## Übersicht

Dieses Dokument beschreibt das Binärprotokoll für die optische Datenübertragung zwischen Browser-Sender und Python-Empfänger. Das Protokoll verwendet QR-Codes als Übertragungsmedium.

## Protokollversion

- **Aktuelle Version:** `1.0`
- **Kompatibilität:** Abwärtskompatibel zu zukünftigen Versionen mit Versionsprüfung

## QR-Code Datenformat

Jeder QR-Code enthält die folgenden Daten im angegebenen Format:

```
OTP:{version}:{transfer_id}:{block_number}:{total_blocks}:{data_length}:{data}:{checksum}
```

### Feldbeschreibungen

| Feld | Typ | Beschreibung | Beispiel |
|------|-----|--------------|----------|
| `OTP` | String | Protokoll-Präfix (konstant) | `OTP` |
| `version` | String | Protokollversion | `1.0` |
| `transfer_id` | UUID | Eindeutige Transfer-Kennung | `550e8400-e29b-41d4-a716-446655440000` |
| `block_number` | Integer | Blocknummer (1-basiert) | `1` |
| `total_blocks` | Integer | Gesamtzahl der Blöcke | `1024` |
| `data_length` | Integer | Länge der Nutzdaten in Bytes | `4096` |
| `data` | Base64 | Nutzdaten (Base64-kodiert) | `SGVsbG8gV29ybGQh...` |
| `checksum` | Integer | CRC-32 Prüfsumme der Nutzdaten | `2924712495` |

### Beispiel-QR-Code-Inhalt

```
OTP:1.0:550e8400-e29b-41d4-a716-446655440000:1:1024:4096:SGVsbG8gV29ybGQh:2924712495
```

## Blockstruktur

### Block-Metadaten

Jeder Block enthält die folgenden Metadaten:

- **Transfer-ID:** Eindeutige Kennung für die gesamte Übertragung (UUID v4)
- **Blocknummer:** Sequenznummer des Blocks (1-basiert)
- **Gesamtzahl Blöcke:** Gesamtzahl der Blöcke in diesem Transfer
- **Datenlänge:** Länge der Nutzdaten in diesem Block
- **Prüfsumme:** CRC-32 Prüfsumme der Nutzdaten

### Nutzdaten

- **Format:** Binärdaten
- **Kodierung:** Base64 für die QR-Code-Übertragung
- **Maximale Größe:** Konfigurierbar (Standard: 4 KB)

## Fehlererkennung und -behandlung

### CRC-32 Prüfsumme

- **Algorithmus:** Standard CRC-32 (Polynom: 0xEDB88320)
- **Anwendung:** Pro Block
- **Zweck:** Erkennung von Übertragungsfehlern

### SHA-256 Hash

- **Algorithmus:** SHA-256
- **Anwendung:** Für die gesamte Datei nach Rekonstruktion
- **Zweck:** Integritätsprüfung der rekonstruierten Datei

## Fehlerfälle und Behandlung

### 1. Fehlendes Bild

**Erkennung:** Block wird nicht innerhalb der Timeout-Zeit empfangen
**Behandlung:** 
- Block wird als fehlend markiert
- Transfer bleibt aktiv, bis alle Blöcke empfangen oder manuell abgebrochen
- Fehlende Blöcke können später manuell angefordert werden

### 2. Doppelt empfangenes Bild

**Erkennung:** Blocknummer bereits in `received_blocks` vorhanden
**Behandlung:**
- Duplikat wird ignoriert
- Zähler für Duplikate wird erhöht
- Gültiger Block wird nicht überschrieben

### 3. Falsche Reihenfolge

**Erkennung:** Blocknummer ist kleiner als die höchste bereits empfangene Blocknummer
**Behandlung:**
- Block wird trotzdem gespeichert
- Reihenfolge wird erst bei der Rekonstruktion berücksichtigt
- Blöcke werden nach Blocknummer sortiert

### 4. Beschädigte Nutzdaten

**Erkennung:** CRC-32 Prüfsumme stimmt nicht überein
**Behandlung:**
- Block wird als ungültig markiert
- Zähler für ungültige Blöcke wird erhöht
- Block wird nicht gespeichert

### 5. Falsche Transfer-ID

**Erkennung:** Transfer-ID stimmt nicht mit einem aktiven Transfer überein
**Behandlung:**
- Neuer Transfer wird erstellt (falls erste Block)
- Block wird dem entsprechenden Transfer zugeordnet

### 6. Unvollständiger Transfer

**Erkennung:** Nicht alle Blöcke wurden empfangen
**Behandlung:**
- Transfer bleibt im aktiven Zustand
- Fehlende Blöcke können exportiert werden
- Transfer kann später fortgesetzt werden

### 7. Unterbrochener Sender oder Empfänger

**Erkennung:** Programm wird beendet
**Behandlung:**
- Transfer-Zustand wird auf Festplatte gespeichert
- Bei Neustart werden aktive Transfers geladen
- Übertragung kann fortgesetzt werden

### 8. Erneute Übertragung einzelner Blöcke

**Erkennung:** Manuelle Anforderung über Browser-Sender
**Behandlung:**
- Sender zeigt spezifischen Block an
- Empfänger erkennt und verarbeitet den Block
- Duplikate werden ignoriert

### 9. Wiederaufnahme nach Programmneustart

**Erkennung:** Vorhandene Transfer-Daten auf Festplatte
**Behandlung:**
- Aktive Transfers werden beim Start geladen
- Empfangene Blöcke werden aus Dateien geladen
- Übertragung kann fortgesetzt werden

## Dateistruktur auf dem Empfänger

```
transfers/
├── {transfer_id}/
│   ├── metadata.json          # Transfer-Metadaten
│   ├── block_000001.dat      # Block 1 Daten
│   ├── block_000002.dat      # Block 2 Daten
│   └── ...
├── {transfer_id}/
│   ├── metadata.json
│   └── ...
└── active_transfers.json     # Zustand aller aktiven Transfers
```

### metadata.json Struktur

```json
{
  "transfer_id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "beispiel.txt",
  "original_size": 4194304,
  "block_size": 4096,
  "total_blocks": 1024,
  "file_hash": "a591a6d40bf420404a011733cfb7b190d62c65bf0bcda32b57b277d9ad9f146e",
  "received_at": "2024-01-15T10:30:00.000000",
  "completed": true
}
```

## Durchsatzberechnung

### Theoretischer Durchsatz

- **Blockgröße:** 4 KB (Standard)
- **QR-Code Kapazität:** ~2.953 Bytes (Version 40, Fehlerkorrekturlevel L)
- **Effektive Nutzdaten:** ~2 KB pro QR-Code (nach Protokoll-Overhead)
- **Anzeigedauer:** 1 Sekunde pro Block
- **Theoretischer Durchsatz:** ~2 KB/s

### Praktische Überlegungen

- **Erkennungsrate:** Nicht alle QR-Codes werden erkannt
- **Fehlerrate:** Abhängig von Bildschirmqualität und Kamera
- **Overhead:** Protokollinformationen, Prüfsummen
- **Wiederholungen:** Fehlende Blöcke müssen wiederholt werden

### Empfohlene Einstellungen für 50+ MB Dateien

| Dateigröße | Blockgröße | Geschätzte Blöcke | Geschätzte Dauer (1s/Block) | Empfohlene Anzeigedauer |
|------------|-------------|-------------------|----------------------------|--------------------------|
| 50 MB | 4 KB | 12.800 | 3,6 Stunden | 0,5 - 1 Sekunde |
| 50 MB | 8 KB | 6.400 | 1,8 Stunden | 0,5 - 1 Sekunde |
| 100 MB | 8 KB | 12.800 | 3,6 Stunden | 0,5 Sekunde |

## Sicherheitsüberlegungen

### Datensicherheit

1. **Keine automatische Ausführung:** Empfangene Dateien werden nicht automatisch ausgeführt
2. **Temporäre Speicherung:** Daten werden in einem dedizierten Transfer-Verzeichnis gespeichert
3. **Integritätsprüfung:** SHA-256 Hash wird verwendet, um die Dateiintegrität zu verifizieren
4. **Keine unbemerkten Aufnahmen:** Bildschirmerfassung ist auf einen explizit definierten Bereich beschränkt

### Fehlerbehandlung

1. **Sichere Pfadverarbeitung:** Dateinamen und Pfade werden sicher verarbeitet
2. **Prüfsummen:** Jeder Block wird auf Integrität geprüft
3. **Duplikaterkennung:** Doppelt empfangene Blöcke werden erkannt und ignoriert
4. **Fehlerprotokollierung:** Alle Fehler werden protolliert

## Zukunftsweisende Erweiterungen

### Variante B: Eigenes Schwarz-Weiß-Raster

Für höhere Durchsatzraten kann ein eigenes Rasterformat implementiert werden:

1. **Feste Bildgeometrie:** z.B. 100x100 Pixel
2. **Synchronisationsmarkierungen:** Eckenmarkierungen für Ausrichtung
3. **Datenkodierung:** Jedes Pixel repräsentiert mehrere Bits
4. **Fehlerkorrektur:** Reed-Solomon oder ähnliche Codes

### Geschätzter Durchsatz mit eigenem Raster

- **Bildgröße:** 100x100 Pixel = 10.000 Pixel
- **Bits pro Pixel:** 2 (4 Graustufen)
- **Daten pro Bild:** ~2.500 Bytes
- **Anzeigedauer:** 0,5 Sekunden
- **Theoretischer Durchsatz:** ~5 KB/s

### Vergleich

| Methode | Daten pro Bild | Durchsatz (1s) | Durchsatz (0.5s) | Implementierungsaufwand |
|---------|----------------|----------------|-------------------|------------------------|
| QR-Code | ~2 KB | 2 KB/s | 4 KB/s | Niedrig |
| Eigenes Raster | ~2.5 KB | 2.5 KB/s | 5 KB/s | Hoch |

## Empfehlungen

1. **Beginnen Sie mit QR-Codes:** Einfache Implementierung, gute Erkennung
2. **Optimieren Sie die Blockgröße:** Größere Blöcke = weniger Overhead, aber längere Übertragungszeit bei Fehlern
3. **Testen Sie verschiedene Anzeigedauern:** Abhängig von Hardware und Umgebungslicht
4. **Verwenden Sie Fehlerkorrektur:** QR-Codes haben eingebaute Fehlerkorrektur
5. **Monitoring:** Überwachen Sie die Erkennungsrate und passen Sie Parameter an

## Protokoll-Erweiterungen

### Version 1.1 (geplant)

- **Komprimierung:** Nutzdaten werden mit zlib komprimiert
- **Verschlüsselung:** Optional AES-Verschlüsselung
- **Fehlerkorrektur:** Reed-Solomon Codes für bessere Fehlerbehebung
- **Mehrere Dateien:** Unterstützung für ZIP-Archive

### Version 2.0 (zukünftig)

- **Eigenes Rasterformat:** Höhere Datendichte
- **Bidirektionale Kommunikation:** Rückkanal für Bestätigungen
- **Adaptive Blockgröße:** Dynamische Anpassung basierend auf Erkennungsrate
- **Parallele Übertragung:** Mehrere QR-Codes gleichzeitig
