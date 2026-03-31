# -*- coding: utf-8 -*-
"""
ZXing.js + PIL + Pyzbar tabanlı barcode scanner
EAN-13, Code-128, vb. barkodları tarar
TRY_HARDER modu ve sürekli odaklama ile çalışır
"""

import streamlit as st
import streamlit.components.v1 as components
from PIL import Image
import io
import numpy as np

def kamera_scanner_html():
    """
    HTML5 + ZXing.js tarayıcı
    """
    html_code = """
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
                background: #1a1a1a;
                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 100vh;
                padding: 10px;
            }
            
            .container {
                width: 100%;
                max-width: 500px;
                background: white;
                border-radius: 15px;
                overflow: hidden;
                box-shadow: 0 10px 40px rgba(0,0,0,0.3);
            }
            
            .scanner-header {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 15px;
                text-align: center;
            }
            
            .scanner-header h2 {
                font-size: 18px;
                margin-bottom: 5px;
            }
            
            .scanner-header p {
                font-size: 12px;
                opacity: 0.9;
            }
            
            .video-container {
                position: relative;
                width: 100%;
                padding-bottom: 100%;
                background: #000;
                overflow: hidden;
            }
            
            .video-container video {
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                object-fit: cover;
            }
            
            .corner {
                position: absolute;
                width: 30px;
                height: 30px;
                border: 3px solid #00ff00;
            }
            
            .corner.top-left {
                top: 10%;
                left: 10%;
                border-right: none;
                border-bottom: none;
            }
            
            .corner.top-right {
                top: 10%;
                right: 10%;
                border-left: none;
                border-bottom: none;
            }
            
            .corner.bottom-left {
                bottom: 10%;
                left: 10%;
                border-right: none;
                border-top: none;
            }
            
            .corner.bottom-right {
                bottom: 10%;
                right: 10%;
                border-left: none;
                border-top: none;
            }
            
            .scanner-info {
                padding: 15px;
                background: #f8f9fa;
                text-align: center;
                font-size: 14px;
                color: #666;
                border-top: 1px solid #e0e0e0;
            }
            
            .result-box {
                padding: 15px;
                background: #e8f5e9;
                border-top: 2px solid #4caf50;
                text-align: center;
                display: none;
            }
            
            .result-box.active {
                display: block;
            }
            
            .result-box h3 {
                color: #4caf50;
                margin-bottom: 8px;
            }
            
            .result-box .barcode-value {
                font-family: 'Courier New', monospace;
                font-size: 16px;
                font-weight: bold;
                color: #2e7d32;
                word-break: break-all;
            }
            
            .controls {
                display: flex;
                gap: 10px;
                padding: 15px;
                background: #f5f5f5;
            }
            
            button {
                flex: 1;
                padding: 10px;
                border: none;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
                cursor: pointer;
                transition: all 0.3s;
            }
            
            .btn-torch {
                background: #ff9800;
                color: white;
            }
            
            .btn-torch:hover {
                background: #f57c00;
            }
            
            .btn-reset {
                background: #2196f3;
                color: white;
            }
            
            .btn-reset:hover {
                background: #1976d2;
            }
            
            .btn-copy {
                background: #4caf50;
                color: white;
            }
            
            .btn-copy:hover {
                background: #45a049;
            }
            
            .error-message {
                color: #d32f2f;
                padding: 15px;
                background: #ffebee;
                border-top: 2px solid #d32f2f;
                display: none;
                text-align: center;
            }
            
            .error-message.active {
                display: block;
            }
            
            .loader {
                display: inline-block;
                width: 20px;
                height: 20px;
                border: 3px solid #f3f3f3;
                border-top: 3px solid #667eea;
                border-radius: 50%;
                animation: spin 1s linear infinite;
            }
            
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="scanner-header">
                <h2>📱 Barkod Tarayıcı</h2>
                <p>Barkodu kameraya gösterin</p>
            </div>
            
            <div class="video-container">
                <video id="barcodeVideo" autoplay playsinline></video>
                <div class="corner top-left"></div>
                <div class="corner top-right"></div>
                <div class="corner bottom-left"></div>
                <div class="corner bottom-right"></div>
            </div>
            
            <div class="error-message" id="errorMessage"></div>
            
            <div class="result-box" id="resultBox">
                <h3>✅ Barkod Okundu!</h3>
                <div class="barcode-value" id="barcodeValue"></div>
            </div>
            
            <div class="scanner-info">
                <div id="scannerStatus">
                    <div class="loader"></div> Hazırlanıyor...
                </div>
            </div>
            
            <div class="controls">
                <button class="btn-torch" id="torchBtn" style="display:none;">💡 Flaş</button>
                <button class="btn-reset" id="resetBtn">🔄 Sıfırla</button>
                <button class="btn-copy" id="copyBtn" style="display:none;">📋 Kopyala</button>
            </div>
        </div>

        <script src="https://unpkg.com/@zxing/library@0.20.0/umd/index.js"></script>
        <script>
            const codeReader = new ZXing.BrowserMultiFormatReader();
            let selectedDeviceId = null;
            let lastResult = '';
            let stream = null;

            // Kamera izni iste
            async function startScanning() {
                try {
                    const videoElement = document.getElementById('barcodeVideo');
                    const statusElement = document.getElementById('scannerStatus');
                    
                    // Cihazları listele
                    const devices = await ZXing.BrowserCodeReader.listVideoInputDevices();
                    if (devices.length > 0) {
                        selectedDeviceId = devices[0].deviceId;
                    }
                    
                    // Kamerayı başlat
                    const constraints = {
                        video: {
                            deviceId: selectedDeviceId ? { exact: selectedDeviceId } : undefined,
                            facingMode: 'environment',
                            width: { ideal: 1280 },
                            height: { ideal: 720 },
                            focusMode: 'continuous'
                        },
                        audio: false
                    };

                    stream = await navigator.mediaDevices.getUserMedia(constraints);
                    videoElement.srcObject = stream;
                    
                    // Flaş düğmesini kontrol et
                    const settings = stream.getVideoTracks()[0].getSettings();
                    if (stream.getVideoTracks()[0].getCapabilities().torch) {
                        document.getElementById('torchBtn').style.display = 'block';
                    }
                    
                    statusElement.textContent = '✅ Hazır - Barkodu tarayın';
                    decodeFromCamera();
                    
                } catch (err) {
                    showError('Kamera erişimi reddedildi: ' + err.message);
                    console.error('Kamera hatası:', err);
                }
            }

            // Kameradan tarama yap
            function decodeFromCamera() {
                const videoElement = document.getElementById('barcodeVideo');
                const canvas = document.createElement('canvas');
                const ctx = canvas.getContext('2d');
                const resultElement = document.getElementById('resultBox');
                const barcodeValueElement = document.getElementById('barcodeValue');
                
                function scan() {
                    if (videoElement.readyState === videoElement.HAVE_ENOUGH_DATA) {
                        canvas.width = videoElement.videoWidth;
                        canvas.height = videoElement.videoHeight;
                        ctx.drawImage(videoElement, 0, 0);
                        
                        try {
                            const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
                            const luminanceSource = new ZXing.HTMLCanvasElementLuminanceSource(canvas);
                            const binarizer = new ZXing.HybridBinarizer(luminanceSource);
                            const bitmap = new ZXing.BinaryBitmap(binarizer);
                            
                            const hints = new Map();
                            hints.set(ZXing.DecodeHintType.TRY_HARDER, true);
                            hints.set(ZXing.DecodeHintType.POSSIBLE_FORMATS, [
                                ZXing.BarcodeFormat.EAN_13,
                                ZXing.BarcodeFormat.CODE_128,
                                ZXing.BarcodeFormat.EAN_8,
                                ZXing.BarcodeFormat.QR_CODE,
                                ZXing.BarcodeFormat.CODE_39
                            ]);
                            
                            const reader = new ZXing.MultiFormatReader();
                            const result = reader.decode(bitmap, hints);
                            
                            if (result && result.text) {
                                if (lastResult !== result.text) {
                                    lastResult = result.text;
                                    barcodeValueElement.textContent = result.text;
                                    resultElement.classList.add('active');
                                    document.getElementById('copyBtn').style.display = 'block';
                                    
                                    // Streamlit'e gönder
                                    window.parent.postMessage({
                                        type: 'barcode_scanned',
                                        value: result.text,
                                        format: result.getBarcodeFormat()
                                    }, '*');
                                }
                            }
                        } catch (err) {
                            // Sessiz hata - tarama devam etsin
                        }
                    }
                    
                    // Her 150ms'de tarama
                    setTimeout(scan, 150);
                }
                
                scan();
            }

            // Flaş aç/kapat
            document.getElementById('torchBtn').addEventListener('click', async () => {
                try {
                    const track = stream.getVideoTracks()[0];
                    const settings = track.getSettings();
                    await track.applyConstraints({
                        advanced: [{ torch: !settings.torch }]
                    });
                } catch (err) {
                    console.log('Flaş desteği yok');
                }
            });

            // Sıfırla
            document.getElementById('resetBtn').addEventListener('click', () => {
                lastResult = '';
                document.getElementById('resultBox').classList.remove('active');
                document.getElementById('copyBtn').style.display = 'none';
                document.getElementById('barcodeVideo').focus();
            });

            // Kopyala
            document.getElementById('copyBtn').addEventListener('click', () => {
                navigator.clipboard.writeText(lastResult);
                alert('Barkod kopyalandı!');
            });

            function showError(message) {
                const errorElement = document.getElementById('errorMessage');
                errorElement.textContent = message;
                errorElement.classList.add('active');
                document.getElementById('scannerStatus').style.display = 'none';
            }

            // Başlat
            window.addEventListener('load', startScanning);

            // Sayfa kapatılırsa kamerayı kapat
            window.addEventListener('beforeunload', () => {
                if (stream) {
                    stream.getTracks().forEach(track => track.stop());
                }
            });
        </script>
    </body>
    </html>
    """
    
    # HTML bileşenini render et
    components.html(html_code, height=800)
    
    return None
