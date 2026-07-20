# 💪 Muscle Tutor

¡Bienvenido al nuevo dispositivo de tortura... digo, herramienta de aprendizaje del repositorio **vive coding**!

**🤖 Aviso de Transparencia:** El 100% del código Python de esta aplicación fue escrito por mí, una IA (Gemini). Mi amigo humano ideó la arquitectura, los estrictos requisitos de diseño y las quejas totalmente válidas sobre el ordenamiento alfabético estándar de los archivos. Yo solo hice el trabajo pesado de escribir el código repetitivo de `tkinter`.

**🧪 El Gran Testeo:** Un agradecimiento especial a mi colega humano, quien fue el **alfa y beta tester oficial** de este proyecto. Sin su incesante búsqueda de errores, sus sugerencias de UX para la barra lateral y su insistencia en una lógica de ordenamiento lógica para C/C++, esta herramienta seguiría siendo solo un script lleno de bugs.

## 🤷‍♂️ ¿Qué es esto?

**Muscle Tutor** (`muscle_tutor.py`) es una aplicación de mecanografía despiadada y agnóstica al lenguaje, diseñada para grabar la sintaxis directamente en tus dedos.

Si alguna vez te has quedado en blanco durante un examen de programación estricto porque olvidaste cómo configurar tus includes, o porque tu moderno y elegante IDE normalmente cierra los corchetes y maneja la indentación por ti, esta herramienta lo soluciona. Elimina todo el autocompletado, linting y ayuda de formato, obligándote a escribir el código *exactamente* como está escrito, pulsación a pulsación en crudo.

## ✨ Características

*   **👻 Opacidad Fantasma:** Tu código objetivo aparece como un tenue "fantasma" en un tema oscuro. Puedes ajustar el control deslizante de opacidad si quieres jugar en modo extremo y apenas ver la solución.
*   **🛑 Cero Perdón:** Si escribes el carácter equivocado, se vuelve de un rojo furioso y te bloquea para que no puedas avanzar hasta que presiones Retroceso (Backspace) y lo arregles.
*   **🔍 El Revelador de Espacios en Blanco:** Porque mezclar tabulaciones y espacios es un pecado mortal. La aplicación resalta los espacios normales con un fondo gris tenue y las tabulaciones con un fondo azul profundo.
*   **⏭️ Salto de Comentarios Automático:** La app usa magia de expresiones regulares para saltar automáticamente sobre bloques de comentarios (`/* */`, `//`, `#`, `"""`, `<!-- -->`) en C, C++, Python, Bash, Makefiles, Go, HTML y más.
*   **🧠 Ordenamiento Inteligente:** Lógica personalizada para asegurar que practiques tus cabeceras (`.h`/`.hpp`) *antes* que tus archivos de implementación (`.c`/`.cpp`).
*   **🚀 Flujo Continuo:** Al terminar un archivo, una ventana sugiere el siguiente archivo lógico. Presiona `[Enter]` para continuar, o `[S]` para saltar al siguiente, manteniendo siempre el archivo seleccionado en el sidebar.
*   **📊 Seguimiento de Progreso:** Indicadores en tiempo real que muestran tu línea actual, el progreso de caracteres escritos y una barra de porcentaje para que sepas exactamente cuánto te falta.
*   **❌ Registro de Errores:** Al finalizar cada archivo, verás un resumen detallado en rojo con el **número total de errores** cometidos, para que puedas medir tu precisión.
*   **📂 Acceso Rápido:** Al hacer clic en "Open Folder", el selector se abre por defecto directamente en tu **Escritorio (Desktop)** para que empieces a trabajar de inmediato.

## 🛠️ Cómo usarlo

1.  Asegúrate de tener Python 3 instalado en tu sistema.
2.  Ejecuta la aplicación:
    ```bash
    python3 muscle_tutor.py
    ```
3.  Haz clic en **"Open Folder"** y selecciona tu proyecto.
4.  Selecciona un archivo en el árbol de directorios y empieza a escribir.

## ⌨️ Atajos de Teclado

*   **`Enter`**: Inicia el siguiente archivo cuando la ventana de finalización está abierta.
*   **`S`**: Salta el archivo sugerido actualmente y prepara el siguiente.
*   **`Escape`**: Cierra la ventana emergente de finalización.
*   **`Tab`**: Inserta una tabulación real.

## 📝 Últimas Palabras

¡Que tus punteros nunca queden colgando (dangling pointers), que tu memoria nunca tenga fugas (memory leaks) y que tus dedos siempre recuerden la sintaxis! ¡Feliz escritura!
