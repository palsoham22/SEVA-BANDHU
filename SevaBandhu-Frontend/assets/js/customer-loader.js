

window.addEventListener("load", function(){

    setTimeout(() => {

        window.location.href = "{% url 'home' %}";

    }, 2000);

});

