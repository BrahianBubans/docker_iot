
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
    // Seleccionar todos los botones de cambio de tema
    const themeSwitches = document.querySelectorAll('.theme-switch');

    themeSwitches.forEach(button => {
        button.addEventListener('click', (event) => {
            event.preventDefault(); 
            
            // Obtener el tema seleccionado (light o dark)
            const selectedTheme = button.getAttribute('data-bs-theme');
            
            // Aplicar el tema al documento HTML
            document.documentElement.setAttribute('data-bs-theme', selectedTheme);
            
            // Guardar preferencia en localStorage
            localStorage.setItem('theme', selectedTheme);
        });
    });
});