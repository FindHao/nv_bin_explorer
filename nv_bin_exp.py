#!/bin/python3
import collections

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
ops_bits = {}
ops_operand = collections.defaultdict(list)
# This list records instructions including modifers and oprands
instructions = []
# the flag of checking operands' encode
FLAG_CHECK_OPERAND = True


def check_operand_types(inst):
    """
    Get every operand's type
    :param inst: The current inst to be analysed
    :return: str, a string like RRR that means 3 operands are Register type
    :return: 'X',
    """
    operand_types = ""
    for operand in inst.operands:
        key = operand[0]
        if key == 'R':  # Register
            value = operand[1:]
            if value == 'Z' or value == 'N' or value == 'M' or \
                    value == 'P' or float(value).is_integer():
                operand_types += 'R'
            else:
                return None
        elif key == 'P':  # Predicate
            value = operand[1:]
            if float(value).is_integer():
                operand_types += 'P'
            else:
                return None
        elif key == 'c':  # Constant memory
            operand_types += 'C'
        elif key == '[':  # Memory
            operand_types += 'M'
        elif key == 'S':  # Special register
            operand_types += 'S'
        else:
            if len(operand) >= 2 and (operand[0:2] == "0x" or operand[0:3] == "-0x"):  # Hex immediate
                operand_types += 'I'
            elif float(operand).is_integer():  # Immediate value
                operand_types += 'I'
            else:
                return None
    if operand_types not in ops_operand.get(inst.op, []):
        ops_operand[inst.op].append(operand_types)
        return operand_types
    else:
        return None


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
    @:return: It currently presents the judgment of operands' different
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
                     origin_inst.modifier, tmp_inst.modifier, reversal_bit_id, (base >> reversal_bit_id) & 0x1,
                     tmp_line[0])
        origin_inst.modifier_positions.append(reversal_bit_id)
    else:
        len_origin = len(origin_inst.operands)
        len_tmp = len(tmp_inst.operands)

        for i in range(min(len_origin, len_tmp)):
            if origin_inst.operands[i] != tmp_inst.operands[i]:
                return i, tmp_inst
        # if len_tmp > len_origin:
        #     return len_origin
    return None, None


def work(input_file_name, output_file, section_start):
    global sass_content, ops_bits

    arch = "sm_75"
    # for debug
    # input_file_name = 'gaussian.cubin'
    init_sass_cubin_files(input_file_name, arch)
    logging.basicConfig(format="%(message)s", filename="./log/%s" % output_file, filemode="a",
                        level=logging.INFO)
    logging.info("Time:\t%s" % time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))

    com_lib.kernel_section_start_offset = int(section_start, 16)

    with open("%s.sass" % os.path.splitext(input_file_name)[0], 'r')as fin:
        sass_content = fin.read()
    tmp_result = code_line_reg.findall(sass_content)
    if not tmp_result:
        logging.error("Not found pairs")
        return
    # @todo: check is there any irregular code
    # how many lines will be checked.
    for j, line in enumerate(tmp_result[:1]):
        logging.info("================================")
        logging.info("raw line:\t\t%s" % line[0])
        a_origin_inst = Inst(line)
        instructions.append(a_origin_inst)

        base = a_origin_inst.enc
        bits = 0x0
        origin_operand_types = check_operand_types(a_origin_inst)
        if FLAG_CHECK_OPERAND:
            if len(a_origin_inst.operands) and origin_operand_types:
                logging.info("Original op and modifier:%s:\t%s" % (a_origin_inst.op, "".join(a_origin_inst.modifier)))
                logging.info("0b{:0128b}".format(base) + ": " + "".join(a_origin_inst.operands))
                logging.info("newcode operand:")
            # if you just want to check operand, uncomment the following else branch
            else:
                continue
        # In volta and turing, len of the instruction code is 128bitk
        for i in range(0, 128):
            # i from right to left
            mask = 2 ** i
            newcode = base ^ mask
            dump_file_content = dump("0x{:032x}".format(newcode), arch, j)

            # print(dump_file_content)
            # Compare the disassemble to check which field changes: opcode, operand or modifer
            if dump_file_content and dump_file_content.find("?") == -1 and dump_file_content.find("error") == -1:
                tmp_pp, tmp_inst = filter_change(a_origin_inst, dump_file_content, base, newcode, j, i)
                if tmp_pp is not None:
                    # the ith bit affects tmp_ppth operand
                    a_origin_inst.operand_positions[tmp_pp].append(i)
                    # @todo print the reverse bit
                    logging.info("%s: %d\t%s" % ("0b{:0128b}".format(newcode), i, " ".join(tmp_inst.operands)))
            # if len(positions) > 0:
            #     logging.info("0b{:0128b}".format(bits) + ": %s opcode bits %s: ", origin_inst.op, positions)

        if len(a_origin_inst.opcode_positions) > 0:
            ops_bits[a_origin_inst.op] = list(set(ops_bits.get(a_origin_inst.op, []) + a_origin_inst.opcode_positions))
        logging.info("Operand combination types: %s", origin_operand_types)
        for i in range(0, len(a_origin_inst.operand_positions)):
            if len(origin_operand_types) > i:
                tmp_type = origin_operand_types[i]
            else:
                tmp_type = 'None'
            logging.info("Operand type: %s", tmp_type)
            logging.info("Encoding: %s", a_origin_inst.operand_positions[i])

    for node in ops_bits:
        logging.info("%s:\t[%s]", node, ",".join(str(x) for x in ops_bits[node]))


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
