// Optische Datenübertragung - Browser-Sender
// Phase 1: Machbarkeitsnachweis mit QR-Codes

class OpticalTransferSender {
    constructor() {
        // DOM-Elemente
        this.fileInput = document.getElementById('fileInput');
        this.zipButton = document.getElementById('zipButton');
        this.startButton = document.getElementById('startButton');
        this.stopButton = document.getElementById('stopButton');
        this.displayTimeSelect = document.getElementById('displayTime');
        this.blockSizeSelect = document.getElementById('blockSize');
        this.transferIdElement = document.getElementById('transferId');
        this.fileSizeElement = document.getElementById('fileSize');
        this.totalBlocksElement = document.getElementById('totalBlocks');
        this.currentBlockElement = document.getElementById('currentBlock');
        this.progressBar = document.getElementById('progressBar');
        this.qrCodeContainer = document.getElementById('qrCodeContainer');
        this.statusMessage = document.getElementById('statusMessage');
        this.blockNumberInput = document.getElementById('blockNumberInput');
        this.showBlockButton = document.getElementById('showBlockButton');
        this.exportMetadataButton = document.getElementById('exportMetadataButton');
        this.metadataOutput = document.getElementById('metadataOutput');

        // Transfer-Status
        this.transferId = null;
        this.fileData = null;
        this.blockSize = 4096; // Standard-Blockgröße
        this.displayTime = 1000; // Standard-Anzeigedauer
        this.totalBlocks = 0;
        this.currentBlock = 0;
        this.blocks = [];
        this.isTransferring = false;
        this.transferInterval = null;
        this.transferMetadata = null;

        // Event-Listener
        this.setupEventListeners();
    }

    setupEventListeners() {
        this.fileInput.addEventListener('change', () => this.handleFileSelection());
        this.zipButton.addEventListener('click', () => this.createZip());
        this.startButton.addEventListener('click', () => this.startTransfer());
        this.stopButton.addEventListener('click', () => this.stopTransfer());
        this.showBlockButton.addEventListener('click', () => this.showSpecificBlock());
        this.exportMetadataButton.addEventListener('click', () => this.exportMetadata());
    }

    handleFileSelection() {
        const files = this.fileInput.files;
        if (files.length === 0) {
            this.resetTransfer();
            return;
        }

        // Mehrere Dateien? ZIP vorschlagen
        if (files.length > 1) {
            this.zipButton.disabled = false;
            this.startButton.disabled = true;
        } else {
            this.zipButton.disabled = true;
            this.startButton.disabled = false;
            this.processFile(files[0]);
        }
    }

    async createZip() {
        const files = this.fileInput.files;
        if (files.length < 2) return;

        this.updateStatus('Erstelle ZIP-Archiv...', 'info');

        try {
            // Verwende JSZip für die ZIP-Erstellung
            const JSZip = await this.loadJSZip();
            const zip = new JSZip();

            for (let i = 0; i < files.length; i++) {
                zip.file(files[i].name, files[i]);
            }

            const zipBlob = await zip.generateAsync({ type: 'blob' });
            this.processFile(zipBlob, 'archive.zip');
            this.updateStatus('ZIP-Archiv erstellt. Bereit für Übertragung.', 'info');
        } catch (error) {
            this.updateStatus('Fehler beim Erstellen des ZIP-Archivs: ' + error.message, 'error');
        }
    }

    async loadJSZip() {
        // Dynamisch JSZip laden
        if (window.JSZip) {
            return window.JSZip;
        }

        return new Promise((resolve, reject) => {
            const script = document.createElement('script');
            script.src = 'https://cdn.jsdelivr.net/npm/jszip@3.10.1/dist/jszip.min.js';
            script.onload = () => resolve(window.JSZip);
            script.onerror = () => reject(new Error('JSZip konnte nicht geladen werden'));
            document.head.appendChild(script);
        });
    }

    processFile(file, filename = null) {
        const reader = new FileReader();
        
        reader.onload = (event) => {
            this.fileData = new Uint8Array(event.target.result);
            this.filename = filename || file.name;
            
            // Blockgröße und Anzeigedauer aktualisieren
            this.blockSize = parseInt(this.blockSizeSelect.value);
            this.displayTime = parseInt(this.displayTimeSelect.value);
            
            // Blöcke erstellen
            this.createBlocks();
            
            // UI aktualisieren
            this.updateFileInfo();
            this.startButton.disabled = false;
            this.showBlockButton.disabled = false;
            this.exportMetadataButton.disabled = false;
            
            this.updateStatus(`Datei "${this.filename}" geladen. Bereit für Übertragung.`, 'info');
        };
        
        reader.onerror = () => {
            this.updateStatus('Fehler beim Lesen der Datei', 'error');
        };
        
        reader.readAsArrayBuffer(file);
    }

