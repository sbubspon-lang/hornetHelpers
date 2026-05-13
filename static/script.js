function showPopup() {
    document.getElementById('popup').style.display = 'block'
}

function redirectHome() {
    window.location.href = '/homepage'
}
/*
function redirectSignup() {
    window.location.href = '/signup'
}
*/
// Have flash messages disappear after 5 seconds
setTimeout(() => {
    const flashMessages = document.querySelector('.flash-messages');

    if (flashMessages) {
        flashMessages.style.opacity = "0";

        setTimeout(() => {
            flashMessages.style.display = "none";
        }, 500);
    }
}, 5000);
