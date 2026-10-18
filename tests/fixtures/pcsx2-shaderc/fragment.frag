#version 450
#ifndef SHADE
#error SHADE must be supplied by the fixture
#endif
layout(location = 0) out vec4 output_color;
void main() {
    output_color = vec4(SHADE, 0.25, 0.5, 1.0);
}
