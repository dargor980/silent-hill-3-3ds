; Own Mach-O/x86_64 assembly fixture; no emulator or original game data.
bits 64
default rel
section .text
global _synthetic_nasm_value
_synthetic_nasm_value:
    lea eax, [rdi + rdi * 2]
    xor eax, 0x5a
    ret
