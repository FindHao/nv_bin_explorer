#!/bin/python3
"""This file is used to """
import logging
import os
import re
import time

from dumper import dump
from inst import Inst
import com_lib
import argparse

sass_content = ''
code_line_reg = re.compile(r'/\*.{4}\*/ +(.+?); +?/\* 0x(.+) \*/\n.+?/\* 0x(.{16}) \*/')
# example:['MOV': [1,2,3,4,5], 'ADD': [1,2,3,4,5,6,7,8]]
# record opcode and mapped bit position
ops = {}
# This list records instructions including modifers and oprands
instructions = []


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


def filter_change(origin_inst, dump_file_content, base, newcode, line_index, reversal_bit_id):
    """Compare the origin inst and redisassember inst, and record the changed part
    """
    tmp_result2 = code_line_reg.findall(dump_file_content)
    if not tmp_result2:
        logging.warning("generated file %s has no legal content" % newcode)
    tmp_line = tmp_result2[line_index]
    tmp_inst = Inst(tmp_line)
    # confirm opcode part
    if tmp_inst.op != origin_inst.op:
        logging.info("Opcode changes: %s => %s when bit [%d] is flipped from [%d]\t\tChange to:%s",
                     origin_inst.op, tmp_inst.op, reversal_bit_id, (base >> reversal_bit_id) & 0x1, tmp_line[0])

        # bits = bits | (((base >> i) & 0x1) << i)
        origin_inst.opcode_positions.append(reversal_bit_id)
    # confirm modifier part
    elif tmp_inst.modifier != origin_inst.modifier:
        logging.info("Modifier changes: %s => %s when bit [%d] is flipped from [%d]\t\tChange to:%s",
                     origin_inst.modifier, tmp_inst.modifier, reversal_bit_id, (base >> reversal_bit_id) & 0x1, tmp_line[0])
        origin_inst.modifier_positions.append(reversal_bit_id)


def work(input_file_name, output_file, section_start):
    global sass_content, ops

    arch = "sm_75"
    # for debug
    # input_file_name = 'gaussian.cubin'
    init_sass_cubin_files(input_file_name, arch)
    logging.basicConfig(filename="./log/%s" % output_file, filemode="a", level=logging.INFO)
    logging.info("Time:\t%s" % time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))

    com_lib.kernel_section_start_offset = int(section_start, 16)

    with open("%s.sass" % os.path.splitext(input_file_name)[0], 'r')as fin:
        sass_content = fin.read()
    tmp_result = code_line_reg.findall(sass_content)
    if not tmp_result:
        logging.error("Not found pairs")
        return
    # @todo: check is there any irregular code
    for j, line in enumerate(tmp_result[:2800]):
        logging.info("\nraw line:\t\t%s" % line[0])
        a_origin_inst = Inst(line)
        instructions.append(a_origin_inst)

        base = a_origin_inst.enc
        bits = 0x0
        # In volta and turing, len of the instruction code is 128bitk
        for i in range(0, 128):
            # i from right to left
            mask = 2 ** i
            newcode = base ^ mask
            dump_file_content = dump("0x{:032x}".format(newcode), arch, j)
            # print(dump_file_content)
            # Compare the disassemble to check which field changes: opcode, operand or modifer
            if dump_file_content and dump_file_content.find("?") == -1 and dump_file_content.find("error") == -1:
                filter_change(a_origin_inst, dump_file_content, base, newcode, j, i)
            # if len(positions) > 0:
            #     logging.info("0b{:0128b}".format(bits) + ": %s opcode bits %s: ", origin_inst.op, positions)

        if len(a_origin_inst.opcode_positions) > 0:
            ops[a_origin_inst.op] = list(set(ops.get(a_origin_inst.op, []) + a_origin_inst.opcode_positions))

    for node in ops:
        logging.info("%s:\t[%s]", node, ",".join(str(x) for x in ops[node]))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='NVIDIA CUDA binary decoding for CC 7.0+ ')
    parser.add_argument('-i', '--input', metavar='Input cubin file', required=True, dest='input_file_name',
                        action='store')
    # the script will not write to log file unless you define the output log file path
    parser.add_argument('-o', '--output', metavar='decoding result', required=True, dest='output_path',
                        action='store')
    parser.add_argument('--section-start', metavar='Hex foramt. You can get it from readelf', required=True,
                        dest='section_start',
                        action='store')
    args = parser.parse_args()
    work(args.input_file_name, args.output_path, args.section_start)
