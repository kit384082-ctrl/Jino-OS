; Jino OS Bootloader v0.3
; 16-bit Real Mode -> 32-bit Protected Mode
; Собирается: nasm -f bin boot.asm -o boot.bin

[org 0x7c00]
[bits 16]

start:
    cli
    xor ax, ax
    mov ds, ax
    mov es, ax
    mov ss, ax
    mov sp, 0x7c00

    ; Приветствие
    mov si, msg_boot
    call print16

    ; Включить A20
    call enable_a20

    ; Загрузить ядро с диска (сектора 2-64, 32KB)
    mov ah, 0x02
    mov al, 64          ; кол-во секторов
    mov ch, 0           ; цилиндр
    mov cl, 2           ; сектор (1 - бут)
    mov dh, 0           ; головка
    mov dl, 0x80        ; диск
    mov bx, 0x1000
    mov es, bx
    xor bx, bx          ; ES:BX = 0x1000:0 = 0x10000
    int 0x13
    jc disk_error

    ; Загрузить GDT
    lgdt [gdt_descriptor]

    ; Перейти в protected mode
    mov eax, cr0
    or eax, 1
    mov cr0, eax

    jmp CODE_SEG:protected_mode

[bits 32]
protected_mode:
    mov ax, DATA_SEG
    mov ds, ax
    mov ss, ax
    mov es, ax
    mov fs, ax
    mov gs, ax
    mov ebp, 0x90000
    mov esp, ebp

    ; Очистить экран, вывести что мы в PM
    mov byte [0xB8000], 'J'
    mov byte [0xB8001], 0x0A

    ; Прыжок в ядро (загружено по 0x10000, копируем в 0x100000)
    mov esi, 0x10000
    mov edi, 0x100000
    mov ecx, 16384       ; 64KB /4
    rep movsd

    jmp CODE_SEG:0x100000
    hlt

disk_error:
    mov si, msg_disk_err
    call print16
    hlt

; --- 16-bit functions ---
[bits 16]
print16:
    lodsb
    or al, al
    jz .done
    mov ah, 0x0E
    int 0x10
    jmp print16
.done: ret

enable_a20:
    in al, 0x92
    or al, 2
    out 0x92, al
    ret

; GDT
gdt_start:
    dq 0
gdt_code:
    dw 0xFFFF
    dw 0
    db 0
    db 10011010b
    db 11001111b
    db 0
gdt_data:
    dw 0xFFFF
    dw 0
    db 0
    db 10010010b
    db 11001111b
    db 0
gdt_end:

gdt_descriptor:
    dw gdt_end - gdt_start - 1
    dd gdt_start

CODE_SEG equ gdt_code - gdt_start
DATA_SEG equ gdt_data - gdt_start

msg_boot db 'Jino OS Bootloader 0.3 Loading...',13,10,0
msg_disk_err db 'Disk error!',0

times 510-($-$$) db 0
dw 0xAA55
