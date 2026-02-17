# emulator_create.py
import subprocess

LDCONSOLE = r"C:\LDPlayer\LDPlayer9\ldconsole.exe"

def create_emulators(count):
    for i in range(count):
        subprocess.run([LDCONSOLE, "add"])
        print(f"LDPlayer-{i + 1} | Created")

create_emulators(999)
