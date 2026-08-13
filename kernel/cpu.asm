; =====================================================================
;  Jino-OS  ::  cpu.asm — CPUID based processor identification
; =====================================================================

                bits    32
%include "kernel.inc"

                global  cpu_detect
                global  cpu_print_info
                global  cpu_vendor
                global  cpu_brand
                global  cpu_features_edx
                global  cpu_features_ecx
                global  cpu_family
                global  cpu_model
                global  cpu_stepping
                global  cpu_max_leaf
                global  cpu_has_feature
                global  cpu_halt
                global  cpu_read_cr0
                global  cpu_read_cr2
                global  cpu_read_cr3
                global  cpu_read_cr4
                global  cpu_read_eflags

                extern  kprintf
                extern  memset

; a few of the EDX feature bits from leaf 1
FEAT_FPU        equ     1 << 0
FEAT_PSE        equ     1 << 3
FEAT_TSC        equ     1 << 4
FEAT_MSR        equ     1 << 5
FEAT_PAE        equ     1 << 6
FEAT_APIC       equ     1 << 9
FEAT_MTRR       equ     1 << 12
FEAT_PGE        equ     1 << 13
FEAT_CMOV       equ     1 << 15
FEAT_MMX        equ     1 << 23
FEAT_FXSR       equ     1 << 24
FEAT_SSE        equ     1 << 25
FEAT_SSE2       equ     1 << 26

                section .text

; ---------------------------------------------------------------------
; cpu_detect — fill in the exported description fields.
; ---------------------------------------------------------------------
cpu_detect:
                push    ebp
                mov     ebp, esp
                push    ebx
                push    esi
                push    edi

                ; ---- leaf 0: vendor string and the highest leaf ------
                xor     eax, eax
                cpuid
                mov     [cpu_max_leaf], eax
                mov     [cpu_vendor + 0], ebx
                mov     [cpu_vendor + 4], edx
                mov     [cpu_vendor + 8], ecx
                mov     byte [cpu_vendor + 12], 0

                ; ---- leaf 1: signature and feature flags -------------
                cmp     dword [cpu_max_leaf], 1
                jb      .no_features

                mov     eax, 1
                cpuid
                mov     [cpu_signature], eax
                mov     [cpu_features_edx], edx
                mov     [cpu_features_ecx], ecx

                ; stepping = bits 3:0
                mov     ebx, eax
                and     ebx, 0x0F
                mov     [cpu_stepping], ebx

                ; model = bits 7:4, extended by bits 19:16
                mov     ebx, eax
                shr     ebx, 4
                and     ebx, 0x0F
                mov     ecx, eax
                shr     ecx, 16
                and     ecx, 0x0F
                shl     ecx, 4
                or      ebx, ecx
                mov     [cpu_model], ebx

                ; family = bits 11:8 plus the extended field
                mov     ebx, eax
                shr     ebx, 8
                and     ebx, 0x0F
                cmp     ebx, 0x0F
                jne     .family_done
                mov     ecx, eax
                shr     ecx, 20
                and     ecx, 0xFF
                add     ebx, ecx
.family_done:
                mov     [cpu_family], ebx

.no_features:
                ; ---- extended leaves: the marketing brand string -----
                mov     eax, 0x80000000
                cpuid
                mov     [ext_max_leaf], eax
                cmp     eax, 0x80000004
                jb      .no_brand

                mov     edi, cpu_brand
                mov     esi, 0x80000002
.brand_loop:
                mov     eax, esi
                cpuid
                mov     [edi + 0], eax
                mov     [edi + 4], ebx
                mov     [edi + 8], ecx
                mov     [edi + 12], edx
                add     edi, 16
                inc     esi
                cmp     esi, 0x80000005
                jb      .brand_loop
                mov     byte [cpu_brand + 48], 0
                jmp     .done

.no_brand:
                mov     byte [cpu_brand], 0
.done:
                pop     edi
                pop     esi
                pop     ebx
                pop     ebp
                ret

