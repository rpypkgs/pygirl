#!/usr/bin/env python 

from pygirl.gameboy import GameBoy
from pygirl.joypad import JoypadDriver
from pygirl.video import VideoDriver
from pygirl.sound import SoundDriver
from pygirl.timer import Clock
from pygirl.video_meta import TileDataWindow, SpriteWindow, \
    WindowPreview, BackgroundPreview, \
    MapAViewer, MapBViewer, \
    SpritesWindow
from pygirl import constants
import time

# Extends the window with windows visualizing meta-data
# WARNING! Window will be very, very big!
show_metadata = False

from rpython.rlib.rarithmetic import intmask, r_int, r_uint
from rpython.rtyper.lltypesystem import lltype, rffi

from rsdl import RSDL, RSDL_helper


def delay(secs): return RSDL.Delay(int(secs * 1000))


# About 64 to make sure we have a clean distrubution of about
# 64 frames per second
FPS = 64


# GAMEBOY ----------------------------------------------------------------------

class GameBoyImplementation(GameBoy):
    def __init__(self):
        GameBoy.__init__(self)
        self.is_running = False
        self.penalty = 0
        self.sync_time = int(time.time())

    def open_window(self):
        self.init_sdl()
        self.video_driver.create_screen()

    def init_sdl(self):
        assert RSDL.Init(RSDL.INIT_VIDEO) >= 0
        self.event = lltype.malloc(RSDL.Event, flavor='raw')

    def create_drivers(self):
        self.clock = Clock()
        self.joypad_driver = JoypadDriverImplementation()
        self.video_driver = VideoDriverImplementation(self)
        self.sound_driver = SoundDriverImplementation()
        with lltype.scoped_alloc(RSDL.AudioSpec, zero=True) as desired:
            with lltype.scoped_alloc(RSDL.AudioSpec, zero=True) as audioSpec:
                rffi.setintfield(desired, "c_freq", 44100)
                rffi.setintfield(desired, "c_format", RSDL.AUDIO_U8)
                rffi.setintfield(desired, "c_channels", 2)
                rffi.setintfield(desired, "c_samples", 512)
                # desired.c_callback = self.sound_driver.write
                RSDL.OpenAudio(desired, audioSpec)
                self.sound_driver.create_sound_driver(audioSpec)

    def mainLoop(self):
        self.reset()
        self.is_running = True
        while self.is_running:
            self.emulate_cycle()
        # try:
        #    while self.is_running:
        #        self.emulate_cycle()
        # except Exception, error:
        #    self.is_running = False
        #    self.handle_execution_error(error)
        return 0

    def emulate_cycle(self):
        self.handle_events()
        # Come back to this cycle every 1/FPS seconds
        self.emulate(constants.GAMEBOY_CLOCK / FPS)
        spent = time.time() - self.sync_time
        left = 1.0 / FPS + self.penalty - spent
        if left > 0:
            delay(left)
            self.penalty = 0.0
        else:
            # Fade out penalties over time.
            self.penalty = left - self.penalty / 2
        self.sync_time = time.time()

    def handle_execution_error(self, error):
        lltype.free(self.event, flavor='raw')
        lltype.free(self.audioSpec, flavor='raw')
        RSDL.Quit()

    def handle_events(self):
        self.poll_event()
        if self.check_for_escape():
            self.is_running = False
        self.joypad_driver.update(self.event)

    def poll_event(self):
        ok = rffi.cast(lltype.Signed, RSDL.PollEvent(self.event))
        return ok > 0

    def check_for_escape(self):
        c_type = rffi.getintfield(self.event, 'c_type')
        if c_type == RSDL.KEYDOWN:
            p = rffi.cast(RSDL.KeyboardEventPtr, self.event)
            if rffi.getintfield(p.c_keysym, 'c_sym') == RSDL.K_ESCAPE:
                return True
        elif c_type == RSDL.QUIT:
            return True
        return False


# VIDEO DRIVER -----------------------------------------------------------------

