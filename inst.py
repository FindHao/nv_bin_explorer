class Inst:
    """
    It is used to filter different part from a line in SASS file.
    """

    def __init__(self, inst, raw=True):
        """
        Fetech binary encoding.
        :param inst: list.
        [0]: raw instructions. str
        [1]: hex part 1. str
        [2]: hex part 2. str
        :param raw: bool. True: the inst from cuobjdump; False: the inst from nvdisasm
        """
        if raw is True:  # From cuobjdump
            """
            hex. In Volta and Turing, it's a 128-bit integer. The executable uses little-endian format for instructions,
            but CUDA’s disassembler instead displays the hexadecimal values of each instruction starting with the most 
            significant byte.
            @:type int
            """
            self.enc = int(inst[1], 16) << 64 | int(inst[2], 16)
        else:  # From nvdisasm
            self.enc = None
        # which bits mapped opcode's change
        self.opcode_positions = []
        self.modifier_positions = []
        self.operand_positions = []
        # raw instruction line split
        tmp = inst[0].strip().split()
        if inst[0] == '{':  # Check dual issue
            self.pred = ""
            tmp.pop(0)
        if inst[0].find('@') != -1:  # Check predicate, such as @P0
            self.pred = tmp.pop(0)

        ops = tmp[0]
        # Fetech opcode
        self.op = ops.split(".")[0]
        # Split opcode
        self.modifier = ops.split(".")[1:]
        self.operand_positions = [[] for _ in range(4)]
        # Fetech operands and remove ; and ,. It's list format
        self.operands = [_.replace(",", "").replace("-", "").replace("|", "") for _ in tmp[1:]]
