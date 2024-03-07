// SPDX-FileCopyrightText: 2024 Thomas Breitner
//
// SPDX-License-Identifier: EUPL-1.2

// Constants from backend
const dlcdbConstants = document.currentScript.dataset;
const DJANGO_DEBUG = dlcdbConstants.djangoDebug;
const API_URL_BASE = dlcdbConstants.apiUrlBase;
const API_TOKEN = dlcdbConstants.apiToken;

console.info("DJANGO_DEBUG: ", DJANGO_DEBUG)

// Constants from frontend
const STATE_BUTTON_PREFIX = 'state-btn-'
const ROW_UUID_PREFIX = 'tr-uuid-'
const uuidFormField = document.getElementById('id_uuids');

const DEVICE_STATE_UNKNOWN = "dev_state_unknown";
const DEVICE_STATE_FOUND = "dev_state_found";
const DEVICE_STATE_ADDED = "dev_state_added";
const DEVICE_STATE_NOTFOUND = "dev_state_notfound";

const uuids_states_map = new Map();


async function getDeviceByUuid(uuid) {
    // console.log("getDeviceByUuid")

    const apiDeviceQuery = `${API_URL_BASE}/devices/${uuid}/`
    const response = await fetch(apiDeviceQuery, {headers: {Authorization: `Token ${API_TOKEN}`} });
    const deviceData = await response.json();
    return deviceData;

    // fetch(apiDeviceQuery, {
    //     headers: {Authorization: `Token ${API_TOKEN}`}
    // })
    // .then((response) => {
    //     if (!response.ok) {
    //         throw new Error(`Network response was not OK, got: ${response.status}`);
    //     }
    //     return response.json();
    // })
    // .then((data) => {
    //     console.log("fetch(apiDeviceQuery): ", data);
    //     addNewDeviceRow(data)
    //     // We do not trigger dev_state_found automatically, user must push button manually
    //     // manageUuid({uuid: uuid, state: DEVICE_STATE_ADDED});
    // })
    // .catch(function(error) {
    //     alert("fetch error: " + error)
    //     console.warn(error);
    // })
}


async function getRoomByUuid(uuid, callback) {
    console.log("getRoomByUuid")
    const apiRoomQuery = `${API_URL_BASE}/rooms/${uuid}/`
    // console.log("apiRoomQuery: ", apiRoomQuery)
    const response = await fetch(apiRoomQuery, {headers: {Authorization: `Token ${API_TOKEN}`} });
    const roomData = await response.json();
    return roomData;
}


// function update_found_devices_count(count) {
//     let count_elem = document.getElementById("found_devices_count")
//     count_elem.classList.add("blink");
//     count_elem.textContent = count;
// }

function btnClick() {
    console.log("=== btnClick =========")
    let this_btn = this;

    // If the clicked element doesn't have the right selector, bail
    if (!this_btn.classList.contains('state-trigger')) return;
    event.preventDefault();

    let this_btn_iconelem = this_btn.querySelector('.fas');
    let uuid = this_btn.id.replace(STATE_BUTTON_PREFIX, '')
    let row = this_btn.closest(".inventory_row")

    console.log("this_btn.id: " + uuid)

    if (row.classList.contains(DEVICE_STATE_ADDED)) {
        row.classList.remove(DEVICE_STATE_ADDED, "table-info")
        row.classList.add(DEVICE_STATE_FOUND, "table-success")
        this_btn_iconelem.className = "fas fa-check-square";
        manageUuid({uuid: uuid, state: DEVICE_STATE_FOUND_UNEXPECTED});
    } else if (row.classList.contains(DEVICE_STATE_UNKNOWN)) {
        row.classList.remove(DEVICE_STATE_UNKNOWN, "table-default")
        row.classList.add(DEVICE_STATE_FOUND, "table-success")
        this_btn_iconelem.className = "fas fa-check-square";
        manageUuid({uuid: uuid, state: DEVICE_STATE_FOUND});
    } else if (row.classList.contains(DEVICE_STATE_FOUND)) {
        row.classList.remove(DEVICE_STATE_FOUND, "table-success")
        row.classList.add(DEVICE_STATE_NOTFOUND, "table-danger")
        this_btn_iconelem.className = "fas fa-times-circle";
        manageUuid({uuid: uuid, state: DEVICE_STATE_NOTFOUND});
    } else if (row.classList.contains(DEVICE_STATE_NOTFOUND)) {
        row.classList.remove(DEVICE_STATE_NOTFOUND, "table-danger")
        row.classList.add(DEVICE_STATE_UNKNOWN, "table-default")
        this_btn_iconelem.className = "fas fa-question-circle";
        manageUuid({uuid: uuid, state: DEVICE_STATE_UNKNOWN});
    } else {
        console.log("[btnClick] This should never happen!")
    }
}