class VideoDriverImplementation(VideoDriver):
    COLOR_MAP = [(0xff, 0xff, 0xff), (0xCC, 0xCC, 0xCC), (0x66, 0x66, 0x66), (0, 0, 0)]

    def __init__(self, gameboy):
        VideoDriver.__init__(self)
        self.scale = 4

        if show_metadata:
            self.create_meta_windows(gameboy)

    def create_screen(self):
        self.screen = RSDL.SetVideoMode(self.width * self.scale, self.height * self.scale, 32, 0)
        fmt = self.screen.c_format
        self.colors = []
        for color in self.COLOR_MAP:
            color = RSDL.MapRGB(fmt, *color)
            self.colors.append(color)
        self.blit_rect = RSDL_helper.mallocrect(0, 0, self.scale, self.scale)

    def create_meta_windows(self, gameboy):
        upper_meta_windows = [SpritesWindow(gameboy),
                              SpriteWindow(gameboy),
                              TileDataWindow(gameboy),
                              ]
        lower_meta_windows = [
            WindowPreview(gameboy),
            BackgroundPreview(gameboy),
            MapAViewer(gameboy),
            MapBViewer(gameboy)]

        self.meta_windows = upper_meta_windows + lower_meta_windows
        for window in upper_meta_windows:
            window.set_origin(self.width, 0)
            self.height = max(self.height, window.height)
            self.width += window.width
        second_x = 0
        second_y = self.height
        for window in lower_meta_windows:
            window.set_origin(second_x, second_y)
            second_x += window.width
            self.width = max(self.width, second_x)
            self.height = max(self.height, second_y + window.height)

    def update_display(self):
        RSDL.LockSurface(self.screen)
        if show_metadata:
            for meta_window in self.meta_windows:
                meta_window.draw()
        self.draw_pixels()
        RSDL.UnlockSurface(self.screen)
        RSDL.Flip(self.screen)
        # print '\x1b[H\x1b[2J'  # Clear screen
        # self.draw_ascii_pixels()

    def draw_pixel(self, x, y, color):
        color = self.colors[color]
        start_x = x * self.scale
        start_y = y * self.scale
        dstrect = self.blit_rect
        rffi.setintfield(dstrect, 'c_x', start_x)
        rffi.setintfield(dstrect, 'c_y', start_y)
        RSDL.FillRect(self.screen, dstrect, color)

    def draw_pixels(self):
        for y in range(constants.GAMEBOY_SCREEN_HEIGHT):
            for x in range(constants.GAMEBOY_SCREEN_WIDTH):
                if self.was_dirty(x, y):
                    self.draw_pixel(x, y, self.get_pixel(x, y))

    def draw_ascii_pixels(self):
        str = []
        for y in range(self.height):
            str.append("\n")
            for x in range(self.width):
                if y % 2 == 0 or True:
                    str.append(["#", "%", "+", "."][self.get_pixel(x, y)])
        print ''.join(str)


# JOYPAD DRIVER ----------------------------------------------------------------

class JoypadDriverImplementation(JoypadDriver):
    def __init__(self):
        JoypadDriver.__init__(self)
        self.last_key = 0

    def update(self, event):
        # fetch the event from sdl
        type = rffi.getintfield(event, 'c_type')
        if type == RSDL.KEYDOWN:
            self.create_called_key(event)
            self.on_key_down()
        elif type == RSDL.KEYUP:
            self.create_called_key(event)
            self.on_key_up()

    def create_called_key(self, event):
        p = rffi.cast(RSDL.KeyboardEventPtr, event)
        self.last_key = rffi.getintfield(p.c_keysym, 'c_sym')

    def on_key_down(self):
        self.toggleButton(self.get_button_handler(self.last_key), True)

    def on_key_up(self):
        self.toggleButton(self.get_button_handler(self.last_key), False)

    def toggleButton(self, pressButtonFunction, enabled):
        if pressButtonFunction is not None:
            pressButtonFunction(self, enabled)

    def get_button_handler(self, key):
        if key == RSDL.K_UP:
            return JoypadDriver.button_up
        elif key == RSDL.K_RIGHT:
            return JoypadDriver.button_right
        elif key == RSDL.K_DOWN:
            return JoypadDriver.button_down
        elif key == RSDL.K_LEFT:
            return JoypadDriver.button_left
        elif key == RSDL.K_RETURN:
            return JoypadDriver.button_start
        elif key == RSDL.K_SPACE:
            return JoypadDriver.button_select
        elif key == RSDL.K_a:
            return JoypadDriver.button_a
        elif key == RSDL.K_s:
            return JoypadDriver.button_b


# SOUND DRIVER -----------------------------------------------------------------

class SoundDriverImplementation(SoundDriver):
    """
    The current implementation doesnt handle sound yet
    """

    enabled = False

    def create_sound_driver(self, audioSpec):
        self.sampleRate = intmask(audioSpec.c_freq)
        self.channelCount = intmask(audioSpec.c_channels)
        self.buffersize = intmask(audioSpec.c_samples)

        self.bitsPerSample = 4
        self.sampleSize = self.bitsPerSample * self.channelCount

    def start(self): RSDL.PauseAudio(0)

    def stop(self): RSDL.PauseAudio(1)

    def write(self, buffer, length):
        if not self.enabled: return
        pass


# ==============================================================================

if __name__ == '__main__':
    import sys

    gameboy = GameBoyImplementation()
    rom = sys.argv[1]
    print rom
    gameboy.load_cartridge_file(rom)
    gameboy.mainLoop()
