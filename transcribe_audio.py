# compliance-silent
import os
import sys
import time
import datetime
import subprocess
import json
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

# Auto-install missing dependencies
REQUIRED_PACKAGES = {
    "sounddevice": "sounddevice",
    "numpy": "numpy",
    "soundfile": "soundfile",
    "whisper": "openai-whisper"
}

missing = []
for module_name, pip_name in REQUIRED_PACKAGES.items():
    try:
        __import__(module_name)
    except ImportError:
        missing.append(pip_name)

if missing:
    print(f"[setup] Missing required packages: {', '.join(missing)}")
    print("[setup] Auto-installing openai-whisper and torch (this might take a minute, please wait)...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install"] + missing)
        print("[setup] Packages installed successfully! Restarting script...")
        os.execv(sys.executable, [sys.executable] + sys.argv)
    except Exception as e:
        print(f"[error] Failed to install packages: {e}")
        sys.exit(1)

import sounddevice as sd
import numpy as np
import soundfile as sf
import whisper

# Global webhook server state
current_reel_metadata = None
webhook_trigger = False

class WebhookHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        return

    def do_POST(self):
        global current_reel_metadata, webhook_trigger
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        try:
            data = json.loads(post_data.decode('utf-8'))
            current_reel_metadata = data  # Schema: {'url': ..., 'title': ..., 'author': ...}
            webhook_trigger = True
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(b'{"status": "ok"}')
        except Exception:
            self.send_response(400)
            self.end_headers()
            
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

