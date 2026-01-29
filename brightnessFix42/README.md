# Solución de Brillo para Hardware Mac en Ubuntu (Sin Sudo)

Este repositorio proporciona una solución simple y efectiva para mapear las teclas de función F1 y F2 en el hardware Mac ejecutando la versión modificada de Ubuntu de 42 Barcelona, permitiendo controlar el brillo de la pantalla sin necesidad de permisos de `sudo`.

## El Problema

En algunas configuraciones de Ubuntu sobre hardware Mac con los nuevos teclados de la marca LMP, las teclas de función F1 y F2 no se reconocen correctamente o no realizan la acción esperada (controlar el brillo). Específicamente, se ha observado que:

- La tecla **F1** envía el `keycode 78` (identificado erróneamente como Scroll Lock).
- La tecla **F2** envía el `keycode 127` (identificado como Pause).

El objetivo es reasignar estos keycodes para que F1 disminuya el brillo y F2 lo aumente, utilizando las acciones estándar de X11 `XF86MonBrightnessDown` y `XF86MonBrightnessUp`.

## ¿Por qué esta solución es ideal para usuarios sin privilegios de root?

Esta solución utiliza `xmodmap`, una utilidad estándar de X11 que permite reasignar keycodes y keysyms a nivel de usuario. Esto significa que **no requiere permisos de `sudo`** ni modifica archivos del sistema global, lo que la hace perfecta para entornos donde el usuario no tiene privilegios de administrador.

## Contenido del Repositorio

- **`setup_brightness.sh`**: Un script de Bash que genera y aplica automáticamente el archivo `.Xmodmap` necesario.
- **`.Xmodmap`**: (Generado por el script) El archivo de configuración que mapea los keycodes 78 y 127 a las funciones de control de brillo.

## Cómo Usar

Sigue estos pasos para aplicar la solución:

1.  **Clona o descarga este repositorio** en tu directorio `HOME` o en cualquier otra ubicación accesible. Por ejemplo, en tu `Desktop`:
    ```bash
    cd ~/Desktop
    # Si estás usando git
    git clone https://github.com/tu_usuario/brightnessFix.git
    # Si has descargado un zip, descomprímelo
    ```
    Asegúrate de que el directorio del proyecto se encuentre en una ruta como `/home/rmanzana/Desktop/brightnessFix`.

2.  **Haz que el script sea ejecutable** (si no lo es ya):
    ```bash
    chmod +x ~/Desktop/brightnessFix/setup_brightness.sh
    ```

3.  **Ejecuta el script:**
    ```bash
    bash ~/Desktop/brightnessFix/setup_brightness.sh
    ```
    Este comando creará el archivo `.Xmodmap` en tu directorio `HOME` y aplicará los cambios de mapeo de teclado inmediatamente. Verás un mensaje de confirmación en la terminal.

4.  **Haz que los cambios persistan después de reiniciar:**
    Para que las asignaciones de teclas se mantengan cada vez que inicies sesión, debes añadir el script `setup_brightness.sh` a tus "Aplicaciones al inicio" (o "Startup Applications").

    -   Abre el menú de aplicaciones y busca "Aplicaciones al inicio" o "Startup Applications".
    -   Haz clic en "Añadir" o "Add".
    -   En el campo "Nombre" (Name), puedes poner algo como: `Configuración de Brillo Mac`
    -   En el campo "Comando" (Command), introduce la ruta completa a tu script:
        ```
        bash /home/rmanzana/Desktop/brightnessFix/setup_brightness.sh
        ```
    -   Puedes dejar el campo "Comentario" (Comment) en blanco o añadir una descripción.
    -   Haz clic en "Añadir" o "Add" para guardar la entrada.

¡Listo! Después de configurar esto, cada vez que inicies sesión, las teclas F1 y F2 de tu Mac deberían controlar el brillo de la pantalla.