; ---------------------------------------------------------------------
; cpu_has_feature(edx_bitmask) -> EAX = 0 or 1
; ---------------------------------------------------------------------
cpu_has_feature:
                push    ebp
                mov     ebp, esp
                mov     eax, [cpu_features_edx]
                and     eax, [ebp + 8]
                jz      .no
                mov     eax, 1
.no:
                pop     ebp
                ret

; ---------------------------------------------------------------------
; cpu_print_info — a human readable summary
; ---------------------------------------------------------------------
cpu_print_info:
                push    ebp
                mov     ebp, esp
                push    ebx

                push    dword cpu_vendor
                push    dword fmt_vendor
                call    kprintf
                add     esp, 8

                cmp     byte [cpu_brand], 0
                je      .no_brand
                push    dword cpu_brand
                push    dword fmt_brand
                call    kprintf
                add     esp, 8
.no_brand:
                push    dword [cpu_stepping]
                push    dword [cpu_model]
                push    dword [cpu_family]
                push    dword fmt_signature
                call    kprintf
                add     esp, 16

                ; ---- print the feature names we care about -----------
                push    dword fmt_features
                call    kprintf
                add     esp, 4

                mov     ebx, 0
.feature_loop:
                cmp     ebx, FEATURE_COUNT
                jae     .features_done

                mov     eax, [feature_bits + ebx * 4]
                test    [cpu_features_edx], eax
                jz      .next_feature

                push    ebx
                push    dword [feature_names + ebx * 4]
                push    dword fmt_feature_name
                call    kprintf
                add     esp, 8
                pop     ebx
.next_feature:
                inc     ebx
                jmp     .feature_loop

.features_done:
                push    dword fmt_nl
                call    kprintf
                add     esp, 4

                pop     ebx
                pop     ebp
                ret

; ---------------------------------------------------------------------
;  Small accessors for the control registers
; ---------------------------------------------------------------------
cpu_read_cr0:
                mov     eax, cr0
                ret
cpu_read_cr2:
                mov     eax, cr2
                ret
cpu_read_cr3:
                mov     eax, cr3
                ret
cpu_read_cr4:
                mov     eax, cr4
                ret
cpu_read_eflags:
                pushfd
                pop     eax
                ret

cpu_halt:
                cli
.forever:
                hlt
                jmp     .forever

; ---------------------------------------------------------------------
                section .rodata
fmt_vendor:     db      "cpu: vendor %s", 10, 0
fmt_brand:      db      "cpu: %s", 10, 0
fmt_signature:  db      "cpu: family %u, model %u, stepping %u", 10, 0
fmt_features:   db      "cpu: features", 0
fmt_feature_name: db    " %s", 0
fmt_nl:         db      10, 0

f_fpu:          db      "fpu", 0
f_tsc:          db      "tsc", 0
f_msr:          db      "msr", 0
f_pae:          db      "pae", 0
f_apic:         db      "apic", 0
f_pge:          db      "pge", 0
f_cmov:         db      "cmov", 0
f_mmx:          db      "mmx", 0
f_fxsr:         db      "fxsr", 0
f_sse:          db      "sse", 0
f_sse2:         db      "sse2", 0
f_pse:          db      "pse", 0

FEATURE_COUNT   equ     12

                align   4
feature_bits:   dd      FEAT_FPU, FEAT_TSC, FEAT_MSR, FEAT_PAE
                dd      FEAT_APIC, FEAT_PGE, FEAT_CMOV, FEAT_MMX
                dd      FEAT_FXSR, FEAT_SSE, FEAT_SSE2, FEAT_PSE

                align   4
feature_names:  dd      f_fpu, f_tsc, f_msr, f_pae
                dd      f_apic, f_pge, f_cmov, f_mmx
                dd      f_fxsr, f_sse, f_sse2, f_pse

; ---------------------------------------------------------------------
                section .bss
                alignb  4
cpu_vendor:         resb 16
cpu_brand:          resb 52
cpu_signature:      resd 1
cpu_features_edx:   resd 1
cpu_features_ecx:   resd 1
cpu_family:         resd 1
cpu_model:          resd 1
cpu_stepping:       resd 1
cpu_max_leaf:       resd 1
ext_max_leaf:       resd 1
