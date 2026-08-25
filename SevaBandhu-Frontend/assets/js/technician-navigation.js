



/////////////////////////////////////////////////////
// MAP
/////////////////////////////////////////////////////

const map = L.map('map', {

    zoomControl: true

});

L.tileLayer(

    'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',

    {

        maxZoom: 19,

        attribution:
        '&copy; OpenStreetMap contributors'

    }

).addTo(map);
setTimeout(() => {

    map.invalidateSize();

}, 1000);
/////////////////////////////////////////////////////
// TECHNICIAN MARKER
/////////////////////////////////////////////////////

const technicianIcon = L.icon({

    iconUrl:
    'https://cdn-icons-png.flaticon.com/512/744/744465.png',

    iconSize: [40, 40],

    iconAnchor: [20, 20]

});

const technicianMarker = L.marker(

    [0, 0],

    {

        icon: technicianIcon,

        zIndexOffset: 1000

    }

)

.addTo(map)
.bindPopup("ðŸš— Technician");
/////////////////////////////////////////////////////
// CUSTOMER LOCATION
/////////////////////////////////////////////////////

const customerLat = parseFloat(
    "{{ service_request.customer_latitude }}"
    
);


const customerLng = parseFloat(
    "{{ service_request.customer_longitude }}"
);

/////////////////////////////////////////////////////
// CUSTOMER MARKER
/////////////////////////////////////////////////////

const customerIcon = L.icon({

    iconUrl:
    'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-blue.png',

    shadowUrl:
    'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',

    iconSize: [25, 41],

    iconAnchor: [12, 41],

    popupAnchor: [1, -34],

    shadowSize: [41, 41]

});

const customerMarker = L.marker(

    [customerLat, customerLng],

    {

        icon: customerIcon,

        zIndexOffset: 999

    }

)

.addTo(map)

.bindPopup("ðŸ  Customer Location");
/////////////////////////////////////////////////////
// ROUTE CONTROL
/////////////////////////////////////////////////////



/////////////////////////////////////////////////////
// LIVE TECHNICIAN GPS
/////////////////////////////////////////////////////

/////////////////////////////////////////////////////
// WEBSOCKET
/////////////////////////////////////////////////////

/////////////////////////////////////////////////////
// WEBSOCKET
/////////////////////////////////////////////////////

const wsProtocol =

    window.location.protocol === "https:"

    ? "wss://"

    : "ws://";

const trackingSocket = new WebSocket(

    wsProtocol +

    window.location.host +

    '/ws/tracking/{{ service_request.id }}/'

);

navigator.geolocation.watchPosition(

    function(position) {

        const lat =
        position.coords.latitude;

        const lng =
        position.coords.longitude;

        /////////////////////////////////////////////////////
// SEND LIVE LOCATION TO CUSTOMER
/////////////////////////////////////////////////////

if (
    trackingSocket.readyState === WebSocket.OPEN
) {

    trackingSocket.send(

        JSON.stringify({

            type: 'live_location',

            request_id:
            "{{ service_request.id }}",

            latitude: lat,

            longitude: lng

        })

    );

}

        /////////////////////////////////////////////////////
        // FIRST GPS LOAD
        /////////////////////////////////////////////////////

setTimeout(() => {
if (!window.mapInitialized) {

    map.setView([lat, lng], 15);

    window.mapInitialized = true;

}

    map.invalidateSize();

}, 500);

technicianMarker.setLatLng([lat, lng]);
        /////////////////////////////////////////////////////
// CREATE ROUTE ONLY AFTER GPS READY
/////////////////////////////////////////////////////

if (!window.routeControl) {

    window.routeControl = L.Routing.control({
        createMarker: function() {

    return null;

},

        waypoints: [

          L.latLng(lat, lng),
L.latLng(customerLat, customerLng)

        ],

        routeWhileDragging: false,

        addWaypoints: false,

        draggableWaypoints: false,

        fitSelectedRoutes: true,

        show: false

    }).addTo(map);
    /////////////////////////////////////////////////////
// ETA + DISTANCE
/////////////////////////////////////////////////////

window.routeControl.on(

    'routesfound',

    function(e) {

        const route =
        e.routes[0];

        const distance =
        (
            route.summary.totalDistance / 1000
        ).toFixed(2);

        const time =
        Math.round(
            route.summary.totalTime / 60
        );

        document.getElementById(
            'journey-info'
        ).innerHTML =

        `ðŸš— ${time} mins away â€¢ ðŸ“ ${distance} km remaining`;

    }

);

}
else {

    window.routeControl.setWaypoints([

        L.latLng(customerLat, customerLng),

        L.latLng(lat, lng)

    ]);

}

        /////////////////////////////////////////////////////        // SEND LIVE LOCATION TO CUSTOMER
        /////////////////////////////////////////////////////

       

        /////////////////////////////////////////////////////        // MOVE TECHNICIAN MARKER
        /////////////////////////////////////////////////////

        technicianMarker.setLatLng([lat, lng]);
    

        /////////////////////////////////////////////////////
        // UPDATE MAP
        /////////////////////////////////////////////////////

     if (!window.mapCentered) {

    map.panTo([lat, lng]);

    window.mapCentered = true;

}

        /////////////////////////////////////////////////////
        // UPDATE TEXT
        /////////////////////////////////////////////////////

    },

    function(error) {

        console.error(
            "âŒ GPS ERROR:",
            error
        );

    },

    {

        enableHighAccuracy: true,

        maximumAge: 1000,

        timeout: 10000
    }

);

