#!/bin/python3
"""This file is used to """
import logging
import os
import sys

import com_lib
import re
from dumper import dump
from inst import Inst

sass_content = ''
code_line_reg = re.compile(r'/\*.{4}\*/ +(.+?); +?/\* 0x(.+) \*/\n.+?/\* 0x(.{16}) \*/')


def work():
    logging.basicConfig(level=logging.INFO)
    global sass_content
    with open("test.sass", 'r')as fin:
        sass_content = fin.read()

    arch = "sm_75"
    tmp_result = code_line_reg.findall(sass_content)
    if not tmp_result:
        logging.error("Not found pairs")
        return
    # @todo: check is there any irregular code
    for j, line in enumerate(tmp_result[:6]):
        logging.info("\n%s" % line[0])
        origin_inst = Inst(line)
        base = origin_inst.enc
        # In volta and turing, len of the instruction code is 128bit
        for i in range(0, 128):
            # i from right to left
            mask = 2 ** i
            bits = 0x0
            pos = []
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
                    pos.append(i)
            # if len(pos) > 0:
            # logging.info("0b{:0128b}".format(bits) + ": %s opcode bits %s: ", origin_inst.op, pos)


if __name__ == "__main__":
    pass
    work()
