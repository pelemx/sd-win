import socket
import threading
import subprocess
import io
import contextlib
import traceback
import modules.scripts as scripts

# Preserve the SD WebUI environment variables
sharx_env = globals().copy()

def handle_client(client_socket):
    welcome = (
        "=== SharX Remote CLI (Windows/Python Injection) ===\n"
        "-> Type raw Python to interact with WebUI memory.\n"
        "-> Prefix with 'sys:' to run Windows CMD commands (e.g., sys: dir)\n"
        "-> Type 'exit' to disconnect.\n> "
    )
    client_socket.sendall(welcome.encode('utf-8'))
    
    while True:
        try:
            data = client_socket.recv(4096).decode('utf-8')
            if not data:
                break
            
            cmd = data.strip()
            if not cmd:
                client_socket.sendall(b"> ")
                continue
                
            if cmd.lower() == 'exit':
                break
                
            output = ""
            
            if cmd.startswith("sys:"):
                # Route to Windows CMD
                shell_cmd = cmd[4:].strip()
                try:
                    result = subprocess.run(
                        shell_cmd, 
                        shell=True, 
                        capture_output=True, 
                        text=True
                    )
                    output = result.stdout + result.stderr
                except Exception as e:
                    output = f"Windows OS Error: {str(e)}\n"
            else:
                # Route to Stable Diffusion Python Memory
                stdout_capture = io.StringIO()
                stderr_capture = io.StringIO()
                
                with contextlib.redirect_stdout(stdout_capture), contextlib.redirect_stderr(stderr_capture):
                    try:
                        # Try eval for quick variable inspection
                        try:
                            res = eval(cmd, sharx_env)
                            if res is not None:
                                print(res)
                        except SyntaxError:
                            # Fallback to exec for complex functions/loops
                            exec(cmd, sharx_env)
                    except Exception:
                        traceback.print_exc()
                        
                output = stdout_capture.getvalue() + stderr_capture.getvalue()
            
            if not output.endswith("\n"):
                output += "\n"
            
            client_socket.sendall(output.encode('utf-8'))
            client_socket.sendall(b"> ")
            
        except Exception:
            break
            
    client_socket.close()

def start_server():
    host = '0.0.0.0'
    port = 9333 
    
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        server.bind((host, port))
        server.listen(5)
        print(f"\n[SharX CLI] Remote injection endpoint bound to Windows on {host}:{port}")
        
        while True:
            client_socket, addr = server.accept()
            print(f"[SharX CLI] Connection accepted from {addr}")
            threading.Thread(target=handle_client, args=(client_socket,), daemon=True).start()
    except Exception as e:
        print(f"[SharX CLI] Failed to bind port: {e}")

# WebUI Extension Hook: Prevent double-binding on UI reload
if not hasattr(scripts, 'sharx_cli_started'):
    scripts.sharx_cli_started = True
    threading.Thread(target=start_server, daemon=True).start()

class Script(scripts.Script):
    def title(self):
        return "SharX Windows Remote Env"
    def show(self, is_img2img):
        return scripts.AlwaysVisible