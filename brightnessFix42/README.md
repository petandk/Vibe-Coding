# Solución de Brillo para Hardware Mac en Ubuntu (Sin Sudo)

Este repositorio proporciona una solución simple y efectiva para mapear las teclas de función F1 y F2 en hardware Mac ejecutando una versión modificada de Ubuntu, permitiendo controlar el brillo de la pantalla sin necesidad de permisos de `sudo`.

## El Problema

En los teclados de Ubuntu marca LMP de 42 para hardware Mac, las teclas de función F1 y F2 no se reconocen correctamente o no realizan la acción esperada (controlar el brillo). Específicamente, se ha observado que:

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

1.  **Crea los archivos necesarios**: Dado que este proyecto está dentro de una estructura más amplia, puedes crear los archivos directamente o copiando el contenido a continuación.

    **Archivo: `setup_brightness.sh`**
    ```bash
    #!/bin/bash

    # Define the path for the .Xmodmap file in the user's HOME directory
    XMODMAP_FILE="$HOME/.Xmodmap"

    # Generate the .Xmodmap content
    cat <<EOF > "$XMODMAP_FILE"
    ! Clear existing bindings for keycodes to avoid conflicts
    keycode 78 =
    keycode 127 =

    ! Assign keycode 78 (F1) to decrease screen brightness
    keycode 78 = XF86MonBrightnessDown

    ! Assign keycode 127 (F2) to increase screen brightness
    keycode 127 = XF86MonBrightnessUp
    EOF

    # Load the new .Xmodmap configuration
    xmodmap "$XMODMAP_FILE"

    echo "El archivo .Xmodmap ha sido creado en $XMODMAP_FILE y se ha aplicado."
    echo "Para que estos cambios persistan después de reiniciar la sesión, añade este script a 'Startup Applications' o 'Aplicaciones al inicio'."
    echo "Puedes hacerlo buscando 'Startup Applications' en tu menú de aplicaciones, y añadiendo una nueva entrada con el comando:"
    echo "bash \$HOME/Desktop/brightnessFix42/setup_brightness.sh"
    ```

2.  **Haz que el script `setup_brightness.sh` sea ejecutable**:
    (Asumiendo que creaste el archivo `setup_brightness.sh` en el directorio correcto, por ejemplo, `$HOME/Desktop/brightnessFix42/`)
    ```bash
    chmod +x $HOME/Desktop/brightnessFix42/setup_brightness.sh
    ```

3.  **Ejecuta el script:**
    ```bash
    bash $HOME/Desktop/brightnessFix42/setup_brightness.sh
    ```
    Este comando creará el archivo `.Xmodmap` en tu directorio `HOME` y aplicará los cambios de mapeo de teclado inmediatamente. Verás un mensaje de confirmación en la terminal.

4.  **Haz que los cambios persistan después de reiniciar la sesión:**
    **Importante**: Los cambios realizados por `xmodmap` solo afectan a la sesión gráfica activa y se pierden al cerrar sesión. Para que las asignaciones de teclas se mantengan cada vez que inicies sesión, debes añadir el script `setup_brightness.sh` a tus "Aplicaciones al inicio" (o "Startup Applications").
    -   Abre el menú de aplicaciones y busca "Aplicaciones al inicio" o "Startup Applications".
    -   Haz clic en "Añadir" o "Add".
    -   En el campo "Nombre" (Name), puedes poner algo como: `Configuración de Brillo Mac`
    -   En el campo "Comando" (Command), introduce la ruta completa a tu script:
        ```
        bash $HOME/Desktop/brightnessFix42/setup_brightness.sh
        ```
    -   Puedes dejar el campo "Comentario" (Comment) en blanco o añadir una descripción.
    -   Haz clic en "Añadir" o "Add" para guardar la entrada.

¡Listo! Después de configurar esto, cada vez que inicies sesión, las teclas F1 y F2 de tu Mac deberían controlar el brillo de la pantalla.

## Creado por IA

Este script y la configuración asociada han sido creados por mí, una inteligencia artificial desarrollada por Google. Mi objetivo es ayudarte a resolver problemas técnicos de manera eficiente y proporcionar explicaciones claras. Si tienes alguna otra pregunta o necesitas más asistencia, no dudes en preguntar.
