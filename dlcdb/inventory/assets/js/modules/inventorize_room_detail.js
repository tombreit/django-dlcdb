import TomSelect from 'tom-select'

export function initInventorizeRoomDetail() {
  // Page-specific code for inventorize_room_detail only
  // TODO: Move this to a separate module
  function inventorizeRoomDetail() {
    // Initialize TomSelect on the "device" field
    const deviceSelect = document.getElementById('id_device')
    if (deviceSelect) {
      new TomSelect(deviceSelect, {
        create: false,
        maxItems: 1,
        closeAfterSelect: true,
      })
    }

    // Filter table functionality
    const devicesTable = document.querySelector('#devices-table tbody')
    const devicesTableSearchInput = document.querySelector('#search-table-input')

    if (devicesTable && devicesTableSearchInput) {
      function filterDeviceTable() {
        const query = devicesTableSearchInput.value.toLowerCase()
        const rows = devicesTable.rows

        for (const row of rows) {
          let matchInRow = false
          for (const cell of row.cells) {
            let cellContent = cell.textContent || cell.innerText
            cellContent = cellContent.toLowerCase()
            if (cellContent.includes(query)) {
              matchInRow = true
              break
            }
          }
          row.style.display = matchInRow ? 'table-row' : 'none'
        }
      }
      devicesTableSearchInput.addEventListener('keyup', filterDeviceTable)
    }
  }

  // Check if we're on the inventorize_room_detail page via a data attribute
  if (document.body.dataset.page === 'inventorize-room-detail') {
    inventorizeRoomDetail()
  }
}
