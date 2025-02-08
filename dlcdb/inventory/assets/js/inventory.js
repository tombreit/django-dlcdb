import { initModal, initToast } from './modules/ui.js'
import { initInventorizeRoomDetail } from './modules/inventorize_room_detail.js'
import { initQrToggle } from './modules/qrtoggle.js'
import { initInventorize } from './modules/inventorize.js'
import { initQrScanner } from './modules/qr_inventorize.js'

document.addEventListener('DOMContentLoaded', () => {
  initModal()
  initToast()
  initInventorizeRoomDetail()
  initQrToggle()
  initInventorize()
  initQrScanner()
})
