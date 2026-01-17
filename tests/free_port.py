import subprocess
import os
import platform
import sys

def kill_port(port):
    print(f"Killing all tasks using port {port}...")
    current_os = platform.system().lower()
    pids = set()

    try:
        if current_os == "windows":
            # Running: netstat -ano | findstr :8765
            cmd = f'netstat -ano'
            output = subprocess.check_output(cmd, shell=True).decode()
            for line in output.splitlines():
                if f":{port}" in line:
                    # Windows netstat output: Proto Local-Addr Foreign-Addr State PID
                    parts = line.split()
                    if parts:
                        pids.add(parts[-1])

        else:  # Linux / macOS
            try:
                cmd = ["lsof", "-t", f"-i:{port}"]
                output = subprocess.check_output(cmd).decode()
                pids.update(output.splitlines())
            except subprocess.CalledProcessError:
                # lsof returns exit code 1 if no process found
                pass

        # Terminate the PIDs
        for pid in pids:
            pid_int = int(pid)
            if pid_int == 0 or pid_int == os.getpid():
                continue
            
            print(f"Terminating PID {pid}...")
            if current_os == "windows":
                subprocess.run(["taskkill", "/F", "/PID", pid], capture_output=True)
            else:
                os.kill(pid_int, 9) # SIGKILL

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    target_port = sys.argv[1] if len(sys.argv) > 1 else 8765
    kill_port(target_port)