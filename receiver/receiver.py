#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Optische Datenübertragung - Python-Empfänger
Phase 1: Machbarkeitsnachweis mit QR-Code Erkennung

Dieses Programm erfasst kontinuierlich einen festgelegten Bildschirmbereich,
erkennt QR-Codes und dekodiert die übertragenen Datenblöcke.
"""

import argparse
import base64
import hashlib
import json
import logging
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import zlib

import cv2
import numpy as np
from mss import mss
from pyzbar import pyzbar
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

# Protokollversion
PROTOCOL_VERSION = "1.0"

# Standard-Konfiguration
DEFAULT_CAPTURE_AREA = {"top": 100, "left": 100, "width": 400, "height": 400}
DEFAULT_CAPTURE_INTERVAL = 0.5  # Sekunden
DEFAULT_TRANSFER_DIR = "transfers"
DEFAULT_BLOCK_TIMEOUT = 10.0  # Sekunden

# Logging-Konfiguration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("receiver.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

# Rich Console für schöne Ausgabe
console = Console()


@dataclass
class BlockData:
    """Datenstruktur für einen empfangenen Block"""
    
    transfer_id: str
    block_number: int
    total_blocks: int
    data: bytes
    checksum: int
    timestamp: float = field(default_factory=time.time)
    is_valid: bool = False
    error: Optional[str] = None


@dataclass
class TransferState:
    """Zustand einer laufenden Übertragung"""
    
    transfer_id: str
    filename: str
    original_size: int
    block_size: int
    total_blocks: int
    file_hash: str
    received_blocks: Dict[int, BlockData] = field(default_factory=dict)
    received_at: float = field(default_factory=time.time)
    completed: bool = False
    missing_blocks: List[int] = field(default_factory=list)
    
    def get_progress(self) -> float:
        """Gibt den Fortschritt in Prozent zurück"""
        if self.total_blocks == 0:
            return 0.0
        return (len(self.received_blocks) / self.total_blocks) * 100
    
    def get_received_count(self) -> int:
        """Gibt die Anzahl der empfangenen Blöcke zurück"""
        return len(self.received_blocks)
    
    def is_complete(self) -> bool:
        """Prüft, ob alle Blöcke empfangen wurden"""
        return len(self.received_blocks) >= self.total_blocks


class OpticalTransferReceiver:
    """Hauptklasse für den optischen Datenempfänger"""
    
    def __init__(
        self,
        capture_area: Optional[Dict[str, int]] = None,
        capture_interval: float = DEFAULT_CAPTURE_INTERVAL,
        transfer_dir: str = DEFAULT_TRANSFER_DIR,
        block_timeout: float = DEFAULT_BLOCK_TIMEOUT,
    ):
        """
        Initialisiert den Empfänger
        
        Args:
            capture_area: Bildschirmbereich für die Erfassung (top, left, width, height)
            capture_interval: Intervall zwischen den Bildschirmaufnahmen in Sekunden
            transfer_dir: Verzeichnis für Transfer-Daten
            block_timeout: Zeitüberschreitung für Block-Empfang in Sekunden
        """
        self.capture_area = capture_area or DEFAULT_CAPTURE_AREA
        self.capture_interval = capture_interval
        self.transfer_dir = Path(transfer_dir)
        self.block_timeout = block_timeout
        
        # Aktive Transfers
        self.active_transfers: Dict[str, TransferState] = {}
        
        # Statistiken
        self.stats = {
            "total_blocks_received": 0,
            "total_transfers": 0,
            "duplicate_blocks": 0,
            "invalid_blocks": 0,
            "start_time": time.time(),
        }
        
        # Bildschirmerfassung
        self.sct = mss()
        
        # Erstelle Transfer-Verzeichnis
        self._ensure_transfer_dir()
        
        logger.info(f"Empfänger initialisiert. Erfassungsbereich: {self.capture_area}")
    
    def _ensure_transfer_dir(self):
        """Stellt sicher, dass das Transfer-Verzeichnis existiert"""
        self.transfer_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_transfer_path(self, transfer_id: str) -> Path:
        """Gibt den Pfad für einen bestimmten Transfer zurück"""
        return self.transfer_dir / transfer_id
    
    def _get_block_path(self, transfer_id: str, block_number: int) -> Path:
        """Gibt den Pfad für einen bestimmten Block zurück"""
        transfer_path = self._get_transfer_path(transfer_id)
        transfer_path.mkdir(parents=True, exist_ok=True)
        return transfer_path / f"block_{block_number:06d}.dat"
    
    def _get_metadata_path(self, transfer_id: str) -> Path:
        """Gibt den Pfad für die Metadaten zurück"""
        transfer_path = self._get_transfer_path(transfer_id)
        return transfer_path / "metadata.json"
    
    def start(self):
        """Startet den Empfangsprozess"""
        logger.info("Starte Empfangsprozess...")
        console.print("[bold green]Empfänger gestartet[/bold green]")
        console.print(f"Erfassungsbereich: {self.capture_area}")
        console.print(f"Erfassungsintervall: {self.capture_interval}s")
        console.print(f"Transfer-Verzeichnis: {self.transfer_dir.resolve()}")
        console.print("Drücke STRG+C zum Beenden...")
        
        try:
            while True:
                self.capture_and_process()
                time.sleep(self.capture_interval)
        except KeyboardInterrupt:
            logger.info("Empfänger durch Benutzer gestoppt")
            console.print("[bold yellow]Empfänger gestoppt[/bold yellow]")
        except Exception as e:
            logger.error(f"Fehler im Empfangsprozess: {e}")
            console.print(f"[bold red]Fehler: {e}[/bold red]")
        finally:
            self.save_active_transfers()
            self.print_statistics()
    
    def capture_and_process(self):
        """Erfasst den Bildschirmbereich und verarbeitet QR-Codes"""
        try:
            # Bildschirmbereich erfassen
            screenshot = self.sct.grab(self.capture_area)
            
            # In OpenCV-Format konvertieren
            img = np.array(screenshot)
            img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
            
            # QR-Codes erkennen
            decoded_objects = self.detect_qr_codes(img)
            
            # Jeden erkannten QR-Code verarbeiten
            for decoded in decoded_objects:
                self.process_qr_data(decoded.data)
                
        except Exception as e:
            logger.warning(f"Fehler bei der Bildschirmerfassung: {e}")
    
    def detect_qr_codes(self, img: np.ndarray) -> List:
        """
        Erkennt QR-Codes im Bild
        
        Args:
            img: OpenCV Bild (BGR-Format)
            
        Returns:
            Liste der dekodierten Objekte
        """
        # In Graustufen konvertieren
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # QR-Codes erkennen
        decoded_objects = pyzbar.decode(gray)
        
        return decoded_objects
    
    def process_qr_data(self, qr_data: str):
        """
        Verarbeitet die Daten aus einem QR-Code
        
        Args:
            qr_data: Dekodierte Daten aus dem QR-Code
        """
        try:
            # Protokoll-Präfix prüfen
            if not qr_data.startswith("OTP:"):
                logger.debug(f"Ungültiges Protokoll-Präfix: {qr_data[:20]}...")
                return
            
            # QR-Daten parsen
            parts = qr_data.split(":")
            if len(parts) < 8:
                logger.warning(f"Ungültiges QR-Code Format: {qr_data}")
                return
            
            # Protokollversion prüfen
            version = parts[1]
            if version != PROTOCOL_VERSION:
                logger.warning(f"Unbekannte Protokollversion: {version}")
                return
            
            # Daten extrahieren
            transfer_id = parts[2]
            block_number = int(parts[3])
            total_blocks = int(parts[4])
            data_length = int(parts[5])
            data_base64 = parts[6]
            checksum = int(parts[7])
            
            logger.debug(
                f"Block empfangen: Transfer={transfer_id}, "
                f"Block={block_number}/{total_blocks}, "
                f"Datenlänge={data_length}, "
                f"Prüfsumme={checksum}"
            )
            
            # Daten dekodieren
            try:
                data = base64.b64decode(data_base64)
            except Exception as e:
                logger.error(f"Fehler beim Dekodieren der Base64-Daten: {e}")
                return
            
            # Datenlänge prüfen
            if len(data) != data_length:
                logger.warning(
                    f"Datenlängenfehler: erwartet {data_length}, "
                    f"erhalten {len(data)}"
                )
                return
            
            # CRC-Prüfsumme berechnen und vergleichen
            calculated_crc = self.calculate_crc32(data)
            if calculated_crc != checksum:
                logger.warning(
                    f"Prüfsummenfehler: erwartet {checksum}, "
                    f"berechnet {calculated_crc}"
                )
                self.stats["invalid_blocks"] += 1
                return
            
            # Block-Daten erstellen
            block_data = BlockData(
                transfer_id=transfer_id,
                block_number=block_number,
                total_blocks=total_blocks,
                data=data,
                checksum=checksum,
                is_valid=True,
            )
            
            # Block verarbeiten
            self.process_block(block_data)
            
        except Exception as e:
            logger.error(f"Fehler beim Verarbeiten der QR-Daten: {e}")
    
    def process_block(self, block: BlockData):
        """
        Verarbeitet einen gültigen Datenblock
        
        Args:
            block: Der empfangene und validierte Block
        """
        self.stats["total_blocks_received"] += 1
        
        # Transfer-Status abrufen oder erstellen
        transfer_state = self.active_transfers.get(block.transfer_id)
        
        if transfer_state is None:
            # Neuer Transfer
            logger.info(f"Neuer Transfer erkannt: {block.transfer_id}")
            transfer_state = TransferState(
                transfer_id=block.transfer_id,
                filename="",
                original_size=0,
                block_size=len(block.data),
                total_blocks=block.total_blocks,
                file_hash="",
            )
            self.active_transfers[block.transfer_id] = transfer_state
        
        # Block bereits empfangen?
        if block.block_number in transfer_state.received_blocks:
            self.stats["duplicate_blocks"] += 1
            logger.debug(
                f"Duplikat-Block ignoriert: "
                f"Transfer={block.transfer_id}, "
                f"Block={block.block_number}"
            )
            return
        
        # Block speichern
        transfer_state.received_blocks[block.block_number] = block
        
        # Block auf Festplatte speichern
        self.save_block_to_disk(block)
        
        # Fortschritt anzeigen
        progress = transfer_state.get_progress()
        logger.info(
            f"Block {block.block_number}/{transfer_state.total_blocks} "
            f"empfangen ({progress:.1f}%) - "
            f"Transfer: {block.transfer_id}"
        )
        
        # Prüfen, ob Transfer abgeschlossen ist
        if transfer_state.is_complete():
            logger.info(f"Transfer {block.transfer_id} abgeschlossen!")
            transfer_state.completed = True
            transfer_state.received_at = time.time()
            
            # Datei rekonstruieren
            self.reconstruct_file(transfer_state)
    
    def save_block_to_disk(self, block: BlockData):
        """
        Speichert einen Block auf der Festplatte
        
        Args:
            block: Der zu speichernde Block
        """
        try:
            block_path = self._get_block_path(block.transfer_id, block.block_number)
            
            # Block-Daten speichern
            with open(block_path, "wb") as f:
                f.write(block.data)
            
            logger.debug(f"Block gespeichert: {block_path}")
            
        except Exception as e:
            logger.error(f"Fehler beim Speichern des Blocks: {e}")
    
    def reconstruct_file(self, transfer_state: TransferState):
        """
        Rekonstruiert die Datei aus den empfangenen Blöcken
        
        Args:
            transfer_state: Der abgeschlossene Transfer
        """
        try:
            # Alle Blöcke in der richtigen Reihenfolge sammeln
            sorted_blocks = sorted(
                transfer_state.received_blocks.values(),
                key=lambda b: b.block_number
            )
            
            # Daten zusammenfügen
            file_data = b"".join(block.data for block in sorted_blocks)
            
            # SHA-256 Hash berechnen
            calculated_hash = hashlib.sha256(file_data).hexdigest()
            
            # Metadaten speichern
            metadata = {
                "transfer_id": transfer_state.transfer_id,
                "filename": transfer_state.filename,
                "original_size": len(file_data),
                "block_size": transfer_state.block_size,
                "total_blocks": transfer_state.total_blocks,
                "file_hash": calculated_hash,
                "received_at": datetime.fromtimestamp(
                    transfer_state.received_at
                ).isoformat(),
                "completed": True,
            }
            
            metadata_path = self._get_metadata_path(transfer_state.transfer_id)
            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            
            # Datei speichern
            transfer_path = self._get_transfer_path(transfer_state.transfer_id)
            output_path = transfer_path / transfer_state.filename
            
            with open(output_path, "wb") as f:
                f.write(file_data)
            
            logger.info(
                f"Datei rekonstruiert: {output_path} "
                f"({len(file_data)} Bytes, SHA-256: {calculated_hash[:16]}...)"
            )
            console.print(
                f"[bold green]Transfer abgeschlossen![/bold green] "
                f"Datei: {output_path}"
            )
            
            # Statistiken aktualisieren
            self.stats["total_transfers"] += 1
            
        except Exception as e:
            logger.error(f"Fehler bei der Dateirekonstruktion: {e}")
    
    def calculate_crc32(self, data: bytes) -> int:
        """
        Berechnet die CRC-32 Prüfsumme
        
        Args:
            data: Die Daten, für die die Prüfsumme berechnet werden soll
            
        Returns:
            Die CRC-32 Prüfsumme als Integer
        """
        crc = 0xFFFFFFFF
        table = self._crc32_table()
        
        for byte in data:
            crc = (crc >> 8) ^ table[(crc ^ byte) & 0xFF]
        
        return crc ^ 0xFFFFFFFF
    
    def _crc32_table(self) -> List[int]:
        """Generiert die CRC-32 Lookup-Tabelle"""
        table = []
        for i in range(256):
            crc = i
            for _ in range(8):
                if crc & 1:
                    crc = (crc >> 1) ^ 0xEDB88320
                else:
                    crc >>= 1
            table.append(crc)
        return table
    
    def save_active_transfers(self):
        """Speichert den Zustand aller aktiven Transfers"""
        try:
            active_transfers_data = {}
            for transfer_id, state in self.active_transfers.items():
                active_transfers_data[transfer_id] = {
                    "transfer_id": state.transfer_id,
                    "filename": state.filename,
                    "original_size": state.original_size,
                    "block_size": state.block_size,
                    "total_blocks": state.total_blocks,
                    "file_hash": state.file_hash,
                    "received_blocks": list(state.received_blocks.keys()),
                    "received_at": state.received_at,
                    "completed": state.completed,
                }
            
            with open("active_transfers.json", "w", encoding="utf-8") as f:
                json.dump(active_transfers_data, f, indent=2, ensure_ascii=False)
            
            logger.info("Aktive Transfers gespeichert")
            
        except Exception as e:
            logger.error(f"Fehler beim Speichern der aktiven Transfers: {e}")
    
    def load_active_transfers(self):
        """Lädt den Zustand der aktiven Transfers"""
        try:
            if not os.path.exists("active_transfers.json"):
                return
            
            with open("active_transfers.json", "r", encoding="utf-8") as f:
                active_transfers_data = json.load(f)
            
            for transfer_id, data in active_transfers_data.items():
                transfer_state = TransferState(
                    transfer_id=data["transfer_id"],
                    filename=data["filename"],
                    original_size=data["original_size"],
                    block_size=data["block_size"],
                    total_blocks=data["total_blocks"],
                    file_hash=data["file_hash"],
                    received_at=data["received_at"],
                    completed=data["completed"],
                )
                
                # Empfangene Blöcke laden
                for block_number in data["received_blocks"]:
                    block_path = self._get_block_path(transfer_id, block_number)
                    if block_path.exists():
                        with open(block_path, "rb") as f:
                            block_data = f.read()
                        
                        # CRC-32 Prüfsumme berechnen
                        checksum = self.calculate_crc32(block_data)
                        
                        block = BlockData(
                            transfer_id=transfer_id,
                            block_number=block_number,
                            total_blocks=data["total_blocks"],
                            data=block_data,
                            checksum=checksum,
                            is_valid=True,
                        )
                        transfer_state.received_blocks[block_number] = block
                
                self.active_transfers[transfer_id] = transfer_state
            
            logger.info(f"{len(self.active_transfers)} aktive Transfers geladen")
            
        except Exception as e:
            logger.error(f"Fehler beim Laden der aktiven Transfers: {e}")
    
    def list_transfers(self):
        """Listet alle Transfers auf"""
        console.print("[bold]Aktive Transfers:[/bold]")
        
        if not self.active_transfers:
            console.print("Keine aktiven Transfers")
            return
        
        for transfer_id, state in self.active_transfers.items():
            status = "[green]abgeschlossen[/green]" if state.completed else "[yellow]laufend[/yellow]"
            console.print(
                f"  {transfer_id}: {state.filename} "
                f"({state.get_received_count()}/{state.total_blocks} Blöcke) "
                f"{status}"
            )
    
    def show_missing_blocks(self, transfer_id: str):
        """
        Zeigt fehlende Blöcke für einen bestimmten Transfer an
        
        Args:
            transfer_id: Die Transfer-ID
        """
        transfer_state = self.active_transfers.get(transfer_id)
        if transfer_state is None:
            console.print(f"[red]Transfer {transfer_id} nicht gefunden[/red]")
            return
        
        received_blocks = set(transfer_state.received_blocks.keys())
        all_blocks = set(range(1, transfer_state.total_blocks + 1))
        missing_blocks = sorted(all_blocks - received_blocks)
        
        console.print(f"[bold]Fehlende Blöcke für Transfer {transfer_id}:[/bold]")
        console.print(f"  Gesamt: {len(missing_blocks)} Blöcke")
        
        if missing_blocks:
            # In Gruppen anzeigen
            for i in range(0, len(missing_blocks), 10):
                group = missing_blocks[i:i+10]
                console.print(f"  {', '.join(map(str, group))}")
        else:
            console.print("  [green]Alle Blöcke empfangen![/green]")
        
        return missing_blocks
    
    def export_missing_blocks(self, transfer_id: str, output_file: str):
        """
        Exportiert fehlende Blöcke in eine Datei
        
        Args:
            transfer_id: Die Transfer-ID
            output_file: Ausgabedatei
        """
        missing_blocks = self.show_missing_blocks(transfer_id)
        if missing_blocks is None:
            return
        
        try:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(f"Fehlende Blöcke für Transfer {transfer_id}:\n")
                f.write(f"Gesamt: {len(missing_blocks)} Blöcke\n")
                f.write("\n".join(map(str, missing_blocks)))
            
            console.print(f"[green]Fehlende Blöcke exportiert nach {output_file}[/green]")
            
        except Exception as e:
            console.print(f"[red]Fehler beim Exportieren: {e}[/red]")
    
    def verify_file_integrity(self, transfer_id: str):
        """
        Überprüft die Integrität der rekonstruierten Datei
        
        Args:
            transfer_id: Die Transfer-ID
        """
        transfer_state = self.active_transfers.get(transfer_id)
        if transfer_state is None:
            console.print(f"[red]Transfer {transfer_id} nicht gefunden[/red]")
            return False
        
        if not transfer_state.completed:
            console.print(f"[yellow]Transfer {transfer_id} noch nicht abgeschlossen[/yellow]")
            return False
        
        try:
            # Datei laden
            transfer_path = self._get_transfer_path(transfer_id)
            output_path = transfer_path / transfer_state.filename
            
            if not output_path.exists():
                console.print(f"[red]Datei nicht gefunden: {output_path}[/red]")
                return False
            
            with open(output_path, "rb") as f:
                file_data = f.read()
            
            # SHA-256 Hash berechnen
            calculated_hash = hashlib.sha256(file_data).hexdigest()
            
            # Mit erwartetem Hash vergleichen
            if transfer_state.file_hash:
                if calculated_hash == transfer_state.file_hash:
                    console.print(
                        f"[green]Datei-Integrität bestätigt![/green] "
                        f"SHA-256: {calculated_hash}"
                    )
                    return True
                else:
                    console.print(
                        f"[red]Hash-Fehler![/red] "
                        f"Erwartet: {transfer_state.file_hash}, "
                        f"Berechnet: {calculated_hash}"
                    )
                    return False
            else:
                console.print(
                    f"[yellow]Kein Referenz-Hash verfügbar[/yellow] "
                    f"Berechneter Hash: {calculated_hash}"
                )
                return True
                
        except Exception as e:
            console.print(f"[red]Fehler bei der Integritätsprüfung: {e}[/red]")
            return False
    
    def print_statistics(self):
        """Gibt Statistiken aus"""
        uptime = time.time() - self.stats["start_time"]
        hours, remainder = divmod(uptime, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        console.print("\n[bold]Statistiken:[/bold]")
        console.print(f"  Laufzeit: {int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}")
        console.print(f"  Empfangene Blöcke: {self.stats['total_blocks_received']}")
        console.print(f"  Abgeschlossene Transfers: {self.stats['total_transfers']}")
        console.print(f"  Duplikat-Blöcke: {self.stats['duplicate_blocks']}")
        console.print(f"  Ungültige Blöcke: {self.stats['invalid_blocks']}")
    
    def interactive_mode(self):
        """Interaktiver Modus für die Kommandozeile"""
        console.print("\n[bold]Optical Data Transfer - Interaktiver Modus[/bold]")
        console.print("Befehle: start, stop, list, missing <id>, export <id> <file>, verify <id>, quit")
        
        while True:
            try:
                command = input("receiver> ").strip()
                
                if not command:
                    continue
                
                parts = command.split()
                cmd = parts[0].lower()
                args = parts[1:]
                
                if cmd == "start":
                    console.print("Starte Empfänger...")
                    self.start()
                    break
                
                elif cmd == "stop":
                    console.print("Stoppe Empfänger...")
                    break
                
                elif cmd == "list":
                    self.list_transfers()
                
                elif cmd == "missing" and len(args) >= 1:
                    self.show_missing_blocks(args[0])
                
                elif cmd == "export" and len(args) >= 2:
                    self.export_missing_blocks(args[0], args[1])
                
                elif cmd == "verify" and len(args) >= 1:
                    self.verify_file_integrity(args[0])
                
                elif cmd in ("quit", "exit", "q"):
                    break
                
                else:
                    console.print(f"[red]Unbekannter Befehl: {cmd}[/red]")
                    
            except KeyboardInterrupt:
                break
            except Exception as e:
                console.print(f"[red]Fehler: {e}[/red]")


def parse_capture_area(capture_area_str: str) -> Dict[str, int]:
    """
    Parsed die Erfassungsbereich-Parameter
    
    Format: "top,left,width,height"
    
    Args:
        capture_area_str: String mit den Bereichsparametern
        
    Returns:
        Dictionary mit den Bereichsparametern
    """
    try:
        parts = [int(x.strip()) for x in capture_area_str.split(",")]
        if len(parts) != 4:
            raise ValueError("Ungültiges Format")
        
        return {
            "top": parts[0],
            "left": parts[1],
            "width": parts[2],
            "height": parts[3],
        }
    except Exception as e:
        raise argparse.ArgumentTypeError(f"Ungültiger Erfassungsbereich: {e}")


def main():
    """Hauptfunktion"""
    parser = argparse.ArgumentParser(
        description="Optical Data Transfer - Python-Empfänger",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Beispiele:
  python receiver.py                          # Standard-Einstellungen
  python receiver.py --area "100,100,400,400"   # Benutzerdefinierter Bereich
  python receiver.py --interval 0.3           # Kürzeres Intervall
  python receiver.py --transfer-dir ./data    # Benutzerdefiniertes Verzeichnis
        """,
    )
    
    parser.add_argument(
        "--area",
        type=parse_capture_area,
        default=None,
        help="Erfassungsbereich im Format 'top,left,width,height' (Standard: 100,100,400,400)",
    )
    
    parser.add_argument(
        "--interval",
        type=float,
        default=DEFAULT_CAPTURE_INTERVAL,
        help=f"Erfassungsintervall in Sekunden (Standard: {DEFAULT_CAPTURE_INTERVAL})",
    )
    
    parser.add_argument(
        "--transfer-dir",
        type=str,
        default=DEFAULT_TRANSFER_DIR,
        help=f"Verzeichnis für Transfer-Daten (Standard: {DEFAULT_TRANSFER_DIR})",
    )
    
    parser.add_argument(
        "--block-timeout",
        type=float,
        default=DEFAULT_BLOCK_TIMEOUT,
        help=f"Zeitüberschreitung für Block-Empfang in Sekunden (Standard: {DEFAULT_BLOCK_TIMEOUT})",
    )
    
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Interaktiver Modus",
    )
    
    args = parser.parse_args()
    
    # Empfänger erstellen
    receiver = OpticalTransferReceiver(
        capture_area=args.area,
        capture_interval=args.interval,
        transfer_dir=args.transfer_dir,
        block_timeout=args.block_timeout,
    )
    
    # Aktive Transfers laden
    receiver.load_active_transfers()
    
    if args.interactive:
        receiver.interactive_mode()
    else:
        receiver.start()


if __name__ == "__main__":
    main()
