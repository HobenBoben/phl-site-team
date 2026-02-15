// Ждём полной загрузки DOM
document.addEventListener('DOMContentLoaded', function() {
    
    // --- Переключение темы ---
    (function() {
        const themeToggleBtn = document.getElementById('theme-toggle');
        if (!themeToggleBtn) {
            console.warn('Кнопка темы не найдена');
            return;
        }
        
        const body = document.body;
        const moonIcon = '🌙';
        const sunIcon = '☀️';
        
        // Применяем сохранённую тему
        const savedTheme = localStorage.getItem('theme');
        if (savedTheme === 'dark') {
            body.classList.add('dark-theme');
            themeToggleBtn.textContent = sunIcon;
        } else {
            themeToggleBtn.textContent = moonIcon;
        }
        
        // Обработчик клика
        themeToggleBtn.addEventListener('click', function() {
            body.classList.toggle('dark-theme');
            const isDark = body.classList.contains('dark-theme');
            localStorage.setItem('theme', isDark ? 'dark' : 'light');
            themeToggleBtn.textContent = isDark ? sunIcon : moonIcon;
        });
    })();
    
    // --- Плавное появление карточек (если есть) ---
    document.querySelectorAll(".card-modern").forEach(card => {
        card.classList.add("fade-in");
    });
    
    // --- Динамическое размытие фона (только на главной, где есть #bg-blur) ---
    (function() {
        const bg = document.getElementById('bg-blur');
        if (!bg) return; // если элемента нет (не главная), выходим
        
        function updateBlur() {
            const scrollY = window.scrollY;
            // Максимальное размытие 20px при прокрутке 600px
            const blurValue = Math.min(20, scrollY / 30);
            bg.style.filter = `blur(${blurValue}px)`;
        }
        
        window.addEventListener('scroll', updateBlur);
        updateBlur(); // установить начальное значение
    })();
    
});