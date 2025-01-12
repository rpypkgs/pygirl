"""
PyGirl Emulator

Work and High RAM
"""

from pygirl import constants


class InvalidMemoryAccess(Exception):
    "A read or write was invalid."
    def __init__(self, message): self.message = message


class iMemory(object):
    "A simple memory interface with reading and writing."
    def write(self, address, data):
        raise InvalidMemoryAccess("Abstract write always fails")

    def read(self, address):
        raise InvalidMemoryAccess("Abstract read always fails")


class MissingMemory(iMemory):
    def write(self, address, data): pass
    def read(self, address): return 0xff
missingMemory = MissingMemory()


class RAM(iMemory):
    def __init__(self):
        self.work_ram = [0] * 8192
        self.hi_ram = [0] * 128
        self.reset()

    def reset(self):
        self.work_ram = [0] * 8192
        self.hi_ram = [0] * 128

    def write(self, address, data):
        # C000-DFFF Work RAM (8KB)
        # E000-FDFF Echo RAM
        if 0xC000 <= address <= 0xFDFF:
            self.work_ram[address & 0x1FFF] = data & 0xFF
        # FF80-FFFE
        elif 0xFF80 <= address <= 0xFFFE:
            self.hi_ram[address & 0x7F] = data & 0xFF

    def read(self, address):
        # C000-DFFF Work RAM
        # E000-FDFF Echo RAM
        if 0xC000 <= address <= 0xFDFF:
            return self.work_ram[address & 0x1FFF]
        # FF80-FFFE
        elif 0xFF80 <= address <= 0xFFFE:
            return self.hi_ram[address & 0x7F]
        raise InvalidMemoryAccess("Invalid Memory access, address out of range")
