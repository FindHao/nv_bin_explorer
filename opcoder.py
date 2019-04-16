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
    # for line in tmp_result:
    origin_inst = Inst(tmp_result[0])
    base = origin_inst.enc
    # In volta and turing, len of the instruction code is 128bit
    for i in range(0, 128):
        # i from right to left
        mask = 2 ** i
        newcode = base ^ mask
        dump_file_content = dump("0x{:032x}".format(newcode), arch)
        # print(dump_file_content)
        # Compare the disassemble to check which field changes: opcode, operand or modifer
        if dump_file_content and dump_file_content.find("?") == -1 and dump_file_content.find("error") == -1:
            tmp_result2 = code_line_reg.findall(dump_file_content)
            if not tmp_result2:
                logging.warning("generated file %s has no legal content" % newcode)
            line = tmp_result2[0]
            tmp_inst = Inst(line)
            if tmp_inst.op != origin_inst.op:
                logging.info("Opcode changes: %s => %s when bit [%d] is flipped from [%d]",
                             origin_inst.op, tmp_inst.op, i, (base >> i) & 0x1)


if __name__ == "__main__":
    pass
    work()
