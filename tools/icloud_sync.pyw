"""iCloud-Sync-Watcher: spiegelt die gepatchte ROM und den Battery-Save
(.dsv, den DeSmuME beim In-Game-Speichern schreibt) automatisch in die
iCloud, sobald sie sich aendern. Das iPhone holt sie per Shortcut ab.

Laeuft unsichtbar im Hintergrund (pythonw). Nur eine Instanz gleichzeitig
(Port-Lock). Start: "iCloud-Sync starten.bat" oder automatisch durch den
Editor.
"""
import os
import shutil
import socket
import sys
import time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WATCH = [
    # (Quelle, Ziel-Ordner)
    (os.path.join(HERE, 'Bleach3P modded.nds'),
     r"C:\Users\danie\iCloudDrive\Modded ROM files"),
    (os.path.join(HERE, 'desmume-0.9.13-win64', 'Battery', 'Bleach3P modded.dsv'),
     r"C:\Users\danie\iCloudDrive\Modded DSV files"),
]
INTERVAL = 5        # Sekunden
SETTLE = 2          # Datei muss so lange unveraendert sein (halbe Writes vermeiden)
LOCK_PORT = 47653   # nur eine Instanz


def main():
    lock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        lock.bind(('127.0.0.1', LOCK_PORT))
    except OSError:
        return          # laeuft schon
    last = {}
    while True:
        for src, dst_dir in WATCH:
            try:
                if not os.path.exists(src) or not os.path.isdir(dst_dir):
                    continue
                m = os.path.getmtime(src)
                if last.get(src) == m:
                    continue
                if time.time() - m < SETTLE:
                    continue    # wird evtl. gerade geschrieben
                dst = os.path.join(dst_dir, os.path.basename(src))
                # .dsv nie ueberschreiben, wenn der iCloud-Stand (Handy)
                # NEUER ist als der PC-Stand - schuetzt Handy-Saves.
                if src.lower().endswith('.dsv') and os.path.exists(dst) \
                        and os.path.getmtime(dst) > m + 2:
                    last[src] = m
                    continue
                tmp = dst + '.tmp'
                shutil.copyfile(src, tmp)
                os.replace(tmp, dst)
                last[src] = m
            except OSError:
                pass            # naechste Runde erneut versuchen
        time.sleep(INTERVAL)


if __name__ == '__main__':
    main()
