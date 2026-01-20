window.onscroll = function () {
    var nav = document.querySelector('nav');

    if (window.pageYOffset > 50) {
        nav.style.backgroundColor = '#000000';
    } else {
        nav.style.backgroundColor = '#1a1a1a';
    }
};

document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.onclick = function (e) {
        e.preventDefault();

        var targetId = this.getAttribute('href');
        var targetElement = document.querySelector(targetId);

        if (targetElement) {
            targetElement.scrollIntoView({
                behavior: 'smooth'
            });
        }
    };
});

console.log("Сайт завантажений!");
