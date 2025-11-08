#! /usr/bin/python
from PIL import Image, ImageDraw, ImageFont
import os
import math
from rgb_array import RgbArray
import psutil
import subprocess as sp
import sys
import colorsys
import time


rgb = RgbArray("192.168.1.134")
changing_color = True # Change bar color depending on usage
refresh_rate = 0.2 # Number of seconds between refreshes

def run_command_win(command):
    val = sp.run(['powershell', '-Command', command], capture_output=True).stdout.decode("ascii")
    return float(val.strip().replace(',', '.'))

def get_gpu_percent_win():
    gpu_usage_cmd = r'(((Get-Counter "\GPU Engine(*engtype_3D)\Utilization Percentage").CounterSamples | where CookedValue).CookedValue | measure -sum).sum'
    load = run_command_win(gpu_usage_cmd)
    print(load)
    return load

def get_gpu_percent_linux(): # Definetly works on AMD and should work on intel. Nvidia might not work
    file = open("/sys/class/drm/card1/device/gpu_busy_percent", 'r')
    return(int(file.read()))

def get_gpu_percent():
    if sys.platform == "linux":
        return(get_gpu_percent_linux())
    elif sys.platform == "win32":
        return(get_gpu_percent_win())
    else:
        print("GPU unsupported on this OS")
        return(None)
    
def calculate_bar_color(usage_percent):
    h = (1 / (1 + math.exp(10 * (usage_percent/100 - 0.5)))) * 0.3 #A non-linear curve. Steeper neer the center and slower near the ends because all the yellows look the same
    color = colorsys.hsv_to_rgb(h, 1, 0.4)
    color = tuple(int(x * 255) for x in color)
    return color

def calculate_len(percent):
    if percent is not None:
        w = math.floor(32*percent / 100)
        rest = (percent - (w*100/32)) / (100/32)
        #print(rest)        
        if w < 0:
            w = 0
        return w
    else:
         return 0
    
def get_percent_text(percent):
    if percent < 10:
         return(f' {str(percent)}')
    elif percent > 99:
         return("99")
    else:
         return(str(percent))
    
def create_text_mask(text, img, x, y, font): # Some horrible stuff needed to workaround pillow's antialiasing which was messing up text colors and can't be disabled
    mask = Image.new("1", img.size, 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.text((x, y), text, font=font, fill=1)
    return mask
        

def compose_image(cpu_usage, ram_usage, gpu_usage, cpu_color=(0,75, 75), ram_color=(0,0, 75), gpu_color=(50, 0, 75), changing_color=True):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        font_path = os.path.join(script_dir, "5x8.ttf")
        font = ImageFont.truetype(font_path, size=8)
        img = Image.new(mode="RGB", size=(32, 32))
        draw = ImageDraw.Draw(img)

        cpu_text_mask = create_text_mask("CPU", img, 0, -2, font)
        ram_text_mask = create_text_mask("RAM", img, 0, 9, font)
        gpu_text_mask = create_text_mask("GPU", img, 0, 20, font)

        img.paste(cpu_color, mask=cpu_text_mask)
        img.paste(ram_color, mask=ram_text_mask)
        img.paste(gpu_color, mask=gpu_text_mask)

        cpu_bar_color = calculate_bar_color(cpu_usage)
        ram_bar_color = calculate_bar_color(ram_usage)
        gpu_bar_color = calculate_bar_color(gpu_usage)

        cpu_mask = create_text_mask(get_percent_text(cpu_usage), img, 20, -2, font)
        ram_mask = create_text_mask(get_percent_text(ram_usage), img, 20, 9, font)
        gpu_mask = create_text_mask(get_percent_text(gpu_usage), img, 20, 20, font)


        img.paste(cpu_bar_color, mask=cpu_mask)
        img.paste(ram_bar_color, mask=ram_mask)
        img.paste(gpu_bar_color, mask=gpu_mask)
        
        img.paste(cpu_bar_color, (0, 8, calculate_len(cpu_usage), 10))
        img.paste(ram_bar_color, (0, 19, calculate_len(ram_usage), 21))
        img.paste(gpu_bar_color, (0, 30, calculate_len(gpu_usage), 32))

        return img


while True:
    try:
        rgb.clear()
        break
    except:
        print("Init failed. Retrying in 5 seconds")
        time.sleep(5)


while True:
    try:
        cpu_percent = psutil.cpu_percent(interval=None)
        ram_percent = psutil.virtual_memory().percent
        gpu_percent = get_gpu_percent()
        if changing_color:
            cpu_color = calculate_bar_color(cpu_percent)
            ram_color = calculate_bar_color(ram_percent)
            gpu_color = calculate_bar_color(gpu_percent)
        else:
            cpu_color, ram_color, gpu_color = (0,75, 75), (0,0, 75), (50, 0, 75)
        image = compose_image(cpu_percent, ram_percent, gpu_percent)
        rgb.send_image_udp(image)
        time.sleep(refresh_rate)
    except:
        print("Screen update failed. Retrying in 5 seconds")
        time.sleep(5)
    
