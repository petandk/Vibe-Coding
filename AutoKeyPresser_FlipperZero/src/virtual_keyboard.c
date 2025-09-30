#include <furi.h>
#include <furi_hal.h>
#include <furi_hal_usb_hid.h>
#include <gui/gui.h>
#include <gui/view_port.h>
#include <gui/canvas.h>
#include <input/input.h>

#define TAG "KeySpammer"

// Frequency options (in milliseconds)
#define FREQ_FAST_MS 20
#define FREQ_MEDIUM_MS 100
#define FREQ_SLOW_MS 500

// Keyboard layout - 4 rows x 10 columns
static const char keyboard[4][10] = {
    {'1', '2', '3', '4', '5', '6', '7', '8', '9', '0'},
    {'q', 'w', 'e', 'r', 't', 'y', 'u', 'i', 'o', 'p'},
    {'a', 's', 'd', 'f', 'g', 'h', 'j', 'k', 'l', ';'},
    {'z', 'x', 'c', 'v', 'b', 'n', 'm', ',', '.', ' '}};

// HID keyboard constants
#define HID_KEYBOARD_A 0x04
#define HID_KEYBOARD_1 0x1E
#define HID_KEYBOARD_0 0x27
#define HID_KEYBOARD_SPACEBAR 0x2C
#define HID_KEYBOARD_SEMICOLON 0x33
#define HID_KEYBOARD_COMMA 0x36
#define HID_KEYBOARD_DOT 0x37

typedef enum
{
    STATE_SELECT_CHAR,
    STATE_SELECT_FREQUENCY,
    STATE_SPAMMING
} AppState;

typedef struct
{
    uint8_t row;
    uint8_t col;
    bool running;
    AppState state;
    char selected_char;
    uint8_t frequency_option; // 0=fast, 1=medium, 2=slow
    FuriTimer *spam_timer;
} KeySpammer;

// Get frequency delay in milliseconds based on option
static uint32_t get_frequency_delay(uint8_t option)
{
    const uint32_t delays[] = {FREQ_FAST_MS, FREQ_MEDIUM_MS, FREQ_SLOW_MS};
    return (option < 3) ? delays[option] : FREQ_MEDIUM_MS;
}

// Get frequency name string
static const char *get_frequency_name(uint8_t option)
{
    const char *names[] = {"20ms", "100ms", "500ms"};
    return (option < 3) ? names[option] : "100ms";
}

// Convert character to HID keycode
static uint8_t char_to_hid(char c)
{
    if (c >= 'a' && c <= 'z')
        return HID_KEYBOARD_A + (c - 'a');
    if (c >= '1' && c <= '9')
        return HID_KEYBOARD_1 + (c - '1');
    if (c == '0')
        return HID_KEYBOARD_0;
    if (c == ' ')
        return HID_KEYBOARD_SPACEBAR;
    if (c == ';')
        return HID_KEYBOARD_SEMICOLON;
    if (c == ',')
        return HID_KEYBOARD_COMMA;
    if (c == '.')
        return HID_KEYBOARD_DOT;
    return HID_KEYBOARD_A; // Default fallback
}

// Send key via USB HID with minimal delay for fast spamming
static void send_key(char c)
{
    // Now use the actual character to get the correct HID code
    uint8_t hid_code = char_to_hid(c);

    // Send the correct key with minimal delays
    furi_hal_hid_kb_press(hid_code);
    furi_delay_ms(10); // Reduced from 50ms to 10ms
    furi_hal_hid_kb_release(hid_code);
    // No additional delay after release - let the timer control the frequency
}

// Timer callback for spamming keys
static void spam_timer_callback(void *context)
{
    KeySpammer *app = context;
    if (app->state == STATE_SPAMMING && app->running)
    {
        send_key(app->selected_char);
    }
}

