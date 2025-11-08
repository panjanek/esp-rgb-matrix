import mpris2
import rgb_array
from PIL import Image, ImageDraw, ImageFont
import os
import time
import pyaudio
import numpy as np
import math
import colorsys
# from vu_meter_utils import *


def get_player_interface():
    try:
        for uri in mpris2.get_players_uri():
            player = mpris2.Player(dbus_interface_info={'dbus_uri': uri})
            if player.PlaybackStatus == 'Playing':
                return player
        for uri in mpris2.get_players_uri():
            player = mpris2.Player(dbus_interface_info={'dbus_uri': uri})
            if player.PlaybackStatus == 'Paused':
                return player
        for uri in mpris2.get_players_uri():
            player = mpris2.Player(dbus_interface_info={'dbus_uri': uri})
            if player.PlaybackStatus == 'Stopped':
                return player
    except:
        print("Unable to detect players. Did a player close?")
        return None
    return None
    
def get_player_info(player):
    metadata = player.Metadata
    title = metadata.get(player.Metadata.TITLE)
    if title != None:
        title = str(title)
    artist = metadata.get(player.Metadata.ARTIST)
    if artist != None:
        artist = str(artist[0])
    album = metadata.get(player.Metadata.ALBUM)
    if album != None:
        album = str(album)
    length = metadata.get(player.Metadata.LENGTH)
    if length != None:
        length = int(length)
    else:
        length = 0
    return title, artist, album, length

def create_text_mask(text, img, x, y, font): # Some horrible stuff needed to workaround pillow's antialiasing which was messing up text colors and can't be disabled
    mask = Image.new("L", img.size, 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.text((x, y), text, font=font, fill=255, align='center') # Some more awfulness to work around more antialiasing issues. If everything is black lower the threshold
    threshold = 100
    mask = mask.point(lambda p: 255 if p > threshold else 0, mode="1")
    return mask

def create_progress_bar(length, position):
    img = Image.new(mode="RGB", size=(1024, 32))
    if length == 0:
        bar_length = 0
    else:
        bar_length = round((position / length) * 1024)
    img.paste((255, 0, 255), (0, 0, bar_length, 32))
    resized = img.resize((32, 2), Image.BILINEAR)
    return resized

def compose_image(title, lower_line, length, position, scroll_pos_title=0, scroll_pos_lower=0, audio_level=0):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    font_path = os.path.join(script_dir, '5x8.ttf')
    font = ImageFont.truetype(font_path, size=8)
    img = Image.new(mode='RGB', size=(32, 32))

          
    if len(title) > 6:
        img.paste((0, 255, 0), mask=create_text_mask(title, img, -scroll_pos_title, -2, font))
    else:
        img.paste((0, 255, 0), mask=create_text_mask(title, img, (32 - len(title)*6)//2, -2, font)) # The weird calculations are to center the text

    if len(lower_line) > 6:
        img.paste((255, 255, 0), mask=create_text_mask(lower_line, img, -scroll_pos_lower, 7, font))
    else:
        img.paste((255, 255, 0), mask=create_text_mask(lower_line, img, (32 - len(lower_line)*6)//2, 7, font))

    seconds = int(position / 1000000)
    minutes = seconds // 60
    seconds = seconds % 60

    if minutes > 99:
        minutes = 99
        seconds = 59

    img.paste((0, 255, 255), mask=create_text_mask(f'{minutes:02}', img, 1, 16, font)) # There are two draw calls so that is's perfectly centered. With one is would always be one pixel off
    img.paste((0, 255, 255), mask=create_text_mask(f':{seconds:02}', img, 14, 16, font))

    img.paste(create_progress_bar(length, position), (0, 28, 32, 30))
    # img.paste(create_vu_bar(audio_level), (0, 30, 32, 32))
    
    return img


rgb = rgb_array.RgbArray('192.168.1.134')
step_title = 0
step_lower = 0
delay_title = 0
delay_lower = 0
title = '' # Needed for track change detection

# Configure things for the VU meter
# device_index = 9
# device_name = "alsa_output.pci-0000_0b_00.1.hdmi-surround.monitor"
# channels = 6
# rate = 48000
# chunk = 512
# format = pyaudio.paInt32p = pyaudio.PyAudio()
# os.environ["PULSE_SOURCE"] = device_name
# p = pyaudio.PyAudio()


# stream = p.open(format=pyaudio.paInt16,
#                 channels=channels,
#                 rate=rate,
#                 input=True,
#                 frames_per_buffer=chunk,
#                 input_device_index=device_index,
#                 stream_callback=None)

try:
    while True:
        player = get_player_interface()
        if player != None:
            old_title = title
            title, artist, album, length = get_player_info(player)
            
            if title == None:
                title = '-'

            if artist == None and album == None:
                lower_line = '-'
            elif album == None:
                lower_line = artist
            elif artist == None:
                lower_line = album
            else:
                lower_line = f'{artist} - {album}'

            if old_title != title: # A janky method to detect track changes. Ideally it could detect the signal sent out by Dbus but IDK how to do that
                step_lower = 0
                step_title = 0
                delay_lower = 0
                delay_title = 0

            scroll_steps_title = len(title)*6 + 4
            scroll_steps_lower = len(lower_line)*6 + 4
            position = int(player.Position)

            if step_title >= scroll_steps_title:
                step_title = 0
            if step_lower >= scroll_steps_lower:
                step_lower = 0

            #audio_level = get_current_amplitude(stream, chunk=chunk, channels=channels)
            rgb.send_image_udp(compose_image(title, lower_line, length, position, scroll_pos_title=int(step_title), scroll_pos_lower=int(step_lower)))
            if step_title == 0 and delay_title<=7:
                delay_title +=1
            else:
                delay_title = 0
                step_title += 1

            if step_lower == 0 and delay_lower<=7:
                delay_lower +=1
            else:
                delay_lower = 0
                step_lower += 1
        else:
            rgb.send_image_udp(compose_image('-', '-', 0, 0, 0, 0))
                
        time.sleep(0.1)
except:
    print("Something went wrong. Exiting")
    # stream.stop_stream()
    # stream.close()
    # p.terminate()

