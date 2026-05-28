import asyncio
import time
import re
import threading

# ---------------------------------------------------------
# DUMMY EXTERNAL API PLACEHOLDERS
# ---------------------------------------------------------
class DummyVAD:
    def is_speech(self, frame: bytes) -> bool:
        # Dummy implementation
        return False

class DummySTT:
    async def transcribe_stream(self, audio_queue: asyncio.Queue):
        # Yield dummy transcriptions
        yield "Hello, how are you today?"

class DummyLLM:
    async def generate_stream(self, prompt: str):
        # Yield dummy tokens
        tokens = ["I", " am", " an", " AI", " assistant,", " here", " to", " help", " you", " with", " whatever", " you", " need."]
        for token in tokens:
            await asyncio.sleep(0.05) # Simulate network latency
            yield token

class DummyTTS:
    async def generate_audio_stream(self, text: str):
        # Yield dummy PCM audio bytes
        await asyncio.sleep(0.2) # Simulate TTFA latency
        yield b'\x00' * 1024


# ---------------------------------------------------------
# BACKGROUND AUDIO PLAYER (Dedicated Thread)
# ---------------------------------------------------------
def audio_playback_worker(playback_queue: queue.Queue, stop_event: threading.Event):
    """
    Dedicated background thread for non-blocking PyAudio/SoundDevice playback.
    """
    # Example PyAudio initialization:
    # p = pyaudio.PyAudio()
    # stream = p.open(format=pyaudio.paInt16, channels=1, rate=24000, output=True)
    
    print("[Player] Audio playback thread started.")
    while not stop_event.is_set():
        try:
            # Block until audio chunk is available
            pcm_chunk = playback_queue.get(timeout=0.1)
            if pcm_chunk is None:
                continue
            
            # stream.write(pcm_chunk)
            # print(f"[Player] Played {len(pcm_chunk)} bytes.")
            playback_queue.task_done()
        except queue.Empty:
            continue
        except Exception as e:
            print(f"[Player Error] {e}")


# ---------------------------------------------------------
# ORCHESTRATION ENGINE
# ---------------------------------------------------------
import queue

