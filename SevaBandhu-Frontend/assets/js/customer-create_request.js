

const params = new URLSearchParams(window.location.search);
const service = params.get("service");

if(service){
document.getElementById("serviceCategory").value = service;
}

navigator.geolocation.getCurrentPosition(

    function(position) {

        document.getElementById(
            "customer_latitude"
        ).value =
        position.coords.latitude;

        document.getElementById(
            "customer_longitude"
        ).value =
        position.coords.longitude;

        console.log(
            "ðŸ“ CUSTOMER LOCATION CAPTURED"
        );

    },

    function(error) {

        console.error(
            "âŒ CUSTOMER GPS ERROR:",
            error
        );

    }

);
