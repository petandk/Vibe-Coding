# Ultimate Coder Trainer ⌨️🚀

Un entrenador de mecanografía ligero y avanzado construido en Python (Tkinter), diseñado específicamente para programadores y usuarios de teclados mecánicos personalizados (QMK/Vial).

## ✨ Características Principales

* **Generación Dinámica de Código:** No solo practicas palabras, el entrenador inyecta símbolos de programación de forma procedimental (brackets, operadores, sentencias, terminaciones) para que desarrolles memoria muscular real para codificar.
* **Integración Nativa con Vial (`.vil`):** Lee la configuración exacta de tu teclado físico al vuelo. Solo tienes que dejar tu archivo `layout.vil` en la misma carpeta.
* **Asistente Físico Inteligente (F1):** Si te atascas con un símbolo, el modo ayuda no te dice "Pulsa Shift+1", sino que calcula la ruta física exacta en tu teclado basándose en tu archivo Vial (Ej: `💡 ! ➜ [L2] + [SHIFT] + [Q]`).
* **Visor de Capas Integrado:** Renderiza un mapa visual bidimensional simétrico de tus capas de teclado directamente en la aplicación.
* **Auto-Scroll Ergonométrico:** Mantiene la línea activa siempre en una posición de lectura cómoda para los ojos.
* **Modo Abecedario:** Un modo secundario para calentar la memoria muscular básica.

## 🛠️ Requisitos

- Python 3.x
- `tkinter` (Normalmente incluido por defecto en las instalaciones de Python)
- (Opcional pero recomendado) Un archivo `.vil` exportado desde [Vial](https://get.vial.today/) para habilitar las pistas inteligentes.

## 🚀 Instalación y Uso

1. Clona este repositorio o descarga los archivos.
2. Exporta el layout de tu teclado desde la app de Vial y guárdalo en la misma carpeta (ej. `layout.vil`).
3. Ejecuta el entrenador:

```bash
python "Silakka54 trainerV2.pyw"
```

## ⌨️ Controles

- **`F1`**: Activa/Desactiva el Asistente Inteligente de símbolos.
- **`F5`**: Reinicia el texto y la práctica actual.
- **`F11`**: Alterna entre el modo ventana y pantalla completa.

## 📝 Notas sobre el Asistente Inteligente

El sistema de pistas está diseñado para ser poco intrusivo:
- Solo aparece para **símbolos de programación**. Ignorará deliberadamente el alfabeto normal y los espacios para forzarte a aprenderlos.
- Distingue claramente si el salto final de una palabra es un `Espacio` o un `Salto de Línea (↵)`.
- Reacciona en tiempo real, incluso si retrocedes (borras) para corregir un error anterior.

## 🤝 Contribuciones
¡Las *Pull Requests* son bienvenidas! Si tienes ideas para mejorar la precisión del lector de Vial o añadir nuevos modos de juego, siéntete libre de contribuir.
