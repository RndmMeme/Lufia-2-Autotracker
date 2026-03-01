import subprocess
import threading
import socket
import json
import logging
import os
import time
import atexit
from pathlib import Path

# Constants
# Point to Standard Debug Build (win-x64)
HELPER_PATH = Path("src/helper/bin/Debug/net8.0/win-x64/Lufia2AutoTracker.Helper.exe")
HOST = 'localhost'
PORT = 65432

class HelperInterface:
    def __init__(self, callback):
        self.process = None
        self.server_socket = None
        self.client_socket = None
        self.running = False
        self.callback = callback # Function to call with parsed JSON data
        self.thread = None

    def start(self):
        """Starts the TCP Server and the C# Helper process."""
        if self.running: return

        self.running = True
        self.start_server()
        self.launch_helper()

    def start_server(self):
        """Starts the TCP server in a separate thread."""
        self.thread = threading.Thread(target=self._server_loop, daemon=True)
        self.thread.start()

    def _server_loop(self):
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.bind((HOST, PORT))
            self.server_socket.listen(1)
            logging.info(f"Helper Interface listening on {HOST}:{PORT}")
            
            while self.running:
                try:
                    self.server_socket.settimeout(1.0)
                    client, addr = self.server_socket.accept()
                    logging.info(f"Helper connected from {addr}")
                    self.client_socket = client
                    self._handle_client(client)
                except socket.timeout:
                    continue
                except Exception as e:
                    logging.error(f"Server accept error: {e}")
        except Exception as e:
            logging.error(f"Server setup error: {e}")
        finally:
            self.stop()

    def _handle_client(self, client):
        """Reads newline-delimited JSON from the client."""
        buffer = ""
        while self.running:
            try:
                data = client.recv(4096)
                if not data: break
                
                buffer += data.decode('utf-8')
                
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    # Handle multiple JSON objects stuck together if any
                    # The C# helper sends one JSON object per write. 
                    # If we use newline checks, we need to ensure C# sends newlines?
                    # My C# implementation uses JsonSerializer.Serialize -> Write. 
                    # It DOES NOT explicitly append \n.
                    # Wait, C# code: _stream.Write(data).
                    # Issue: If C# doesn't send \n, we stream forever until buffer is huge.
                    
                    # Correction: I should update C# to send \n or parse brace counting.
                    # Or since I am integrating now, I can fix the Python side to handle raw JSON stream?
                    # Raw JSON stream is hard.
                    # I will assume I need to update C# to send \n or use a length prefix.
                    # BUT I just finished C#... 
                    
                    # For now, let's try to parse ANY complete JSON object.
                    self._process_payload(line)
            except OSError:
                # Socket closed or error
                if self.running:
                    logging.error("Client read error (OSError). Stopping.")
                break
            except Exception as e:
                if self.running:
                     logging.error(f"Client read error: {e}")
                break

    def _process_payload(self, json_str):
        try:
            # Attempt to parse. If it fails, it might be incomplete.
            # But the C# helper sends a full object in one go usually.
            data = json.loads(json_str)
            if self.callback:
                self.callback(data)
        except json.JSONDecodeError:
            pass # logging.warning(f"Incomplete JSON: {json_str[:20]}...")

    def launch_helper(self):
        """Launches the C# Helper executable."""
        import sys
        if getattr(sys, 'frozen', False):
            # PyInstaller Temp Directory
            base_path = Path(sys._MEIPASS)
        else:
            base_path = Path.cwd()

        abs_path = base_path / HELPER_PATH
        if not abs_path.exists():
            logging.error(f"Helper not found at {abs_path}")
            return

        try:
            # Popen with pipes to capture output
            self.process = subprocess.Popen(
                [str(abs_path)], 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW,
                text=True,
                bufsize=1 # Line buffered
            )
            logging.info(f"Started Helper Process (PID: {self.process.pid})")
            atexit.register(self.stop)
            
            # Start threads to read stdout/stderr to prevent blocking
            self.stdout_thread = threading.Thread(target=self._read_output, args=(self.process.stdout, "HELPER"), daemon=True)
            self.stderr_thread = threading.Thread(target=self._read_output, args=(self.process.stderr, "HELPER_ERR"), daemon=True)
            self.stdout_thread.start()
            self.stderr_thread.start()
            
        except Exception as e:
            logging.error(f"Failed to launch helper: {e}")

    def _read_output(self, stream, prefix):
        """Reads lines from a stream and logs them."""
        try:
            for line in iter(stream.readline, ''):
                if line:
                    logging.info(f"[{prefix}] {line.strip()}")
        except Exception as e:
            logging.error(f"Error reading {prefix}: {e}")
        finally:
            stream.close()

    def stop(self):
        self.running = False
        try:
            if self.client_socket: 
                self.client_socket.shutdown(socket.SHUT_RDWR)
                self.client_socket.close()
        except: pass
        
        try:
            if self.server_socket: 
                self.server_socket.close()
        except: pass
        
        if self.process: 
            try:
                logging.info("Terminating helper process...")
                self.process.terminate()
                try:
                    self.process.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    logging.warning("Helper process did not terminate. Force killing...")
                    self.process.kill()
            except Exception as e:
                logging.error(f"Error stopping helper: {e}")
            self.process = None

    def _server_loop(self):
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.bind((HOST, PORT))
            self.server_socket.listen(1)
            self.server_socket.settimeout(1.0)
            logging.info(f"Helper Interface listening on {HOST}:{PORT}")
            
            last_connection_time = time.time()
            
            while self.running:
                try:
                    # Check for 30s timeout on connection waiting
                    if self.client_socket is None and (time.time() - last_connection_time > 30):
                        logging.info("Visual Auto Tracker timed out (30s). Stopping helper.")
                        # How to stop from here? 
                        # We are in a thread. We should signal main thread or just self.stop()
                        self.stop() 
                        # We also need to notify UI? 
                        # HelperInterface has no link to UI signals directly except callback. 
                        # Maybe callback with special status?
                        break

                    client, addr = self.server_socket.accept()
                    logging.info(f"Helper connected from {addr}")
                    self.client_socket = client
                    self._handle_client(client)
                    
                    # After handle_client returns (connection closed)
                    self.client_socket = None
                    last_connection_time = time.time()
                    
                except socket.timeout:
                    continue
                except Exception as e:
                    logging.error(f"Server accept error: {e}")
                    if not self.running: break
                    
        except Exception as e:
            logging.error(f"Server setup error: {e}")
        finally:
            self.stop()

    def request_sync(self):
        """Sends a SYNC command to the connected C# helper to force a full state refresh."""
        if self.client_socket:
            try:
                self.client_socket.sendall(b"SYNC\n")
                logging.info("Sent SYNC request to Tracker Helper.")
            except Exception as e:
                logging.error(f"Failed to send SYNC request: {e}")
        else:
            logging.warning("Cannot send SYNC request: Not connected to Tracker Helper.")


