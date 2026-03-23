import os
import json
import base64
import subprocess
import traceback
import time
import uuid
import shutil
import threading
from channels.generic.websocket import WebsocketConsumer
from django.conf import settings
# NOTE: Transcription is now the responsibility of services/FasterWhisper.py
# This consumer only saves incoming audio files/chunks and notifies the frontend
# when FasterWhisper.py produces the transcript files (.txt / .json).

class ChatConsumer(WebsocketConsumer):
    def connect(self):
        try:
            print("ChatConsumer.connect() called")
            audio_dir = os.path.join(settings.BASE_DIR, 'Jarvis', 'services', 'audio')
            os.makedirs(audio_dir, exist_ok=True)
            self.AUDIO_DIR = audio_dir

            # état de session de transcription en streaming
            self.session_id = None
            self.session_list = None
            self.session_out = None
            self.session_base = None
            self.session_active = False
            self.session_thread = None

            # buffer pour enregistrement complet envoyé depuis le front (raw blob)
            self.audio_buffer = b""

            # no transcription here

            self.accept()
            print("ChatConsumer: accepted, AUDIO_DIR=", self.AUDIO_DIR)
        except Exception as e:
            print("ChatConsumer.connect() error:", repr(e))
            traceback.print_exc()
            try: self.close()
            except: pass

    def _start_session_if_needed(self):
        if self.session_active:
            return
        self.session_id = str(uuid.uuid4())[:8]
        ts = int(time.time())
        self.session_base = f"recording_{ts}_{self.session_id}"
        self.session_list = os.path.join(self.AUDIO_DIR, f"{self.session_base}_list.txt")
        self.session_out  = os.path.join(self.AUDIO_DIR, f"{self.session_base}.wav")
        # create empty list file
        with open(self.session_list, "w", encoding="utf-8") as f:
            f.write("") 
        self.session_active = True

        # Note: We don't transcribe here. When recording is completed the consumer
        # will create the final audio file (session_out) and FasterWhisper.py (watcher)
        # will detect it and produce .txt/.json. The consumer will wait for that output
        # and forward it to the frontend.

    def receive(self, text_data=None, bytes_data=None):
        try:
            if bytes_data:
                # message binaire: 4 bytes little-endian header length, then header JSON, then audio bytes
                try:
                    header_len = int.from_bytes(bytes_data[:4], 'little')
                    header_json = bytes_data[4:4+header_len].decode('utf-8')
                    header = json.loads(header_json)
                except Exception as e:
                    print("Erreur parsing header bytes:", repr(e))
                    return

                audio_bytes = bytes_data[4+header_len:]
                return self.handle_audio_bytes(header, audio_bytes)

            data = json.loads(text_data) if text_data else {}
            msg_type = data.get('type')

            if msg_type == 'audio_chunk':
                self.handle_audio_chunk(data)
            elif msg_type == 'recording_complete':
                self.handle_recording_complete(data)
            else:
                self.send(text_data=f"Le server a capté: {text_data}")
        except json.JSONDecodeError:
            self.send(text_data=f"Le server a capté que vous avez dit: {text_data}")

    def handle_audio_bytes(self, header, audio_bytes):
        try:
            # support both chunked streaming and full recording from frontend
            msg_type = header.get('type', 'audio_chunk')

            if msg_type == 'full_recording':
                # accumulate the whole recording (single message expected from frontend)
                self.audio_buffer += audio_bytes

                # write temp file
                temp_name = header.get('filename', f"recording_{int(time.time())}.webm")
                temp_path = os.path.join(self.AUDIO_DIR, temp_name)
                try:
                    with open(temp_path, "wb") as f:
                        f.write(self.audio_buffer)
                    print(f"Saved full recording to {temp_path}")
                except Exception as e:
                    print("Erreur écriture full recording:", repr(e))
                    self.send(text_data=json.dumps({'type': 'error', 'message': 'Échec sauvegarde enregistrement'}))
                    return

                # Reset buffer and then wait for external transcription result.
                self.audio_buffer = b""
                # Start a waiter thread that will poll for FasterWhisper output (.json/.txt)
                base = os.path.splitext(os.path.basename(temp_path))[0]
                # allow more time for transcription (e.g. 120s)
                threading.Thread(target=self._wait_and_forward_transcript, args=(base, temp_path, 120), daemon=True).start()
                return

            # fallback: old chunk handling
            chunk_index = header.get('chunk_index', 0)
            orig_name = header.get('chunk_name', f'audio_chunk_{chunk_index}.webm')

            # ensure extension
            name_root, ext = os.path.splitext(orig_name)
            if not ext:
                ext = '.webm'
                orig_name = f"{name_root}{ext}"

            saved_path = os.path.join(self.AUDIO_DIR, orig_name)
            os.makedirs(os.path.dirname(saved_path), exist_ok=True)
            with open(saved_path, 'wb') as f:
                f.write(audio_bytes)

            print(f"Saved chunk to {saved_path}")

            # conversion et pipeline existant (réutilise la logique de try_convert)
            name_root, _ = os.path.splitext(orig_name)
            wav_name = f"{name_root}_{chunk_index}.wav"
            wav_path = os.path.join(self.AUDIO_DIR, wav_name)

            def try_convert(src, dst, attempts=3, delay=0.3):
                ffmpeg_path = shutil.which("ffmpeg") or shutil.which("ffmpeg.exe")
                if not ffmpeg_path:
                    print("ffmpeg introuvable dans le PATH — installez ffmpeg et ajoutez-le au PATH.")
                    return False
                try:
                    size = os.path.getsize(src)
                    if size < 1000:
                        print(f"Fichier trop petit pour conversion ({size} bytes): {src}")
                        return False
                except OSError:
                    pass

                cmds = [
                    [ffmpeg_path, '-y', '-hide_banner', '-loglevel', 'error', '-i', src, '-ac', '1', '-ar', '16000', '-c:a', 'pcm_s16le', dst],
                    [ffmpeg_path, '-y', '-hide_banner', '-loglevel', 'error', '-f', 'webm', '-i', src, '-ac', '1', '-ar', '16000', '-c:a', 'pcm_s16le', dst],
                    [ffmpeg_path, '-y', '-hide_banner', '-loglevel', 'error', '-i', src, '-vn', '-acodec', 'pcm_s16le', '-ar', '16000', '-ac', '1', dst],
                ]
                for attempt in range(attempts):
                    for cmd in cmds:
                        try:
                            proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                            print(f"ffmpeg rc={proc.returncode} cmd={' '.join(cmd)}")
                            if proc.stderr:
                                print("ffmpeg stderr:", proc.stderr[:400])
                            if proc.returncode == 0 and os.path.exists(dst) and os.path.getsize(dst) > 0:
                                return True
                        except Exception as e:
                            print("ffmpeg subprocess error:", repr(e))
                        time.sleep(delay)
                return False

            converted = try_convert(saved_path, wav_path)
            if converted:
                try:
                    os.remove(saved_path)
                except:
                    pass
                saved_file_for_transcription = wav_path
            else:
                saved_file_for_transcription = saved_path
                print(f"Conversion failed for {saved_path}, keeping original.")

            # démarrer session si besoin et ajouter à la liste pour concat
            self._start_session_if_needed()
            safe_path = saved_file_for_transcription.replace('\\', '/')
            try:
                with open(self.session_list, "a", encoding="utf-8") as lf:
                    lf.write(f"file '{safe_path}'\n")
            except Exception as e:
                print("Erreur ajout fichier liste:", repr(e))

            self.send(text_data=json.dumps({
                'type': 'chunk_received',
                'chunk_index': chunk_index,
                'status': 'success',
                'chunk_name': orig_name,
                'wav_name': os.path.basename(saved_file_for_transcription),
                'message': f'Chunk {chunk_index} reçu et sauvegardé en {os.path.splitext(saved_file_for_transcription)[1].lstrip(".")}'
            }))
        except Exception as e:
            print("handle_audio_bytes error:", repr(e))
            traceback.print_exc()
            self.send(text_data=json.dumps({
                'type': 'chunk_error',
                'error': str(e)
            }))

    def handle_recording_complete(self, data):
        total_chunks = data.get('total_chunks', 0)
        # Create final concatenated audio file for this session so FasterWhisper.py can transcribe it.
        try:
            self.session_active = False
            ffmpeg_path = shutil.which("ffmpeg") or shutil.which("ffmpeg.exe")
            if ffmpeg_path and os.path.exists(self.session_list):
                # transcode while concatenating to ensure a consistent wav file
                cmd = [ffmpeg_path, '-y', '-hide_banner', '-loglevel', 'error',
                       '-f', 'concat', '-safe', '0', '-i', self.session_list,
                       '-ac', '1', '-ar', '16000', '-c:a', 'pcm_s16le', self.session_out]
                proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                if proc.returncode != 0:
                    print("ffmpeg concat failed:", proc.stderr[:400])
                else:
                    # ensure output exists and is not empty
                    if not os.path.exists(self.session_out) or os.path.getsize(self.session_out) == 0:
                        print("ffmpeg produced empty output or missing file:", self.session_out)
            # notify frontend that recording saved and that transcription will follow
            self.send(text_data=json.dumps({
                'type': 'recording_saved',
                'total_chunks': total_chunks,
                'message': f'Enregistrement complet: {total_chunks} chunks',
                'session': self.session_base if self.session_base else None,
                'audio_file': os.path.basename(self.session_out)
            }))
            # start waiter thread to forward the transcript produced by FasterWhisper.py
            base = os.path.splitext(os.path.basename(self.session_out))[0]
            # allow more time for transcription (long files / CPU)
            threading.Thread(target=self._wait_and_forward_transcript, args=(base, self.session_out, 120), daemon=True).start()
        except Exception as e:
            print("handle_recording_complete error:", repr(e))
            self.send(text_data=json.dumps({'type': 'error', 'message': 'Erreur finalisation enregistrement'}))

    def disconnect(self, close_code):
        # s'assurer d'arrêter la session si la connexion se ferme
        self.session_active = False
        if self.session_thread and self.session_thread.is_alive():
            self.session_thread.join(timeout=2.0)
        pass

    def _wait_and_forward_transcript(self, base, audio_path, timeout=30, poll_interval=0.8):
        """
        Poll for base.json or base.txt produced by FasterWhisper.py and forward to WebSocket.
        """
        json_path = os.path.join(self.AUDIO_DIR, f"{base}.json")
        txt_path = os.path.join(self.AUDIO_DIR, f"{base}.txt")
        start = time.time()
        while time.time() - start < timeout:
            try:
                if os.path.exists(json_path):
                    with open(json_path, "r", encoding="utf-8") as jf:
                        meta = json.load(jf)
                    text = meta.get("text", "")
                    txt_file = meta.get("transcript_file") or os.path.basename(txt_path)
                    self.send(text_data=json.dumps({
                        'type': 'final_transcript',
                        'session': base,
                        'text': text,
                        'audio_file': os.path.basename(audio_path),
                        'txt_file': txt_file,
                        'meta': meta
                    }))
                    return
                if os.path.exists(txt_path):
                    with open(txt_path, "r", encoding="utf-8") as tf:
                        text = tf.read()
                    self.send(text_data=json.dumps({
                        'type': 'final_transcript',
                        'session': base,
                        'text': text,
                        'audio_file': os.path.basename(audio_path),
                        'txt_file': os.path.basename(txt_path)
                    }))
                    return
            except Exception as e:
                print("wait_and_forward error:", repr(e))
            time.sleep(poll_interval)
        # timeout -> notify frontend
        try:
            self.send(text_data=json.dumps({
                'type': 'transcript_timeout',
                'session': base,
                'audio_file': os.path.basename(audio_path),
                'message': 'Aucun transcript trouvé dans le délai imparti'
            }))
        except:
            pass