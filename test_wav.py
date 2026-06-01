import wave, struct, math, io, subprocess

def create_wav_header(sample_rate, num_channels, bytes_per_sample, data_size=0x7FFFFFFF):
    header = b'RIFF'
    header += struct.pack('<L', 36 + data_size)
    header += b'WAVE'
    header += b'fmt '
    header += struct.pack('<L', 16)
    header += struct.pack('<H', 3 if bytes_per_sample == 4 else 1)
    header += struct.pack('<H', 1)
    header += struct.pack('<L', sample_rate)
    header += struct.pack('<L', sample_rate * 1 * bytes_per_sample)
    header += struct.pack('<H', 1 * bytes_per_sample)
    header += struct.pack('<H', bytes_per_sample * 8)
    header += b'data'
    header += struct.pack('<L', data_size)
    return header

header = create_wav_header(24000, 1, 2)
with open("test.wav", "wb") as f:
    f.write(header)
    for i in range(24000):
        val = int(math.sin(2 * math.pi * 440 * (i / 24000.0)) * 32767)
        f.write(struct.pack("<h", val))