class VoiceConversationManager:
    def __init__(self):
        # Async Queues
        self.audio_in_queue = asyncio.Queue()
        self.stt_text_queue = asyncio.Queue()
        self.llm_text_queue = asyncio.Queue()
        
        # Thread-safe queue for the synchronous audio playback thread
        self.playback_queue = queue.Queue()
        
        # Interruption & State
        self.is_speaking = False
        self.interrupt_event = asyncio.Event()
        self.shutdown_event = asyncio.Event()
        
        # API Clients
        self.vad = DummyVAD()
        self.stt = DummySTT()
        self.llm = DummyLLM()
        self.tts = DummyTTS()

        # Audio Threading
        self.player_stop_event = threading.Event()
        self.player_thread = threading.Thread(
            target=audio_playback_worker, 
            args=(self.playback_queue, self.player_stop_event),
            daemon=True
        )

    def trigger_interruption(self):
        """Immediately clear all downstream queues and halt TTS playback."""
        print("\n[VAD] 🛑 INTERRUPTION DETECTED! Clearing pipelines...")
        self.interrupt_event.set()
        
        # Clear async queues
        while not self.llm_text_queue.empty():
            self.llm_text_queue.get_nowait()
            
        # Clear synchronous playback buffer
        with self.playback_queue.mutex:
            self.playback_queue.queue.clear()
            
        self.is_speaking = False

    async def listen_and_vad_worker(self):
        """
        Simulates inbound WebRTC/WebSocket audio streaming with aggressive VAD.
        Turn-completion threshold: 400ms-500ms.
        """
        print("[Engine] 🎤 VAD & Listen Worker started.")
        silence_start = None
        silence_threshold = 0.45  # 450ms aggressive turn detection
        
        while not self.shutdown_event.is_set():
            # Simulate receiving audio bytes from WebSocket
            await asyncio.sleep(0.02)
            frame = b'\x00' * 512 
            is_speech = self.vad.is_speech(frame)
            
            if is_speech:
                # If user speaks while AI is speaking -> INTERRUPT
                if self.is_speaking and not self.interrupt_event.is_set():
                    self.trigger_interruption()
                
                silence_start = None
                await self.audio_in_queue.put(frame)
            else:
                if silence_start is None:
                    silence_start = time.perf_counter()
                elif (time.perf_counter() - silence_start) > silence_threshold:
                    # Turn complete! Trigger STT (simulated)
                    if not self.audio_in_queue.empty():
                        print("\n[VAD] 🏁 Turn completed (450ms silence). Dispatching to STT.")
                        # Empty the inbound queue to simulate passing to STT
                        while not self.audio_in_queue.empty():
                            self.audio_in_queue.get_nowait()
                            
                        # Simulate STT returning a transcript
                        transcript = "Hello, how are you today?"
                        await self.stt_text_queue.put((transcript, time.perf_counter()))
                    
                    silence_start = None

    async def chunking_bridge(self, token_stream, stt_end_time):
        """
        Groups LLM tokens into logical chunks (4-8 words, or punctuation).
        Instantly yields chunks to TTS.
        """
        buffer = ""
        word_count = 0
        first_token_time = None
        
        async for token in token_stream:
            if self.interrupt_event.is_set():
                break
                
            if first_token_time is None:
                first_token_time = time.perf_counter()
                print(f"[Metrics] ⏱️ STT to First Token (TTFT): {(first_token_time - stt_end_time) * 1000:.2f} ms")
                
            buffer += token
            word_count += len(token.split())
            
            # Flush chunk on punctuation OR if word count > 6
            if re.search(r'[.,!?]\s*$', buffer) or word_count >= 6:
                chunk = buffer.strip()
                if chunk:
                    await self.llm_text_queue.put(chunk)
                buffer = ""
                word_count = 0
                
        # Flush remaining
        if buffer.strip() and not self.interrupt_event.is_set():
            await self.llm_text_queue.put(buffer.strip())

    async def llm_streaming_worker(self):
        """
        Waits for STT transcripts, hits the LLM endpoint, and streams tokens.
        """
        print("[Engine] 🧠 LLM Streaming Worker started.")
        while not self.shutdown_event.is_set():
            try:
                transcript, stt_end_time = await asyncio.wait_for(self.stt_text_queue.get(), timeout=1.0)
                
                print(f"[LLM] User said: '{transcript}'")
                self.interrupt_event.clear()
                
                # Start LLM stream
                token_stream = self.llm.generate_stream(transcript)
                
                # Bridge tokens to TTS
                await self.chunking_bridge(token_stream, stt_end_time)
                
                # Signal end of stream for this turn
                await self.llm_text_queue.put(None) 
                
            except asyncio.TimeoutError:
                continue

    async def tts_streaming_worker(self):
        """
        Consumes text chunks from the LLM, hits the TTS endpoint, 
        and pushes raw PCM bytes to the PyAudio background thread.
        """
        print("[Engine] 🗣️ TTS Streaming Worker started.")
        while not self.shutdown_event.is_set():
            try:
                text_chunk = await asyncio.wait_for(self.llm_text_queue.get(), timeout=1.0)
                
                if text_chunk is None:
                    continue # End of turn
                if self.interrupt_event.is_set():
                    continue # Drop chunk
                    
                self.is_speaking = True
                print(f"[TTS] Synthesizing chunk: '{text_chunk}'")
                
                tts_start = time.perf_counter()
                first_byte_received = False
                
                # Stream audio bytes from TTS provider
                async for pcm_bytes in self.tts.generate_audio_stream(text_chunk):
                    if self.interrupt_event.is_set():
                        break
                        
                    if not first_byte_received:
                        first_byte_received = True
                        print(f"[Metrics] ⏱️ Text Chunk to First Audio Byte: {(time.perf_counter() - tts_start) * 1000:.2f} ms")
                        
                    # Push bytes to the synchronous audio player thread
                    self.playback_queue.put(pcm_bytes)
                    
            except asyncio.TimeoutError:
                continue

    async def start(self):
        """Launches the orchestration engine."""
        self.player_thread.start()
        
        # Run all workers concurrently
        await asyncio.gather(
            self.listen_and_vad_worker(),
            self.llm_streaming_worker(),
            self.tts_streaming_worker()
        )
        
    def stop(self):
        self.shutdown_event.set()
        self.player_stop_event.set()
        self.player_thread.join()

# ---------------------------------------------------------
# ENTRY POINT
# ---------------------------------------------------------
if __name__ == "__main__":
    engine = VoiceConversationManager()
    
    # Simulate a user speaking instantly to test the pipeline flow
    async def simulate_user():
        await asyncio.sleep(1)
        engine.vad.is_speech = lambda x: True
        await asyncio.sleep(0.5)
        engine.vad.is_speech = lambda x: False
        
        # Wait for TTS to finish, then simulate an interrupt
        await asyncio.sleep(2)
        print("\n--- SIMULATING USER INTERRUPTION ---")
        engine.vad.is_speech = lambda x: True
        await asyncio.sleep(0.1)
        engine.vad.is_speech = lambda x: False
        
        await asyncio.sleep(1)
        engine.stop()

    async def run():
        await asyncio.gather(engine.start(), simulate_user())

    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        engine.stop()
