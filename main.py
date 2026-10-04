"""Laptop node: mic -> faster-whisper -> matcher -> one serial byte to the XIAO.

    python main.py --list-ports                 # find the XIAO's port
    python main.py --list-devices               # find the mic index
    python main.py --send T                     # bench-test the motor, then exit (X = stop all)
    python main.py --say "Shibu watch out"      # matcher -> serial, no mic, no model
    python main.py --no-serial --debug          # mic + whisper dry run, no hardware
    python main.py --port auto --debug          # live
    python main.py --port auto --needle         # live, cactus-needle as backup when the matcher misses

Levels: N name, W "watch out", R "run", T "tsunami" (higher outranks lower). X stops the motor.
Needs matcher.py in the same folder.
"""
import argparse
import queue
import sys
import time

import numpy as np

try:
    from rapidfuzz import fuzz
    from matcher import detect
except ImportError as e:
    sys.exit(f"{e}\nRun: pip install -r requirements.txt (and keep matcher.py next to main.py)")

SR = 16000
PROMPT = "Shibu, watch out, run, tsunami."


def looks_like_prompt(text):
    """Whisper sometimes parrots its own initial prompt back on noise; never fire on that."""
    return len(text) >= 20 and fuzz.partial_ratio(text.lower(), PROMPT.lower()) >= 90


def need_serial():
    try:
        import serial
        from serial.tools import list_ports as lp
    except ImportError:
        sys.exit("pyserial missing. Run: pip install -r requirements.txt")
    return serial, lp


def list_ports():
    return list(need_serial()[1].comports())


def find_port():
    ports = list_ports()
    for vid in (0x303A, 0x2886):  # Espressif, Seeed
        for p in ports:
            if p.vid == vid:
                return p.device
    return None


def open_serial(port):
    serial, _ = need_serial()
    if not port or port == "auto":
        port = find_port()
        if port is None:
            sys.exit("No XIAO found. Plug it in, then run: python main.py --list-ports")
        print(f"using {port}")
    s = serial.Serial()
    s.port = port
    s.baudrate = 115200
    s.dtr = False  # don't reset the ESP32-S3 when opening the port
    s.rts = False
    try:
        s.open()
    except serial.SerialException as e:
        sys.exit(f"Can't open {port}: {e}\nClose Arduino Serial Monitor / other programs using it, "
                 "and on Linux make sure you're in the 'dialout' group.")
    return s


def send(ser, level):
    ser.write(level.encode())
    ser.flush()


def send_once(port, level):
    ser = open_serial(port)
    time.sleep(0.5)
    send(ser, level)
    print(f"sent {level}")
    time.sleep(0.2)
    ser.close()


def open_stream(sd, device, cb):
    try:
        st = sd.InputStream(samplerate=SR, channels=1, dtype="float32",
                            blocksize=1024, device=device, callback=cb)
        return st, SR
    except sd.PortAudioError as e:
        rate = int(sd.query_devices(device, "input")["default_samplerate"])
        print(f"mic refused {SR} Hz ({e}); using {rate} Hz and resampling")
        st = sd.InputStream(samplerate=rate, channels=1, dtype="float32",
                            blocksize=1024, device=device, callback=cb)
        return st, rate


def to16k(x, rate):
    if rate == SR:
        return x
    if rate % SR == 0:
        k = rate // SR
        return x[: len(x) // k * k].reshape(-1, k).mean(axis=1).astype(np.float32)
    n = int(len(x) * SR / rate)
    return np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)