// Draw the interface based on current state
static void draw_callback(Canvas *canvas, void *context)
{
    KeySpammer *app = context;

    canvas_clear(canvas);
    canvas_set_font(canvas, FontPrimary);

    if (app->state == STATE_SELECT_CHAR)
    {
        // Draw keyboard (no label to save space and move keyboard up)
        for (int r = 0; r < 4; r++)
        {
            for (int c = 0; c < 10; c++)
            {
                int x = 3 + c * 12;
                int y = 5 + r * 15; // Moved up from y = 15 to y = 5

                // Highlight selected key
                if (r == app->row && c == app->col)
                {
                    canvas_draw_box(canvas, x, y, 11, 11);
                    canvas_set_color(canvas, ColorWhite);
                }
                else
                {
                    canvas_draw_frame(canvas, x, y, 11, 11);
                }

                // Draw character
                char str[2] = {keyboard[r][c], 0};
                if (keyboard[r][c] == ' ')
                {
                    canvas_draw_str(canvas, x + 4, y + 9, "_");
                }
                else
                {
                    canvas_draw_str(canvas, x + 4, y + 9, str);
                }
                canvas_set_color(canvas, ColorBlack);
            }
        }
    }
    else if (app->state == STATE_SELECT_FREQUENCY)
    {
        // Draw frequency selection screen
        canvas_draw_str(canvas, 2, 10, "Select spam frequency:");

        char selected_char_str[20];
        snprintf(selected_char_str, sizeof(selected_char_str), "Character: %c",
                 app->selected_char == ' ' ? '_' : app->selected_char);
        canvas_draw_str(canvas, 2, 25, selected_char_str);

        // Draw frequency options
        const char *freq_labels[] = {"20ms (Fast)", "100ms (Medium)", "500ms (Slow)"};
        for (int i = 0; i < 3; i++)
        {
            int y = 40 + i * 15;
            if (i == app->frequency_option)
            {
                canvas_draw_box(canvas, 2, y - 10, 124, 12);
                canvas_set_color(canvas, ColorWhite);
            }
            canvas_draw_str(canvas, 5, y, freq_labels[i]);
            canvas_set_color(canvas, ColorBlack);
        }
    }
    else if (app->state == STATE_SPAMMING)
    {
        // Draw spamming status screen
        canvas_draw_str(canvas, 2, 10, "SPAMMING ACTIVE");

        char char_info[30];
        snprintf(char_info, sizeof(char_info), "Character: %c",
                 app->selected_char == ' ' ? '_' : app->selected_char);
        canvas_draw_str(canvas, 2, 25, char_info);

        char freq_info[30];
        snprintf(freq_info, sizeof(freq_info), "Frequency: %s", get_frequency_name(app->frequency_option));
        canvas_draw_str(canvas, 2, 40, freq_info);

        canvas_draw_str(canvas, 2, 55, "Press OK to stop");
    }
}

// Handle input based on current state
static void input_callback(InputEvent *event, void *context)
{
    KeySpammer *app = context;

    if (event->type != InputTypeShort)
        return;

    if (app->state == STATE_SELECT_CHAR)
    {
        // Character selection navigation
        switch (event->key)
        {
        case InputKeyUp:
            if (app->row > 0)
                app->row--;
            break;
        case InputKeyDown:
            if (app->row < 3)
                app->row++;
            break;
        case InputKeyLeft:
            if (app->col > 0)
                app->col--;
            break;
        case InputKeyRight:
            if (app->col < 9)
                app->col++;
            break;
        case InputKeyOk:
            // Select character and move to frequency selection
            app->selected_char = keyboard[app->row][app->col];
            app->state = STATE_SELECT_FREQUENCY;
            app->frequency_option = 0; // Default to 100ms
            break;
        case InputKeyBack:
            app->running = false;
            break;
        default:
            break;
        }
    }
    else if (app->state == STATE_SELECT_FREQUENCY)
    {
        // Frequency selection navigation
        switch (event->key)
        {
        case InputKeyUp:
            if (app->frequency_option > 0)
                app->frequency_option--;
            break;
        case InputKeyDown:
            if (app->frequency_option < 2)
                app->frequency_option++;
            break;
        case InputKeyOk:
            // Start spamming with selected frequency
            app->state = STATE_SPAMMING;
            uint32_t delay = get_frequency_delay(app->frequency_option);
            furi_timer_start(app->spam_timer, furi_ms_to_ticks(delay));
            break;
        case InputKeyBack:
            // Go back to character selection
            app->state = STATE_SELECT_CHAR;
            break;
        default:
            break;
        }
    }
    else if (app->state == STATE_SPAMMING)
    {
        // Spamming mode - only OK stops it
        switch (event->key)
        {
        case InputKeyOk:
        case InputKeyBack:
            // Stop spamming and go back to character selection
            furi_timer_stop(app->spam_timer);
            app->state = STATE_SELECT_CHAR;
            break;
        default:
            break;
        }
    }
}

// Main app entry point
int32_t virtual_keyboard_app(void *p)
{
    UNUSED(p);

    // Initialize USB HID mode
    furi_hal_usb_unlock();
    furi_hal_usb_set_config(&usb_hid, NULL);
    furi_delay_ms(200);

    // Allocate and initialize app
    KeySpammer *app = malloc(sizeof(KeySpammer));
    app->row = 1; // Start at 'q' row
    app->col = 0; // Start at first column
    app->running = true;
    app->state = STATE_SELECT_CHAR;
    app->selected_char = 'q';  // Default to 'q' (matches starting position)
    app->frequency_option = 1; // Default to medium speed

    // Create spam timer
    app->spam_timer = furi_timer_alloc(spam_timer_callback, FuriTimerTypePeriodic, app);

    // Create view port
    ViewPort *view_port = view_port_alloc();
    view_port_draw_callback_set(view_port, draw_callback, app);
    view_port_input_callback_set(view_port, input_callback, app);
    view_port_enabled_set(view_port, true);

    // Setup GUI
    Gui *gui = furi_record_open(RECORD_GUI);
    gui_add_view_port(gui, view_port, GuiLayerFullscreen);

    // Main loop
    while (app->running)
    {
        view_port_update(view_port);
        furi_delay_ms(100);
    }

    // Cleanup
    furi_timer_stop(app->spam_timer);
    furi_timer_free(app->spam_timer);
    gui_remove_view_port(gui, view_port);
    view_port_free(view_port);
    furi_record_close(RECORD_GUI);
    free(app);

    // Restore original USB mode
    furi_hal_usb_unlock();
    furi_hal_usb_set_config(&usb_cdc_single, NULL);

    return 0;
}