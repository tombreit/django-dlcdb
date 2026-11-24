// SPDX-FileCopyrightText: 2024 Thomas Breitner
//
// SPDX-License-Identifier: EUPL-1.2

// SCANNER via https://github.com/nimiq/qr-scanner

import QrScanner from 'qr-scanner'

import { handleDeviceScan, handleRoomScan } from './inventorize.js'
import { getJsVars, getPage } from './ui.js'

const jsVars = getJsVars()
const djangoDebug = jsVars.djangoDebug

const videoElem = document.getElementById('qr-video')
const camHasCamera = document.getElementById('cam-has-camera')
const camQrResult = document.getElementById('cam-qr-result')
const camQrResultTimestamp = document.getElementById('cam-qr-result-timestamp')

const escapeRegExp = text => text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')

// {modelName, uuid} of a DLCDB label, null for any other QR code.
// A label encodes QRCODE_PREFIX, the infix of its model (QRCODE_INFIXES) and
// the object's uuid, e.g. "DLCDBD3f2c…". Any UUID version; label software may
// print the hex digits in upper case.
function parseQrCode(text) {
  const modelNameByInfix = Object.fromEntries(
    Object.entries(jsVars.qrCodeInfixes).map(([modelName, infix]) => [infix, modelName]),
  )
  const pattern = new RegExp(
    '^' + escapeRegExp(jsVars.qrCodePrefix)
    + '(' + Object.keys(modelNameByInfix).map(escapeRegExp).join('|') + ')'
    + '([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})$',
  )
  const match = pattern.exec(text)
  if (!match) return null
  return { modelName: modelNameByInfix[match[1]], uuid: match[2].toLowerCase() }
}

function setResult(label, result) {
  label.textContent = result.data
  camQrResultTimestamp.textContent = new Date().toString()
  label.style.color = 'teal'
  clearTimeout(label.highlightTimeout)
  label.highlightTimeout = setTimeout(() => label.style.color = 'inherit', 100)

  // Other QR codes (a vendor's, a URL) only show in the result line above.
  const qrCode = parseQrCode(result.data)
  if (qrCode?.modelName === 'device') {
    handleDeviceScan(qrCode.uuid)
  }
  else if (qrCode?.modelName === 'room') {
    handleRoomScan(qrCode.uuid)
  }
}

export function initQrScanner() {
  const qrScannerEnabled = jsVars.qrScannerEnabled
  console.log('qrScannerEnabled: ', qrScannerEnabled)

  if (qrScannerEnabled && ['inventorize-room-detail', 'inventorize-room-list'].includes(getPage())) {
    console.log('initQrScanner...')

    const qrScanner = new QrScanner(videoElem, result => setResult(camQrResult, result), {
      onDecodeError: (error) => {
        camQrResult.textContent = error
        camQrResult.style.color = 'inherit'
      },
      returnDetailedScanResult: true,
      highlightScanRegion: true,
      highlightCodeOutline: true,
    })

    qrScanner.start().then(() => {
      console.log('qrScanner start...')
    })

    QrScanner.hasCamera().then(hasCamera => camHasCamera.textContent = hasCamera)

    if (djangoDebug) {
      window.scanner = qrScanner
    }
  }
}
