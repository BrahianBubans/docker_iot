
const btnDelete= document.querySelectorAll('.btn-borrar');
if(btnDelete) {
  const btnArray = Array.from(btnDelete);
  btnArray.forEach((btn) => {
    btn.addEventListener('click', (e) => {
      if(!confirm('¿Está seguro de querer borrar?')){
        e.preventDefault();
      }
    });
  })
}

document.addEventListener('DOMContentLoaded', () => {
    const themeSwitches = document.querySelectorAll('.theme-switch');

    themeSwitches.forEach(button => {
        button.addEventListener('click', (event) => {
            event.preventDefault(); 
            
            const selectedTheme = button.getAttribute('data-bs-theme');
            const userId = button.getAttribute('data-user');
            
            document.documentElement.setAttribute('data-bs-theme', selectedTheme);
            
            // Guarda la selección usando un prefijo único por usuario
            if (userId) {
                localStorage.setItem(`theme_${userId}`, selectedTheme);
            }
        });
    });
});