function deviceRowTemplate(device){
    return `
        <tr id="${ROW_UUID_PREFIX}${device.uuid}" class="inventory_row ${DEVICE_STATE_UNKNOWN} table-info">
            <td>
                ${device.edv_id}
                <br>
                <span class="badge badge-pill badge-warning small">
                    ADDED
                </span>
            </td>
            <td>
                ${device.manufacturer}, ${device.series}
            </td>
            <td>
                <button 
                    type="button"
                    class="state-trigger btn btn-outline-secondary" 
                    id="${STATE_BUTTON_PREFIX}${device.uuid}"
                >
                    <i class="fas fa-question-circle {# fa-plus-square #}"></i>
                </button>
            </td>
            <td>
                Current:
                <span class="badge badge-pill badge-warning small">
                    ${device.record_type} ${device.room ? device.room : ''}
                </span>
            </td>
            <td>
                <abbr title="Not Implemented">501</abbr>
            </td>
        </tr>
    `;
}


async function addNewDeviceRow(device) {
    console.log("[addNewDeviceRow] for device: ", device)
    // console.log(typeof device)
    // console.log(device.length)
    // console.info("device: ", device)

    // If no device is selected, do nothing
    if (device.length) {
        alert("Select device first...");
        return;
    }

    let tableTbody = document.getElementById("devices-table-tbody");
    let newRow = deviceRowTemplate(device);
    tableTbody.insertAdjacentHTML( 'afterbegin', newRow );

    let query = STATE_BUTTON_PREFIX + device.uuid
    let stateButton = document.getElementById(query);
    // console.log("stateButton: ", stateButton)
    stateButton.addEventListener('click', btnClick, false);

    $('#id_device').val(null).trigger('change');

    manageUuid({uuid: device.uuid, state: DEVICE_STATE_UNKNOWN});

    return true;
}


function manageUuid({ uuid, state }) {
    console.log("uuidFormField: " + uuidFormField.getAttribute('value'))
    console.log("manageUuid: uuid: " + uuid + " state: " + state);

    if (( state == DEVICE_STATE_FOUND ) || ( state == DEVICE_STATE_NOTFOUND) || ( state == DEVICE_STATE_UNKNOWN)) {
        uuids_states_map.set(uuid, state);
        // markRow({uuid: uuid, state: state});
        // update_found_devices_count(uuids_states_map.size);

        let serialized_uuids_states_map = JSON.stringify(Object.fromEntries(uuids_states_map));
        uuidFormField.setAttribute('value', serialized_uuids_states_map);
    } else {
        alert("[manageUuid] This should never happen! uuid: " + uuid + " state: " + state + "Please get in touch with your IT.");
    }
}


async function handleDeviceScan(uuid){
    /* 
    1. if scanned uuid is in current uuid table -> mark as "found"
    2. if scanned uuid is not in current uuid table -> add new device row
    */

    // const _myuuid = "e65b4119-2147-4ff7-9d8a-754995c62d9c"
    const rowID = `tr-uuid-${uuid}`
    console.log("rowID: ", rowID)
    const matchedRow = document.getElementById(rowID);

    if (matchedRow){
        console.log("matchedRow: ", matchedRow)
        const row = matchedRow
        const this_btn_iconelem = row.querySelector('.fas');

        row.classList.remove(DEVICE_STATE_UNKNOWN, "table-default")
        row.classList.add(DEVICE_STATE_FOUND, "table-success")
        this_btn_iconelem.className = "fas fa-check-square";
        manageUuid({uuid: uuid, state: DEVICE_STATE_FOUND});
    } else {
        device = await getDeviceByUuid(uuid);
        const isDone = await addNewDeviceRow(device);
        if (isDone) {
            console.info(`Successfully added new device row for ${device}`);
            return true;
        }
    }
}


async function handleRoomScan(uuid){
    const roomModalElem = document.querySelector('#switch_room_modal');
    const roomNumberElem = document.querySelector('#modal-to-room-number');
    const roomObj = await getRoomByUuid(uuid);
    
    roomModalElem.dataset.uuid = uuid;
    roomNumberElem.textContent = roomObj.number;

    $('#switch_room_modal').modal('show');

    $('#switch_room_modal .modal-footer button').on('click', function (event) {
        let clicked_button = $(event.target);
        let parent = clicked_button.closest(".modal")
        let uuid = parent[0].dataset.uuid

        if (clicked_button[0].id === "change_room") {
            location = `room/${roomObj.pk}`;
        }
    });
}


// DEVICE: live collection of matched elements
let btns = document.getElementsByClassName('state-trigger');
if (btns) {
    for (let btn of btns) {
        btn.addEventListener('click', btnClick, false);
    }
}

// Add new device via form
const addDeviceButton = document.querySelector("#add-device-button");

if (addDeviceButton){
    addDeviceButton.addEventListener("click", function(event) {
        let select2SelectedOption = $('#id_device').select2('data')[0].id;
        console.log("[addDeviceButton] adding device: ", select2SelectedOption)
        handleDeviceScan(select2SelectedOption);
        event.preventDefault();
    }, false);
}
