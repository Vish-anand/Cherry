import subprocess
import os

def kill_process_on_port(port):
    print(f"Scanning for active processes on port {port}...")
    try:
        # Find process IDs using netstat
        result = subprocess.run(["netstat", "-ano"], capture_output=True, text=True, check=True)
        pids_to_kill = set()
        
        for line in result.stdout.splitlines():
            # Check for local address matches on port
            if f":{port}" in line:
                parts = line.strip().split()
                if len(parts) >= 5:
                    # The last element in netstat -ano output is the PID
                    pid = parts[-1]
                    # Ensure it is a valid PID (numeric) and not 0 (System Idle Process)
                    if pid.isdigit() and pid != "0":
                        pids_to_kill.add(pid)
        
        if not pids_to_kill:
            print(f"No active process found listening on port {port}.")
            return
            
        for pid in pids_to_kill:
            print(f"Found process PID {pid} listening on port {port}. Terminating...")
            kill_res = subprocess.run(["taskkill", "/F", "/T", "/PID", pid], capture_output=True, text=True)
            if kill_res.returncode == 0:
                print(f"Successfully terminated PID {pid}.")
            else:
                print(f"Failed to terminate PID {pid}: {kill_res.stderr.strip()}")
                
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    kill_process_on_port(8001)