def start_webhook_server():
    server = HTTPServer(('127.0.0.1', 8080), WebhookHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    print("[server] Local webhook server listening on http://127.0.0.1:8080")
    print("[server] To install Chrome script, open: http://127.0.0.1:8080/")

def select_audio_device():
    devices = sd.query_devices()
    wasapi_loopbacks = []
    other_inputs = []

    for i, dev in enumerate(devices):
        if dev['max_input_channels'] > 0:
            name = dev['name']
            host_api = sd.query_hostapis(dev['hostapi'])['name']
            device_info = f"[{i}] {name} ({host_api})"
            
            if "loopback" in name.lower() or "stereo mix" in name.lower() or ("wasapi" in host_api.lower() and "output" in name.lower()):
                wasapi_loopbacks.append((i, device_info))
            else:
                other_inputs.append((i, device_info))

    if wasapi_loopbacks:
        selected_idx, selected_info = wasapi_loopbacks[0]
        print(f"\n[info] Auto-selected loopback device: {selected_info}")
        return selected_idx

    print("\n--- Available Audio Devices ---")
    print("\n[Recommended System Audio/Loopback Devices]:")
    print("  None detected automatically. Make sure Stereo Mix/WASAPI loopback is enabled.")

    print("\n[Other Input Devices (Microphones/Inputs)]:")
    for index, info in other_inputs:
        print(f"  {info}")

    default_idx = other_inputs[0][0] if other_inputs else None
    prompt = f"\nSelect device index [default {default_idx}]: " if default_idx is not None else "\nSelect device index: "
    user_input = input(prompt).strip()
    
    if not user_input and default_idx is not None:
        return default_idx
    try:
        return int(user_input)
    except ValueError:
        print("[error] Invalid index selected. Using default device.")
        return default_idx

def is_music(audio_data, sample_rate):
    if len(audio_data.shape) > 1 and audio_data.shape[1] > 1:
        mono_data = np.mean(audio_data, axis=1)
    else:
        mono_data = audio_data.flatten()
        
    if len(mono_data) == 0:
        return False
        
    frame_length = int(sample_rate * 0.1)
    if len(mono_data) < frame_length:
        return False
        
    num_frames = len(mono_data) // frame_length
    rms_values = []
    
    for i in range(num_frames):
        frame = mono_data[i*frame_length : (i+1)*frame_length]
        rms = np.sqrt(np.mean(frame**2))
        rms_values.append(rms)
        
    rms_values = np.array(rms_values)
    
    max_rms = np.max(rms_values)
    if max_rms == 0:
        return False
    rms_norm = rms_values / max_rms
    
    variance = np.var(rms_norm)
    return variance < 0.038

def process_and_transcribe_slice(audio_slice, samplerate, target_folder, index, metadata, model):
    duration = len(audio_slice) / samplerate
    print(f"\n[process] Processing segment #{index} (Duration: {duration:.2f}s)...")
    
    # Check if the audio is music/song
    if is_music(audio_slice, samplerate):
        print(f"[process] Segment #{index}: Detected music/song. Skipping transcription.")
        return
        
    temp_wav = os.path.join(target_folder, f"_temp_segment_{index}.wav")
    try:
        sf.write(temp_wav, audio_slice, samplerate, subtype='PCM_16')
        
        # Transcribe locally via Whisper (fp16=False runs CPU inference stably without warning)
        print(f"[process] Transcribing segment #{index} offline using Whisper...")
        result = model.transcribe(temp_wav, fp16=False, language="en")
        text = result.get("text", "").strip()
        
        if not text:
            print(f"[process] Segment #{index}: No speech recognized.")
            return
            
        # Format output filename and prep metadata
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        author_suffix = ""
        meta = metadata
        
        if meta and meta.get("author"):
            author = "".join([c for c in meta.get("author").strip().replace(" ", "_") if c.isalnum() or c == "_"])
            if author:
                author_suffix = f"_{author}"
                
        filename = f"reel_{index}{author_suffix}_{timestamp}.md"
        filepath = os.path.join(target_folder, filename)
        
        # Write transcript to Markdown file
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"# Reel #{index} Transcript\n\n")
            if meta:
                f.write(f"- **Source URL**: [{meta.get('url', 'Link')}]({meta.get('url', '')})\n")
                f.write(f"- **Title**: {meta.get('title', 'N/A')}\n")
                f.write(f"- **Author**: {meta.get('author', 'N/A')}\n")
            f.write(f"- **Duration**: {duration:.2f} seconds\n")
            f.write(f"- **Processed At**: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("---\n\n")
            f.write(text + "\n")
            
        print(f"[success] Segment #{index} completed! Saved to:\n{filepath}")
        
    except Exception as e:
        print(f"[error] Failed to process segment #{index}: {e}")
    finally:
        if os.path.exists(temp_wav):
            try:
                os.remove(temp_wav)
            except Exception:
                pass

def main():
    global webhook_trigger, current_reel_metadata
    
    # Start the webhook server in background
    start_webhook_server()

    # 1. Ask for output folder and check for --reels flag
    reels_mode = False
    silence_mode = True
    
    if "--reels" in sys.argv:
        reels_mode = True
        sys.argv.remove("--reels")
    else:
        choice = input("Enable Reels Mode (record/transcribe multiple reels sequentially)? (y/n) [default: n]: ").strip().lower()
        if choice == 'y':
            reels_mode = True

    if reels_mode:
        if "--no-silence" in sys.argv:
            silence_mode = False
            sys.argv.remove("--no-silence")
        else:
            choice = input("Enable automatic silence splitting? (y/n) [default: y]: ").strip().lower()
            if choice == 'n':
                silence_mode = False

    if len(sys.argv) > 1:
        target_folder = sys.argv[1].strip()
    else:
        target_folder = input("Enter output folder path for the transcript: ").strip()
        
    if not target_folder:
        target_folder = "transcripts"
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    if not os.path.isabs(target_folder):
        target_folder = os.path.abspath(os.path.join(script_dir, target_folder))
    
    os.makedirs(target_folder, exist_ok=True)
    print(f"[info] Transcripts will be saved to: {target_folder}")

    # 2. Load local OpenAI Whisper base model
    print("[info] Loading local OpenAI Whisper 'base' model (runs offline)...")
    model = whisper.load_model("base")

    # 3. Select Audio Device
    device_idx = select_audio_device()
    if device_idx is None:
        print("[error] No input device selected or available. Exiting.")
        return

    device_info = sd.query_devices(device_idx, 'input')
    samplerate = int(device_info['default_samplerate'])
    channels = 1 

    print(f"\n[info] Selected device: {device_info['name']}")
    print(f"[info] Sample rate: {samplerate} Hz, Channels: {channels}")

    # Reset metadata state
    current_reel_metadata = None
    webhook_trigger = False

    audio_data = []
    split_timestamps = []  # List of tuples: (seconds, metadata)
    
    start_time = time.time()
    has_played = False
    silence_start_time = None
    recording_active = True

    # 4. Background splits monitor thread
    def monitor_splits():
        global webhook_trigger, current_reel_metadata
        nonlocal has_played, silence_start_time
        
        # Give it a small warm-up time
        time.sleep(0.5)
        
        last_split_time = 0.0
        MIN_REEL_DURATION = 10.0 # Minimum seconds between splits to ignore internal speaker pauses
        
        while recording_active:
            time.sleep(0.05)
            
            # 1. Check Webhook Trigger from Browser Scroll
            if webhook_trigger:
                webhook_trigger = False
                elapsed = time.time() - start_time
                print(f"\n[split] Webhook received at {elapsed:.2f}s (Browser scroll)")
                split_timestamps.append((elapsed, current_reel_metadata))
                last_split_time = elapsed
                current_reel_metadata = None
                has_played = False
                silence_start_time = None
                
            # 2. Check Silence Detection (if in reels_mode and silence_mode enabled)
            if reels_mode and len(audio_data) > 0:
                latest_chunk = audio_data[-1]
                rms = np.sqrt(np.mean(latest_chunk**2))
                
                # Live VU Volume Bar in console
                bars = int(rms * 40)
                if bars > 20: bars = 20
                bar_str = "█" * bars + "░" * (20 - bars)
                sys.stdout.write(f"\r[hearing] Volume: [{bar_str}] (RMS: {rms:.4f})  ")
                sys.stdout.flush()
                
                if silence_mode:
                    if rms > 0.008:
                        has_played = True
                        silence_start_time = None
                    elif has_played:
                        if silence_start_time is None:
                            silence_start_time = time.time()
                        elif time.time() - silence_start_time > 0.7:  # 0.7 seconds silence
                            elapsed = time.time() - start_time
                            split_point = elapsed - 0.7
                            
                            # Only register silence split if we have recorded at least MIN_REEL_DURATION
                            if split_point - last_split_time >= MIN_REEL_DURATION:
                                print(f"\n[split] Silence detected at {split_point:.2f}s (Auto-split)")
                                split_timestamps.append((split_point, None))
                                last_split_time = split_point
                            
                            has_played = False
                            silence_start_time = None

    monitor_thread = threading.Thread(target=monitor_splits, daemon=True)

    def callback(indata, frames, time_info, status):
        if status:
            print(status, file=sys.stderr)
        audio_data.append(indata.copy())

    # 5. Start continuous InputStream
    print(f"\n==========================================")
    print(f"             RECORDING SESSION             ")
    print(f"==========================================")
    if reels_mode:
        print("[info] Play your reels. The script will record continuously and log splits.")
    else:
        print("[info] Recording continuously in a single segment.")
    print("Press Enter to STOP the entire session and start processing.")

    try:
        monitor_thread.start()
        with sd.InputStream(samplerate=samplerate, device=device_idx, channels=channels, callback=callback):
            input()  # Wait for user to press Enter to stop the entire session
    except KeyboardInterrupt:
        print("\n[info] Recording ended by user interrupt.")
    finally:
        recording_active = False

    print("\n[info] Recording stopped. Preparing to process audio segments...")

    if not audio_data:
        print("[info] No audio recorded.")
        return

    # Concatenate continuous audio stream
    full_audio = np.concatenate(audio_data, axis=0)
    total_duration = len(full_audio) / samplerate
    print(f"[info] Total session recording duration: {total_duration:.2f} seconds")

    # 6. Slice and Process segments
    if not reels_mode or not split_timestamps:
        # Single transcript mode, or no splits occurred
        process_and_transcribe_slice(full_audio, samplerate, target_folder, 1, None, model)
    else:
        # Reels Mode: slice audio by recorded timestamps
        split_timestamps = sorted(list(set(split_timestamps)), key=lambda x: x[0])
        
        filtered_splits = []
        last_t = 0.0
        for t, meta in split_timestamps:
            if t - last_t > 1.5 and t < total_duration:
                filtered_splits.append((t, meta))
                last_t = t

        # Append final boundary (end of audio)
        filtered_splits.append((total_duration, None))
        
        print(f"[info] Slicing continuous audio into {len(filtered_splits)} segments...")
        
        start_sample = 0
        segment_index = 1
        
        for t, meta in filtered_splits:
            end_sample = int(t * samplerate)
            if end_sample > start_sample:
                audio_slice = full_audio[start_sample:end_sample]
                process_and_transcribe_slice(audio_slice, samplerate, target_folder, segment_index, meta, model)
                start_sample = end_sample
                segment_index += 1

    print("\n[info] All segments processed. Goodbye!")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nExiting script. Goodbye!")
        sys.exit(0)
