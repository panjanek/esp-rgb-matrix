from PIL import Image
import numpy as np
import colorsys
import math

def get_current_amplitude(stream, chunk=512, channels=2, exponent=0.5):
    try:
        while stream.get_read_available() > 0:
            stream.read(stream.get_read_available(), exception_on_overflow=False) # Clearout buffered chunks
        data = stream.read(chunk, exception_on_overflow=False)
    except IOError:
        return 0  # buffer overrun, treat as silence
    samples = np.frombuffer(data, dtype=np.int16).astype(np.float32)

    if samples.size == 0:
        return 0 # Empty list, treat as silence

    # For stereo, average channels to get RMS
    if channels > 1:
        samples = samples.reshape(-1, channels)
        rms = np.sqrt(np.mean(np.mean(samples**2, axis=1)))
    else:
        rms = np.sqrt(np.mean(samples**2))

    # Normalize RMS
    norm = rms / 32767.0
    norm = min(1.0, norm)

    # Apply exponent for more visual dynamics
    level = int((norm ** exponent) * 100)
    level = max(0, min(100, level))
    return level

def create_vu_bar(level):
    img = Image.new(mode="RGB", size=(1024, 32))
    bar_length = round(level * 10.24)
    color = calculate_bar_color(level)
    img.paste(color, (0, 0, bar_length, 32))
    resized = img.resize((32, 2), Image.BILINEAR)
    return resized

def calculate_bar_color(level):
    h = (1 / (1 + math.exp(10 * (level/100 - 0.5)))) * 0.3 #A non-linear curve. Steeper neer the center and slower near the ends because all the yellows look the same
    color = colorsys.hsv_to_rgb(h, 1, 0.4)
    color = tuple(int(x * 255) for x in color)
    return color