    createBlocks() {
        if (!this.fileData) return;

        this.blocks = [];
        this.totalBlocks = Math.ceil(this.fileData.length / this.blockSize);
        this.currentBlock = 0;

        // Generiere Transfer-ID (UUID v4)
        this.transferId = this.generateTransferId();

        // Blöcke aufteilen
        for (let i = 0; i < this.totalBlocks; i++) {
            const start = i * this.blockSize;
            const end = Math.min(start + this.blockSize, this.fileData.length);
            const blockData = this.fileData.slice(start, end);
            
            // Block-Metadaten erstellen
            const block = {
                blockNumber: i + 1,
                totalBlocks: this.totalBlocks,
                transferId: this.transferId,
                filename: this.filename,
                data: blockData,
                timestamp: Date.now()
            };
            
            // Prüfsumme berechnen (CRC-32)
            block.checksum = this.calculateCRC32(blockData);
            
            this.blocks.push(block);
        }

        // Transfer-Metadaten erstellen
        this.createTransferMetadata();
    }

    createTransferMetadata() {
        if (!this.fileData || !this.transferId) return;

        // SHA-256 Hash der gesamten Datei
        const fileHash = this.calculateSHA256(this.fileData);

        this.transferMetadata = {
            transferId: this.transferId,
            filename: this.filename,
            originalSize: this.fileData.length,
            blockSize: this.blockSize,
            totalBlocks: this.totalBlocks,
            fileHash: fileHash,
            timestamp: Date.now(),
            blocks: this.blocks.map(block => ({
                blockNumber: block.blockNumber,
                checksum: block.checksum
            }))
        };
    }

