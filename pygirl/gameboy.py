"""
PyGirl Emulator

GameBoy Scheduler and Memory Mapper

"""
from pygirl import constants
from pygirl.cpu import CPU
from pygirl.interrupt import Interrupt
from pygirl.cartridge import CartridgeManager
from pygirl.joypad import Joypad, JoypadDriver
from pygirl.ram import missingMemory, RAM
from pygirl.serial import Serial
from pygirl.sound import Sound, SoundDriver
from pygirl.timer import Timer, Clock
from pygirl.video import Video, VideoDriver
from pygirl.cartridge import CartridgeManager, CartridgeFile


class GameBoy(object):
    def __init__(self):
        self.create_drivers()
        self.create_gameboy_elements()

    def create_drivers(self):
        self.joypad_driver = JoypadDriver()
        self.video_driver = VideoDriver()
        self.sound_driver = SoundDriver()

    def create_gameboy_elements(self):
        self.clock = Clock()
        self.ram = RAM()
        self.cartridge_manager = CartridgeManager(self.clock)
        self.interrupt = Interrupt()
        self.cpu = CPU(self.interrupt, self)
        self.serial = Serial(self.interrupt)
        self.timer = Timer(self.interrupt)
        self.joypad = Joypad(self.joypad_driver, self.interrupt)
        self.video = Video(self.video_driver, self.interrupt, self)
        self.sound = Sound()

    def get_cartridge_manager(self):
        return self.cartridge_manager

    def load_cartridge(self, cartridge, verify=True):
        self.cartridge_manager.load(cartridge, verify)
        self.cpu.set_rom(self.cartridge_manager.get_rom())
        self.memory_bank_controller = self.cartridge_manager.get_memory_bank()

    def load_cartridge_file(self, path, verify=True):
        self.load_cartridge(CartridgeFile(path), verify)

    def get_frame_skip(self):
        return self.video.get_frame_skip()

    def set_frame_skip(self, frameSkip):
        self.video.set_frame_skip(frameSkip)

    def save(self, cartridgeName):
        self.cartridge_manager.save(cartridgeName)

    def start(self):
        self.sound_driver.start()

    def stop(self):
        self.sound_driver.stop()

    def reset(self):
        self.ram.reset()
        self.memory_bank_controller.reset()
        self.interrupt.reset()
        self.cpu.reset()
        self.serial.reset()
        self.timer.reset()
        self.joypad.reset()
        self.video.reset()
        self.sound.reset()
        self.cpu.set_rom(self.cartridge_manager.get_rom())
        self.draw_logo()

    def get_cycles(self):
        # RPython supports only two arguments in min()
        return min(min(min(self.video.get_cycles(), self.serial.get_cycles()),
                       self.timer.get_cycles()), self.joypad.get_cycles())

    def emulate(self, ticks):
        while ticks > 0:
            count = self.get_cycles()
            self.cpu.emulate(count)
            self.serial.emulate(count)
            self.timer.emulate(count)
            self.video.emulate(count)
            self.joypad.emulate(count)
            # self.print_cycles()
            if count == 0:
                # self.print_cycles()
                return 0
            ticks -= count
        return 0

    def emulate_step(self):
        self.cpu.emulate_step()
        self.serial.emulate(1)
        self.timer.emulate(1)
        self.video.emulate(1)
        self.joypad.emulate(1)

    def print_cycles(self):
        return
        # for element in [(" video:", self.video),
        #                ("serial:", self.serial),
        #                (" timer:", self.timer), 
        #                ("joypad:", self.joypad)]:
        #    #print "        ", element[0], element[1].get_cycles()
        #    pass

    def write(self, address, data):
        self.get_receiver(address).write(address, data)
        if address in (constants.STAT, 0xFFFF):
            self.cpu.handle_pending_interrupts()

    def read(self, address): return self.get_receiver(address).read(address)

    def print_receiver_msg(self, address, name):
        # print "    recei: ", hex(address), name
        pass

    def get_receiver(self, address):
        """
        General Memory Map
        0000-3FFF   16KB ROM Bank 00     (in cartridge, fixed at bank 00)
        4000-7FFF   16KB ROM Bank 01..NN (in cartridge, switchable bank number)
        8000-9FFF   8KB Video RAM (VRAM)
        A000-BFFF   8KB External RAM     (in cartridge, switchable bank, if any)
        C000-CFFF   4KB Work RAM Bank 0 (WRAM)
        D000-DFFF   4KB Work RAM Bank 1 (WRAM)
        E000-FDFF   Same as C000-DDFF (ECHO)    (typically not used)
        FE00-FE9F   Sprite Attribute Table (OAM)
        FEA0-FEFF   Not Usable
        FF00-FF7F   I/O Ports
        FF80-FFFE   High RAM (HRAM)
        FFFF        Interrupt Enable Register
        """
        if 0x0000 <= address <= 0x7FFF:
            self.print_receiver_msg(address, "memoryBank")
            return self.cartridge_manager.get_memory_bank()
        elif 0x8000 <= address <= 0x9FFF:
            self.print_receiver_msg(address, "video")
            return self.video
        elif 0xA000 <= address <= 0xBFFF:
            self.print_receiver_msg(address, "memoryBank")
            return self.cartridge_manager.get_memory_bank()
        elif 0xC000 <= address <= 0xFDFF:
            self.print_receiver_msg(address, "ram")
            return self.ram
        elif 0xFE00 <= address <= 0xFEFF:
            self.print_receiver_msg(address, "video")
            return self.video
        elif address == 0xFF00:
            self.print_receiver_msg(address, "joypad")
            return self.joypad
        elif 0xFF01 <= address <= 0xFF02:
            self.print_receiver_msg(address, "serial")
            return self.serial
        elif 0xFF04 <= address <= 0xFF07:
            self.print_receiver_msg(address, "timer")
            return self.timer
        elif address == 0xFF0F:
            self.print_receiver_msg(address, "interrupt")
            return self.interrupt
        elif 0xFF10 <= address <= 0xFF3F:
            self.print_receiver_msg(address, "sound")
            return self.sound
        elif 0xFF40 <= address <= 0xFF4B:
            self.print_receiver_msg(address, "video")
            return self.video
        elif 0xFF80 <= address <= 0xFFFE:
            self.print_receiver_msg(address, "ram")
            return self.ram
        elif address == 0xFFFF:
            self.print_receiver_msg(address, "interrupt")
            return self.interrupt
        return missingMemory

    def draw_logo(self):
        for index in range(0, 48):
            bits = self.memory_bank_controller.read(0x0104 + index)
            pattern0 = ((bits >> 0) & 0x80) + ((bits >> 1) & 0x60) + \
                       ((bits >> 2) & 0x18) + ((bits >> 3) & 0x06) + \
                       ((bits >> 4) & 0x01)
            pattern1 = ((bits << 4) & 0x80) + ((bits << 3) & 0x60) + \
                       ((bits << 2) & 0x18) + ((bits << 1) & 0x06) + \
                       ((bits << 0) & 0x01)
            self.video.write(0x8010 + (index << 3), pattern0)
            self.video.write(0x8012 + (index << 3), pattern0)
            self.video.write(0x8014 + (index << 3), pattern1)
            self.video.write(0x8016 + (index << 3), pattern1)
        for index in range(0, 8):
            self.video.write(0x8190 + (index << 1), \
                             constants.REGISTERED_BITMAP[index])
        for tile in range(0, 12):
            self.video.write(0x9904 + tile, tile + 1)
            self.video.write(0x9924 + tile, tile + 13)
        self.video.write(0x9904 + 12, 25)


if __name__ == '__main__':
    import sys
    from gameboy_implementation import GameBoyImplementation

    gameboy = GameBoyImplementation()
    rom = sys.argv[1]
    print rom
    gameboy.load_cartridge_file(rom, verify=True)
    gameboy.mainLoop()
