

function selectService(service){

    const baseUrl =
    "{% url 'customer_create_request' %}";

    window.location.href =
    baseUrl + "?service=" +
    encodeURIComponent(service);
}