    generateTransferId() {
        // UUID v4 generieren
        return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
            const r = Math.random() * 16 | 0;
            const v = c === 'x' ? r : (r & 0x3 | 0x8);
            return v.toString(16);
        });
    }

    calculateCRC32(data) {
        // Einfache CRC-32 Implementierung
        let crc = 0xFFFFFFFF;
        const table = this.crc32Table();

        for (let i = 0; i < data.length; i++) {
            crc = (crc >>> 8) ^ table[(crc ^ data[i]) & 0xFF];
        }

        return (crc ^ 0xFFFFFFFF) >>> 0;
    }

    crc32Table() {
        // CRC-32 Tabelle generieren
        const table = [];
        for (let i = 0; i < 256; i++) {
            let crc = i;
            for (let j = 0; j < 8; j++) {
                crc = (crc & 1) ? (crc >>> 1) ^ 0xEDB88320 : crc >>> 1;
            }
            table[i] = crc;
        }
        return table;
    }

    async calculateSHA256(data) {
        // SHA-256 Hash berechnen
        const buffer = await crypto.subtle.digest('SHA-256', data);
        const hashArray = Array.from(new Uint8Array(buffer));
        return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
    }

    updateFileInfo() {
        if (!this.fileData) return;

        this.transferIdElement.textContent = this.transferId || '-';
        this.fileSizeElement.textContent = this.formatFileSize(this.fileData.length);
        this.totalBlocksElement.textContent = this.totalBlocks;
        this.currentBlockElement.textContent = this.currentBlock;
        this.progressBar.style.width = '0%';
        this.progressBar.textContent = '0%';
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    updateStatus(message, type = 'info') {
        this.statusMessage.textContent = message;
        this.statusMessage.className = type === 'error' ? 'status error' : 'status';
        console.log(`[${type.toUpperCase()}] ${message}`);
    }

    startTransfer() {
        if (this.isTransferring || !this.blocks || this.blocks.length === 0) {
            return;
        }

        this.isTransferring = true;
        this.currentBlock = 0;
        this.updateTransferUI();

        this.updateStatus('Übertragung gestartet...', 'info');

        // Erzeuge und zeige Blöcke nacheinander
        this.transferInterval = setInterval(() => {
            this.showCurrentBlock();
        }, this.displayTime);

        this.startButton.disabled = true;
        this.stopButton.disabled = false;
    }

    stopTransfer() {
        if (!this.isTransferring) return;

        clearInterval(this.transferInterval);
        this.isTransferring = false;
        this.updateStatus('Übertragung angehalten', 'info');

        this.startButton.disabled = false;
        this.stopButton.disabled = true;
    }

    showCurrentBlock() {
        if (!this.blocks || this.currentBlock >= this.blocks.length) {
            this.stopTransfer();
            this.updateStatus('Übertragung abgeschlossen!', 'info');
            return;
        }

        const block = this.blocks[this.currentBlock];
        this.displayBlock(block);
        
        // Fortschritt aktualisieren
        this.currentBlock++;
        this.updateTransferUI();

        if (this.currentBlock >= this.blocks.length) {
            this.stopTransfer();
            this.updateStatus('Alle Blöcke übertragen!', 'info');
        }
    }

    showSpecificBlock() {
        const blockNumber = parseInt(this.blockNumberInput.value);
        if (isNaN(blockNumber) || blockNumber < 1 || blockNumber > this.totalBlocks) {
            this.updateStatus(`Ungültige Blocknummer: ${blockNumber}`, 'error');
            return;
        }

        const block = this.blocks[blockNumber - 1];
        this.displayBlock(block);
        this.currentBlock = blockNumber;
        this.updateTransferUI();
        this.updateStatus(`Block ${blockNumber} wird angezeigt`, 'info');
    }

    displayBlock(block) {
        // Block-Daten für QR-Code vorbereiten
        const qrData = this.createQRData(block);
        
        // QR-Code generieren
        this.generateQRCode(qrData);

        // Block-Info anzeigen
        this.currentBlockElement.textContent = block.blockNumber;
    }

    createQRData(block) {
        // Protokollformat für QR-Code
        // Format: "OTP:{version}:{transferId}:{blockNumber}:{totalBlocks}:{dataLength}:{data}:{checksum}"
        
        // Daten als Base64 kodieren
        const dataBase64 = this.uint8ArrayToBase64(block.data);
        
        // Protokollversion
        const version = '1.0';
        
        // QR-Code Daten zusammenbauen
        const qrData = `OTP:${version}:${block.transferId}:${block.blockNumber}:${block.totalBlocks}:${block.data.length}:${dataBase64}:${block.checksum}`;
        
        return qrData;
    }

    uint8ArrayToBase64(uint8Array) {
        // Uint8Array zu Base64 konvertieren
        let binary = '';
        for (let i = 0; i < uint8Array.length; i++) {
            binary += String.fromCharCode(uint8Array[i]);
        }
        return btoa(binary);
    }

    base64ToUint8Array(base64) {
        // Base64 zu Uint8Array konvertieren
        const binary = atob(base64);
        const bytes = new Uint8Array(binary.length);
        for (let i = 0; i < binary.length; i++) {
            bytes[i] = binary.charCodeAt(i);
        }
        return bytes;
    }

    generateQRCode(data) {
        // QR-Code Container leeren
        this.qrCodeContainer.innerHTML = '';

        // QR-Code generieren
        QRCode.toCanvas(
            this.qrCodeContainer,
            data,
            {
                width: 400,
                margin: 2,
                color: {
                    dark: '#000000',
                    light: '#ffffff'
                }
            },
            (error) => {
                if (error) {
                    this.updateStatus('Fehler beim Generieren des QR-Codes: ' + error.message, 'error');
                    this.qrCodeContainer.innerHTML = '<p style="color: red;">Fehler beim QR-Code</p>';
                }
            }
        );
    }

    updateTransferUI() {
        this.currentBlockElement.textContent = this.currentBlock;
        
        const progressPercent = this.totalBlocks > 0 ? 
            Math.round((this.currentBlock / this.totalBlocks) * 100) : 0;
        
        this.progressBar.style.width = `${progressPercent}%`;
        this.progressBar.textContent = `${progressPercent}%`;
    }

    exportMetadata() {
        if (!this.transferMetadata) {
            this.updateStatus('Keine Metadaten verfügbar', 'error');
            return;
        }

        const metadataJson = JSON.stringify(this.transferMetadata, null, 2);
        this.metadataOutput.value = metadataJson;
        this.updateStatus('Metadaten exportiert', 'info');
    }

    resetTransfer() {
        this.stopTransfer();
        this.fileData = null;
        this.blocks = [];
        this.totalBlocks = 0;
        this.currentBlock = 0;
        this.transferId = null;
        this.transferMetadata = null;
        this.qrCodeContainer.innerHTML = '<p>QR-Code wird hier angezeigt...</p>';
        
        this.updateFileInfo();
        this.updateStatus('Bereit für neue Übertragung', 'info');
        this.startButton.disabled = true;
        this.stopButton.disabled = true;
        this.showBlockButton.disabled = true;
        this.exportMetadataButton.disabled = true;
        this.zipButton.disabled = true;
        this.metadataOutput.value = '';
    }
}

// Initialisierung
window.addEventListener('DOMContentLoaded', () => {
    window.sender = new OpticalTransferSender();
});
