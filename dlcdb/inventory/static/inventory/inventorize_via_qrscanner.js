// SPDX-FileCopyrightText: 2024 Thomas Breitner
//
// SPDX-License-Identifier: EUPL-1.2

// SCANNER
// via https://github.com/nimiq/qr-scanner
// import QrScanner from QR_LIB_URL;
// QrScanner.WORKER_PATH = "{% static 'dist/inventory/js/qr-scanner-worker.min.js' %}";

const dlcdbQrConstants = document.currentScript.dataset;
const QRCODE_PREFIX = dlcdbQrConstants.qrcodePrefix;

const videoElem = document.getElementById('qr-video');
const camHasCamera = document.getElementById('cam-has-camera');
const camQrResult = document.getElementById('cam-qr-result');
const camQrResultTimestamp = document.getElementById('cam-qr-result-timestamp');


function isDlcdbQrCode(qrstring) {
    // Check if QrCode is a valid DLCDB QR code
    // console.log("Test for isDlcdbQrCode")
    let re = new RegExp("^DLCDB[RD][0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$");
    return re.test(qrstring)
}


function QrCode(qrstring) {
    console.info("qrstring: ", qrstring)
    if ( !isDlcdbQrCode(qrstring)) return false

    this.uuid = getUnprefixedUuid(qrstring)
    this.infix = getInfix(qrstring)
    this.raw = qrstring
    return this
}

function getUnprefixedUuid(uuid) {
    // console.log("getUnprefixedUuid")
    let re = new RegExp("^" + QRCODE_PREFIX + "[RD]")
    let result = uuid.replace(re, '')
    // console.log("getUnprefixedUuid: " + result)
    return result
}

function getInfix(qrstring) {
    // console.log("getInfix")
    let len_prefix = QRCODE_PREFIX.length
    // console.log("len_prefix: " + len_prefix)
    let infix = qrstring.substring(len_prefix, len_prefix + 1)
    // console.log("infix: ", infix)
    return infix
}

function setResult(label, result) {
    console.log(result.data);
    label.textContent = result.data;
    camQrResultTimestamp.textContent = new Date().toString();
    label.style.color = 'teal';
    clearTimeout(label.highlightTimeout);
    label.highlightTimeout = setTimeout(() => label.style.color = 'inherit', 100);


    let QrObj = new QrCode(result.data)
    console.log("QrObj: ", QrObj)
    if (!QrObj) return;

    if (QrObj.infix === 'D') {
        console.info("Trigger DEVICE related tasks...")
        // manageUuid({uuid: QrObj.uuid, state: DEVICE_STATE_FOUND});
        handleDeviceScan(QrObj.uuid);
    } else if (QrObj.infix === 'R') {
        console.info("Trigger ROOM related tasks...")
        handleRoomScan(QrObj.uuid);
    } else {
        alert(`INFIX "${QrObj.infix}" NOT GIVEN OR NOT KNOWN! Ignoring this QrCode!`)
        return;
    }
}

const qrScanner = new QrScanner(videoElem, result => setResult(camQrResult, result), {
    onDecodeError: error => {
        camQrResult.textContent = error;
        camQrResult.style.color = 'inherit';
    },
    returnDetailedScanResult: true,
    highlightScanRegion: true,
    highlightCodeOutline: true,
});

qrScanner.start().then(() => {
    console.log("qrScanner start...")
});

QrScanner.hasCamera().then(hasCamera => camHasCamera.textContent = hasCamera);


if (DJANGO_DEBUG) {
    window.scanner = qrScanner;
}
