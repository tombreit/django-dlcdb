/* Hide initially populated device field for add_form when called with a device */

document.addEventListener("DOMContentLoaded", function(event) {
    const params = (new URL(location)).searchParams;
    const withDevice = params.get('device');
    console.info("withDevice: ", withDevice)

    if (withDevice) {
        const formFieldDeviceElem = document.querySelector(".field-device");
        console.info("formFieldDeviceElem: ", formFieldDeviceElem);
        formFieldDeviceElem.style.setProperty('display', 'none');
    } else {
        console.info("Form instanciated without a device.");
    }
});
