"""iCloud -> PC: den auf dem HANDY gespeicherten Spielstand (.dsv) aus der
iCloud in den PC-DeSmuME-Battery-Ordner holen (Rueckrichtung des Sync).

Ablauf (das iPhone-Shortcut erledigt Schritt 1):
  1) iPhone: DeSmuME-Battery-.dsv  ->  iCloud\\Modded DSV files\\  (Shortcut)
  2) DIESES Tool: iCloud\\Modded DSV files\\  ->  PC-Battery-Ordner

Sicherheits-Regeln:
- Vor dem Ueberschreiben wird der bisherige PC-Stand als Backup in
  saves/_vom_handy_backup/ gesichert.
- Ist der PC-Stand NEUER als der iCloud-Stand, wird gewarnt und NICHT
  ueberschrieben (ausser mit --force) - schuetzt vor Verlust von
  PC-Fortschritt.

CLI:
  python tools/icloud_pull.py          # holen (mit Schutzabfrage)
  python tools/icloud_pull.py --force  # immer holen (iCloud gewinnt)
  python tools/icloud_pull.py --status # nur Zeitstempel vergleichen
"""
import os
import shutil
import sys
import time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BATTERY_DIR = os.path.join(HERE, 'desmume-0.9.13-win64', 'Battery')
ICLOUD_DSV_DIR = r"C:\Users\danie\iCloudDrive\Modded DSV files"
BACKUP_DIR = os.path.join(HERE, 'saves', '_vom_handy_backup')
DSV_NAME = 'Bleach3P modded.dsv'


def _mtime(p):
    return os.path.getmtime(p) if os.path.exists(p) else 0


def pull(force=False, status_only=False):
    src = os.path.join(ICLOUD_DSV_DIR, DSV_NAME)
    dst = os.path.join(BATTERY_DIR, DSV_NAME)
    if not os.path.exists(src):
        return f'FEHLER: iCloud-Datei fehlt:\n{src}\n(iPhone-Shortcut zuerst laufen lassen?)'
    ms, md = _mtime(src), _mtime(dst)
    ds = time.strftime('%d.%m. %H:%M', time.localtime(ms))
    dd = time.strftime('%d.%m. %H:%M', time.localtime(md)) if md else '-'
    info = f'iCloud (Handy): {ds}\nPC-Battery:     {dd}'
    if status_only:
        return info
    if md and md > ms + 2 and not force:
        return (info + '\n\nACHTUNG: Der PC-Stand ist NEUER als der Handy-Stand.\n'
                'Nicht geholt (sonst ginge PC-Fortschritt verloren).\n'
                'Trotzdem holen: mit --force bzw. im Editor bestaetigen.')
    # Backup des bisherigen PC-Stands
    if os.path.exists(dst):
        os.makedirs(BACKUP_DIR, exist_ok=True)
        stamp = time.strftime('%Y%m%d-%H%M%S')
        shutil.copyfile(dst, os.path.join(BACKUP_DIR, f'{stamp}_{DSV_NAME}'))
    os.makedirs(BATTERY_DIR, exist_ok=True)
    tmp = dst + '.tmp'
    shutil.copyfile(src, tmp); os.replace(tmp, dst)
    return f'OK: Handy-Spielstand geholt.\n{info}\n-> {dst}'


if __name__ == '__main__':
    args = set(sys.argv[1:])
    print(pull(force='--force' in args, status_only='--status' in args))
