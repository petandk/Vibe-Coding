# Fix de brillo para teclados Mac en Ubuntu (entorno 42)

Resumen rápido
- En algunos equipos Mac con la imagen de 42/Ubuntu, las teclas F1/F2 envían keycodes incorrectos:
  - F1 → keycode 78
  - F2 → keycode 127
- Objetivo: que F1 baje el brillo (XF86MonBrightnessDown) y F2 lo suba (XF86MonBrightnessUp) sin usar `sudo`.

Comando exacto para añadir a "Aplicaciones al inicio"
- Añade exactamente esta línea como entrada en "Aplicaciones al inicio" / "Startup Applications":

```bash
bash -c "sleep 5 && xmodmap -e 'keycode 78 = XF86MonBrightnessDown' && xmodmap -e 'keycode 127 = XF86MonBrightnessUp'"
```

Por qué y notas rápidas
- `sleep 5` da tiempo a que el servidor gráfico y el entorno de escritorio terminen de iniciarse antes de aplicar los mapeos. (sin esto no funciona, aunque he conseguido que funcione con solo 3).
- `xmodmap -e '...'` aplica el mapeo directamente a la sesión X actual.
- Las reasignaciones hechas con `xmodmap` son por sesión: se aplican al iniciar sesión y deben recargarse en cada inicio de sesión (por eso se usa la entrada en Autostart).
- Si tu sesión usa Wayland en lugar de Xorg, `xmodmap` puede no funcionar; en ese caso habrá que usar una solución específica para el compositor/Wayland.
- Si el entorno tarda más en estar listo, aumenta `sleep` (por ejemplo `sleep 8`).

Cómo probar antes de añadir
- Abre una terminal y ejecuta exactamente el comando anterior. Si F1/F2 pasan a controlar el brillo, añade la misma línea a "Aplicaciones al inicio".

Eso es todo: pega el comando en "Aplicaciones al inicio" y, si es necesario, ajusta el `sleep` al valor que funcione en tu entorno.
