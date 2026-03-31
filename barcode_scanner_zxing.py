# -*- coding: utf-8 -*-
"""
ZXing.js tabanlı barcode scanner
Streamlit HTML component aracılığıyla
"""

import streamlit as st
import streamlit.components.v1 as components

def zxing_barcode_scanner():
    """
    ZXing.js ile HTML5 video barcode tarayıcı
    
    Returns:
        str or None: Okunan barkod değeri
    """
    
    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 100vh;
                padding: 10px;
            }
            
            .scanner-container {
                width: 100%;
                max-width: 500px;
                background: white;
                border-radius: 20px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                overflow: hidden;
            }
            
            .scanner-header {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 20px;
                text-align: center;
                border-bottom: 3px solid rgba(255,255,255,0.1);
            }
            
            .scanner-header h2 {
                font-size: 20px;
                margin: 0 0 5px 0;
            }
            
            .scanner-header p {
                font-size: 13px;
                opacity: 0.9;
                margin: 0;
            }
            
            .video-wrapper {
                position: relative;
                width: 100%;
                background: #000;
                aspect-ratio: 1;
                overflow: hidden;
            }
            
            #videoElement {
                width: 100%;
                height: 100%;
                object-fit: cover;
                display: block;
            }
            
            .scan-line {
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                height: 2px;
                background: linear-gradient(to right, transparent, #00ff00, transparent);
                animation: scan 2s infinite;
            }
            
            @keyframes scan {
                0%, 100% { top: 10%; }
                50% { top: 90%; }
            }
            
            .corner-marker {
                position: absolute;
                width: 40px;
                height: 40px;
                border: 3px solid #00ff00;
            }
            
            .corner-marker.top-left {
                top: 15px;
                left: 15px;
                border-right: none;
                border-bottom: none;
            }
            
            .corner-marker.top-right {
                top: 15px;
                right: 15px;
                border-left: none;
                border-bottom: none;
            }
            
            .corner-marker.bottom-left {
                bottom: 15px;
                left: 15px;
                border-right: none;
                border-top: none;
            }
            
            .corner-marker.bottom-right {
                bottom: 15px;
                right: 15px;
                border-left: none;
                border-top: none;
            }
            
            .controls {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 10px;
                padding: 15px;
                background: #f8f9fa;
            }
            
            button {
                padding: 12px 16px;
                border: none;
                border-radius: 10px;
                font-size: 14px;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.2s;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
            
            .btn-primary {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
            }
            
            .btn-primary:hover {
                transform: translateY(-2px);
                box-shadow: 0 10px 20px rgba(102, 126, 234, 0.3);
            }
            
            .btn-secondary {
                background: #e0e0e0;
                color: #333;
            }
            
            .btn-secondary:hover {
                background: #d0d0d0;
            }
            
            .status-area {
                padding: 15px;
                background: #f0f7ff;
                border-top: 1px solid #e0e0e0;
                text-align: center;
                font-size: 13px;
                color: #666;
                min-height: 40px;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            
            .status-area.success {
                background: #e8f5e9;
                color: #2e7d32;
                font-weight: 600;
                border-top-color: #4caf50;
            }
            
            .status-area.scanning .spinner {
                display: inline-block;
                width: 16px;
                height: 16px;
                border: 2px solid #667eea;
                border-top-color: transparent;
                border-radius: 50%;
                animation: spin 1s linear infinite;
                margin-right: 8px;
            }
            
            @keyframes spin {
                to { transform: rotate(360deg); }
            }
            
            .barcode-display {
                font-family: 'Courier New', monospace;
                font-size: 18px;
                font-weight: bold;
                word-break: break-all;
                margin: 0;
            }
            
            .error-message {
                background: #ffebee;
                color: #c62828;
                padding: 15px;
                border-top: 1px solid #e0e0e0;
                text-align: center;
                font-size: 13px;
                display: none;
            }
            
            .error-message.show {
                display: block;
            }
        </style>
    </head>
    <body>
        <div class="scanner-container">
            <div class="scanner-header">
                <h2>📱 Barkod Tarayıcı</h2>
                <p>Barkodu kameraya gösterin</p>
            </div>
            
            <div class="video-wrapper">
                <video id="videoElement" autoplay playsinline muted></video>
                <div class="scan-line"></div>
                <div class="corner-marker top-left"></div>
                <div class="corner-marker top-right"></div>
                <div class="corner-marker bottom-left"></div>
                <div class="corner-marker bottom-right"></div>
            </div>
            
            <div class="status-area scanning" id="statusArea">
                <span class="spinner"></span>
                Hazırlanıyor...
            </div>
            
            <div class="error-message" id="errorArea"></div>
            
            <div class="controls">
                <button class="btn-primary" id="torchBtn" style="display:none;">💡 Flaş</button>
                <button class="btn-secondary" id="resetBtn">🔄 Sıfırla</button>
            </div>
        </div>

        <script src="https://unpkg.com/@zxing/library@0.20.0/umd/index.js"></script>
        <script>
            const videoElement = document.getElementById('videoElement');
            const statusArea = document.getElementById('statusArea');
            const errorArea = document.getElementById('errorArea');
            const resetBtn = document.getElementById('resetBtn');
            const torchBtn = document.getElementById('torchBtn');
            
            let stream = null;
            let scanning = true;
            let lastScannedValue = '';

            async function initCamera() {
                try {
                    const constraints = {
                        video: {
                            facingMode: 'environment',
                            width: { ideal: 1280 },
                            height: { ideal: 720 }
                        },
                        audio: false
                    };

                    stream = await navigator.mediaDevices.getUserMedia(constraints);
                    videoElement.srcObject = stream;
                    
                    // Try to enable continuous autofocus
                    const track = stream.getVideoTracks()[0];
                    try {
                        const capabilities = track.getCapabilities();
                        if (capabilities.focusMode && capabilities.focusMode.includes('continuous')) {
                            await track.applyConstraints({
                                advanced: [{ focusMode: 'continuous' }]
                            });
                        }
                        
                        // Check for torch capability
                        if (capabilities.torch) {
                            torchBtn.style.display = 'block';
                            torchBtn.onclick = toggleTorch;
                        }
                    } catch (e) {
                        console.log('Focus/torch constraints not available');
                    }
                    
                    statusArea.textContent = '✅ Hazır - Barkodu tarayın';
                    statusArea.className = 'status-area success';
                    startScanning();
                    
                } catch (err) {
                    showError('Kamera erişimi reddedildi: ' + err.message);
                }
            }

            async function toggleTorch() {
                if (stream) {
                    const track = stream.getVideoTracks()[0];
                    const settings = track.getSettings();
                    try {
                        await track.applyConstraints({
                            advanced: [{ torch: !settings.torch }]
                        });
                    } catch (e) {
                        console.log('Torch toggle failed');
                    }
                }
            }

            function startScanning() {
                const canvas = document.createElement('canvas');
                const ctx = canvas.getContext('2d');

                function scan() {
                    if (!scanning) return;
                    
                    if (videoElement.readyState === videoElement.HAVE_ENOUGH_DATA) {
                        canvas.width = videoElement.videoWidth;
                        canvas.height = videoElement.videoHeight;
                        ctx.drawImage(videoElement, 0, 0);

                        try {
                            const luminanceSource = new ZXing.HTMLCanvasElementLuminanceSource(canvas);
                            const binarizer = new ZXing.HybridBinarizer(luminanceSource);
                            const bitmap = new ZXing.BinaryBitmap(binarizer);

                            const hints = new Map();
                            hints.set(ZXing.DecodeHintType.TRY_HARDER, true);

                            const reader = new ZXing.MultiFormatReader();
                            try {
                                const result = reader.decode(bitmap, hints);
                                
                                if (result && result.text && result.text !== lastScannedValue) {
                                    lastScannedValue = result.text;
                                    
                                    statusArea.textContent = '📌 ' + result.text;
                                    statusArea.className = 'status-area success';
                                    errorArea.classList.remove('show');
                                    
                                    // Send to parent
                                    window.parent.postMessage({
                                        type: 'barcode_detected',
                                        value: result.text
                                    }, '*');
                                }
                            } catch (e) {
                                // Normal - no barcode found in frame
                            }
                        } catch (err) {
                            console.error('Decode error:', err);
                        }
                    }

                    // Scan every 150ms
                    setTimeout(scan, 150);
                }

                scan();
            }

            function showError(message) {
                errorArea.textContent = '❌ ' + message;
                errorArea.classList.add('show');
            }

            resetBtn.onclick = () => {
                lastScannedValue = '';
                statusArea.textContent = '✅ Hazır - Barkodu tarayın';
                statusArea.className = 'status-area success';
                videoElement.focus();
            };

            window.addEventListener('load', initCamera);
            
            window.addEventListener('beforeunload', () => {
                if (stream) {
                    stream.getTracks().forEach(track => track.stop());
                }
            });
        </script>
    </body>
    </html>
    """
    
    components.html(html_template, height=800)
