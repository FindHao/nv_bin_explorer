# coding:utf8
import os
import struct
import com_lib


def arch2mode(arch):
    return arch.replace("_", "").upper()


def dump(newcode, arch):
    """
    @:arg newcode: str. a 128-bit int. So we have to split it to two part
    @:return the content of new cubin
    """
    # version = int(arch.split("_")[1])
    # create a tmp cubin file in working directory
    # @todo check the data directory exist
    tmp_cubin = "%s/data/%s/%s.tmp.cubin" % (com_lib.work_dir, arch, arch)
    f = open(tmp_cubin, 'rb+')
    f.seek(com_lib.kernel_section_offset)
    # for volta and turing
    tmp1 = int(newcode, 16)
    part0 = tmp1 >> 64
    part1 = tmp1 & 0xffffffffffffffff
    f.write(struct.pack('Q', int("0x{:016x}".format(part0), 16)))
    f.write(struct.pack('Q', int("0x{:016x}".format(part1), 16)))
    f.close()
    cmd = com_lib.DISASM_BIN_TO_PTX_CMD_STDOUT % (com_lib.CUDA_TOOLKIT, arch, tmp_cubin)
    # cmd = com_lib.DISASM_BIN_TO_PTX_CMD % (com_lib.CUDA_TOOLKIT, arch, tmp_cubin, "data/%s/%s.sass" % (arch, newcode))
    tmp_read = os.popen(cmd).read()
    return tmp_read
