#!/bin/python3
"""This file is used to """
import logging
import os
import re
from dumper import dump
from inst import Inst
import com_lib

sass_content = ''
code_line_reg = re.compile(r'/\*.{4}\*/ +(.+?); +?/\* 0x(.+) \*/\n.+?/\* 0x(.{16}) \*/')
# example:['MOV': [1,2,3,4,5], 'ADD': [1,2,3,4,5,6,7,8]]
# record opcode and the bit position
ops = {}


def init_sass_cubin_files(input_file, arch):
    """
    disasm input cubin file to sass and copy it to data/$arch/
    @:arg input_file: input cubin file
    """
    cmd = com_lib.DISASM_BIN_TO_PTX_CMD % (
        com_lib.CUDA_TOOLKIT, arch, input_file, "%s.sass" % os.path.splitext(input_file)[0])
    tmp_read = os.popen(cmd).read()
    if tmp_read:
        logging.error("Error: when disasm input cubin file:\t%s" % tmp_read)
    cmd = "cp %s data/%s/%s.tmp.cubin" % (input_file, arch, arch)
    tmp_read = os.popen(cmd).read()
    if tmp_read:
        logging.error("Error: when copy input cubin file:\t%s" % tmp_read)


def work():
    global sass_content, ops

    arch = "sm_75"
    # init_sass_cubin_files('test.cubin', arch)
    logging.basicConfig(level=logging.INFO)
    with open("test.sass", 'r')as fin:
        sass_content = fin.read()

    tmp_result = code_line_reg.findall(sass_content)
    if not tmp_result:
        logging.error("Not found pairs")
        return
    # @todo: check is there any irregular code
    for j, line in enumerate(tmp_result):
        logging.info("\nraw line:\t\t%s" % line[0])
        origin_inst = Inst(line)
        base = origin_inst.enc
        bits = 0x0
        positions = []
        # In volta and turing, len of the instruction code is 128bit
        for i in range(0, 128):
            # i from right to left
            mask = 2 ** i
            newcode = base ^ mask
            dump_file_content = dump("0x{:032x}".format(newcode), arch, j)
            # print(dump_file_content)
            # Compare the disassemble to check which field changes: opcode, operand or modifer
            if dump_file_content and dump_file_content.find("?") == -1 and dump_file_content.find("error") == -1:
                tmp_result2 = code_line_reg.findall(dump_file_content)
                if not tmp_result2:
                    logging.warning("generated file %s has no legal content" % newcode)
                tmp_line = tmp_result2[j]
                tmp_inst = Inst(tmp_line)
                if tmp_inst.op != origin_inst.op:
                    logging.info("Opcode changes: %s => %s when bit [%d] is flipped from [%d]\t\tChange to:%s",
                                 origin_inst.op, tmp_inst.op, i, (base >> i) & 0x1, tmp_line[0])
                    bits = bits | (((base >> i) & 0x1) << i)
                    positions.append(i)
        # if len(positions) > 0:
        #     logging.info("0b{:0128b}".format(bits) + ": %s opcode bits %s: ", origin_inst.op, positions)
        if len(positions) > 0:
            ops[origin_inst.op] = list(set(ops.get(origin_inst.op, []) + positions))
    for node in ops:
        logging.info("%s:\t[%s]", node, ",".join(str(x) for x in ops[node]))


if __name__ == "__main__":
    pass
    work()
