#include <stdlib.h>
#include <wayland-client.h>
#include "wayland_support.h"

struct wl_display* init_wayland_display(void) {
    struct wl_display *display = wl_display_connect(NULL);
    if (!display)
        return NULL;
    return display;
}

void cleanup_wayland_display(struct wl_display* display) {
    if (display)
        wl_display_disconnect(display);
}