def main():
    try:
        sys.stdout.reconfigure(errors="replace")  # odd characters shouldn't crash a Windows console
    except Exception:
        pass

    ap = argparse.ArgumentParser()
    ap.add_argument("--port", default="auto")
    ap.add_argument("--no-serial", action="store_true")
    ap.add_argument("--send", choices=list("NWRTX"), help="send one byte and exit")
    ap.add_argument("--say", default=None, help="run the matcher on this text, send the level, exit")
    ap.add_argument("--list-ports", action="store_true")
    ap.add_argument("--list-devices", action="store_true")
    ap.add_argument("--debug", action="store_true", help="print rms and every transcript")
    ap.add_argument("--model", default="base.en")
    ap.add_argument("--threads", type=int, default=4)
    ap.add_argument("--device", default=None)
    ap.add_argument("--window", type=float, default=3.0)
    ap.add_argument("--stride", type=float, default=1.0)
    ap.add_argument("--cooldown", type=float, default=None, help="default = window")
    ap.add_argument("--gate", type=float, default=0.008)
    ap.add_argument("--no-prompt", action="store_true")
    ap.add_argument("--needle", action="store_true",
                    help="use cactus-needle tool calling when the matcher finds nothing")
    args = ap.parse_args()
    cooldown = args.window if args.cooldown is None else args.cooldown

    if args.list_ports:
        ports = list_ports()
        for p in ports:
            print(f"{p.device}  vid={p.vid and hex(p.vid)}  {p.description}")
        if not ports:
            print("no serial ports found")
        return
    if args.list_devices:
        import sounddevice as sd

        print(sd.query_devices())
        return

    if args.say is not None:
        level, tok = detect(args.say)
        print(f"matcher: {args.say!r} -> {level or 'no match'} ({tok})")
        if level and not args.no_serial:
            send_once(args.port, level)
        return

    if args.send:
        if args.no_serial:
            sys.exit("--send needs the serial port; drop --no-serial")
        send_once(args.port, args.send)
        return

    ser = None
    if not args.no_serial:
        ser = open_serial(args.port)
        time.sleep(0.5)

    nd = None
    if args.needle:
        try:
            from needle_layer import NeedleDetector

            nd = NeedleDetector()
            print("cactus-needle ready")
        except Exception as e:
            print(f"cactus-needle unavailable ({type(e).__name__}); using matcher only")

    try:
        from faster_whisper import WhisperModel
        import sounddevice as sd
    except ImportError as e:
        sys.exit(f"{e}\nRun: pip install -r requirements.txt")

    print(f"loading {args.model} (first run downloads it, needs internet) ...")
    model = WhisperModel(args.model, device="cpu", compute_type="int8", cpu_threads=args.threads)
    prompt = None if args.no_prompt else PROMPT

    def transcribe(audio):
        segs, _ = model.transcribe(
            audio, language="en", beam_size=1, temperature=0.0, vad_filter=True,
            condition_on_previous_text=False, max_new_tokens=32, initial_prompt=prompt,
        )
        return " ".join(s.text.strip() for s in segs).strip()

    device = int(args.device) if args.device and args.device.isdigit() else args.device
    q = queue.Queue()

    def cb(indata, frames, t, status):
        if status:
            print(status)
        q.put(indata[:, 0].copy())

    transcribe(np.zeros(SR, dtype=np.float32))  # warmup
    buf = np.zeros(0, dtype=np.float32)
    last_fire = {}
    next_t = time.time() + args.stride

    stream, rate = open_stream(sd, device, cb)
    with stream:
        print(f"listening ({'dry run' if ser is None else ser.port}). Ctrl+C to stop.")
        try:
            while True:
                try:
                    chunks = [q.get(timeout=0.5)]  # timeout keeps Ctrl+C working on Windows
                except queue.Empty:
                    continue
                while not q.empty():
                    chunks.append(q.get_nowait())
                buf = np.concatenate([buf, *chunks])[-int(args.window * rate):]
                if time.time() < next_t:
                    continue
                next_t = time.time() + args.stride
                rms = float(np.sqrt(np.mean(buf ** 2)))
                if rms < args.gate:
                    if args.debug:
                        print(f"quiet  rms={rms:.4f} (gate {args.gate})")
                    continue

                t0 = time.time()
                text = transcribe(to16k(buf, rate))
                if args.debug:
                    print(f"heard  rms={rms:.4f} {text!r}")
                if looks_like_prompt(text):
                    if args.debug:
                        print("ignored: prompt echo")
                    continue
                level, tok = detect(text)
                if not level and nd is not None:
                    try:
                        level, tok = nd.detect(text)
                    except Exception as e:
                        print(f"needle error: {e}")
                if not level:
                    continue
                now = time.time()
                if now - last_fire.get(level, 0) <= cooldown:
                    continue
                last_fire[level] = now
                if ser is not None:
                    try:
                        send(ser, level)
                    except Exception as e:
                        print(f"serial write failed: {e}")
                        break
                print(f"FIRE {level} ({tok}) <- {text!r}  [stt {(now - t0) * 1000:.0f} ms]")
        except KeyboardInterrupt:
            print("\nstopped")
    if ser is not None:
        ser.close()


if __name__ == "__main__":
    main()
