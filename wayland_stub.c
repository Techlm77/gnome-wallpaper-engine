#include <stdlib.h>
#include <wayland-client.h>

int main(int argc, char **argv) {
    if (!getenv("WAYLAND_DISPLAY"))
        return 1;
    return 0;
}
