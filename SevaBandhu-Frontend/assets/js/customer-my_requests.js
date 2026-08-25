

console.log('ðŸš€ Script loaded');

const popup =
document.getElementById('techPopup');

const backdrop =
document.getElementById('popupBackdrop');

const popupCloseBtn =
document.getElementById('popupCloseBtn');

/////////////////////////////////////////////////////
// SHOW POPUP
/////////////////////////////////////////////////////

function showTechnicianPopup(technicianData){

    document.getElementById(
        'popupTechName'
    ).textContent =
    technicianData.name || 'N/A';

    document.getElementById(
        'popupTechContact'
    ).textContent =
    technicianData.contact || 'N/A';

    document.getElementById(
        'popupTechEmail'
    ).textContent =
    technicianData.email || 'N/A';

    document.getElementById(
        'popupTechSpec'
    ).textContent =
    technicianData.specialization || 'N/A';

    document.getElementById(
        'popupTechExp'
    ).textContent =
    (technicianData.experience || 'N/A') + ' years';

    document.getElementById(
        'popupTechAreas'
    ).textContent =
    technicianData.areas || 'N/A';

    popup.classList.add('show');

    backdrop.classList.add('show');
}

/////////////////////////////////////////////////////
// CLOSE POPUP
/////////////////////////////////////////////////////

function closePopup(){

    popup.classList.remove('show');

    backdrop.classList.remove('show');
}

/////////////////////////////////////////////////////
// STATUS CLICK
/////////////////////////////////////////////////////

document.addEventListener(
    'DOMContentLoaded',

function(){

    const statusBadges =
    document.querySelectorAll(
        '.status-assigned-clickable'
    );

    statusBadges.forEach((badge) => {

        badge.addEventListener(
            'click',

        function(e){

            e.preventDefault();

            const technicianData = {

                name:
                this.getAttribute('data-tech-name'),

                contact:
                this.getAttribute('data-tech-contact'),

                email:
                this.getAttribute('data-tech-email'),

                specialization:
                this.getAttribute('data-tech-specialization'),

                experience:
                this.getAttribute('data-tech-experience'),

                areas:
                this.getAttribute('data-tech-areas')
            };

            showTechnicianPopup(
                technicianData
            );
        });

    });

});

/////////////////////////////////////////////////////
// CLOSE EVENTS
/////////////////////////////////////////////////////

popupCloseBtn.addEventListener(
    'click',

function(e){

    e.preventDefault();

    closePopup();
});

backdrop.addEventListener(
    'click',

function(){

    closePopup();
});

document.addEventListener(
    'keydown',

function(e){

    if(
        e.key === 'Escape' &&
        popup.classList.contains('show')
    ){

        closePopup();
    }
});

