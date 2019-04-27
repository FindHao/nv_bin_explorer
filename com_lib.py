#!/bin/python3
# CUDA toolkit path
CUDA_TOOLKIT = "/usr/local/cuda-10.0/"
# the cmd used to compile ptx to binary
# args: cuda_toolkit, arch code, input file, output file
COMPILE_TO_BIN_CMD = "%s/bin/ptxas -arch %s -m 64 %s -o %s > /dev/null 2>&1"
# the cmd used to disasm binary to ptx
# args: cuda_toolkit, arch, input file, output file
DISASM_BIN_TO_PTX_CMD = "%s/bin/cuobjdump --gpu-architecture %s --dump-sass %s > %s"
DISASM_BIN_TO_PTX_CMD_STDOUT = "%s/bin/cuobjdump --gpu-architecture %s --dump-sass %s 2>&1"
# current working dir
work_dir = "./"

# where the kernel section start. You can get it from readelf
kernel_section_start_offset = 0x1300
