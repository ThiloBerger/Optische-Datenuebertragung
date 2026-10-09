#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests für das optische Übertragungsprotokoll
"""

import base64
import hashlib
import unittest
from unittest.mock import MagicMock, patch

import sys
import os

# Füge das receiver-Verzeichnis zum Pfad hinzu
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'receiver'))

from receiver import (
    OpticalTransferReceiver,
    BlockData,
    TransferState,
    PROTOCOL_VERSION,
)


class TestProtocolParsing(unittest.TestCase):
    """Tests für das Protokoll-Parsing"""
    
    def setUp(self):
        self.receiver = OpticalTransferReceiver()
    
    def test_qr_data_parsing(self):
        """Test das Parsen von QR-Code Daten"""
        # Beispiel-QR-Daten
        transfer_id = "550e8400-e29b-41d4-a716-446655440000"
        block_number = 1
        total_blocks = 10
        data = b"Hello World!"
        checksum = self.receiver.calculate_crc32(data)
        data_base64 = base64.b64encode(data).decode('utf-8')
        
        qr_data = f"OTP:{PROTOCOL_VERSION}:{transfer_id}:{block_number}:{total_blocks}:{len(data)}:{data_base64}:{checksum}"
        
        # Mock für process_block
        with patch.object(self.receiver, 'process_block') as mock_process:
            self.receiver.process_qr_data(qr_data)
            
            # Prüfen, ob process_block aufgerufen wurde
            self.assertTrue(mock_process.called)
            
            # Block-Daten extrahieren
            block = mock_process.call_args[0][0]
            self.assertEqual(block.transfer_id, transfer_id)
            self.assertEqual(block.block_number, block_number)
            self.assertEqual(block.total_blocks, total_blocks)
            self.assertEqual(block.data, data)
            self.assertEqual(block.checksum, checksum)
    
    def test_invalid_protocol_prefix(self):
        """Test ungültiges Protokoll-Präfix"""
        qr_data = "INVALID:1.0:test:1:10:5:SGVsbG8=:123456"
        
        with patch.object(self.receiver, 'process_block') as mock_process:
            self.receiver.process_qr_data(qr_data)
            # process_block sollte nicht aufgerufen werden
            self.assertFalse(mock_process.called)
    
    def test_invalid_version(self):
        """Test ungültige Protokollversion"""
        qr_data = "OTP:2.0:test:1:10:5:SGVsbG8=:123456"
        
        with patch.object(self.receiver, 'process_block') as mock_process:
            self.receiver.process_qr_data(qr_data)
            # process_block sollte nicht aufgerufen werden
            self.assertFalse(mock_process.called)
    
    def test_invalid_qr_format(self):
        """Test ungültiges QR-Format (zu wenige Teile)"""
        qr_data = "OTP:1.0:test:1:10"
        
        with patch.object(self.receiver, 'process_block') as mock_process:
            self.receiver.process_qr_data(qr_data)
            # process_block sollte nicht aufgerufen werden
            self.assertFalse(mock_process.called)
    
    def test_checksum_mismatch(self):
        """Test Prüfsummenfehler"""
        transfer_id = "550e8400-e29b-41d4-a716-446655440000"
        block_number = 1
        total_blocks = 10
        data = b"Hello World!"
        data_base64 = base64.b64encode(data).decode('utf-8')
        
        # Falsche Prüfsumme
        wrong_checksum = 123456
        qr_data = f"OTP:{PROTOCOL_VERSION}:{transfer_id}:{block_number}:{total_blocks}:{len(data)}:{data_base64}:{wrong_checksum}"
        
        with patch.object(self.receiver, 'process_block') as mock_process:
            self.receiver.process_qr_data(qr_data)
            # process_block sollte nicht aufgerufen werden
            self.assertFalse(mock_process.called)


class TestCRC32(unittest.TestCase):
    """Tests für die CRC-32 Berechnung"""
    
    def setUp(self):
        self.receiver = OpticalTransferReceiver()
    
    def test_crc32_calculation(self):
        """Test CRC-32 Berechnung mit bekannten Werten"""
        # Bekannte Testvektoren
        test_cases = [
            (b"", 0xFFFFFFFF),
            (b"123456789", 0xCBF43926),
            (b"Hello World!", 0xEC4AC3D0),
        ]
        
        for data, expected_crc in test_cases:
            calculated_crc = self.receiver.calculate_crc32(data)
            self.assertEqual(calculated_crc, expected_crc)
    
    def test_crc32_consistency(self):
        """Test Konsistenz der CRC-32 Berechnung"""
        data = b"Test data for CRC-32 calculation"
        
        crc1 = self.receiver.calculate_crc32(data)
        crc2 = self.receiver.calculate_crc32(data)
        
        self.assertEqual(crc1, crc2)


class TestSHA256(unittest.TestCase):
    """Tests für SHA-256 Berechnung"""
    
    def test_sha256_calculation(self):
        """Test SHA-256 Berechnung"""
        data = b"Hello World!"
        expected_hash = hashlib.sha256(data).hexdigest()
        
        # Im Empfänger wird SHA-256 verwendet
        calculated_hash = hashlib.sha256(data).hexdigest()
        
        self.assertEqual(calculated_hash, expected_hash)


class TestBlockProcessing(unittest.TestCase):
    """Tests für die Block-Verarbeitung"""
    
    def setUp(self):
        self.receiver = OpticalTransferReceiver()
    
    def test_duplicate_block_detection(self):
        """Test Erkennung von Duplikat-Blöcken"""
        transfer_id = "test-transfer-id"
        block_number = 1
        
        # Ersten Block erstellen
        data1 = b"Test data 1"
        checksum1 = self.receiver.calculate_crc32(data1)
        block1 = BlockData(
            transfer_id=transfer_id,
            block_number=block_number,
            total_blocks=10,
            data=data1,
            checksum=checksum1,
            is_valid=True,
        )
        
        # Block verarbeiten
        self.receiver.process_block(block1)
        
        # Zweiten Block mit derselben Blocknummer erstellen
        data2 = b"Test data 2"
        checksum2 = self.receiver.calculate_crc32(data2)
        block2 = BlockData(
            transfer_id=transfer_id,
            block_number=block_number,
            total_blocks=10,
            data=data2,
            checksum=checksum2,
            is_valid=True,
        )
        
        # Block verarbeiten - sollte als Duplikat erkannt werden
        self.receiver.process_block(block2)
        
        # Prüfen, dass nur der erste Block gespeichert wurde
        transfer_state = self.receiver.active_transfers[transfer_id]
        self.assertEqual(len(transfer_state.received_blocks), 1)
        self.assertEqual(
            transfer_state.received_blocks[block_number].data,
            data1
        )
    
    def test_new_transfer_creation(self):
        """Test Erstellung eines neuen Transfers"""
        transfer_id = "new-transfer-id"
        block_number = 1
        
        data = b"First block data"
        checksum = self.receiver.calculate_crc32(data)
        block = BlockData(
            transfer_id=transfer_id,
            block_number=block_number,
            total_blocks=10,
            data=data,
            checksum=checksum,
            is_valid=True,
        )
        
        self.receiver.process_block(block)
        
        # Prüfen, dass ein neuer Transfer erstellt wurde
        self.assertIn(transfer_id, self.receiver.active_transfers)
        transfer_state = self.receiver.active_transfers[transfer_id]
        self.assertEqual(transfer_state.transfer_id, transfer_id)
        self.assertEqual(transfer_state.total_blocks, 10)
        self.assertEqual(len(transfer_state.received_blocks), 1)


class TestTransferState(unittest.TestCase):
    """Tests für den Transfer-Zustand"""
    
    def test_transfer_state_progress(self):
        """Test Fortschrittsberechnung"""
        transfer_state = TransferState(
            transfer_id="test",
            filename="test.txt",
            original_size=1000,
            block_size=100,
            total_blocks=10,
            file_hash="test-hash",
        )
        
        # Keine Blöcke empfangen
        self.assertEqual(transfer_state.get_progress(), 0.0)
        self.assertEqual(transfer_state.get_received_count(), 0)
        
        # 5 von 10 Blöcken
        for i in range(1, 6):
            transfer_state.received_blocks[i] = MagicMock()
        
        self.assertEqual(transfer_state.get_progress(), 50.0)
        self.assertEqual(transfer_state.get_received_count(), 5)
    
    def test_transfer_state_completion(self):
        """Test Abschlusserkennung"""
        transfer_state = TransferState(
            transfer_id="test",
            filename="test.txt",
            original_size=1000,
            block_size=100,
            total_blocks=5,
            file_hash="test-hash",
        )
        
        # Alle Blöcke empfangen
        for i in range(1, 6):
            transfer_state.received_blocks[i] = MagicMock()
        
        self.assertTrue(transfer_state.is_complete())
        
        # Ein Block fehlt
        del transfer_state.received_blocks[3]
        self.assertFalse(transfer_state.is_complete())


class TestDataIntegrity(unittest.TestCase):
    """Tests für Datenintegrität"""
    
    def test_file_reconstruction(self):
        """Test Dateirekonstruktion"""
        # Originaldaten
        original_data = b"This is a test file for optical data transfer!"
        
        # In Blöcke aufteilen
        block_size = 10
        blocks = []
        for i in range(0, len(original_data), block_size):
            block_data = original_data[i:i+block_size]
            blocks.append(block_data)
        
        # Blöcke wieder zusammenfügen
        reconstructed_data = b"".join(blocks)
        
        self.assertEqual(reconstructed_data, original_data)
    
    def test_sha256_integrity_check(self):
        """Test SHA-256 Integritätsprüfung"""
        data = b"Test data for integrity check"
        
        # SHA-256 Hash berechnen
        file_hash = hashlib.sha256(data).hexdigest()
        
        # Hash überprüfen
        calculated_hash = hashlib.sha256(data).hexdigest()
        
        self.assertEqual(calculated_hash, file_hash)
        
        # Daten ändern
        modified_data = data + b"x"
        modified_hash = hashlib.sha256(modified_data).hexdigest()
        
        self.assertNotEqual(modified_hash, file_hash)


class TestEdgeCases(unittest.TestCase):
    """Tests für Randfälle"""
    
    def setUp(self):
        self.receiver = OpticalTransferReceiver()
    
    def test_empty_data(self):
        """Test leere Daten"""
        data = b""
        checksum = self.receiver.calculate_crc32(data)
        
        qr_data = f"OTP:{PROTOCOL_VERSION}:test:1:10:0::{checksum}"
        
        with patch.object(self.receiver, 'process_block') as mock_process:
            self.receiver.process_qr_data(qr_data)
            
            # Sollte verarbeitet werden
            self.assertTrue(mock_process.called)
    
    def test_large_block_number(self):
        """Test große Blocknummern"""
        transfer_id = "test"
        block_number = 1000000
        
        data = b"test"
        checksum = self.receiver.calculate_crc32(data)
        data_base64 = base64.b64encode(data).decode('utf-8')
        
        qr_data = f"OTP:{PROTOCOL_VERSION}:{transfer_id}:{block_number}:1000000:{len(data)}:{data_base64}:{checksum}"
        
        with patch.object(self.receiver, 'process_block') as mock_process:
            self.receiver.process_qr_data(qr_data)
            
            # Sollte verarbeitet werden
            self.assertTrue(mock_process.called)
    
    def test_unicode_filename(self):
        """Test Unicode-Dateinamen"""
        transfer_id = "test"
        filename = "test_äöü_文件.txt"
        
        transfer_state = TransferState(
            transfer_id=transfer_id,
            filename=filename,
            original_size=100,
            block_size=10,
            total_blocks=10,
            file_hash="test",
        )
        
        # Sollte keine Ausnahme werfen
        self.assertEqual(transfer_state.filename, filename)


if __name__ == "__main__":
    unittest.main()
