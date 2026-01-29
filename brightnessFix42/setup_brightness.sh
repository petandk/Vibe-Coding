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
echo "Para que estos cambios persistan después de reiniciar, añade este script a 'Startup Applications' o 'Aplicaciones al inicio'."
echo "Puedes hacerlo buscando 'Startup Applications' en tu menú de aplicaciones, y añadiendo una nueva entrada con el comando:"
echo "bash $HOME/Desktop/brightnessFix/setup_brightness.sh"
