"""Bleach: The 3rd Phantom - Stat- & Turm-Editor (GUI).

Start:  python stat_editor.py   (oder Doppelklick auf "Editor starten.bat")

Liest die ROM (Pfad oben einstellbar), zeigt alle Charaktere mit Stats und
die 30 Bleach-Tower-Etagen. Aenderungen werden auf Wunsch in eine Kopie
der ROM geschrieben (empfohlen), das Original bleibt unberuehrt.
"""
import os, re, sys, shutil, random, subprocess, json
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog

DESMUME_EXE = (r"C:\Users\danie\OneDrive - Technische Hochschule Rosenheim\Desktop"
               r"\Bleach3P_RE\desmume-0.9.13-win64\DeSmuME_0.9.13_x64.exe")
BATTERY_DIR = os.path.join(os.path.dirname(DESMUME_EXE), 'Battery')
# iCloud-Sync fuers iPhone: gepatchte ROM und der aktuelle Spielstand werden
# nach jedem Speichern dorthin gespiegelt (iPhone-Shortcut holt sie ab).
ICLOUD_ROM_DIR = r"C:\Users\danie\iCloudDrive\Modded ROM files"
ICLOUD_DSV_DIR = r"C:\Users\danie\iCloudDrive\Modded DSV files"
# Save-Manager-Profile (.dsv-Kopien) - liegen im Projektordner (OneDrive-Sync)
SAVES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'saves')
# Frei vergebbare Map-Namen (Editor-Komfort; nicht in der ROM, nur hier)
MAP_NAMES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'map_names.json')

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'tools'))
from romfs import RomFS, DEFAULT_ROM
from formats import bgsm_strings, bgsm_replace_strings, narc_subfiles
from tower import floor_units, pack_units, party_slots, pack_party
from faces import face_png
from fmap import map_png
from formats import parse_inc

STATUS_PATH = '/yamada/DataBase/db_status.inc'
NUM_RE = re.compile(r'-?\d+')

# Kompilierte Charakter-Tabelle im ARM9: DIE Quelle, aus der die Engine die
# Kampfwerte liest (db_status.inc ist nur ein Build-Artefakt!). In-game
# verifiziert: .inc-Boosts ohne ARM9-Sync haben keinerlei Effekt.
# Record-Offset = ARM9_STATUS_ROM + (unit-15)*70, 70 Bytes:
#   +4 u16 person, +6 u16 unit(Pruef-Key), +8 typ, +9 unk3, +10 face, +11 lv,
#   +12 u16 hp, +14 u16 sp, +16 atk, +17 def, +18 hit, +19 eva, +20 mov,
#   +21 aType, +25 unk17, +26 S-Pressure, +28 u16[10] Equip,
#   +48 u16 unk20, +50 u16[10] Faehigkeiten
ARM9_STATUS_ROM = 0x101C52

# Vanilla-Referenz (dumps/vanilla_ref.json, aus der unmodifizierten ROM):
#   floors: Etage -> initial platzierte Original-Slots {slot, active, raw}.
#     Der Randomizer nimmt sie als Templates (AI-raw/Team) und fuellt bei
#     Bedarf mit Extra-Slots auf - das ist in-game verifiziert (Etage 1 mit
#     25 Gegnern auf den Slots 16-40). Sonder-Records (x=y=0, Welle -3)
#     sind nicht enthalten. ACHTUNG: enthalten sind aber die echten
#     NACHSCHUB-Slots (Welle 1-3) der Etagen 5/6/9/23/24 - deren raw[0]
#     darf nicht mitgeklont werden, sonst spawnt der Gegner nicht.
#   stats: unit -> [hp, sp, atk, def, hit, eva] Vanilla-Basiswerte.
#     Boosts rechnen IMMER von diesen Werten aus - dadurch idempotent,
#     kein Aufschaukeln ueber mehrere Sessions/Randomize-Laeufe mehr.
VREF_PATH = os.path.join(HERE, 'dumps', 'vanilla_ref.json')
try:
    VANILLA_REF = json.load(open(VREF_PATH))
except Exception:
    VANILLA_REF = {'floors': {}, 'stats': {}}

# Design: modernes Dark-Theme mit Bleach-Anime-Identitaet -
# Shinigami-Schwarz + Ichigo-Orange, klare Flaechen, viel Kontrast
G_BG = '#111318'      # Haupthintergrund (fast schwarz, leicht blau)
G_DARK = '#1a1d24'    # Panels / Tabs / Buttons
G_FIELD = '#20242d'   # Listen- und Tabellen-Hintergrund
G_INPUT = '#2a2f3a'   # Eingabefelder
G_GOLD = '#ff7a1a'    # Akzent: Ichigo-Orange (Ueberschriften, Auswahl, Aktionen)
G_RED = '#d92b2b'     # Gefahr/GOD-MODE (Blut-Rot)
G_TEXT = '#eceff4'    # Haupttext
G_HINT = '#8f9aa8'    # gedaempfte Hinweistexte
G_FONT = ('Segoe UI', 10)
G_FONT_B = ('Segoe UI Semibold', 10)
G_HEAD = ('Bahnschrift', 11)

# Token-Indizes innerhalb einer db_status.inc-Zeile (42 Zahlen pro Zeile)
TOK_PERSON, TOK_UNIT, TOK_TYPE, TOK_FACE = 0, 1, 2, 4
TYPE_LABELS = {0: '0 - ungenutzt', 1: '1 - spielbar/verbuendet', 3: '3 - Gegner (Boss?)',
               4: '4 - Gegner', 5: '5 - Gegner', 6: '6 - Hollow'}
# Reihenfolge lt. Spiel-Tutorial: HP, SP, Attack, Defense, Accuracy, Evasion,
# Spiritual Pressure (Zusatzschlag-Chance, im Kampf aufladbar)
STAT_FIELDS = [('Level', 5), ('HP', 6), ('SP', 7), ('ATK', 8), ('DEF', 9),
               ('HIT', 10), ('EVA', 11), ('MOV', 12),
               ('Attribut*', 13), ('S-Pressure*', 18), ('unk22*', 40), ('unk23*', 41)]
EQUIP_TOKENS = list(range(19, 29))    # 10 Ausruestungs-Slots
ABIL_TOKENS = list(range(30, 40))     # 10 Faehigkeits-Slots (roh)
TOKENS_PER_LINE = 42

# In-game kaputte/nicht kampffaehige Einheiten - NIE vom Randomizer spawnen:
#   176/177 "Whole" (Demi-Hollow-Geister, in-game kaputt - User-verifiziert),
#   185 "Sky Rift" (zerstoerbares Objekt von Etage 28, kein Kaempfer),
#   151 "Familiar" = XP-FARM-DUMMY (Etage 28): Stat-Tabelle HP=1/Werte=1 +
#   Growth-Tail-Bytes gesetzt (Turm liest dadurch die Stat-Tabelle).
#   Nie boosten/wuerfeln, sonst ist die Farm kaputt; 152/153 bleiben im Pool.
RANDOMIZER_BLACKLIST = {176, 177, 185, 151}

# Riesen-Sprites (4-Feld-Charaktere): bleiben manuell setzbar, aber der
# Randomizer laesst sie weg (User-Wunsch; das 25er-Limit wurde ohne sie
# verifiziert): Grand Savage, Menos Grande, Huge Hollow, Jidanbo, Giant Entity
BIG_UNITS = {148, 149, 150, 163, 164, 165, 166, 167, 168, 237, 252}

# Max. VERSCHIEDENE Sprites pro Etage - in-game bisektiert auf Etage 1
# (2026-07-06): 25 Gegner/25 unique OK, 26 = Crash (2 Charsets), jeweils
# ohne Riesen-Sprites und mit 8 Deploy-Slots.
MAX_UNIQUE_SPRITES = 25

# Globaler Stat-Boost (User-Wunsch 2026-07-06: Gegner skalierten zu
# schwach): NUR der Stat-Faktor der randomisierten Gegner x1.25
# gegenueber der alten Skalierung - die Level bleiben wie eingestellt.
LEVEL_STAT_SCALE = 1.25

# Ausreisser-Daempfung (User-Wunsch 2026-07-06): ATK/DEF/HIT/EVA, die
# beim Charakter schon von Haus aus ueberdurchschnittlich hoch sind
# (> OUTLIER_THRESH x Pool-Durchschnitt der Vanilla-Werte), kriegen nur
# OUTLIER_SCALE statt des vollen Level-Faktors - sonst wird z. B.
# Yoruichi (EVA-Basis 42) auf Lv80 mit EVA 95 praktisch untreffbar.
# HP/SP sind ausgenommen (hohe HP sollen ja skalieren).
OUTLIER_THRESH = 1.3
OUTLIER_SCALE = 1.1

# Passiva, die die Gegner-AI zu Endlos-Zuegen missbraucht - NICHT in die
# Zufalls-Loadouts wuerfeln (manuell zuweisbar bleiben sie):
#   375 "Hit & Run" (kind 5, "Enable movement after attacking"): AI greift
#   an -> darf ziehen -> greift SOFORT wieder an, Endloskette bis zum Tod
#   (in-game 2026-07-07: Yachiru auf Etage 2, User-Report)
AI_ABUSE_PASSIVES = {375}

# PFLICHT-FAEHIGKEITEN. 370 und 401 (beide kind=4, Wert 999 in
# db_ability.inc) tragen im Original genau die 59 BENANNTEN Einheiten
# (Captains, Espada, Vize-Captains) - Hollows, Soul-Reaper-Mobs, Zivilisten
# und Zanpakuto-Wesen haben sie NICHT. Die Stat-Randomisierung hat bisher
# die Slots 1-9 pauschal ueberschrieben und sie damit geloescht; genau die
# betroffenen Chars zeigen in-game die kaputten 53/11 HP (HANDOVER 5.3).
# Deshalb: nie ueberschreiben, nie wuerfeln - und nur bei den Einheiten
# eintragen, die sie im Vanilla-Record wirklich hatten (nichts erfinden).
ESSENTIAL_ABILITIES = (370, 401)
#   unit (str) -> Liste der Pflicht-Faehigkeiten dieses Vanilla-Records.
#   Erzeugt aus dumps/characters.csv via tools/gen_essential_abil.py.
ESSENTIAL_ABIL = VANILLA_REF.get('essential_abil', {})

# Thematische Preset-Batches fuer den Tower-Tab (nur verifizierte
# Pool-IDs, Riesen-Sprites bewusst nicht enthalten). Namen: names.csv.
PRESET_BATCHES = {
    'Captains (Turm)': [132, 133, 134, 136, 137, 139, 140, 141, 142, 144],
    'Bankai-Chars': [136, 137, 140, 141, 142, 115, 207, 217, 254],
    'Arrancar & Espada': [113, 115, 117, 119, 121, 123, 125, 127, 129],
    'Vize-Captains & Offiziere': [196, 206, 207, 208, 209, 216, 217, 218, 227],
    'Hollows (klein/mittel)': [131, 145, 146, 147, 151, 152, 153, 154, 155, 156,
                               157, 158, 159, 160, 161, 162, 182, 183, 184,
                               186, 187, 188, 189],
    'Aizen & Verraeter': [5, 18, 43, 198, 129, 249],
    'Ichigo & Freunde': [241, 228, 242, 243, 244, 245, 246, 105, 219, 229],
    'Zanpakuto-Wesen': [9, 24, 37, 56, 135, 138, 143],
    'Soul-Reaper-Mobs': [63, 64, 65, 66, 67, 68],
    # Rollen-Batches (datenbasiert aus den Vanilla-Stats gewaehlt):
    # Tanks = hoechste HP+DEF im Pool (ohne Riesen/Immobile),
    # Support = Heal-/Kido-/Debuff-Kits mit Kampf-Attribut (kein NONCOM!),
    # Carries = hoechster ATK/HIT/EVA-Mix
    'Rolle: Tanks (4)': [141, 137, 247, 121],          # Kenpachi, Komamura, Shinji, Edrad
    'Rolle: Healer/Support (4)': [244, 206, 196, 227],  # Orihime, Momo, Izuru, Nemu
    'Rolle: Carries/DPS (4)': [129, 18, 217, 248],      # Arturo, Aizen, Ikkaku, Hiyori
    'Rolle: Balanced Lobby (12)': [141, 137, 247, 121,
                                   244, 206, 196, 227,
                                   129, 18, 217, 248],
}

# Einzeln in-game verifizierte Exoten (Batch-Test 2026-07-03, alle Lv90 ok):
# Zanpakuto-/Bankai-Wesen + Zivilisten, die das Spiel nie als Turmgegner
# nutzt, aber sauber spawnen und skalieren. Erweitern den Pool auf 60.
VERIFIED_EXTRA_IDS = {9, 37, 56, 89, 92, 105, 135, 138, 143}

# FINALE, komplett in-game verifizierte Gegner-Whitelist (Batch-Tests 1-10,
# 2026-07-03): jede einzelne ID wurde auf Etage 1 gespawnt und zeigte exakt
# das eingestellte dpos-Level (45/90) mit sauberem Sprite - inkl. aller
# Turm-Captains (132-144), Gin/Tosen/Aizen, Enemy-Ichigo/Rukia/Yoruichi,
# Vize-Captains, Soul-Reaper-Mobs, Zivilisten und Zanpakuto-Wesen.
# Roster-verknuepfte Einheiten (Partner-Flag 1 oder echte Roster-Units)
# fehlen bewusst: sie ziehen Save-Stats. Erweiterungen NUR nach In-Game-Test!
VERIFIED_POOL_IDS = {
    5, 9, 14, 15, 16, 18, 23, 24, 28, 29, 37, 43, 56, 63, 64, 65,
    66, 67, 68, 89, 92, 105, 113, 115, 117, 119, 121, 123, 125, 127, 129, 131,
    132, 133, 134, 135, 136, 137, 138, 139, 140, 141, 142, 143, 144, 145, 146, 147,
    148, 149, 150, 151, 152, 153, 154, 155, 156, 157, 158, 159, 160, 161, 162, 163,
    164, 165, 166, 167, 168, 182, 183, 184, 186, 187, 188, 189, 196, 197, 198, 199,
    206, 207, 208, 209, 216, 217, 218, 219, 226, 227, 228, 229, 236, 237, 238, 239,
    240, 241, 242, 243, 244, 245, 246, 247, 248, 249, 250, 251, 252, 253, 254,
}

# Einheiten, die das ORIGINALSPIEL selbst irgendwo als Team-3-Gegner einsetzt
# (alle db_dpos der unmodifizierten ROM gescannt). Nur solche skalieren sicher
# mit dem dpos-Level. Rekrutierbare Duplikate (114/116/118/130 Ulquiorra/
# Grimmjow/Yammy/Arturo) fehlen absichtlich: sie haengen am SPIELSTAND-Roster
# und spawnen mit Save-Stats statt dem eingestellten Level (in-game bestaetigt).
VANILLA_ENEMY_IDS = {
    1, 3, 5, 7, 8, 12, 14, 15, 16, 18, 20, 23,
    24, 28, 29, 31, 32, 33, 36, 40, 43, 45, 46, 47,
    48, 49, 50, 51, 54, 55, 57, 58, 61, 63, 64, 65,
    66, 67, 68, 70, 72, 77, 94, 95, 96, 97, 101, 112,
    113, 115, 117, 119, 121, 123, 125, 127, 129, 131, 132, 133,
    134, 136, 137, 139, 140, 141, 142, 144, 145, 146, 147, 148,
    149, 150, 151, 152, 153, 154, 155, 156, 157, 158, 159, 160,
    161, 162, 163, 164, 165, 166, 167, 168, 179, 180, 181, 182,
    183, 184, 185, 186, 187, 188, 189, 190, 191, 196, 197, 198,
    199, 206, 207, 208, 209, 216, 217, 218, 219, 226, 227, 228,
    229, 236, 237, 238, 239, 241, 242, 243, 244, 245, 246, 247,
    248, 249, 252, 253, 254,
}

# Ability-Typen aus db_ability.inc (Token 1 jeder Zeile):
#   1=Zanpakuto/Waffe  2=gewaehrt benutzbaren Battle-Skill (Token 5 = Skill-ID)
#   6=Bankai  8=Shunko  9=Zenkai        -> im Kampf aktiv einsetzbar
#   3/5/7=Stat-Passiva  4=Status-Effekte (Token 5 = Voraussetzung)
#   10/11=Slots  12=Route End           -> passiv (Skill-Tree)
ACTIVE_KINDS = {1, 2, 6, 8, 9}


def line_tokens(line):
    return [(m.start(), m.end(), int(m.group())) for m in NUM_RE.finditer(line)]


def replace_tokens(line, updates):
    """updates: {token_index: neuer_wert}; ersetzt von hinten nach vorn."""
    toks = line_tokens(line)
    for idx in sorted(updates, reverse=True):
        s, e, _ = toks[idx]
        line = line[:s] + str(int(updates[idx])) + line[e:]
    return line


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('BLEACH: The 3rd Phantom - Mod Studio')
        self.geometry('1420x820')
        self.minsize(960, 600)
        self.fs = None
        self.names = {}
        self.status_lines = []      # Zeilen von db_status.inc
        self.status_orig_size = 0
        self.char_rows = []         # (zeilen_index, unit_id, name, typ)
        self.tower_cache = {}       # etage -> unit-liste (inkl. eigener Aenderungen)
        self.party_cache = {}       # etage -> spieler-slot-liste
        self.dirty_status = False
        self.dirty_floors = set()
        self.dirty_party = set()
        self.dirty_maps = set()     # Etagen mit geaenderter Map (btower patchen)
        self.narc_base = {}         # etage -> Donor-NARC nach Map-Wechsel
        self.ai_base = {}           # etage -> NARC mit editierten Subfile-1-AI-Skills
        self.btower_orig = {}       # originale Etage->Map-Zuordnung der ROM
        self.god_boosted = set()    # bereits stat-geboostete Charaktere
        self._unit_clip = None      # kopierte Einheit (Copy/Paste im Tower-Tab)
        self.face_cache = {}        # face_id -> PhotoImage (oder None)
        self.face_by_unit = {}      # unit_id -> face_id
        self.btower = {}            # etage -> map_id
        self.map_cache = {}         # etage -> PhotoImage der Karte
        self.walk_cache = {}        # etage -> begehbare Grid-Zellen
        self.skill_lines = []       # db_skill.inc
        self.skill_orig_size = 0
        self.dirty_skill = False
        self.skill_names = {}
        self.skill_help = {}
        self.abil_names = {}
        self.abil_help = {}
        self.abil_kind = {}         # ability-id -> Typ (2=Skill, 4=Status, ...)
        self.abil_ref = {}          # ability-id -> Skill-ID (kind=2) / Voraussetzung (kind=4)
        self._last_sel = 'enemy'    # zuletzt angeklickte Liste (enemy/deploy)
        self._apply_game_style()
        self._build_ui()
        self.after(50, self.load_rom)

    # ---------- iCloud: Handy-Spielstand holen ----------
    def _pull_from_phone(self):
        """Den auf dem Handy gespeicherten .dsv aus der iCloud in den
        PC-Battery-Ordner holen (Rueckrichtung; mit Schutzabfrage)."""
        import importlib
        try:
            pull = importlib.import_module('icloud_pull')
            importlib.reload(pull)
        except Exception as e:
            messagebox.showerror('Handy holen', f'Tool nicht gefunden: {e}')
            return
        status = pull.pull(status_only=True)
        res = pull.pull(force=False)
        if 'ACHTUNG' in res:
            if messagebox.askyesno('PC-Stand ist neuer!',
                    res + '\n\nTrotzdem den Handy-Stand holen (PC-Fortschritt '
                    'wird als Backup gesichert)?'):
                res = pull.pull(force=True)
            else:
                self.status_var.set('Handy-Sync abgebrochen (PC-Stand war neuer).')
                return
        messagebox.showinfo('DSV vom Handy geholt', res)
        self.status_var.set('Handy-Spielstand in Battery-Ordner geholt. '
                            'DeSmuME neu starten zum Weiterspielen.')

    # ---------- iCloud-Sync ----------
    def _push_rom_icloud(self, rom_path=None):
        """NUR die ROM in die iCloud spiegeln (fuers iPhone-Export).
        Beruehrt den Spielstand NICHT."""
        import shutil as _sh
        src = rom_path or self.rom_var.get()
        try:
            if os.path.exists(src) and os.path.isdir(ICLOUD_ROM_DIR):
                dst = os.path.join(ICLOUD_ROM_DIR, os.path.basename(src))
                _sh.copyfile(src, dst + '.tmp'); os.replace(dst + '.tmp', dst)
                return dst
        except OSError:
            pass
        return None

    def _rom_to_phone(self):
        """Button: aktuelle ROM sofort in den iCloud-ROM-Ordner (Handy)."""
        dst = self._push_rom_icloud()
        if dst:
            messagebox.showinfo('ROM -> Handy',
                                f'ROM in die iCloud kopiert (fuers Handy):\n{dst}')
            self.status_var.set('ROM in iCloud (Modded ROM files) gespiegelt.')
        else:
            messagebox.showerror('ROM -> Handy',
                                 f'iCloud-Ordner nicht gefunden:\n{ICLOUD_ROM_DIR}')

    def _sync_icloud(self, rom_path=None):
        """Beim Speichern: ROM IMMER spiegeln; den Spielstand (.dsv) nur, wenn
        der PC-Stand NEUER ist als der in der iCloud - so wird ein neuerer
        Handy-Save nie ueberschrieben. Fehler sind nie fatal."""
        import shutil as _sh
        n = 0
        if self._push_rom_icloud(rom_path):
            n += 1
        # DSV nur bei echtem PC-Fortschritt hochschieben
        try:
            src = self._dsv_path()
            dst = os.path.join(ICLOUD_DSV_DIR, os.path.basename(src))
            if os.path.exists(src) and os.path.isdir(ICLOUD_DSV_DIR):
                icloud_newer = (os.path.exists(dst)
                                and os.path.getmtime(dst) > os.path.getmtime(src) + 2)
                if not icloud_newer:
                    _sh.copyfile(src, dst + '.tmp'); os.replace(dst + '.tmp', dst)
                    n += 1
        except OSError:
            pass
        return n

    def _start_icloud_watcher(self):
        """Hintergrund-Watcher starten (spiegelt In-Game-Saves auch dann,
        wenn der Editor laengst zu ist). Port-Lock verhindert Duplikate."""
        try:
            import subprocess
            subprocess.Popen(
                ['pythonw', os.path.join(HERE, 'tools', 'icloud_sync.pyw')],
                creationflags=0x08000008)   # DETACHED | CREATE_NO_WINDOW
        except OSError:
            pass

    def _dsv_path(self):
        """Battery-Save der aktuell geladenen ROM (an ROM-Dateinamen gebunden)."""
        stem = os.path.splitext(os.path.basename(self.rom_var.get()))[0]
        return os.path.join(BATTERY_DIR, stem + '.dsv')

    def _save_manager(self):
        """Beliebig viele Spielstand-Profile: sichert/laedt .dsv-Kopien.
        Ersetzt das fehlende dritte Save-Slot im Spiel - Profile liegen in
        Bleach3P_RE/saves/ (synct via OneDrive mit)."""
        os.makedirs(SAVES_DIR, exist_ok=True)
        cur = self._dsv_path()

        dlg = tk.Toplevel(self)
        dlg.title('Save-Manager')
        dlg.transient(self)
        dlg.grab_set()
        dlg.geometry('520x420')
        dlg.configure(bg=G_BG)

        info = ttk.Label(dlg, wraplength=480, justify='left')
        info.pack(anchor='w', padx=10, pady=(10, 4))
        lb = tk.Listbox(dlg, height=10)
        lb.pack(fill='both', expand=True, padx=10)
        profiles = []

        def refresh():
            import datetime
            if os.path.exists(cur):
                mt = datetime.datetime.fromtimestamp(os.path.getmtime(cur))
                info.config(text=f'Aktiver Spielstand: {os.path.basename(cur)}\n'
                                 f'(zuletzt geaendert {mt:%d.%m.%Y %H:%M})')
            else:
                info.config(text=f'Noch kein Spielstand fuer diese ROM vorhanden:\n{cur}')
            lb.delete(0, 'end')
            profiles.clear()
            import glob
            for p in sorted(glob.glob(os.path.join(SAVES_DIR, '*.dsv'))):
                mt = datetime.datetime.fromtimestamp(os.path.getmtime(p))
                lb.insert('end', f'{os.path.splitext(os.path.basename(p))[0]}'
                                 f'   ({mt:%d.%m. %H:%M})')
                profiles.append(p)

        row = ttk.Frame(dlg)
        row.pack(fill='x', padx=10, pady=8)
        name_var = tk.StringVar()
        ttk.Entry(row, textvariable=name_var, width=26).pack(side='left')

        def snap():
            name = re.sub(r'[^\w\- ]', '', name_var.get().strip())
            if not name:
                messagebox.showinfo('Name fehlt', 'Erst einen Profilnamen eingeben.',
                                    parent=dlg)
                return
            if not os.path.exists(cur):
                messagebox.showerror('Kein Spielstand',
                                     f'{cur} existiert nicht.', parent=dlg)
                return
            dst = os.path.join(SAVES_DIR, name + '.dsv')
            if os.path.exists(dst) and not messagebox.askyesno(
                    'Ueberschreiben?', f'Profil "{name}" existiert - ersetzen?',
                    parent=dlg):
                return
            shutil.copyfile(cur, dst)
            refresh()

        def load():
            sel = lb.curselection()
            if not sel:
                return
            src = profiles[sel[0]]
            name = os.path.splitext(os.path.basename(src))[0]
            if not messagebox.askyesno(
                    'Profil laden',
                    f'"{name}" als aktiven Spielstand setzen?\n\n'
                    'DeSmuME wird dafuer beendet; der aktuelle Spielstand wird '
                    'vorher automatisch als Profil "_vorher" gesichert.',
                    parent=dlg):
                return
            subprocess.run(['taskkill', '/IM', os.path.basename(DESMUME_EXE), '/F'],
                           capture_output=True)
            if os.path.exists(cur):
                shutil.copyfile(cur, os.path.join(SAVES_DIR, '_vorher.dsv'))
            shutil.copyfile(src, cur)
            refresh()
            self.status_var.set(f'Spielstand-Profil "{name}" aktiv - DeSmuME neu starten.')

        def delete():
            sel = lb.curselection()
            if not sel:
                return
            src = profiles[sel[0]]
            name = os.path.splitext(os.path.basename(src))[0]
            if messagebox.askyesno('Loeschen', f'Profil "{name}" wirklich loeschen?',
                                   parent=dlg):
                os.remove(src)
                refresh()

        ttk.Button(row, text='Aktuellen Stand sichern als...', style='Accent.TButton',
                   command=snap).pack(side='left', padx=6)
        row2 = ttk.Frame(dlg)
        row2.pack(fill='x', padx=10, pady=(0, 10))
        ttk.Button(row2, text='Profil laden (aktiv setzen)', style='Accent.TButton',
                   command=load).pack(side='left')
        ttk.Button(row2, text='Loeschen', command=delete).pack(side='left', padx=6)
        ttk.Button(row2, text='Schliessen', command=dlg.destroy).pack(side='right')
        ttk.Label(dlg, foreground=G_HINT, wraplength=480, justify='left',
                  text='Tipp: DeSmuME hat zusaetzlich 10 Savestate-Slots '
                       '(Shift+F1..F10 speichern, F1..F10 laden).'
                  ).pack(anchor='w', padx=10, pady=(0, 8))
        lb.bind('<Double-Button-1>', lambda e: load())
        refresh()

    def _launch_desmume(self, rom):
        """DeSmuME mit der angegebenen ROM (neu) starten. Beendet vorher
        laufende Instanzen - die halten sonst den alten ROM-Stand im RAM."""
        if not os.path.exists(DESMUME_EXE):
            messagebox.showerror('DeSmuME', f'Emulator nicht gefunden:\n{DESMUME_EXE}')
            return
        if not os.path.exists(rom):
            messagebox.showerror('DeSmuME', f'ROM nicht gefunden:\n{rom}')
            return
        subprocess.run(['taskkill', '/IM', os.path.basename(DESMUME_EXE), '/F'],
                       capture_output=True)
        subprocess.Popen([DESMUME_EXE, rom])
        self.status_var.set(f'DeSmuME gestartet mit {os.path.basename(rom)}')

    def _apply_game_style(self):
        """Modernes Dark-Theme im Bleach-Anime-Stil: Schwarz + Ichigo-Orange,
        flache Flaechen, klare Typografie (Bahnschrift-Headlines)."""
        self.configure(bg=G_BG)
        for opt, val in (('*Listbox.background', G_FIELD),
                         ('*Listbox.foreground', G_TEXT),
                         ('*Listbox.selectBackground', G_GOLD),
                         ('*Listbox.selectForeground', 'black'),
                         ('*Listbox.font', '{Segoe UI} 10'),
                         ('*Listbox.borderWidth', 0),
                         ('*Listbox.highlightThickness', 1),
                         ('*Listbox.highlightBackground', '#2c313c'),
                         ('*Listbox.highlightColor', G_GOLD),
                         ('*Listbox.activeStyle', 'none'),
                         ('*TCombobox*Listbox.background', G_FIELD),
                         ('*TCombobox*Listbox.foreground', G_TEXT),
                         ('*TCombobox*Listbox.selectBackground', G_GOLD),
                         ('*TCombobox*Listbox.selectForeground', 'black'),
                         ('*Toplevel.background', G_BG)):
            self.option_add(opt, val)
        st = ttk.Style(self)
        st.theme_use('clam')
        st.configure('.', background=G_BG, foreground=G_TEXT, font=G_FONT,
                     bordercolor='#2c313c', lightcolor=G_BG, darkcolor=G_BG,
                     fieldbackground=G_INPUT, relief='flat')
        st.configure('TLabel', background=G_BG, foreground=G_TEXT)
        st.configure('TFrame', background=G_BG)
        st.configure('TLabelframe', background=G_BG, bordercolor='#2c313c',
                     relief='solid', borderwidth=1)
        st.configure('TLabelframe.Label', background=G_BG, foreground=G_GOLD,
                     font=G_HEAD)
        st.configure('TButton', background=G_DARK, foreground=G_TEXT,
                     font=G_FONT_B, padding=(10, 5), borderwidth=0)
        st.map('TButton', background=[('active', '#2c313c')],
               foreground=[('active', G_GOLD)])
        # Primaer-Aktionen: Orange-Buttons mit schwarzer Schrift
        st.configure('Accent.TButton', background=G_GOLD, foreground='#111111',
                     font=G_FONT_B, padding=(12, 5))
        st.map('Accent.TButton', background=[('active', '#ffa04d')],
               foreground=[('active', 'black')])
        st.configure('TNotebook', background=G_BG, borderwidth=0)
        st.configure('TNotebook.Tab', background=G_BG, foreground=G_HINT,
                     font=('Bahnschrift', 12), padding=(18, 8), borderwidth=0)
        st.map('TNotebook.Tab', background=[('selected', G_DARK)],
               foreground=[('selected', G_GOLD)])
        st.configure('Treeview', background=G_FIELD, fieldbackground=G_FIELD,
                     foreground=G_TEXT, rowheight=24, borderwidth=0)
        st.configure('Treeview.Heading', background=G_DARK, foreground=G_GOLD,
                     font=G_FONT_B, relief='flat', padding=4)
        st.map('Treeview', background=[('selected', G_GOLD)],
               foreground=[('selected', 'black')])
        st.map('Treeview.Heading', background=[('active', G_DARK)])
        for w in ('TEntry', 'TCombobox', 'TSpinbox'):
            st.configure(w, fieldbackground=G_INPUT, foreground=G_TEXT,
                         insertcolor=G_GOLD, bordercolor='#3a4150',
                         lightcolor=G_INPUT, darkcolor=G_INPUT, padding=3)
            st.map(w, bordercolor=[('focus', G_GOLD)],
                   fieldbackground=[('readonly', G_DARK)],
                   foreground=[('readonly', G_TEXT)])
        st.configure('TCombobox', arrowcolor=G_GOLD)
        st.configure('TSpinbox', arrowcolor=G_GOLD)
        st.configure('TRadiobutton', background=G_BG, foreground=G_TEXT,
                     indicatorcolor=G_INPUT)
        st.configure('TCheckbutton', background=G_BG, foreground=G_TEXT,
                     indicatorcolor=G_INPUT)
        for w in ('TRadiobutton', 'TCheckbutton'):
            st.map(w, background=[('active', G_BG)],
                   indicatorcolor=[('selected', G_GOLD)])
        st.configure('TScrollbar', background=G_DARK, troughcolor=G_BG,
                     bordercolor=G_BG, arrowcolor=G_HINT)
        st.map('TScrollbar', background=[('active', G_GOLD)])

    # ---------- UI ----------
    def _build_ui(self):
        top = ttk.Frame(self, padding=6)
        top.pack(fill='x')
        ttk.Label(top, text='ROM:').pack(side='left')
        self.rom_var = tk.StringVar(value=DEFAULT_ROM)
        ttk.Entry(top, textvariable=self.rom_var, width=80).pack(side='left', padx=4, fill='x', expand=True)
        ttk.Button(top, text='...', width=3, command=self._pick_rom).pack(side='left')
        ttk.Button(top, text='Laden', command=self.load_rom).pack(side='left', padx=4)
        ttk.Button(top, text='> DeSmuME starten',
                   command=lambda: self._launch_desmume(self.rom_var.get())
                   ).pack(side='left', padx=4)
        ttk.Button(top, text='Save-Manager',
                   command=self._save_manager).pack(side='left', padx=4)
        ttk.Button(top, text='DSV vom Handy holen',
                   command=self._pull_from_phone).pack(side='left', padx=4)
        ttk.Button(top, text='ROM -> Handy (iCloud)',
                   command=self._rom_to_phone).pack(side='left', padx=4)

        out = ttk.Frame(self, padding=(6, 0, 6, 6))
        out.pack(fill='x')
        self.save_mode = tk.StringVar(value='orig')
        ttk.Radiobutton(out, text='In Kopie speichern:', variable=self.save_mode,
                        value='copy').pack(side='left')
        self.copy_var = tk.StringVar(value=os.path.join(HERE, 'Bleach3P modded kopie.nds'))
        ttk.Entry(out, textvariable=self.copy_var, width=60).pack(side='left', padx=4, fill='x', expand=True)
        ttk.Radiobutton(out, text='Direkt in geladene ROM speichern (Standard)',
                        variable=self.save_mode, value='orig').pack(side='left', padx=8)
        self.autostart_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(out, text='danach DeSmuME starten',
                        variable=self.autostart_var).pack(side='left', padx=8)

        # Untere Leiste VOR dem Notebook packen (side=bottom): zuletzt
        # gepackte Widgets verlieren beim Verkleinern zuerst ihren Platz -
        # so bleibt der Speicher-Button bei jeder Fenstergroesse sichtbar.
        bar = ttk.Frame(self, padding=6)
        bar.pack(side='bottom', fill='x')
        self.status_var = tk.StringVar(value='Bereit.')
        ttk.Label(bar, textvariable=self.status_var).pack(side='left')
        ttk.Button(bar, text='Alle Aenderungen in ROM speichern', style='Accent.TButton',
                   command=self.save_all).pack(side='right')

        nb = ttk.Notebook(self)
        nb.pack(fill='both', expand=True, padx=6, pady=4)
        self.nb = nb
        self._build_char_tab(nb)
        self._build_tower_tab(nb)
        self._build_designer_tab(nb)
        self._build_skill_tab(nb)
        self._build_debuff_tab(nb)

    def _build_char_tab(self, nb):
        tab = ttk.Frame(nb, padding=6)
        nb.add(tab, text=' Charaktere ')
        left = ttk.Frame(tab)
        left.pack(side='left', fill='y')
        self.filter_var = tk.StringVar(value='Alle')
        fil = ttk.Combobox(left, textvariable=self.filter_var, state='readonly',
                           values=['Alle', 'Nur spielbare', 'Nur Gegner/NPC'])
        fil.pack(fill='x')
        fil.bind('<<ComboboxSelected>>', lambda e: self._fill_charlist())
        self.search_var = tk.StringVar()
        self.search_var.trace_add('write', lambda *a: self._fill_charlist())
        ttk.Entry(left, textvariable=self.search_var).pack(fill='x', pady=(4, 0))
        self.charlist = tk.Listbox(left, width=32)
        self.charlist.pack(fill='both', expand=True, pady=4)
        self.charlist.bind('<<ListboxSelect>>', self._on_char_select)

        right = ttk.Frame(tab, padding=(16, 4))
        right.pack(side='left', fill='both', expand=True, anchor='n')
        head = ttk.Frame(right)
        head.grid(row=0, column=0, columnspan=4, sticky='we', pady=(0, 10))
        self.face_label = ttk.Label(head)
        self.face_label.pack(side='left', padx=(0, 12))
        self.char_title = ttk.Label(head, text='-', font=('Bahnschrift', 15), foreground=G_GOLD)
        self.char_title.pack(side='left')
        self.type_var = tk.StringVar()
        self.type_combo = ttk.Combobox(head, textvariable=self.type_var, width=24,
                                       state='readonly', values=list(TYPE_LABELS.values()))
        self.type_combo.pack(side='right')

        self.stat_vars = {}
        for i, (label, tok) in enumerate(STAT_FIELDS):
            r, c = divmod(i, 4)
            ttk.Label(right, text=label).grid(row=1 + r * 2, column=c, sticky='w', padx=(0, 12))
            v = tk.StringVar()
            self.stat_vars[tok] = v
            ttk.Entry(right, textvariable=v, width=10).grid(row=2 + r * 2, column=c,
                                                            sticky='w', padx=(0, 12), pady=(0, 8))
        ttk.Label(right, text='Ausruestung (Item-IDs, max. 10, siehe dumps/abilities.csv & Item-Liste):').grid(
            row=7, column=0, columnspan=4, sticky='w', pady=(12, 2))
        self.equip_var = tk.StringVar()
        ttk.Entry(right, textvariable=self.equip_var, width=52).grid(row=8, column=0, columnspan=4, sticky='w')
        ttk.Label(right, text='Faehigkeiten (erster Wert = Skill-Set-ID des Charakters, dann Ability-IDs):').grid(
            row=9, column=0, columnspan=4, sticky='w', pady=(10, 2))
        self.abil_var = tk.StringVar()
        self.abil_var.trace_add('write', lambda *a: self._update_abil_preview())
        arow = ttk.Frame(right)
        arow.grid(row=10, column=0, columnspan=4, sticky='w')
        ttk.Entry(arow, textvariable=self.abil_var, width=44).pack(side='left')
        ttk.Button(arow, text='Skills waehlen...', command=self._pick_abilities).pack(
            side='left', padx=(8, 0))
        self.abil_preview = ttk.Label(right, text='', wraplength=430, justify='left',
                                      foreground='#7ee08a')
        self.abil_preview.grid(row=11, column=0, columnspan=4, sticky='w', pady=(4, 0))

        ttk.Button(right, text='Werte uebernehmen', style='Accent.TButton',
                   command=self._apply_char).grid(
            row=12, column=0, columnspan=2, sticky='w', pady=14)
        ttk.Label(right, foreground=G_HINT, justify='left',
                  text='* Attribut: Kampf-Element (13 = "All", z. B. Prolog-Gin/Arturo).\n'
                       '* S-Pressure: Startwert der Spiritual-Pressure-Leiste (vermutet;\n'
                       '  Yamamoto 40, Kenpachi 37, Rukia 0). unk22/23: noch unbekannt.\n'
                       'Wachstum pro Level-Up (inkl. Pressure) steht in db_growt.inc.').grid(
            row=13, column=0, columnspan=4, sticky='w')

    # ---------- Debuff-/Status-Lexikon ----------
    def _build_debuff_tab(self, nb):
        tab = ttk.Frame(nb, padding=6)
        nb.add(tab, text=' Debuffs & Status ')
        ttk.Label(tab, text='Debuff- & Status-Lexikon  (live aus der ROM generiert)',
                  font=('Bahnschrift', 13), foreground=G_GOLD).pack(anchor='w')
        ttk.Label(tab, foreground=G_HINT, justify='left',
                  text='power = Staerke des Effekts, Chance = Trefferwahrscheinlichkeit '
                       'in % (999 = wirkt sicher/auf Verbuendete).').pack(anchor='w', pady=(0, 6))
        wrap = ttk.Frame(tab)
        wrap.pack(fill='both', expand=True)
        self.debuff_text = tk.Text(wrap, wrap='word', bg='#111318', fg='#e8e8e8',
                                   insertbackground='#e8e8e8', relief='flat',
                                   font=('Consolas', 10), state='disabled')
        sb = ttk.Scrollbar(wrap, orient='vertical', command=self.debuff_text.yview)
        self.debuff_text.configure(yscrollcommand=sb.set)
        self.debuff_text.pack(side='left', fill='both', expand=True)
        sb.pack(side='left', fill='y')
        self.debuff_text.tag_configure('h1', foreground='#ff7a1a',
                                       font=('Bahnschrift', 12, 'bold'))
        self.debuff_text.tag_configure('h2', foreground=G_GOLD,
                                       font=('Consolas', 10, 'bold'))
        self.debuff_text.tag_configure('dim', foreground='#9a9a9a')

    def _fill_debuff_info(self):
        """Lexikon aus db_skill (Effektbloecke) + db_ability (kind-4-Passiva)
        generieren. Effektblock = {typ, power, wert}; wert < 999 = Chance %."""
        t = self.debuff_text
        t.configure(state='normal')
        t.delete('1.0', 'end')

        def w(txt='', tag=None):
            t.insert('end', txt + '\n', tag)

        # Skills nach Ailment-Stichwort im Hilfetext gruppieren
        import re as _re
        skill_fx = {}    # skill-id -> (name, kosten?, [(typ,power,wert)], help)
        for ln in self.skill_lines:
            tok = [int(x) for x in NUM_RE.findall(ln)]
            if len(tok) < 15:
                continue
            n_eff = (len(tok) - 14) // 3
            fx = [(tok[3 + e * 3], tok[4 + e * 3], tok[5 + e * 3])
                  for e in range(n_eff)]
            sid = tok[0]
            skill_fx[sid] = (self.skill_names.get(sid, f'?{sid}'), fx,
                             self.skill_help.get(sid, '').replace('\n', ' '))

        def skills_with(keyword_re):
            out = []
            for sid, (nm, fx, hlp) in sorted(skill_fx.items()):
                if _re.search(keyword_re, hlp, _re.I):
                    chance = next((v for ty, p, v in fx
                                   if ty not in (0, 1) and v < 999), None)
                    out.append((sid, nm, chance, hlp))
            return out

        # kind-4-Passiva-Familien (Burn 1-5 usw.) + Schutz-Gegenstuecke
        fams = {}
        for aid, k in sorted(self.abil_kind.items()):
            nm = self.abil_names.get(aid, '')
            if k == 4 and nm.strip():
                fam = _re.sub(r'\s*\d+$', '', nm)
                fams.setdefault(fam, []).append(aid)

        # Wirkungen = OFFIZIELLE In-Game-Definitionen aus dem Tutorial
        # (db_tutorial_msg.bin [14] "Status Ailment Types"):
        DEBUFFS = [
            ('POISON (Gift)', r'\bpoison',
             'Spieltext: "HP drops at turn start" - HP sinken zu Rundenbeginn.'),
            ('VENOM (starkes Gift)', r'\bvenom',
             'Spieltext: "Large HP drop at turn start" - GROSSER HP-Verlust '
             'zu Rundenbeginn.'),
            ('BURNED (verbrannt)', r'\bburn',
             'Spieltext: "Attack/defense drop" - ATK und DEF des Ziels sinken '
             '(KEIN Schaden ueber Zeit!).'),
            ('FROZEN (vereist)', r'\bfr(eeze|ozen)',
             'Spieltext: "Accuracy/evasion drop" - ACC und EVA des Ziels '
             'sinken (Ziel bleibt handlungsfaehig!).'),
            ('SHOCKED (geschockt)', r'\bshock',
             'Spieltext: "Only Move, Attack, Standby usable" - Ziel kann '
             'KEINE Skills/Kido mehr benutzen.'),
            ('HELD (gefesselt)', r'\bh(old|eld)\b',
             'Spieltext: "Only Skill or Standby usable" - Ziel kann sich '
             'NICHT bewegen und nicht normal angreifen (Konter bleibt '
             'moeglich!).'),
            ('ICE CELL (Eiszelle)', r'ice cell|encases targets in ice',
             'Spieltext: "Frozen + Held status" - Kombination aus beidem '
             '(Konter bleibt moeglich).'),
            ('HOMONKA (Suzumebachi-Mal)', r'homonka|nigeki',
             'Spieltext: "Death if struck by Nigeki Kessatsu in this state" - '
             'Ziel stirbt sofort beim zweiten Nigeki-Kessatsu-Treffer.'),
            ('S-PRESSURE-SENKUNG (Skill-Effekt, kein Ailment)',
             r'lowers spiritual pres|absorbs spiritual',
             'Senkt/stiehlt die Spiritual-Pressure-Leiste des Ziels (weniger '
             'Zusatzschlaege/Verwandlungen).'),
            ('ZUFALLS-AILMENT', r'random status|random ailment|cause random',
             'Verursacht einen zufaelligen der obigen Status-Effekte.'),
        ]
        w('STATUS-EFFEKTE (DEBUFFS)', 'h1')
        w('Quelle: In-Game-Tutorial "Status Ailment Types" (db_tutorial_msg [14]).', 'dim')
        w('Regeln lt. Tutorial [13]: Nur EIN Ailment gleichzeitig - das neueste', 'dim')
        w('ersetzt das alte. Heilt automatisch nach einigen Runden oder durch', 'dim')
        w('Cure-Skills/-Items. Chance = Ausloese-% des Skills.', 'dim')
        w()
        FAM = {'POISON': 'Poison', 'VENOM': 'Venom', 'BURNED': 'Burn',
               'FROZEN': 'Freeze', 'SHOCKED': 'Shock', 'HELD': 'Hold',
               'HOMONKA': 'Homonka'}
        for title, pat, desc in DEBUFFS:
            w(title, 'h2')
            w('  ' + desc)
            sk = skills_with(pat)
            if sk:
                w('  Verursacht durch Skills:')
                for sid, nm, chance, hlp in sk:
                    c = f'{chance}%' if chance is not None else '-'
                    w(f'    {sid:3d} {nm:<18} Chance {c:>4}  {hlp[:58]}', 'dim')
            fam = FAM.get(title.split(' ')[0])
            if fam and fam in fams:
                ids = sorted(fams[fam])
                w(f'  Passiva (Chance beim NORMALEN Angriff): '
                  f'{fam} 1-{len(ids)} = Ability {ids[0]}-{ids[-1]}')
            for guard in (f'Res {fam}', f'Block {fam}', f'{fam} Blck'):
                if fam and guard in fams:
                    gids = sorted(fams[guard])
                    w(f'  Schutz: {guard} (Ability {gids[0]}'
                      + (f'-{gids[-1]}' if len(gids) > 1 else '') + ')')
            w()

        w('BUFFS & SUPPORT (Gegenstueck)', 'h1')
        w()
        BUFFS = [(6, 'DEF erhoehen (power = +DEF)'),
                 (7, 'Treffsicherheit/ACC erhoehen (power = +ACC)'),
                 (8, 'Ausweichen/EVA erhoehen (power = +EVA)'),
                 (18, 'S-Pressure aufladen (power = +Stufen)'),
                 (15, 'HP-Drain (power = % der eigenen Heilung)'),
                 (13, 'Status-Heilung (entfernt Ailments)')]
        for typ, desc in BUFFS:
            w(desc, 'h2')
            for sid, (nm, fx, hlp) in sorted(skill_fx.items()):
                for ty, p, v in fx:
                    if ty == typ:
                        w(f'    {sid:3d} {nm:<18} power={p:<4} '
                          f'{"sicher" if v >= 999 else str(v) + "%":>6}  {hlp[:52]}', 'dim')
            w()
        t.configure(state='disabled')

    # ---------- Char-Designer ----------
    # Eigene "Spezial-Charaktere" bauen: Pool-Charakter waehlen, umbenennen
    # (s_name.bin wird beim Speichern neu gepackt), Stats + Faehigkeiten
    # setzen und direkt in die aktuelle Etage stellen. Aenderungen wirken
    # GLOBAL fuer den Charakter (ARM9-Tabelle) - wie im Charaktere-Tab.
    DESIGNER_STATS = [('Level', 5), ('HP', 6), ('SP', 7), ('ATK', 8), ('DEF', 9),
                      ('HIT', 10), ('EVA', 11), ('MOV', 12), ('S-Pressure', 18)]

    def _build_designer_tab(self, nb):
        tab = ttk.Frame(nb, padding=6)
        nb.add(tab, text=' Char-Designer ')
        left = ttk.Frame(tab)
        left.pack(side='left', fill='y')
        ttk.Label(left, text='Basis-Charakter (verifizierter Pool):').pack(anchor='w')
        self.des_search = tk.StringVar()
        self.des_search.trace_add('write', lambda *a: self._fill_designer_list())
        ttk.Entry(left, textvariable=self.des_search).pack(fill='x', pady=(2, 0))
        # exportselection=0: Auswahl bleibt bestehen, wenn man in die
        # Stat-Entries klickt (sonst gibt die Listbox die X-Selection ab
        # und curselection wird leer -> "Kein Charakter" beim Speichern)
        self.des_list = tk.Listbox(left, width=32, exportselection=False)
        self.des_list.pack(fill='both', expand=True, pady=4)
        self.des_list.bind('<<ListboxSelect>>', self._on_designer_select)
        self._des_sel_unit = None       # zuletzt gewaehlte Unit (Fallback)
        ttk.Button(left, text='ALLE Chars: Slots auf 9 auffuellen',
                   command=self._fill_all_ability_slots).pack(fill='x', pady=(0, 4))

        right = ttk.Frame(tab, padding=(16, 4))
        right.pack(side='left', fill='both', expand=True, anchor='n')
        head = ttk.Frame(right)
        head.pack(anchor='w', pady=(0, 10), fill='x')
        self.des_face = ttk.Label(head)
        self.des_face.pack(side='left', padx=(0, 12))
        self.des_title = ttk.Label(head, text='-', font=('Bahnschrift', 15),
                                   foreground=G_GOLD)
        self.des_title.pack(side='left')

        nrow = ttk.Frame(right)
        nrow.pack(anchor='w', pady=(0, 10))
        ttk.Label(nrow, text='Name:').pack(side='left')
        self.des_name = tk.StringVar()
        ttk.Entry(nrow, textvariable=self.des_name, width=24,
                  font=G_FONT_B).pack(side='left', padx=6)
        ttk.Label(nrow, foreground=G_HINT,
                  text='(wird in s_name.bin umbenannt - gilt ueberall im Spiel)'
                  ).pack(side='left')

        grid = ttk.Frame(right)
        grid.pack(anchor='w')
        self.des_stats = {}
        for i, (label, tok) in enumerate(self.DESIGNER_STATS):
            r, c = divmod(i, 5)
            ttk.Label(grid, text=label).grid(row=r * 2, column=c, sticky='w', padx=(0, 12))
            v = tk.StringVar()
            self.des_stats[tok] = v
            ttk.Entry(grid, textvariable=v, width=8).grid(
                row=r * 2 + 1, column=c, sticky='w', padx=(0, 12), pady=(0, 8))

        ttk.Label(right, text='Faehigkeiten (erster Wert = Skill-Set-ID, bleibt erhalten):'
                  ).pack(anchor='w', pady=(10, 2))
        arow = ttk.Frame(right)
        arow.pack(anchor='w')
        self.des_abil = tk.StringVar()
        ttk.Entry(arow, textvariable=self.des_abil, width=44).pack(side='left')
        ttk.Button(arow, text='Skills waehlen...',
                   command=lambda: self._pick_abilities(
                       var=self.des_abil,
                       title=f'Skills & Faehigkeiten - {self.des_title.cget("text")}')
                   ).pack(side='left', padx=(8, 0))

        brow = ttk.Frame(right)
        brow.pack(anchor='w', pady=14)
        ttk.Button(brow, text='Design speichern', style='Accent.TButton',
                   command=self._designer_save).pack(side='left')
        ttk.Button(brow, text='In aktuelle Etage einsetzen',
                   command=self._designer_place).pack(side='left', padx=8)
        self.des_floor_lbl = ttk.Label(brow, foreground=G_HINT)
        self.des_floor_lbl.pack(side='left')
        ttk.Label(right, foreground=G_HINT, justify='left',
                  text='* Aenderungen gelten GLOBAL fuer den Charakter (ARM9) - auch dort,\n'
                       '  wo er schon steht. Erst "Design speichern", dann einsetzen.\n'
                       '* Der Randomizer wuerfelt Skills neu - designte Gegner danach\n'
                       '  nicht nochmal randomisieren (oder Skills neu vergeben).\n'
                       '* "In ROM speichern" unten schreibt Name+Stats endgueltig.'
                  ).pack(anchor='w')

    def _fill_all_ability_slots(self):
        """TO-DO-Punkt: ALLEN Charakteren (Gegner UND Teammates) die maximale
        Anzahl Faehigkeits-Slots geben - leere Slots 1-9 werden mit zufaelligen
        Skill-Tree-Passiva aufgefuellt (Slot 0 = Set-ID und alles Vorhandene
        bleibt unangetastet; Hit & Run ausgenommen)."""
        if not self.fs:
            return
        if not messagebox.askyesno(
                'Slots auffuellen',
                'Bei ALLEN Charakteren (auch spielbaren!) die leeren '
                'Faehigkeits-Slots 1-9 mit zufaelligen Passiva fuellen?\n\n'
                'Hinweis: Ob spielbare Charaktere die Passiva in-game nutzen '
                '(oder ihr Skill-Tree aus dem Save kommt), ist ungetestet.'):
            return
        passives = [a for a, nm in self.abil_names.items()
                    if nm.strip() and self.abil_kind.get(a) in (3, 4, 5, 7)
                    and a not in AI_ABUSE_PASSIVES
                    and a not in ESSENTIAL_ABILITIES]
        n = 0
        for li, unit, name, typ in self.char_rows:
            if unit in self.risky_units:
                continue
            toks = line_tokens(self.status_lines[li])
            if len(toks) != TOKENS_PER_LINE:
                continue
            ab = [toks[t][2] for t in ABIL_TOKENS]
            if 0 not in ab[1:]:
                continue        # schon voll
            have = set(ab)
            fill = [a for a in passives if a not in have]
            random.shuffle(fill)
            for i in range(1, 10):
                if ab[i] == 0 and fill:
                    ab[i] = fill.pop()
            self.status_lines[li] = replace_tokens(
                self.status_lines[li], dict(zip(ABIL_TOKENS, ab)))
            n += 1
        if n:
            self.dirty_status = True
        self.status_var.set(f'{n} Charaktere: Faehigkeits-Slots auf 9 aufgefuellt '
                            '(noch nicht gespeichert).')

    def _fill_designer_list(self):
        prev = self._des_unit()         # Auswahl ueber den Rebuild erhalten
        q = self.des_search.get().lower()
        self.des_list.delete(0, 'end')
        self._des_visible = []
        for unit in sorted(self.enemy_pool):
            name = self.dirty_names.get(unit, self.names.get(unit, '?'))
            if q and q not in name.lower() and q != str(unit):
                continue
            mark = ' *' if unit in self.dirty_names else ''
            self.des_list.insert('end', f'{unit:3d}  {name}{mark}')
            self._des_visible.append(unit)
        if prev in self._des_visible:
            self.des_list.selection_set(self._des_visible.index(prev))

    def _des_unit(self):
        sel = self.des_list.curselection()
        if sel:
            return self._des_visible[sel[0]]
        # Fallback: gemerkte Auswahl (falls die Listbox die Selektion an ein
        # Entry-Feld verloren hat), sofern noch sichtbar
        if self._des_sel_unit in getattr(self, '_des_visible', []):
            return self._des_sel_unit
        return None

    def _on_designer_select(self, _=None):
        sel = self.des_list.curselection()
        unit = self._des_visible[sel[0]] if sel else None
        if unit is None or not self.fs:
            return
        self._des_sel_unit = unit
        li = next(l for l, un, _, _ in self.char_rows if un == unit)
        toks = line_tokens(self.status_lines[li])
        self.des_title.config(
            text=f'#{unit}  {self.dirty_names.get(unit, self.names.get(unit, "?"))}')
        self._set_face(self.des_face, toks[TOK_FACE][2])
        self.des_name.set(self.dirty_names.get(unit, self.names.get(unit, '')))
        for _, tok in self.DESIGNER_STATS:
            self.des_stats[tok].set(toks[tok][2])
        self.des_abil.set(', '.join(str(toks[t][2]) for t in ABIL_TOKENS))
        self.des_floor_lbl.config(text=f'(Etage {int(self.floor_var.get())})')

    def _designer_save(self):
        if not self.fs:
            return
        unit = self._des_unit()
        if unit is None:
            messagebox.showinfo('Kein Charakter', 'Erst links einen Charakter waehlen.')
            return
        li = next(l for l, un, _, _ in self.char_rows if un == unit)
        try:
            updates = {tok: int(self.des_stats[tok].get())
                       for _, tok in self.DESIGNER_STATS}
            abil = [int(x) for x in re.split(r'[,\s]+', self.des_abil.get().strip()) if x]
            if len(abil) > 10:
                raise ValueError('max. 10 Faehigkeiten-Eintraege')
            for v in list(updates.values()) + abil:
                if not 0 <= v <= 65535:
                    raise ValueError(f'Wert {v} ausserhalb 0..65535')
            # ARM9-Records: atk/def/hit/eva/mov sind u8!
            for tok in (8, 9, 10, 11, 12):
                if updates[tok] > 255:
                    raise ValueError('ATK/DEF/HIT/EVA/MOV max. 255 (u8 im ARM9)')
            name = self.des_name.get().strip()
            if not name:
                raise ValueError('Name darf nicht leer sein')
        except ValueError as e:
            messagebox.showerror('Ungueltige Eingabe', str(e))
            return
        abil += [0] * (10 - len(abil))
        updates.update({t: v for t, v in zip(ABIL_TOKENS, abil)})
        self.status_lines[li] = replace_tokens(self.status_lines[li], updates)
        self.dirty_status = True
        if name != self.names.get(unit, ''):
            self.dirty_names[unit] = name
        else:
            self.dirty_names.pop(unit, None)
        self._fill_designer_list()
        self._fill_charlist()          # Namen auch links im Charaktere-Tab
        self._fill_unit_choices()
        self.des_title.config(text=f'#{unit}  {name}')
        self.status_var.set(f'Design fuer #{unit} "{name}" gespeichert '
                            '(noch nicht in ROM geschrieben).')

    def _designer_place(self):
        if not self.fs:
            return
        unit = self._des_unit()
        if unit is None:
            messagebox.showinfo('Kein Charakter', 'Erst links einen Charakter waehlen.')
            return
        floor = int(self.floor_var.get())
        if floor not in self.tower_cache:
            self._load_floor()
        units = self.tower_cache[floor]
        used = {u['slot'] for u in units}
        slot = next((s for s in range(16, 129) if s not in used), None)
        if slot is None:
            messagebox.showerror('Voll', 'Kein freier Slot auf der Etage.')
            return
        uniq = {u['char'] for u in units if u['slot'] >= 16} | {unit}
        if len(uniq) > MAX_UNIQUE_SPRITES:
            messagebox.showerror('Sprite-Limit',
                                 f'Mehr als {MAX_UNIQUE_SPRITES} verschiedene '
                                 'Charaktere auf der Etage = Crash!')
            return
        # freie begehbare Zelle, nicht auf/neben Deploy-Slots oder Einheiten
        blocked = {(u['x'] - 1, u['y'] - 1) for u in units}
        pslots = self.party_cache.get(floor, [])
        for s in pslots:
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    blocked.add((s['x'] - 1 + dx, s['y'] - 1 + dy))
        cells = [c for c in self._walkable_cells(floor) if c not in blocked]
        if not cells:
            messagebox.showerror('Kein Platz', 'Keine freie begehbare Zelle gefunden.')
            return
        gx, gy = random.choice(cells)
        pcx = sum(s['x'] for s in pslots) / len(pslots) if pslots else 19.5
        pcy = sum(s['y'] for s in pslots) / len(pslots) if pslots else 19.5
        dx, dy = pcx - (gx + 1), pcy - (gy + 1)
        face = (0 if dx > 0 else 2) if abs(dx) >= abs(dy) else (3 if dy > 0 else 1)
        try:
            level = max(1, min(99, int(self.des_stats[5].get())))
        except ValueError:
            level = 50
        if unit in self.noncom_units:
            messagebox.showwarning(
                'NONCOM-Charakter',
                f'"{self.names.get(unit, "?")}" ist ein NONCOM-Typ (Healer/'
                'Zivilist): normale Angriffe/Pressure koennen crashen - '
                'nur mit reinen Skill-Loadouts einsetzen!')
        units.append({'slot': slot, 'active': 3, 'char': unit, 'level': level,
                      'unk3': 10, 'x': gx + 1, 'y': gy + 1, 'dir': face, 'unk7': 1,
                      'raw': [0, 3, 100] + [0] * 16})    # aggressive AI
        self.dirty_floors.add(floor)
        self._load_floor()
        nm = self.dirty_names.get(unit, self.names.get(unit, '?'))
        self.status_var.set(f'"{nm}" (#{unit}) Lv{level} auf Etage {floor} '
                            f'Slot {slot} bei ({gx + 1},{gy + 1}) eingesetzt '
                            '(noch nicht gespeichert).')

    def _build_tower_tab(self, nb):
        tab = ttk.Frame(nb, padding=6)
        nb.add(tab, text=' Bleach Tower ')
        top = ttk.Frame(tab)
        top.pack(fill='x')
        ttk.Label(top, text='Etage:').pack(side='left')
        self.floor_var = tk.IntVar(value=1)
        self.floor_combo = ttk.Combobox(top, textvariable=self.floor_var, width=5,
                                        values=list(range(1, 31)), state='readonly')
        self.floor_combo.pack(side='left', padx=4)
        self.floor_combo.bind('<<ComboboxSelected>>', lambda e: self._load_floor())
        ttk.Label(top, text='Map:').pack(side='left', padx=(16, 0))
        self.map_combo = ttk.Combobox(top, width=40, state='readonly')
        self.map_combo.pack(side='left', padx=4)
        self.map_combo.bind('<<ComboboxSelected>>', lambda e: self._change_map())
        ttk.Button(top, text='Map benennen...', command=self._rename_map).pack(side='left')
        ttk.Label(top, foreground=G_HINT,
                  text='(Map-Wechsel uebernimmt Terrain+Spawns der Donor-Etage)'
                  ).pack(side='left', padx=8)

        mid = ttk.Frame(tab)
        mid.pack(fill='both', expand=True)

        # Karte ZUERST packen (side=right): zuletzt gepackte Widgets werden
        # beim Verkleinern zuerst abgeschnitten - so bleibt die Karte bei
        # jeder Fenstergroesse vollstaendig sichtbar, die linke Tabelle
        # gibt stattdessen nach. Der Rahmen schmiegt sich an die tatsaechliche
        # Kartengroesse an (kein schwarzer Leerraum) - _draw_map setzt die
        # Canvas-Groesse pro Etage; bei Uebergroesse deckeln + scrollen.
        right = ttk.LabelFrame(mid, text='Karte  (Klick: Einheit versetzen / Marker waehlen)', padding=4)
        right.pack(side='right', fill='none', expand=False, anchor='n', padx=(10, 0))

        left = ttk.Frame(mid)
        left.pack(side='left', fill='both', expand=True)
        right.rowconfigure(0, weight=1)
        right.columnconfigure(0, weight=1)
        self.map_canvas = tk.Canvas(right, width=460, height=400, bg='#0c0e12',
                                    highlightthickness=0)
        self.map_hbar = ttk.Scrollbar(right, orient='horizontal',
                                      command=self.map_canvas.xview)
        self.map_vbar = ttk.Scrollbar(right, orient='vertical',
                                      command=self.map_canvas.yview)
        self.map_canvas.configure(xscrollcommand=self.map_hbar.set,
                                  yscrollcommand=self.map_vbar.set)
        self.map_canvas.grid(row=0, column=0, sticky='nsew')
        self.map_vbar.grid(row=0, column=1, sticky='ns')
        self.map_hbar.grid(row=1, column=0, sticky='we')
        self.map_canvas.bind('<Button-1>', self._canvas_click)
        self.map_canvas.bind('<MouseWheel>', lambda e: self.map_canvas.yview_scroll(
            -e.delta // 120, 'units'))
        self.map_canvas.bind('<Shift-MouseWheel>', lambda e: self.map_canvas.xview_scroll(
            -e.delta // 120, 'units'))

        cols = ('slot', 'team', 'char', 'name', 'level', 'x', 'y', 'dir')
        # Grid statt pack: nur die Tabelle (row 0, weight 1) schrumpft beim
        # Verkleinern - Einheiten-Editor, Randomizer (inkl. Batches/Filter)
        # und Deploy-Slots bleiben IMMER sichtbar.
        left.rowconfigure(0, weight=1)
        left.columnconfigure(0, weight=1)
        self.tree = ttk.Treeview(left, columns=cols, show='headings', height=10)
        widths = {'slot': 45, 'team': 65, 'char': 55, 'name': 185, 'level': 55,
                  'x': 45, 'y': 45, 'dir': 45}
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=widths[c], anchor='w')
        self.tree.grid(row=0, column=0, sticky='nsew', pady=6)
        self.tree.bind('<<TreeviewSelect>>', self._on_unit_select)

        edit = ttk.Frame(left)
        edit.grid(row=1, column=0, sticky='we')
        self.unit_vars = {}
        ttk.Label(edit, text='Charakter:').grid(row=0, column=0, sticky='w')
        self.unit_char = ttk.Combobox(edit, width=28)
        self.unit_char.grid(row=1, column=0, padx=(0, 10), sticky='w')
        # ai = raw[1] (AI-Typ), aggro = raw[2] (Aggressivitaet 0-100):
        # 0/0 = passiv-defensiv (greift erst bei Annaeherung an),
        # 3/100 = jagt den Spieler aktiv (Vanilla-Muster aggressiver Gegner)
        for i, f in enumerate(('level', 'x', 'y', 'dir', 'ai', 'aggro')):
            ttk.Label(edit, text=f).grid(row=0, column=1 + i, sticky='w')
            v = tk.StringVar()
            self.unit_vars[f] = v
            ttk.Entry(edit, textvariable=v, width=6).grid(row=1, column=1 + i, padx=(0, 8), sticky='w')
        ttk.Label(edit, text='Team').grid(row=0, column=7, sticky='w')
        self.unit_team = ttk.Combobox(edit, width=10, state='readonly',
                                      values=['3 Gegner', '1 Spieler'])
        self.unit_team.grid(row=1, column=7, padx=(0, 10), sticky='w')
        ttk.Button(edit, text='Einheit uebernehmen', command=self._apply_unit).grid(row=1, column=8, padx=6)
        ttk.Button(edit, text='Neue Einheit', command=self._new_unit).grid(row=1, column=9, padx=6)
        ttk.Button(edit, text='Einheit loeschen', command=self._del_unit).grid(row=1, column=10, padx=6)
        ttk.Button(edit, text='Skills/Faehigkeiten...',
                   command=self._edit_unit_abilities).grid(row=0, column=8,
                                                           columnspan=2, padx=6, sticky='we')
        ttk.Button(edit, text='AI-Skills...', command=self._edit_ai_skills).grid(row=1, column=11, padx=6)
        ttk.Button(edit, text='Kopieren', command=self._copy_unit).grid(row=0, column=10, padx=6)
        ttk.Button(edit, text='Einfuegen', command=self._paste_unit).grid(row=0, column=11, padx=6)
        self.tface_label = ttk.Label(edit)
        self.tface_label.grid(row=0, column=12, rowspan=2, padx=(14, 0))

        # Randomizer: Etage mit zufaelligen Gegnern eines Ziel-Levels fuellen
        rnd = ttk.LabelFrame(left, text='Randomizer', padding=6)
        rnd.grid(row=2, column=0, sticky='we', pady=(10, 0))
        ttk.Label(rnd, text='Ziel-Level:').pack(side='left')
        self.rand_level_var = tk.StringVar(value='80')
        ttk.Spinbox(rnd, from_=1, to=99, textvariable=self.rand_level_var,
                    width=5).pack(side='left', padx=(2, 12))
        ttk.Label(rnd, text='Gegner:').pack(side='left')
        self.rand_min_var = tk.StringVar(value='6')
        ttk.Spinbox(rnd, from_=1, to=113, textvariable=self.rand_min_var,
                    width=4).pack(side='left', padx=2)
        ttk.Label(rnd, text='bis').pack(side='left')
        self.rand_max_var = tk.StringVar(value='20')
        ttk.Spinbox(rnd, from_=1, to=113, textvariable=self.rand_max_var,
                    width=4).pack(side='left', padx=2)
        ttk.Label(rnd, text='Verhalten:').pack(side='left', padx=(8, 0))
        self.rand_behave = ttk.Combobox(rnd, width=10, state='readonly',
                                        values=['Original', 'Aggressiv', 'Defensiv'])
        self.rand_behave.set('Aggressiv')
        self.rand_behave.pack(side='left', padx=2)
        ttk.Button(rnd, text='Etage randomisieren!', style='Accent.TButton',
                   command=self._randomize_floor).pack(side='left', padx=(12, 4))
        god = tk.Button(rnd, text='GOD-MODE Lv90+', bg=G_RED, fg='white',
                        activebackground='#ff4d4d', activeforeground='black',
                        font=G_FONT_B, relief='flat', bd=0, padx=12, pady=4,
                        cursor='hand2',
                        command=lambda: self._randomize_floor(god=True))
        god.pack(side='left', padx=(4, 12))
        chaos = tk.Button(rnd, text='Skill-Chaos', bg='#a83af0', fg='white',
                          activebackground='#c060ff', activeforeground='black',
                          font=G_FONT_B, relief='flat', bd=0, padx=12, pady=4,
                          cursor='hand2', command=self._skill_chaos)
        chaos.pack(side='left', padx=(0, 12))
        # HP-Bug-Werkzeug: stellt 370/401 bei allen Chars wieder her, denen
        # eine frueherer Randomisierung sie weggewuerfelt hat (HANDOVER 5.3).
        fix = tk.Button(rnd, text='370/401 reparieren', bg='#1f8a4c', fg='white',
                        activebackground='#2fb468', activeforeground='black',
                        font=G_FONT_B, relief='flat', bd=0, padx=12, pady=4,
                        cursor='hand2', command=self._repair_essential_abil)
        fix.pack(side='left', padx=(0, 12))
        ttk.Button(rnd, text='?', width=2,
                   command=self._randomizer_info).pack(side='left', padx=(8, 0))

        # Thematische Preset-Batches (statt Zufalls-Pool): ganze Gruppe
        # auf einmal einsetzen; Ziel-Level/Verhalten gelten wie oben
        prow = ttk.Frame(rnd)
        prow.pack(side='bottom', fill='x', pady=(6, 0))
        ttk.Label(prow, text='Preset-Batch:').pack(side='left')
        self.preset_var = ttk.Combobox(prow, width=28, state='readonly',
                                       values=list(PRESET_BATCHES))
        self.preset_var.set(next(iter(PRESET_BATCHES)))
        self.preset_var.pack(side='left', padx=(4, 12))
        ttk.Button(prow, text='Batch einsetzen!', style='Accent.TButton',
                   command=self._apply_preset_batch).pack(side='left', padx=(4, 16))
        ttk.Button(prow, text='ALLE 30 Etagen randomisieren (Challenge-Run)',
                   command=self._randomize_all_floors).pack(side='left')

        # Filter/Challenges fuer den Zufalls-Randomizer
        frow = ttk.Frame(rnd)
        frow.pack(side='bottom', fill='x', pady=(6, 0))
        ttk.Label(frow, text='Randomizer nur aus:').pack(side='left')
        self.rand_only = ttk.Combobox(frow, width=28, state='readonly',
                                      values=['- alle -'] + list(PRESET_BATCHES))
        self.rand_only.set('- alle -')
        self.rand_only.pack(side='left', padx=(4, 12))
        ttk.Label(frow, text='ohne:').pack(side='left')
        self.rand_except = ttk.Combobox(frow, width=28, state='readonly',
                                        values=['- keine -'] + list(PRESET_BATCHES))
        self.rand_except.set('- keine -')
        self.rand_except.pack(side='left', padx=(4, 12))
        ttk.Label(frow, text='Challenge:').pack(side='left')
        self.rand_challenge = ttk.Combobox(frow, width=32, state='readonly',
                                           values=['- keine -',
                                                   'Gegner spawnen bei den Teammates'])
        self.rand_challenge.set('- keine -')
        self.rand_challenge.pack(side='left', padx=4)

        # Spieler-Startpositionen (wo die eigenen - spielbaren - Charaktere starten)
        pfrm = ttk.LabelFrame(left, text='Spieler-Startpositionen (Deploy-Slots)', padding=6)
        pfrm.grid(row=3, column=0, sticky='we', pady=(10, 0))
        self.ptree = ttk.Treeview(pfrm, columns=('slot', 'x', 'y'), show='headings', height=4)
        for c, w in (('slot', 60), ('x', 60), ('y', 60)):
            self.ptree.heading(c, text=c)
            self.ptree.column(c, width=w, anchor='w')
        self.ptree.pack(side='left')
        self.ptree.bind('<<TreeviewSelect>>', self._on_pslot_select)
        pedit = ttk.Frame(pfrm, padding=(12, 0))
        pedit.pack(side='left', anchor='n')
        self.pslot_vars = {}
        for i, f in enumerate(('x', 'y')):
            ttk.Label(pedit, text=f).grid(row=0, column=i, sticky='w')
            v = tk.StringVar()
            self.pslot_vars[f] = v
            ttk.Entry(pedit, textvariable=v, width=7).grid(row=1, column=i, padx=(0, 10), sticky='w')
        ttk.Button(pedit, text='Position uebernehmen',
                   command=self._apply_pslot).grid(row=1, column=2, padx=6)
        ttk.Label(pedit, text='Hier starten die im Spiel ausgewaehlten\nspielbaren Charaktere auf der Etage.',
                  foreground=G_HINT).grid(row=2, column=0, columnspan=3, sticky='w', pady=(6, 0))

    def _build_skill_tab(self, nb):
        tab = ttk.Frame(nb, padding=6)
        nb.add(tab, text=' Skills & Faehigkeiten ')

        # links: alle Battle-Skills (in Leveln einsetzbar)
        lf = ttk.LabelFrame(tab, text='Battle-Skills (Kido usw. - im Level einsetzbar)', padding=6)
        lf.pack(side='left', fill='both', expand=True)
        self.skill_search = tk.StringVar()
        self.skill_search.trace_add('write', lambda *a: self._fill_skill_list())
        ttk.Entry(lf, textvariable=self.skill_search, width=30).pack(anchor='w')
        self.skill_list = tk.Listbox(lf, width=34, height=16)
        self.skill_list.pack(side='left', fill='y', pady=4)
        self.skill_list.bind('<<ListboxSelect>>', self._on_skill_select)

        sed = ttk.Frame(lf, padding=(12, 4))
        sed.pack(side='left', fill='both', expand=True, anchor='n')
        self.skill_title = ttk.Label(sed, text='-', font=('Bahnschrift', 13), foreground=G_GOLD)
        self.skill_title.grid(row=0, column=0, columnspan=6, sticky='w')
        self.skill_helplbl = ttk.Label(sed, text='', wraplength=380, justify='left',
                                       foreground=G_HINT)
        self.skill_helplbl.grid(row=1, column=0, columnspan=6, sticky='w', pady=(2, 10))
        self.skill_vars = {}
        ttk.Label(sed, text='SP-Kosten').grid(row=2, column=0, sticky='w')
        self.skill_vars['cost'] = tk.StringVar()
        ttk.Entry(sed, textvariable=self.skill_vars['cost'], width=8).grid(
            row=3, column=0, sticky='w', padx=(0, 14))
        for e in (1, 2):
            for c, f in enumerate(('Typ', 'Power', 'Wert')):
                ttk.Label(sed, text=f'E{e}-{f}').grid(row=2 + (e - 1) * 2, column=1 + c, sticky='w')
                v = tk.StringVar()
                self.skill_vars[f'e{e}{f}'] = v
                ttk.Entry(sed, textvariable=v, width=8).grid(
                    row=3 + (e - 1) * 2, column=1 + c, sticky='w', padx=(0, 10))
        ttk.Button(sed, text='Skill uebernehmen', command=self._apply_skill).grid(
            row=6, column=0, columnspan=2, sticky='w', pady=12)
        ttk.Label(sed, foreground=G_HINT, justify='left',
                  text='Effekt-Typen (beobachtet): 1 = Schaden, 5/7/8 = Status-\n'
                       'effekte (Laehmung usw.), 0 = keiner. Power = Staerke,\n'
                       'Wert = Treffer-/Chance-Modifikator. Negative Werte erlaubt.').grid(
            row=7, column=0, columnspan=6, sticky='w')

        # rechts: Ability-Referenz (IDs fuer die Faehigkeiten-Liste im Charaktere-Tab)
        rf = ttk.LabelFrame(tab, text='Ability-Referenz (IDs fuer Charaktere-Tab)', padding=6)
        rf.pack(side='left', fill='both', padx=(10, 0))
        self.abil_search = tk.StringVar()
        self.abil_search.trace_add('write', lambda *a: self._fill_abil_list())
        ttk.Entry(rf, textvariable=self.abil_search, width=28).pack(anchor='w')
        self.abil_list = tk.Listbox(rf, width=30, height=16)
        self.abil_list.pack(fill='y', pady=4)
        self.abil_list.bind('<<ListboxSelect>>', self._on_abil_select)
        self.abil_helplbl = ttk.Label(rf, text='', wraplength=230, justify='left',
                                      foreground=G_HINT)
        self.abil_helplbl.pack(anchor='w')

    # ---------- Laden ----------
    def _pick_rom(self):
        p = filedialog.askopenfilename(filetypes=[('NDS ROM', '*.nds')])
        if p:
            self.rom_var.set(p)

    def load_rom(self):
        try:
            self.fs = RomFS(self.rom_var.get())
        except Exception as e:
            messagebox.showerror('Fehler', f'ROM konnte nicht geladen werden:\n{e}')
            return
        self.names = bgsm_strings(self.fs.read('/yamada/ScrDat/s_name.bin'))
        # db_partner.inc Token 1 = Roster-Flag: 1 = Charakter gehoert (potentiell)
        # zum Spieler-Roster -> zieht als Gegner Stats aus dem SPIELSTAND!
        # (validiert: Rangiku 47, Ulquiorra 114, Yammy 118, Arturo 130,
        #  Shinji 179, Hiyori 180 = 1; reine Kopien 209/242/247/113/... = 0)
        self.roster_flag = {}
        for l in self.fs.read('/yamada/DataBase/db_partner.inc').decode('ascii').split('\r\n'):
            toks = [int(m.group()) for m in NUM_RE.finditer(l)]
            if len(toks) >= 2:
                self.roster_flag[toks[0]] = toks[1]
        raw = self.fs.read(STATUS_PATH).decode('ascii')
        self.status_orig_size = len(raw)
        self.status_lines = raw.split('\r\n')
        self.char_rows = []
        self.face_by_unit = {}
        self.face_cache = {}
        for li, line in enumerate(self.status_lines):
            toks = line_tokens(line)
            if len(toks) == TOKENS_PER_LINE:
                unit = toks[TOK_UNIT][2]
                self.char_rows.append((li, unit, self.names.get(unit, f'?{unit}'),
                                       toks[TOK_TYPE][2]))
                self.face_by_unit[unit] = toks[TOK_FACE][2]
        # ARM9-Tabelle ist die Wahrheit - .inc-Modell damit ueberschreiben
        self._load_arm9_into_model()
        self.tower_cache = {}
        self.party_cache = {}
        self.dirty_status = False
        self.dirty_floors = set()
        self.dirty_party = set()
        # Sichere Einheiten: haben Stats UND ein Battle-Sprite in der ROM.
        # Alles andere (leere db_status-Zeilen, reine Dialog-Sprecher) kann crashen.
        sprites = set()
        for p in self.fs.by_path:
            m = re.match(r'/kuro/nc_main/bat_main_nc(\d+)(_b)?\.bin', p)
            if m:
                sprites.add(int(m.group(1)))
        self.safe_units, self.risky_units = set(), set()
        self.noncom_units = set()       # Attribut 0/4 = NONCOM (nur Skills sicher)
        # Gegner-Pool fuer den Randomizer: nur echte Gegner-Typen (typ 3-6).
        # typ=1-Charaktere (Spieler-Roster) ziehen ihre Werte aus dem SPIELSTAND
        # und spawnen daher unterlevelt, wenn der Spieler sie nie trainiert hat.
        self.enemy_pool = set()
        self._pool_avg_cache = None     # Ausreisser-Referenz neu berechnen
        self.dirty_names = {}           # unit-id -> neuer Name (s_name.bin)
        for li, line in enumerate(self.status_lines):
            toks = line_tokens(line)
            if len(toks) != TOKENS_PER_LINE:
                continue
            person, unit, typ, hp = (toks[0][2], toks[1][2], toks[2][2], toks[6][2])
            if typ != 0 and hp > 0 and person in sprites:
                self.safe_units.add(unit)
                # NONCOM-Kampftypen (Attribut 0/4: Healer/Zivilisten) crashen,
                # wenn sie normal angreifen bzw. Pressure ausfuehren (in-game:
                # Female Spirit 251 -> Pressure = Crash, 2026-07-06)
                if toks[13][2] in (0, 4):
                    self.noncom_units.add(unit)
                # Pool = explizit in-game verifizierte Whitelist (Batch-Tests);
                # Sicherheitschecks (Sprite/HP) bleiben als Netz davor
                if unit in VERIFIED_POOL_IDS and unit not in RANDOMIZER_BLACKLIST:
                    self.enemy_pool.add(unit)
            else:
                self.risky_units.add(unit)
        self._fill_charlist()
        self._fill_unit_choices()
        self._fill_designer_list()
        try:
            rows = parse_inc(self.fs.read('/yamada/DataBase/db_btower.inc').decode('ascii'))
            self.btower = {r[0]: r[1] for r in rows}
        except Exception:
            self.btower = {}
        self.btower_orig = dict(self.btower)
        self.dirty_maps = set()
        self.narc_base = {}
        self.god_boosted = set()
        # Map-Auswahl: Turm-Etagen als Donoren + STORY-MAPS ueber Free-Battle-
        # Donoren (dpos_8xx mit vollem 4-Subfile-Terrain; party_8xx hat ein
        # ANDERES Format -> Deploy-Slots werden dort automatisch platziert)
        by_map = {}
        for fl, mp in sorted(self.btower_orig.items()):
            by_map.setdefault(mp, []).append(fl)
        # mapid -> ('fb'|'story', kampf-nr): externe Donoren fuer Maps, die
        # keine Turm-Etage nutzt. Free Battles aus db_fbattle; Story-Kaempfe
        # aus der ARM9-fbattle-Tabelle abgeleitet (226 -> Map 12, Turmformat).
        self.map_fb_donors = {}
        try:
            fb = self.fs.read('/yamada/DataBase/db_fbattle.inc').decode('ascii')
            for ln in fb.split('\r\n'):
                r = [int(t) for t in NUM_RE.findall(ln)]
                if len(r) < 5:
                    continue
                nr, mapid = r[0], r[3]
                p = f'/yamada/DataBase/db_dpos_{800+nr}.narc'
                if (mapid not in by_map and mapid not in self.map_fb_donors
                        and p in self.fs.by_path):
                    subs = narc_subfiles(self.fs.read(p))
                    if len(subs) == 4 and len(subs[1]) == 9288:
                        self.map_fb_donors[mapid] = ('fb', nr)
            # Story-Kampf-Donoren. Map 12 ist ueber die ARM9-fbattle-Tabelle
            # BELEGT (Kampf 226). Die uebrigen Zuordnungen wurden visuell
            # verifiziert (Terrain-Grid ueber Map-Grafik gelegt, s.
            # dumps/story_map_matching/): 9/99 und 18/220 eindeutig,
            # 3/1, 23/190, 28/229, 32/264 plausibel -> in-game testen!
            for mapid, nr in {12: 226, 3: 1, 9: 99, 18: 220,
                              23: 190, 28: 229, 32: 264}.items():
                p = f'/yamada/DataBase/db_dpos_{nr:03d}.narc'
                if (mapid not in by_map and mapid not in self.map_fb_donors
                        and p in self.fs.by_path):
                    subs = narc_subfiles(self.fs.read(p))
                    if len(subs) >= 3:
                        self.map_fb_donors[mapid] = ('story', nr)
        except Exception:
            pass
        self._map_choice_ids = sorted(set(by_map) | set(self.map_fb_donors))
        self._map_donor_floors = {mp: fls for mp, fls in by_map.items()}
        self._load_map_names()
        self._refresh_map_combo()
        self.map_cache = {}
        self.walk_cache = {}
        self._load_floor()
        # Skills & Abilities
        raw = self.fs.read('/yamada/DataBase/db_skill.inc').decode('ascii')
        self.skill_orig_size = len(raw)
        self.skill_lines = raw.split('\r\n')
        self.dirty_skill = False
        self.skill_names = bgsm_strings(self.fs.read('/yamada/DataBase/db_skill_name.bin'))
        self.skill_help = bgsm_strings(self.fs.read('/yamada/DataBase/db_skill_help.bin'))
        self.abil_names = bgsm_strings(self.fs.read('/yamada/DataBase/db_ability_name.bin'))
        self.abil_help = bgsm_strings(self.fs.read('/yamada/DataBase/db_ability_msg1.bin'))
        # Ability-Typen: kind (Token 1) + Referenz (Token 5: bei kind=2 die
        # Skill-ID, bei kind=4 die Vorgaenger-Ability der Upgrade-Kette)
        self.abil_kind, self.abil_ref = {}, {}
        for l in self.fs.read('/yamada/DataBase/db_ability.inc').decode('ascii').split('\r\n'):
            toks = [int(m.group()) for m in NUM_RE.finditer(l)]
            if len(toks) > 5:
                self.abil_kind[toks[0]] = toks[1]
                self.abil_ref[toks[0]] = toks[5]
        self._fill_skill_list()
        self._fill_abil_list()
        self._fill_debuff_info()
        self.status_var.set(f'{len(self.char_rows)} Einheiten geladen aus {os.path.basename(self.rom_var.get())}')

    # ---------- Charaktere ----------
    def _fill_charlist(self):
        q = self.search_var.get().lower()
        mode = self.filter_var.get()
        self.charlist.delete(0, 'end')
        self._visible = []
        for li, unit, name, typ in self.char_rows:
            if unit in getattr(self, 'risky_units', set()):
                continue    # unfertige Charaktere ausblenden (wuerden im Spiel crashen)
            if q and q not in name.lower() and q != str(unit):
                continue
            if mode == 'Nur spielbare' and typ != 1:
                continue
            if mode == 'Nur Gegner/NPC' and typ in (0, 1):
                continue
            star = '★ ' if typ == 1 else '   '
            self.charlist.insert('end', f'{star}{unit:3d}  {name}')
            self._visible.append(li)

    def _face_image(self, face_id):
        """PhotoImage des Portraits (gecacht), None wenn keins vorhanden."""
        if face_id not in self.face_cache:
            png = face_png(self.fs, face_id)
            self.face_cache[face_id] = tk.PhotoImage(data=png) if png else None
        return self.face_cache[face_id]

    def _set_face(self, label, face_id):
        img = self._face_image(face_id) if face_id else None
        if img:
            label.config(image=img, text='')
        else:
            label.config(image='', text='(kein\nPortrait)')

    def _sel_line(self):
        sel = self.charlist.curselection()
        return self._visible[sel[0]] if sel else None

    def _on_char_select(self, _=None):
        li = self._sel_line()
        if li is None:
            return
        toks = line_tokens(self.status_lines[li])
        unit = toks[TOK_UNIT][2]
        self.char_title.config(text=f'#{unit}  {self.names.get(unit, "?")}')
        typ = toks[TOK_TYPE][2]
        self.type_var.set(TYPE_LABELS.get(typ, f'{typ} - ?'))
        self._set_face(self.face_label, toks[TOK_FACE][2])
        for _, tok in STAT_FIELDS:
            self.stat_vars[tok].set(toks[tok][2])
        self.equip_var.set(', '.join(str(toks[t][2]) for t in EQUIP_TOKENS))
        self.abil_var.set(', '.join(str(toks[t][2]) for t in ABIL_TOKENS))

    def _update_abil_preview(self):
        ids = [int(x) for x in re.split(r'[,\s]+', self.abil_var.get().strip())
               if x.isdigit()]
        act = [self.abil_names.get(i) or f'?{i}' for i in ids[1:]
               if i and self._abil_is_active(i)]
        pas = [self.abil_names.get(i) or f'?{i}' for i in ids[1:]
               if i and not self._abil_is_active(i)]
        parts = []
        if act:
            parts.append('AKTIV: ' + ' / '.join(act))
        if pas:
            parts.append('passiv: ' + ' / '.join(pas))
        self.abil_preview.config(text='   |   '.join(parts))

    def _abil_is_active(self, aid):
        """True = im Kampf einsetzbar (Skill/Zanpakuto/Bankai), False = passiv."""
        return self.abil_kind.get(aid, 0) in ACTIVE_KINDS

    def _abil_info(self, aid):
        """Zusatzinfo fuer eine Ability (gewaehrter Skill / Voraussetzung / Typ)."""
        kind = self.abil_kind.get(aid, 0)
        ref = self.abil_ref.get(aid, 0)
        extra = {1: 'Zanpakuto/Waffe', 2: 'benutzbarer Skill', 3: 'Stat-Passiv',
                 4: 'Status-Effekt (passiv)', 5: 'Stat-Passiv', 6: 'Bankai',
                 7: 'Boost-Passiv', 8: 'Shunko', 9: 'Zenkai', 10: 'Co-op Slot',
                 11: 'Ability Slot', 12: 'Route End'}.get(kind, f'Typ {kind}')
        if kind == 2 and ref:
            extra += f'  ->  Skill #{ref} "{self.skill_names.get(ref, "?")}"'
        elif kind == 4 and ref:
            extra += f'  (setzt {ref} "{self.abil_names.get(ref, "?")}" voraus)'
        return extra

    def _pick_abilities(self, auto_apply=False, var=None, title=None):
        """Dialog: benutzbare Skills und passive Faehigkeiten GETRENNT
        zusammenstellen. auto_apply=True (Aufruf aus dem Tower-Tab):
        OK uebernimmt die Werte sofort in den Charakter.
        var: alternative StringVar (z. B. Designer-Tab) statt abil_var."""
        if var is None and self._sel_line() is None:
            messagebox.showinfo('Kein Charakter', 'Erst links einen Charakter auswaehlen.')
            return
        avar = var if var is not None else self.abil_var
        cur = [int(x) for x in re.split(r'[,\s]+', avar.get().strip()) if x.isdigit()]
        set_id = cur[0] if cur else 0
        chosen = [i for i in cur[1:] if i]

        dlg = tk.Toplevel(self)
        dlg.title(title or f'Skills & Faehigkeiten - {self.char_title.cget("text")}')
        dlg.transient(self)
        dlg.grab_set()
        dlg.geometry('760x460')

        nb = ttk.Notebook(dlg)
        nb.pack(side='left', fill='both', expand=True, padx=6, pady=6)
        lists = {}    # tab-name -> (listbox, ids, query_var)

        def make_tab(title, active):
            tab = ttk.Frame(nb, padding=6)
            nb.add(tab, text=title)
            q_var = tk.StringVar()
            ttk.Entry(tab, textvariable=q_var).pack(fill='x')
            lb = tk.Listbox(tab, width=40)
            lb.pack(fill='both', expand=True, pady=4)
            ids = []

            def fill(*_):
                q = q_var.get().lower()
                lb.delete(0, 'end')
                ids.clear()
                for aid in sorted(self.abil_names):
                    name = self.abil_names[aid]
                    if not name.strip() or self._abil_is_active(aid) != active:
                        continue
                    if q and q not in name.lower() and q != str(aid):
                        continue
                    suffix = ''
                    if self.abil_kind.get(aid) == 2 and self.abil_ref.get(aid):
                        suffix = f'  -> {self.skill_names.get(self.abil_ref[aid], "?")}'
                    lb.insert('end', f'{aid:3d}  {name}{suffix}')
                    ids.append(aid)

            q_var.trace_add('write', fill)
            fill()
            return lb, ids

        lb_act, ids_act = make_tab(' Benutzbare Skills (im Kampf) ', True)
        lb_pas, ids_pas = make_tab(' Passive Faehigkeiten (Skill-Tree) ', False)
        help_lbl = ttk.Label(dlg, text='', wraplength=280, justify='left', foreground=G_HINT)

        rf = ttk.LabelFrame(dlg, text=f'Zugewiesen (max. 9)  -  Skill-Set-ID {set_id} bleibt',
                            padding=6)
        rf.pack(side='left', fill='both', padx=6, pady=6)
        mine = tk.Listbox(rf, width=36)
        mine.pack(fill='both', expand=True)
        help_lbl.pack(in_=rf, anchor='w', pady=(6, 0))

        def fill_mine():
            mine.delete(0, 'end')
            for aid in chosen:
                tag = 'AKTIV ' if self._abil_is_active(aid) else 'passiv'
                mine.insert('end', f'[{tag}] {aid:3d}  {self.abil_names.get(aid, f"?{aid}")}')

        def add_from(lb, ids):
            def _add(_=None):
                sel = lb.curselection()
                if not sel:
                    return
                if len(chosen) >= 9:
                    messagebox.showwarning('Voll', 'Maximal 9 Faehigkeiten pro Charakter.',
                                           parent=dlg)
                    return
                chosen.append(ids[sel[0]])
                fill_mine()
            return _add

        def show_help_from(lb, ids):
            def _help(_=None):
                sel = lb.curselection()
                if sel:
                    aid = ids[sel[0]]
                    help_lbl.config(text=self._abil_info(aid) + '\n'
                                    + self.abil_help.get(aid, ''))
            return _help

        def remove(_=None):
            sel = mine.curselection()
            if sel:
                chosen.pop(sel[0])
                fill_mine()

        def ok():
            avar.set(', '.join(str(v) for v in [set_id] + chosen))
            dlg.destroy()
            if var is not None:
                self.status_var.set('Faehigkeiten gewaehlt - "Design speichern" '
                                    'nicht vergessen!')
            elif auto_apply:
                self._apply_char()
                self.status_var.set('Faehigkeiten direkt uebernommen '
                                    '(noch nicht in ROM gespeichert).')
            else:
                self.status_var.set('Faehigkeiten gesetzt - "Werte uebernehmen" nicht vergessen!')

        lb_act.bind('<Double-Button-1>', add_from(lb_act, ids_act))
        lb_act.bind('<<ListboxSelect>>', show_help_from(lb_act, ids_act))
        lb_pas.bind('<Double-Button-1>', add_from(lb_pas, ids_pas))
        lb_pas.bind('<<ListboxSelect>>', show_help_from(lb_pas, ids_pas))
        mine.bind('<Double-Button-1>', remove)
        btns = ttk.Frame(rf)
        btns.pack(fill='x', pady=(6, 0))
        ttk.Button(btns, text='Entfernen', command=remove).pack(side='left')
        ttk.Button(btns, text='OK', command=ok).pack(side='right')
        ttk.Button(btns, text='Abbrechen', command=dlg.destroy).pack(side='right', padx=6)
        fill_mine()

    def _apply_char(self):
        li = self._sel_line()
        if li is None:
            return
        try:
            updates = {tok: int(self.stat_vars[tok].get()) for _, tok in STAT_FIELDS}
            equip = [int(x) for x in re.split(r'[,\s]+', self.equip_var.get().strip()) if x]
            abil = [int(x) for x in re.split(r'[,\s]+', self.abil_var.get().strip()) if x]
            if len(equip) > 10 or len(abil) > 10:
                raise ValueError('max. 10 Eintraege')
            for v in list(updates.values()) + equip + abil:
                if not 0 <= v <= 65535:
                    raise ValueError(f'Wert {v} ausserhalb 0..65535')
        except ValueError as e:
            messagebox.showerror('Ungueltige Eingabe', str(e))
            return
        equip += [0] * (10 - len(equip))
        abil += [0] * (10 - len(abil))
        updates.update({t: v for t, v in zip(EQUIP_TOKENS, equip)})
        updates.update({t: v for t, v in zip(ABIL_TOKENS, abil)})
        if self.type_var.get():
            updates[TOK_TYPE] = int(self.type_var.get().split(' ')[0])
        self.status_lines[li] = replace_tokens(self.status_lines[li], updates)
        # Typ auch in der Listenansicht aktualisieren
        self.char_rows = [(l, u, n, updates.get(TOK_TYPE, t) if l == li else t)
                          for l, u, n, t in self.char_rows]
        self._fill_charlist()
        self.dirty_status = True
        self.status_var.set('Charakter geaendert (noch nicht in ROM gespeichert).')

    # ---------- Turm ----------
    def _fill_unit_choices(self):
        # Gegner-taugliche Einheiten zuerst; Roster-Charaktere (typ=1) markiert,
        # da sie als Gegner ihre Stats aus dem Spielstand ziehen wuerden
        self.unit_char['values'] = (
            [f'{i} {self.names.get(i, "?")}' for i in sorted(self.enemy_pool)]
            + [f'{i} {self.names.get(i, "?")} [Roster!]'
               for i in sorted(self.safe_units - self.enemy_pool)])

    def _load_floor(self):
        if not self.fs:
            return
        floor = int(self.floor_var.get())
        if floor not in self.tower_cache:
            self.tower_cache[floor] = floor_units(self.fs, floor)
        if floor not in self.party_cache:
            self.party_cache[floor] = party_slots(self.fs, floor)
        self.tree.delete(*self.tree.get_children())
        for u in self.tower_cache[floor]:
            nm = self.names.get(u['char'], f'?{u["char"]}')
            team = {3: 'Gegner', 1: 'Spieler'}.get(u['active'], u['active'])
            self.tree.insert('', 'end', iid=str(u['slot']),
                             values=(u['slot'], team, u['char'], nm, u['level'],
                                     u['x'], u['y'], u['dir']))
        self.ptree.delete(*self.ptree.get_children())
        for s in self.party_cache[floor]:
            self.ptree.insert('', 'end', iid=str(s['id']), values=(s['id'], s['x'], s['y']))
        mp = self.btower.get(floor)
        if mp in getattr(self, '_map_choice_ids', []):
            self.map_combo.current(self._map_choice_ids.index(mp))
        self._draw_map(floor)

    def _load_map_names(self):
        """Frei vergebene Map-Namen aus map_names.json laden (Editor-Komfort)."""
        self.map_names = {}
        try:
            with open(MAP_NAMES_FILE, encoding='utf-8') as f:
                self.map_names = {int(k): v for k, v in json.load(f).items()}
        except (OSError, ValueError):
            pass

    def _refresh_map_combo(self):
        """Dropdown-Beschriftungen (mit Namen) neu aufbauen, Auswahl erhalten."""
        keep = self.map_combo.current()
        vals = []
        for mp in self._map_choice_ids:
            fls = self._map_donor_floors.get(mp, [])
            nm = self.map_names.get(mp)
            label = f'Map {mp}'
            if nm:
                label += f' - {nm}'
            if fls:
                label += f'  (Etage {", ".join(str(f) for f in fls)})'
            else:
                kind, nr = getattr(self, 'map_fb_donors', {}).get(mp, ('?', '?'))
                src = 'Free Battle' if kind == 'fb' else 'Story-Kampf'
                label += f'  (STORY, {src} {nr})'
            vals.append(label)
        self.map_combo['values'] = vals
        if 0 <= keep < len(vals):
            self.map_combo.current(keep)

    def _rename_map(self):
        """Der aktuell im Dropdown gewaehlten Map einen freien Namen geben."""
        sel = self.map_combo.current()
        if sel < 0:
            messagebox.showinfo('Map benennen', 'Erst oben eine Map im Dropdown waehlen.')
            return
        mp = self._map_choice_ids[sel]
        cur = self.map_names.get(mp, '')
        name = simpledialog.askstring(
            'Map benennen', f'Name fuer Map {mp} (leer = Name entfernen):',
            initialvalue=cur, parent=self)
        if name is None:
            return
        name = name.strip()
        if name:
            self.map_names[mp] = name
        else:
            self.map_names.pop(mp, None)
        try:
            with open(MAP_NAMES_FILE, 'w', encoding='utf-8') as f:
                json.dump({str(k): v for k, v in self.map_names.items()},
                          f, ensure_ascii=False, indent=1)
        except OSError as e:
            messagebox.showerror('Map benennen', f'Konnte nicht speichern: {e}')
            return
        self._refresh_map_combo()
        self.map_combo.current(sel)
        self.status_var.set(f'Map {mp} benannt: "{name}"' if name
                            else f'Map {mp}: Name entfernt')

    def _change_map(self):
        """Etage auf eine andere Map umstellen: Terrain-/Spawn-Subfiles kommen
        von einer Donor-Etage, die diese Map original nutzt; Spieler-Spawns
        werden von dort uebernommen. btower (.inc + ARM9) wird beim Speichern
        gepatcht."""
        floor = int(self.floor_var.get())
        sel = self.map_combo.current()
        if sel < 0:
            return
        new_map = self._map_choice_ids[sel]
        if new_map == self.btower.get(floor):
            return
        # Kleinste Donor-Etage der Ziel-Map waehlen (schont ROM-Platz; groessere
        # NARCs werden beim Speichern per Relocation in freien ROM-Platz gelegt)
        donors = [fl for fl, mp in sorted(self.btower_orig.items()) if mp == new_map]
        if donors:
            donor = min(donors, key=lambda fl:
                        len(self.fs.read(f'/yamada/DataBase/db_dpos_{900+fl}.narc')))
            self.narc_base[floor] = self.fs.read(f'/yamada/DataBase/db_dpos_{900+donor}.narc')
            donor_label = f'Etage {donor}'
            # Spieler-Startpositionen von der Donor-Etage uebernehmen (alte
            # Positionen waeren auf der neuen Map evtl. nicht begehbar)
            donor_party = party_slots(self.fs, donor)
            for s, d in zip(self.party_cache[floor], donor_party):
                s['x'], s['y'] = d['x'], d['y']
        elif new_map in self.map_fb_donors:
            # STORY-MAP via Free-Battle-/Story-Donor: Terrain-Subfiles 1-3
            # vom Donor, Subfile 0 aufs Turmformat (128x54 B) gebracht.
            # Die Party-Dateien dieser Kaempfe haben ein anderes Format ->
            # Deploy-Slots automatisch auf einen begehbaren Cluster setzen.
            kind, nr = self.map_fb_donors[new_map]
            base_nr = 800 + nr if kind == 'fb' else nr
            don = self.fs.read(f'/yamada/DataBase/db_dpos_{base_nr:03d}.narc')
            dsubs = narc_subfiles(don)
            # Subfile 0 kommt von der AKTUELLEN Etage (bewaehrtes Turm-Slot-
            # Layout: leere Records behalten ihre aktiv-Bytes), Terrain vom
            # Donor. 3-Subfile-Story-dpos haben KEIN Spawn-Subfile (9288) ->
            # das kommt ebenfalls von der eigenen Etage.
            template = self.fs.read(f'/yamada/DataBase/db_dpos_{900+floor}.narc')
            tsubs = narc_subfiles(template)
            if len(dsubs) == 4:
                terr = list(dsubs[1:])
            else:
                def _is_grid(s):
                    return len(s) == 1521 and set(s) <= {0, 10, 255}
                g_terr, g_other = ((dsubs[1], dsubs[2]) if _is_grid(dsubs[1])
                                   else (dsubs[2], dsubs[1]))
                terr = [tsubs[1], g_terr, g_other]
            from formats import narc_rebuild
            self.narc_base[floor] = narc_rebuild(template, [tsubs[0]] + terr)
            donor_label = ('Free Battle ' if kind == 'fb' else 'Story-Kampf ') + str(nr)
            grid = dsubs[2]
            cells = [(x, y) for y in range(39) for x in range(39)
                     if y * 39 + x < len(grid) and grid[y * 39 + x] == 10]
            if cells:
                cx = sum(c[0] for c in cells) / len(cells)
                cy = sum(c[1] for c in cells) / len(cells)
                p0 = min(cells, key=lambda c: (c[0] - cx) ** 2 + (c[1] - cy) ** 2)
                near = sorted(cells, key=lambda c: (c[0] - p0[0]) ** 2 + (c[1] - p0[1]) ** 2)
                for s, (gx, gy) in zip(self.party_cache[floor], near):
                    s['x'], s['y'] = gx + 1, gy + 1
        else:
            messagebox.showerror(
                'Map-Wechsel', f'Kein Donor fuer Map {new_map} gefunden.')
            self._load_floor()
            return
        self.btower[floor] = new_map
        self.dirty_maps.add(floor)
        self.dirty_floors.add(floor)
        self.dirty_party.add(floor)
        self.map_cache.pop(floor, None)
        self.walk_cache.pop(floor, None)
        self._load_floor()
        self.status_var.set(
            f'Etage {floor} -> Map {new_map} (Donor: {donor_label}). Gegner-Positionen '
            'passen evtl. nicht mehr - am besten randomisieren! (noch nicht gespeichert)')

    # ---------- Karte ----------
    # WICHTIG: Einheiten-/Party-Koordinaten sind 1-basiert, das Terrain-Grid
    # und die Pixel-Karte 0-basiert. Zelle (x,y) einer Einheit liegt also bei
    # Pixel ((x-1)*8, (y-1)*8). Verifiziert: mit diesem Versatz stehen alle
    # 739 Einheiten aller 30 Etagen exakt auf begehbaren Grid-Feldern (Wert 10).
    CELL = 8  # Pixel pro Spielfeld-Zelle

    def _map_image(self, floor):
        if floor not in self.map_cache:
            img = None
            map_id = self.btower.get(floor)
            if map_id is not None:
                png = map_png(self.fs, map_id)
                if png:
                    img = tk.PhotoImage(data=png)
            self.map_cache[floor] = img
        return self.map_cache[floor]

    def _draw_map(self, floor):
        c = self.map_canvas
        c.delete('all')
        img = self._map_image(floor)
        if img is None:
            c.configure(width=460, height=400)
            c.create_text(230, 200, text='(keine Karte)', fill='#aaa')
            return
        # Canvas exakt auf Kartengroesse bringen (kein leerer Rand);
        # nur uebergrosse Karten deckeln und dann Scrollbalken zeigen
        MAXW, MAXH = 620, 560
        w, h = img.width(), img.height()
        c.configure(width=min(w, MAXW), height=min(h, MAXH))
        if w > MAXW:
            self.map_hbar.grid()
        else:
            self.map_hbar.grid_remove()
        if h > MAXH:
            self.map_vbar.grid()
        else:
            self.map_vbar.grid_remove()
        c.create_image(0, 0, anchor='nw', image=img)
        c.configure(scrollregion=(0, 0, img.width(), img.height()))
        z = self.CELL
        # begehbare Felder dezent markieren (hilft beim Level-Bauen)
        for gx, gy in self._walkable_cells(floor):
            cx, cy = gx * z + z // 2, gy * z + z // 2
            c.create_rectangle(cx - 1, cy - 1, cx + 1, cy + 1,
                               fill='#40c040', outline='')
        sel_enemy = {int(i) for i in self.tree.selection()}
        sel_dep = {int(i) for i in self.ptree.selection()}
        for u in self.tower_cache.get(floor, []):
            x0, y0 = (u['x'] - 1) * z, (u['y'] - 1) * z
            hot = u['slot'] in sel_enemy
            fill = '#e02020' if u['active'] == 3 else '#20c0c0'   # rot=Gegner, tuerkis=Spielerseite
            c.create_rectangle(x0, y0, x0 + z, y0 + z, fill=fill,
                               outline='#ffff00' if hot else '#600',
                               width=2 if hot else 1)
        for s in self.party_cache.get(floor, []):
            x0, y0 = (s['x'] - 1) * z, (s['y'] - 1) * z
            hot = s['id'] in sel_dep
            c.create_rectangle(x0, y0, x0 + z, y0 + z, fill='#2050ff',
                               outline='#ffff00' if hot else '#006',
                               width=2 if hot else 1)

    def _canvas_click(self, ev):
        floor = int(self.floor_var.get())
        # Pixel -> 1-basierte Einheiten-Koordinate
        cx = int(self.map_canvas.canvasx(ev.x)) // self.CELL + 1
        cy = int(self.map_canvas.canvasy(ev.y)) // self.CELL + 1
        # Klick auf vorhandenen Marker -> auswaehlen
        for u in self.tower_cache.get(floor, []):
            if (u['x'], u['y']) == (cx, cy):
                self.tree.selection_set(str(u['slot']))
                self._last_sel = 'enemy'
                return
        for s in self.party_cache.get(floor, []):
            if (s['x'], s['y']) == (cx, cy):
                self.ptree.selection_set(str(s['id']))
                self._last_sel = 'deploy'
                return
        # freie Zelle -> gewaehlte Einheit dorthin versetzen
        if self._last_sel == 'deploy':
            s = self._cur_pslot()
            if not s:
                return
            s['x'], s['y'] = cx, cy
            self.dirty_party.add(floor)
            sel = str(s['id'])
        else:
            u = self._cur_unit()
            if not u:
                return
            u['x'], u['y'] = cx, cy
            self.dirty_floors.add(floor)
            sel = str(u['slot'])
        self._load_floor()
        (self.ptree if self._last_sel == 'deploy' else self.tree).selection_set(sel)
        self.status_var.set(f'Position -> ({cx},{cy}) gesetzt (noch nicht gespeichert).')

    def _cur_unit(self):
        sel = self.tree.selection()
        if not sel:
            return None
        slot = int(sel[0])
        floor = int(self.floor_var.get())
        for u in self.tower_cache[floor]:
            if u['slot'] == slot:
                return u
        return None

    def _cur_ai_narc(self, floor):
        """Aktueller NARC dieser Etage als Basis fuer AI-Skill-Edits."""
        return (self.ai_base.get(floor) or self.narc_base.get(floor)
                or self.fs.read(f'/yamada/DataBase/db_dpos_{900+floor}.narc'))

    def _skill_chaos(self):
        """Skill-Chaos: gibt ALLEN Gegnern der aktuellen Etage je 1-5 zufaellige
        Battle-Skills, die ihre AI im Kampf einsetzt (Subfile 1). Ideal NACH
        dem Randomisieren - die Tabelle liefert die Gegner."""
        from tower import set_ai_block, ai_block_count
        if not self.fs:
            return
        floor = int(self.floor_var.get())
        enemies = sorted((u for u in self.tower_cache.get(floor, []) if u['slot'] >= 16),
                         key=lambda u: u['slot'])
        if not enemies:
            messagebox.showinfo('Skill-Chaos', 'Keine Gegner auf der Etage - erst randomisieren.')
            return
        # Pool = alle benannten Battle-Skills (kein reiner Bankai-/S-Press-Zwang)
        pool = [sid for sid, nm in self.skill_names.items()
                if nm.strip() and 1 <= sid <= 116]
        if not pool:
            return
        narc = self._cur_ai_narc(floor)
        if ai_block_count(narc) < len(enemies):
            messagebox.showwarning('Skill-Chaos',
                'AI-Bloecke passen nicht zur Etage (umgebaut?). Erst neu laden/randomisieren.')
            return
        for i, u in enumerate(enemies):
            n = random.randint(1, 5)
            narc = set_ai_block(narc, i, random.sample(pool, min(n, len(pool))))
        self.ai_base[floor] = narc
        self.dirty_floors.add(floor)
        self._load_floor()
        self.status_var.set(f'SKILL-CHAOS: {len(enemies)} Gegner auf Etage {floor} '
                            'mit je 1-5 Zufalls-Skills - noch nicht gespeichert.')

    def _edit_ai_skills(self):
        """Subfile-1-AI-Skill-Liste der gewaehlten Gegner-Einheit bearbeiten.
        Block-Index = Position der Einheit unter den GEGNERN (Slot-Reihenfolge)."""
        from tower import ai_block, set_ai_block, ai_block_count
        u = self._cur_unit()
        if not u:
            messagebox.showinfo('AI-Skills', 'Erst eine Gegner-Einheit in der Tabelle waehlen.')
            return
        floor = int(self.floor_var.get())
        narc = self._cur_ai_narc(floor)
        # Block-Index: Position dieser Einheit in Slot-Reihenfolge aller Records
        recs = sorted(self.tower_cache[floor], key=lambda x: x['slot'])
        try:
            bidx = recs.index(u)
        except ValueError:
            bidx = 0
        if bidx >= ai_block_count(narc):
            messagebox.showwarning('AI-Skills',
                'Fuer diese Einheit gibt es keinen AI-Block (Etage evtl. umgebaut). '
                'AI-Skills lassen sich nur fuer die Original-Slot-Reihenfolge editieren.')
            return
        _hdr, cur = ai_block(narc, bidx)
        # nur benutzbare Battle-Skills (db_skill) anbieten, IDs 1..116
        cur_sk = [i for i in cur if i in self.skill_names and self.skill_names[i].strip()]

        dlg = tk.Toplevel(self); dlg.title(f'AI-Skills - {self.names.get(u["char"],"?")}')
        dlg.transient(self); dlg.grab_set(); dlg.geometry('620x460')
        ttk.Label(dlg, text=f'Skills, die die AI dieses Gegners im Kampf einsetzt '
                  f'(Block {bidx}):', foreground=G_GOLD).pack(anchor='w', padx=8, pady=(8, 2))
        body = ttk.Frame(dlg); body.pack(fill='both', expand=True, padx=8)
        # links: alle Skills, rechts: gewaehlte
        lf = ttk.Frame(body); lf.pack(side='left', fill='both', expand=True)
        q = tk.StringVar()
        ttk.Entry(lf, textvariable=q).pack(fill='x')
        lb = tk.Listbox(lf, width=34); lb.pack(fill='both', expand=True, pady=4)
        ids = []
        def fill(*_):
            lb.delete(0, 'end'); ids.clear()
            s = q.get().lower()
            for sid in sorted(self.skill_names):
                nm = self.skill_names[sid]
                if not nm.strip() or (s and s not in nm.lower() and s != str(sid)):
                    continue
                lb.insert('end', f'{sid:3d}  {nm}'); ids.append(sid)
        q.trace_add('write', fill); fill()
        rf = ttk.LabelFrame(body, text='AI benutzt (max. 30)', padding=6)
        rf.pack(side='left', fill='both', padx=(8, 0))
        mine = tk.Listbox(rf, width=30); mine.pack(fill='both', expand=True)
        chosen = list(cur_sk)
        def refill():
            mine.delete(0, 'end')
            for sid in chosen:
                mine.insert('end', f'{sid:3d}  {self.skill_names.get(sid, "?")}')
        refill()
        def add(_=None):
            s = lb.curselection()
            if s and len(chosen) < 30 and ids[s[0]] not in chosen:
                chosen.append(ids[s[0]]); refill()
        def rem(_=None):
            s = mine.curselection()
            if s: chosen.pop(s[0]); refill()
        lb.bind('<Double-Button-1>', add); mine.bind('<Double-Button-1>', rem)
        def ok():
            # Passiva des Original-Blocks erhalten (nicht-Skill-IDs anhaengen)
            passives = [i for i in cur if i not in cur_sk]
            new = set_ai_block(narc, bidx, chosen + passives)
            self.ai_base[floor] = new
            self.dirty_floors.add(floor)
            dlg.destroy()
            self.status_var.set(f'AI-Skills von {self.names.get(u["char"],"?")} gesetzt '
                                f'({len(chosen)} Skills) - noch nicht gespeichert.')
        btns = ttk.Frame(rf); btns.pack(fill='x', pady=(6, 0))
        ttk.Button(btns, text='Entfernen', command=rem).pack(side='left')
        ttk.Button(btns, text='OK', command=ok, style='Accent.TButton').pack(side='right')
        ttk.Button(btns, text='Abbrechen', command=dlg.destroy).pack(side='right', padx=6)

    def _edit_unit_abilities(self):
        """Skill-Picker fuer den gewaehlten Turm-Gegner. WICHTIG: Faehigkeiten
        haengen am CHARAKTER (ARM9-Stat-Tabelle), nicht an der Platzierung -
        die Aenderung gilt also ueberall, wo dieser Charakter auftaucht.
        Achtung: Der Randomizer wuerfelt Loadouts neu - Skills fuer Test-
        Gegner erst NACH dem Randomisieren vergeben."""
        u = self._cur_unit()
        if not u:
            messagebox.showinfo('Keine Einheit',
                                'Erst eine Einheit in der Tabelle waehlen.')
            return
        char = u['char']
        if not any(un == char for _, un, _, _ in self.char_rows):
            messagebox.showerror('Unbekannt', f'Charakter {char} nicht in db_status.')
            return
        # Charakter-Tab auf den Char filtern und auswaehlen, dann Picker
        self.filter_var.set('Alle')
        self.search_var.set(str(char))      # Trace fuellt die Liste
        li = next(l for l, un, _, _ in self.char_rows if un == char)
        if li not in self._visible:
            messagebox.showerror('Ausgeblendet',
                                 f'{self.names.get(char, "?")} ist im Crash-Schutz '
                                 'ausgeblendet (unfertige Einheit).')
            return
        idx = self._visible.index(li)
        self.charlist.selection_clear(0, 'end')
        self.charlist.selection_set(idx)
        self.charlist.see(idx)
        self._on_char_select()
        self.nb.select(0)                   # Charaktere-Tab anzeigen
        self._pick_abilities(auto_apply=True)

    def _on_unit_select(self, _=None):
        u = self._cur_unit()
        if not u:
            return
        self._last_sel = 'enemy'
        self.unit_char.set(f"{u['char']} {self.names.get(u['char'], '?')}")
        for f in ('level', 'x', 'y', 'dir'):
            self.unit_vars[f].set(u[f])
        self.unit_vars['ai'].set(u['raw'][1])
        self.unit_vars['aggro'].set(u['raw'][2])
        self.unit_team.set({3: '3 Gegner', 1: '1 Spieler'}.get(u['active'],
                                                               str(u['active'])))
        self._set_face(self.tface_label, self.face_by_unit.get(u['char']))
        self._draw_map(int(self.floor_var.get()))

    def _apply_unit(self):
        u = self._cur_unit()
        if not u:
            return
        try:
            char = int(self.unit_char.get().split()[0])
            vals = {f: int(self.unit_vars[f].get()) for f in ('level', 'x', 'y', 'dir')}
            ai = int(self.unit_vars['ai'].get() or 0)
            aggro = int(self.unit_vars['aggro'].get() or 0)
            if char not in self.names:
                raise ValueError(f'unbekannte Charakter-ID {char}')
            if not 0 <= vals['dir'] <= 3:
                raise ValueError('dir muss 0..3 sein')
            if not (0 <= ai <= 65535 and 0 <= aggro <= 65535):
                raise ValueError('ai/aggro muessen 0..65535 sein')
        except (ValueError, IndexError) as e:
            messagebox.showerror('Ungueltige Eingabe', str(e))
            return
        if char not in self.safe_units:
            messagebox.showerror(
                'Unfertiger Charakter',
                f'"{self.names.get(char)}" (ID {char}) hat keine vollstaendigen '
                'Kampfdaten in der ROM und wuerde das Spiel crashen - nicht einsetzbar.')
            return
        u['char'] = char
        if self.unit_team.get():
            u['active'] = int(self.unit_team.get().split()[0])
        u['raw'][1] = ai
        u['raw'][2] = aggro
        u.update(vals)
        self.dirty_floors.add(int(self.floor_var.get()))
        self._load_floor()
        # Charaktere ausserhalb des Gegner-Pools (Roster-Typen, rekrutierbare
        # Duplikate wie 114/118, nie-als-Gegner-genutzte) ziehen als Gegner ihre
        # Stats aus dem SPIELSTAND oder sind kaputt -> Enemy-Variante vorschlagen
        if u['active'] == 3 and char not in self.enemy_pool:
            nm = self.names.get(char, '')
            alts = [un for _, un, n, t in self.char_rows
                    if n == nm and un != char and un in self.enemy_pool]
            hint = (f' Besser: Enemy-Variante {alts[0]} {nm} nehmen!' if alts
                    else ' (keine Enemy-Variante vorhanden)')
            messagebox.showwarning(
                'Kein echter Gegner-Charakter',
                f'"{nm}" (ID {char}) wird vom Originalspiel nie als Gegner genutzt '
                f'oder haengt am Spieler-Roster: er spawnt mit SPIELSTAND-Stats '
                f'statt dem eingestellten Level (oder ist kaputt).{hint}')
        elif u['active'] == 3 and char in self.noncom_units:
            messagebox.showwarning(
                'NONCOM-Charakter',
                f'"{self.names.get(char, "?")}" (ID {char}) ist ein NONCOM-Typ '
                '(Healer/Zivilist): normale Angriffe/Pressure koennen das Spiel '
                'CRASHEN (in-game: Female Spirit). Nur einsetzen, wenn er '
                'ausschliesslich Skills nutzen soll - auf eigenes Risiko!')
        self.status_var.set('Einheit geaendert (noch nicht in ROM gespeichert).')

    def _new_unit(self):
        floor = int(self.floor_var.get())
        units = self.tower_cache[floor]
        used = {u['slot'] for u in units}
        slot = next(s for s in range(16, 129) if s not in used)
        ref = units[-1] if units else {'char': 151, 'level': 1, 'x': 20, 'y': 20,
                                       'dir': 0, 'unk3': 10, 'unk7': 1, 'raw': [0] * 19}
        # active = TEAM: 3 = Gegnerseite, 1 = Spielerseite
        units.append({'slot': slot, 'active': ref.get('active', 3), 'char': ref['char'],
                      'level': ref['level'],
                      'unk3': ref.get('unk3', 10), 'x': ref['x'] + 1, 'y': ref['y'],
                      'dir': ref['dir'], 'unk7': ref.get('unk7', 1),
                      'raw': list(ref.get('raw', [0] * 19))})
        self.dirty_floors.add(floor)
        self._load_floor()
        self.tree.selection_set(str(slot))

    def _del_unit(self):
        u = self._cur_unit()
        if not u:
            return
        floor = int(self.floor_var.get())
        self.tower_cache[floor] = [x for x in self.tower_cache[floor] if x['slot'] != u['slot']]
        self.dirty_floors.add(floor)
        self._load_floor()

    def _copy_unit(self):
        """Gewaehlte Einheit ins Clipboard legen (Char/Level/Dir/Team/AI/raw).
        Position wird beim Einfuegen neu vergeben."""
        u = self._cur_unit()
        if not u:
            messagebox.showinfo('Kopieren', 'Erst eine Einheit in der Tabelle waehlen.')
            return
        self._unit_clip = {'char': u['char'], 'level': u['level'],
                           'active': u['active'], 'dir': u['dir'],
                           'unk3': u.get('unk3', 10), 'unk7': u.get('unk7', 1),
                           'raw': list(u['raw'])}
        self.status_var.set(
            f'"{self.names.get(u["char"], "?")}" (Lv{u["level"]}) kopiert - '
            '"Einfuegen" fuegt eine Kopie auf der aktuellen Etage ein.')

    def _paste_unit(self):
        """Kopierte Einheit als neue Kopie auf die aktuelle Etage setzen -
        gleiche Werte, freier Slot, freie begehbare Zelle."""
        if not self._unit_clip:
            messagebox.showinfo('Einfuegen', 'Erst eine Einheit "Kopieren".')
            return
        floor = int(self.floor_var.get())
        if floor not in self.tower_cache:
            self._load_floor()
        units = self.tower_cache[floor]
        used = {u['slot'] for u in units}
        slot = next((s for s in range(16, 129) if s not in used), None)
        if slot is None:
            messagebox.showerror('Einfuegen', 'Kein freier Slot auf der Etage.')
            return
        clip = self._unit_clip
        # Sprite-Limit nur pruefen, wenn der Char noch NICHT auf der Etage ist
        # (Duplikat desselben Chars kostet keinen zusaetzlichen Sprite-Slot)
        uniq = {u['char'] for u in units if u['slot'] >= 16}
        if clip['char'] not in uniq and len(uniq) + 1 > MAX_UNIQUE_SPRITES:
            messagebox.showerror('Sprite-Limit',
                                 f'Mehr als {MAX_UNIQUE_SPRITES} verschiedene '
                                 'Charaktere auf der Etage = Crash!')
            return
        blocked = {(u['x'] - 1, u['y'] - 1) for u in units}
        for s in self.party_cache.get(floor, []):
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    blocked.add((s['x'] - 1 + dx, s['y'] - 1 + dy))
        cells = [c for c in self._walkable_cells(floor) if c not in blocked]
        if not cells:
            messagebox.showerror('Einfuegen', 'Keine freie begehbare Zelle gefunden.')
            return
        gx, gy = random.choice(cells)
        units.append({'slot': slot, 'active': clip['active'], 'char': clip['char'],
                      'level': clip['level'], 'unk3': clip['unk3'],
                      'x': gx + 1, 'y': gy + 1, 'dir': clip['dir'],
                      'unk7': clip['unk7'], 'raw': list(clip['raw'])})
        self.dirty_floors.add(floor)
        self._load_floor()
        self.tree.selection_set(str(slot))
        self.status_var.set(
            f'"{self.names.get(clip["char"], "?")}" (Lv{clip["level"]}) auf Slot '
            f'{slot} bei ({gx + 1},{gy + 1}) eingefuegt (noch nicht gespeichert).')

    # ---------- Randomizer ----------
    def _walkable_cells(self, floor):
        """Begehbare 0-basierte Grid-Zellen der Etage (Terrain-Grid Subfile 2, Wert 10).
        Einheiten-Koordinaten sind 1-basiert: Einheit (x,y) steht auf Zelle (x-1,y-1)."""
        if floor not in self.walk_cache:
            data = self.narc_base.get(floor) or self.fs.read(
                f'/yamada/DataBase/db_dpos_{900+floor}.narc')
            grid = narc_subfiles(data)[2]
            self.walk_cache[floor] = [(x, y) for y in range(39) for x in range(39)
                                      if y * 39 + x < len(grid) and grid[y * 39 + x] == 10]
        return self.walk_cache[floor]

    def _randomizer_info(self):
        messagebox.showinfo(
            'Randomizer - Infos',
            'Ersetzt alle Gegner der Etage durch Zufalls-Charaktere.\n\n'
            '- Level = Ziel-Level +-5; Stats skalieren mit Faktor\n'
            '  (1+Level/100) x 1.25 (Ausreisser-Stats gedaempft).\n'
            '- Jeder Charakter max. 1x; max. 25 pro Etage (in-game\n'
            '  bisektiert, 26 = Crash). Grund sind laut Decompiler die\n'
            '  32 Aktor-Plaetze, die die Deploy-Party zuerst belegt -\n'
            '  nicht die Sprite-Zahl. Riesen-Sprites (Jidanbo, Menos ...)\n'
            '  und NONCOM-Chars (Healer/Zivilisten) sind ausgeschlossen.\n'
            '- Jeder Gegner bekommt 7 Zufalls-Skills (4 aktiv/3 passiv)\n'
            '  (Hit & Run ausgenommen - AI-Endloszuege). Die Pflicht-\n'
            '  Faehigkeiten 370/401 bleiben erhalten, wenn der Charakter\n'
            '  sie im Original hatte (Verdacht auf den HP-Bug).\n'
            '- Alle Gegner landen in Welle 0, erscheinen also beim\n'
            '  Betreten der Etage (vorher konnten geklonte Nachschub-\n'
            '  Slots dafuer sorgen, dass Gegner unsichtbar blieben).\n'
            '- Positionen: nur begehbare Felder, nie auf/neben Deploy-\n'
            '  Slots; Blickrichtung zum Deploy-Zentrum.\n\n'
            'Filter-Zeile: "nur aus" wuerfelt nur aus einem Batch,\n'
            '"ohne" schliesst einen Batch aus. Challenge "Gegner spawnen\n'
            'bei den Teammates" setzt alle Gegner nah an die Deploy-Zone.\n\n'
            'Preset-Batch: setzt eine komplette thematische Gruppe ein\n'
            '(gekappt auf Etagen-/25er-Limit). "ALLE 30 Etagen" macht\n'
            'einen Challenge-Run mit den aktuellen Einstellungen.')

    def _apply_preset_batch(self):
        name = self.preset_var.get()
        ids = PRESET_BATCHES.get(name)
        if ids:
            self._randomize_floor(preset=ids, preset_name=name)

    def _randomize_all_floors(self):
        """Challenge-Run: alle 30 Etagen mit den aktuellen Einstellungen
        (Ziel-Level, Anzahl, Verhalten, Batch-Filter, Challenge) randomisieren."""
        if not self.fs:
            return
        if not messagebox.askyesno(
                'Challenge-Run',
                'Wirklich ALLE 30 Etagen mit den aktuellen Randomizer-'
                'Einstellungen neu wuerfeln?'):
            return
        cur = int(self.floor_var.get())
        for fl in range(1, 31):
            self.floor_var.set(fl)
            self._load_floor()
            self._randomize_floor()
        self.floor_var.set(cur)
        self._load_floor()
        self.status_var.set('CHALLENGE-RUN: alle 30 Etagen randomisiert '
                            '(noch nicht gespeichert).')

    def _randomize_floor(self, god=False, preset=None, preset_name=''):
        if not self.fs:
            return
        # Etage 30 = XP-Farm: doppelt bestaetigen, bevor sie ueberschrieben wird
        if int(self.floor_var.get()) == 30:
            if not messagebox.askyesno(
                    'Etage 30 - XP-Farm!',
                    'Etage 30 ist als XP-Farm eingerichtet (1 Oneshot-Gegner).\n'
                    'Wirklich randomisieren und die Farm ueberschreiben?'):
                return
            if not messagebox.askyesno(
                    'Etage 30 - sicher?',
                    'Zweite Bestaetigung: Etage 30 wirklich ueberschreiben?'):
                return
        floor = int(self.floor_var.get())
        try:
            nmin = int(self.rand_min_var.get())
            nmax = int(self.rand_max_var.get())
            if god:
                lvl_lo, lvl_hi = 91, 99
            else:
                lvl = int(self.rand_level_var.get())
                if not 1 <= lvl <= 99:
                    raise ValueError('Ziel-Level muss 1..99 sein')
                lvl_lo, lvl_hi = max(1, lvl - 5), min(99, lvl + 5)
            if not 1 <= nmin <= nmax <= 113:
                raise ValueError('Gegneranzahl muss 1..113 sein (min <= max)')
        except ValueError as e:
            messagebox.showerror('Ungueltige Eingabe', str(e))
            return
        units = self.tower_cache[floor]
        keep = [u for u in units if u['slot'] < 16]          # Reserve-Slots unangetastet
        # Vanilla-Templates (AI-raw/Team) zuerst; zusaetzliche Slots ueber das
        # Original hinaus sind in-game verifiziert (Etage 1: Slots 30-40 ok) -
        # bei Bedarf bis MAX_UNIQUE_SPRITES mit Extra-Slots auffuellen.
        templates = VANILLA_REF['floors'].get(str(floor))
        if not templates:
            raws = [list(u['raw']) for u in units if u['slot'] >= 16] or [[0] * 19]
            templates = [{'slot': 16 + i, 'active': 3, 'raw': random.choice(raws)}
                         for i in range(14)]    # Fallback: konservative 14
        templates = sorted(templates, key=lambda t: t['slot'])
        next_slot = templates[-1]['slot'] + 1
        while len(templates) < MAX_UNIQUE_SPRITES and next_slot <= 128:
            templates.append({'slot': next_slot, 'active': 3,
                              'raw': list(templates[0]['raw'])})
            next_slot += 1
        capacity = len(templates)
        # Kandidaten: begehbar, nicht auf/neben Spieler-Spawns, nicht doppelt belegt
        # (Grid ist 0-basiert, Einheiten-Koordinaten 1-basiert -> -1 beim Vergleich)
        blocked = set()
        for s in self.party_cache.get(floor, []):
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    blocked.add((s['x'] - 1 + dx, s['y'] - 1 + dy))
        blocked.update((u['x'] - 1, u['y'] - 1) for u in keep)
        cells = [c for c in self._walkable_cells(floor) if c not in blocked]
        # Jeder Charakter nur EINMAL pro Etage (User-Wunsch). Dadurch greift
        # das Sprite-Limit (25 unique in-game bisektiert, 26 = Crash) direkt
        # als Obergrenze der Gegnerzahl. Riesen-Sprites bleiben draussen.
        if preset:
            # Preset-Batch: komplette thematische Gruppe einsetzen
            # (nur Pool-Chars, Riesen + NONCOM raus; gekappt auf die Limits)
            pool = sorted(set(preset) & self.enemy_pool
                          - BIG_UNITS - self.noncom_units)
            count = min(len(pool), len(cells), capacity, MAX_UNIQUE_SPRITES)
        else:
            pool_set = self.enemy_pool - BIG_UNITS - self.noncom_units
            # Batch-Filter: nur aus einer Gruppe wuerfeln / eine ausschliessen
            only = getattr(self, 'rand_only', None)
            if only is not None and only.get() in PRESET_BATCHES:
                pool_set &= set(PRESET_BATCHES[only.get()])
            exc = getattr(self, 'rand_except', None)
            if exc is not None and exc.get() in PRESET_BATCHES:
                pool_set -= set(PRESET_BATCHES[exc.get()])
            pool = sorted(pool_set)
            if not pool:
                messagebox.showerror('Randomizer',
                                     'Batch-Filter laesst keine Charaktere uebrig.')
                return
            count = min(random.randint(nmin, nmax), len(cells), capacity,
                        MAX_UNIQUE_SPRITES, len(pool))
        if count == 0:
            messagebox.showerror('Randomizer', 'Keine freien begehbaren Felder gefunden.')
            return
        # Challenge "Gegner spawnen bei den Teammates": nur die naechsten
        # Zellen um das Deploy-Zentrum nutzen (1-Feld-Sicherheitsring bleibt)
        chal = getattr(self, 'rand_challenge', None)
        if chal is not None and 'Teammates' in chal.get():
            ps = self.party_cache.get(floor, [])
            if ps:
                pcx0 = sum(s['x'] for s in ps) / len(ps) - 1
                pcy0 = sum(s['y'] for s in ps) / len(ps) - 1
                cells = sorted(cells, key=lambda c: (c[0] - pcx0) ** 2
                               + (c[1] - pcy0) ** 2)[:max(count * 2, 16)]
        chars = random.sample(pool, count)   # ohne Zuruecklegen -> keine Doppelten
        behave = self.rand_behave.get() if hasattr(self, 'rand_behave') else 'Original'
        # Blickrichtung zum Deploy-Zentrum (0=Ost/+x, 1=Nord/-y, 2=West/-x,
        # 3=Sued/+y; aus Vanilla-Statistik abgeleitet, in-game bestaetigt)
        pslots = self.party_cache.get(floor, [])
        pcx = sum(s['x'] for s in pslots) / len(pslots) if pslots else 19.5
        pcy = sum(s['y'] for s in pslots) / len(pslots) if pslots else 19.5
        new_units = list(keep)
        for tpl, (gx, gy), char in zip(templates, random.sample(cells, count), chars):
            raw = list(tpl.get('raw', [0] * 19))
            # raw[0] = WELLE (dpos +0x10, s16). Nur Welle 0 spawnt beim
            # Betreten der Etage; 1-3 sind Nachschub, -3 (=65533) Sonderfaelle.
            # Aus Ghidra (Overlay 1, FUN_02182068) und gegen alle 499
            # Vanilla-Records gegengeprueft - 100 % trennscharf.
            # Die Vanilla-Templates der Etagen 5/6/9/23/24 enthalten
            # Nachschub-Slots (36 von 376); wird deren raw[0] mitgeklont,
            # steht der Gegner in der Tabelle, erscheint aber nicht.
            raw[0] = 0
            # raw[1] = AI-Typ, raw[2] = Aggressivitaet (Vanilla: 3/100 = jagt
            # den Spieler aktiv, 0/0 = wartet bis man sich naehert)
            if behave == 'Aggressiv':
                raw[1], raw[2] = 3, 100
            elif behave == 'Defensiv':
                raw[1], raw[2] = 0, 0
            dx, dy = pcx - (gx + 1), pcy - (gy + 1)
            if abs(dx) >= abs(dy):
                face = 0 if dx > 0 else 2
            else:
                face = 3 if dy > 0 else 1
            new_units.append({
                'slot': tpl['slot'], 'active': tpl.get('active', 3),
                'char': char,
                'level': random.randint(lvl_lo, lvl_hi),
                'unk3': 10, 'x': gx + 1, 'y': gy + 1,
                'dir': face, 'unk7': 1,
                'raw': raw,
            })
        self.tower_cache[floor] = new_units
        self.dirty_floors.add(floor)
        spawned = {u['char'] for u in new_units if u['slot'] >= 16}
        if god:
            n_boost = self._boost_stats(spawned,
                                        hp_f=3.0 * LEVEL_STAT_SCALE,
                                        st_f=2.0 * LEVEL_STAT_SCALE)
            self._load_floor()
            self.status_var.set(
                f'GOD-MODE Etage {floor}: {count} Gegner (Etagen-Limit {capacity}) '
                f'Lv{lvl_lo}-{lvl_hi}, {n_boost} Chars: Stats '
                f'HPx{3.0 * LEVEL_STAT_SCALE:.2f}/x{2.0 * LEVEL_STAT_SCALE:.2f} '
                '+ Skills randomisiert (noch nicht gespeichert).')
        else:
            # Stats skalieren mit dem Ziel-Level mit (Hollow-Basiswerte sind
            # sonst selbst auf Lv 90 zu schwach), plus globaler x1.25-Boost:
            # Lv 50 -> x1.88, Lv 80 -> x2.25
            factor = (1.0 + lvl / 100.0) * LEVEL_STAT_SCALE
            n_boost = self._boost_stats(spawned, hp_f=factor, st_f=factor)
            self._load_floor()
            src = f'Batch "{preset_name}"' if preset else 'Zufalls-Gegner'
            self.status_var.set(
                f'Etage {floor}: {count} {src} (Etagen-Limit {capacity}) '
                f'Lv{lvl_lo}-{lvl_hi}, {n_boost} Chars: Stats x{factor:.2f} '
                '(inkl. x1.25-Boost) + Skills randomisiert (noch nicht gespeichert).')

    def _pool_avg(self):
        """Durchschnitt der Vanilla-Stats [hp,sp,atk,def,hit,eva] ueber den
        Gegner-Pool - Referenz fuer die Ausreisser-Daempfung."""
        if getattr(self, '_pool_avg_cache', None) is None:
            rows = [VANILLA_REF['stats'][str(u)] for u in self.enemy_pool
                    if str(u) in VANILLA_REF['stats']]
            if not rows:
                return [1e9] * 6        # keine Referenz -> nie daempfen
            self._pool_avg_cache = [sum(r[i] for r in rows) / len(rows)
                                    for i in range(6)]
        return self._pool_avg_cache

    @staticmethod
    def _abil_loadout(unit, actives, passives):
        """Zufalls-Loadout fuer die Faehigkeits-Slots 1-9 eines Charakters.

        -> {token_index: ability_id}. Slot 0 (Set-ID) wird nie angefasst.
        Die Pflicht-Faehigkeiten des Vanilla-Records (ESSENTIAL_ABILITIES)
        werden zuerst reserviert und hinten eingetragen, der Rest wird im
        Verhaeltnis 5 Aktive : 4 Passiva aufgefuellt. Hat der Charakter im
        Original keine Pflicht-Faehigkeiten (Hollows, Mobs, Zivilisten),
        bleibt es bei 9 Zufallswerten wie bisher."""
        keep = [a for a in ESSENTIAL_ABIL.get(str(unit), [])
                if a in ESSENTIAL_ABILITIES]
        free = len(ABIL_TOKENS) - 1 - len(keep)         # 9 Slots minus Pflicht
        n_act = min(round(free * 5 / 9), len(actives))
        n_pas = min(free - n_act, len(passives))
        loadout = random.sample(actives, n_act) + random.sample(passives, n_pas)
        loadout = (loadout + [0] * free)[:free] + keep  # Pflicht ganz hinten
        return {ABIL_TOKENS[i + 1]: v for i, v in enumerate(loadout)}

    def _repair_essential_abil(self, silent=False):
        """Pflicht-Faehigkeiten 370/401 bei ALLEN Charakteren wiederherstellen,
        die sie im Vanilla-Record hatten (HANDOVER 5.3 - Verdacht auf die
        Ursache der kaputten 53/11 HP).

        Repariert die Chars, die eine fruehere Randomisierung bereits
        beschaedigt hat. Idempotent: wer sie schon hat, wird nicht angefasst.
        Geschrieben wird in die hintersten freien Slots 1-9; ist alles belegt,
        werden die letzten Zufalls-Slots geopfert. Slot 0 bleibt tabu."""
        if not self.fs:
            return 0
        n, touched = 0, []
        for li, unit, name, typ in self.char_rows:
            need = [a for a in ESSENTIAL_ABIL.get(str(unit), [])
                    if a in ESSENTIAL_ABILITIES]
            if not need:
                continue
            toks = line_tokens(self.status_lines[li])
            if len(toks) != TOKENS_PER_LINE:
                continue
            ab = [toks[t][2] for t in ABIL_TOKENS]
            miss = [a for a in need if a not in ab]
            if not miss:
                continue
            # Zielslots: erst leere von hinten, dann die hintersten belegten
            free = [i for i in range(9, 0, -1) if ab[i] == 0]
            busy = [i for i in range(9, 0, -1) if ab[i] != 0]
            for a in miss:
                slot = free.pop(0) if free else busy.pop(0)
                ab[slot] = a
            self.status_lines[li] = replace_tokens(
                self.status_lines[li], dict(zip(ABIL_TOKENS, ab)))
            touched.append(f'{unit} {name}')
            n += 1
        if n:
            self.dirty_status = True
            self._on_char_select()          # Anzeige des gewaehlten Chars frisch
            self._update_abil_preview()
        if not silent:
            if n:
                self.status_var.set(
                    f'{n} Charaktere repariert: Pflicht-Faehigkeiten '
                    f'{"/".join(str(a) for a in ESSENTIAL_ABILITIES)} wieder '
                    'eingetragen (noch nicht gespeichert).')
                messagebox.showinfo(
                    'Pflicht-Faehigkeiten repariert',
                    f'{n} Charaktere hatten 370/401 nicht mehr:\n\n'
                    + ', '.join(touched[:25])
                    + ('\n...' if len(touched) > 25 else '')
                    + '\n\nJetzt speichern und Etage 15 in DeSmuME testen:\n'
                      'zeigt Kenpachi wieder normale HP, war das die Ursache.')
            else:
                messagebox.showinfo(
                    'Pflicht-Faehigkeiten',
                    'Alles in Ordnung - jeder Charakter, der 370/401 im '
                    'Original hatte, hat sie auch jetzt.')
        return n

    def _boost_stats(self, chars, hp_f, st_f):
        """Charaktere aufwerten: Basis-Stats hochskalieren (HP-Faktor, Stat-
        Faktor fuer SP/ATK/DEF/HIT/EVA) UND Faehigkeiten randomisieren:
        5 zufaellige benutzbare Skills (kind=2) + 4 zufaellige Skill-Tree-
        Passiva; die Zanpakuto-Set-ID (Token 0 der Liste) bleibt erhalten.
        Wirkt global fuer den Charakter - der Randomizer-Pool enthaelt aber
        nur reine Gegner-Einheiten, Spieler-Charaktere sind nie betroffen.
        Pro Charakter nur einmal pro Session (kein Aufschaukeln). Caps
        konservativ, da die ARM9-Record-Felder u8 sind."""
        actives = [a for a, nm in self.abil_names.items()
                   if nm.strip() and self.abil_kind.get(a) == 2]
        passives = [a for a, nm in self.abil_names.items()
                    if nm.strip() and self.abil_kind.get(a) in (3, 4, 5, 7)
                    and a not in AI_ABUSE_PASSIVES
                    and a not in ESSENTIAL_ABILITIES]
        n = 0
        for li, unit, name, typ in self.char_rows:
            if unit not in chars:
                continue
            toks = line_tokens(self.status_lines[li])
            # IMMER von den Vanilla-Basiswerten ausgehen -> idempotent,
            # egal wie oft (auch ueber Sessions hinweg) randomisiert wird
            base = VANILLA_REF['stats'].get(str(unit)) or \
                [toks[t][2] for t in (6, 7, 8, 9, 10, 11)]
            upd = {6: min(int(base[0] * hp_f), 30000),             # HP
                   7: min(int(base[1] * st_f), 999)}               # SP
            for k, t in enumerate((8, 9, 10, 11)):                 # ATK DEF HIT EVA
                # Ausreisser-Daempfung (stetig): der Anteil bis zur Schwelle
                # (1.3x Pool-Schnitt) skaliert voll, nur der ueberschuessige
                # Anteil darueber kriegt x1.1 - sonst wird z. B. hohe
                # EVA-Basis auf Lv80 zu EVA 95+ = praktisch untreffbar.
                b = base[2 + k]
                knee = OUTLIER_THRESH * self._pool_avg()[2 + k]
                val = b * st_f if b <= knee else \
                    knee * st_f + (b - knee) * OUTLIER_SCALE
                upd[t] = min(int(val), 200)
            # Faehigkeiten-Slots 1-9 neu wuerfeln (Slot 0 = Set-ID bleibt).
            # Die Pflicht-Faehigkeiten des Vanilla-Records (370/401) bleiben
            # IMMER drin und landen HINTEN - genau wie im Original, wo sie
            # nach den echten Faehigkeiten stehen (Kenpachi: 242 370 401).
            upd.update(self._abil_loadout(unit, actives, passives))
            self.status_lines[li] = replace_tokens(self.status_lines[li], upd)
            self.god_boosted.add(unit)
            n += 1
        if n:
            self.dirty_status = True
        return n

    # ---------- Skills ----------
    @staticmethod
    def _skill_layout(line):
        """-> (n_effekte, kosten_tokenindex). Zeilen haben 1-2 Effektbloecke a 3 Tokens."""
        n = len(NUM_RE.findall(line))
        n_eff = (n - 14) // 3
        return n_eff, 3 + 3 * n_eff + 2

    def _fill_skill_list(self):
        q = self.skill_search.get().lower()
        self.skill_list.delete(0, 'end')
        self._skill_visible = []
        for li, line in enumerate(self.skill_lines):
            toks = line_tokens(line)
            if len(toks) < 15:
                continue
            sid = toks[0][2]
            name = self.skill_names.get(sid, f'?{sid}')
            if q and q not in name.lower() and q != str(sid):
                continue
            self.skill_list.insert('end', f'{sid:3d}  {name}')
            self._skill_visible.append(li)

    def _sel_skill_line(self):
        sel = self.skill_list.curselection()
        return self._skill_visible[sel[0]] if sel else None

    def _on_skill_select(self, _=None):
        li = self._sel_skill_line()
        if li is None:
            return
        line = self.skill_lines[li]
        toks = line_tokens(line)
        sid = toks[0][2]
        n_eff, cost_idx = self._skill_layout(line)
        self.skill_title.config(text=f'#{sid}  {self.skill_names.get(sid, "?")}')
        self.skill_helplbl.config(text=self.skill_help.get(sid, ''))
        self.skill_vars['cost'].set(toks[cost_idx][2])
        for e in (1, 2):
            for c, f in enumerate(('Typ', 'Power', 'Wert')):
                v = self.skill_vars[f'e{e}{f}']
                if e <= n_eff:
                    v.set(toks[3 + (e - 1) * 3 + c][2])
                else:
                    v.set('')

    def _apply_skill(self):
        li = self._sel_skill_line()
        if li is None:
            return
        line = self.skill_lines[li]
        n_eff, cost_idx = self._skill_layout(line)
        try:
            updates = {cost_idx: int(self.skill_vars['cost'].get())}
            for e in range(1, n_eff + 1):
                for c, f in enumerate(('Typ', 'Power', 'Wert')):
                    updates[3 + (e - 1) * 3 + c] = int(self.skill_vars[f'e{e}{f}'].get())
            for idx, v in updates.items():
                if not -9999 <= v <= 9999:
                    raise ValueError(f'Wert {v} ausserhalb -9999..9999')
        except ValueError as e:
            messagebox.showerror('Ungueltige Eingabe', str(e))
            return
        self.skill_lines[li] = replace_tokens(line, updates)
        self.dirty_skill = True
        self.status_var.set('Skill geaendert (noch nicht in ROM gespeichert).')

    def _fill_abil_list(self):
        q = self.abil_search.get().lower()
        self.abil_list.delete(0, 'end')
        self._abil_visible = []
        for aid in sorted(self.abil_names):
            name = self.abil_names[aid]
            if not name.strip():
                continue
            if q and q not in name.lower() and q != str(aid):
                continue
            tag = 'A' if self._abil_is_active(aid) else 'p'
            self.abil_list.insert('end', f'{aid:3d} [{tag}] {name}')
            self._abil_visible.append(aid)

    def _on_abil_select(self, _=None):
        sel = self.abil_list.curselection()
        if sel:
            aid = self._abil_visible[sel[0]]
            self.abil_helplbl.config(text=self._abil_info(aid) + '\n'
                                     + self.abil_help.get(aid, '(kein Hilfetext)'))

    def _cur_pslot(self):
        sel = self.ptree.selection()
        if not sel:
            return None
        sid = int(sel[0])
        for s in self.party_cache[int(self.floor_var.get())]:
            if s['id'] == sid:
                return s
        return None

    def _on_pslot_select(self, _=None):
        s = self._cur_pslot()
        if s:
            self._last_sel = 'deploy'
            self.pslot_vars['x'].set(s['x'])
            self.pslot_vars['y'].set(s['y'])
            self._draw_map(int(self.floor_var.get()))

    def _apply_pslot(self):
        s = self._cur_pslot()
        if not s:
            return
        try:
            x, y = int(self.pslot_vars['x'].get()), int(self.pslot_vars['y'].get())
            if not (1 <= x <= 39 and 1 <= y <= 39):
                raise ValueError('x/y muessen 1..39 sein (Koordinaten sind 1-basiert)')
        except ValueError as e:
            messagebox.showerror('Ungueltige Eingabe', str(e))
            return
        s['x'], s['y'] = x, y
        self.dirty_party.add(int(self.floor_var.get()))
        self._load_floor()
        self.status_var.set('Startposition geaendert (noch nicht in ROM gespeichert).')

    def _load_arm9_into_model(self):
        """Charakterwerte aus der ARM9-Tabelle (= was die Engine WIRKLICH liest)
        in das .inc-Zeilenmodell uebernehmen. Noetig, weil die .inc-Datei nur
        ein Build-Artefakt ist und beim Speichern uebersprungen werden kann,
        wenn sie zu klein geworden ist - die ARM9-Records sind massgeblich."""
        import struct as _st
        try:
            with open(self.rom_var.get(), 'rb') as f:
                for i, (li, unit, name, typ) in enumerate(self.char_rows):
                    off = ARM9_STATUS_ROM + (unit - 15) * 70
                    if off < 0x4000:
                        continue
                    f.seek(off)
                    r = f.read(70)
                    if _st.unpack_from('<H', r, 6)[0] != unit:
                        continue
                    upd = {0: _st.unpack_from('<H', r, 4)[0],
                           2: r[8], 3: r[9], 4: r[10], 5: r[11],
                           6: _st.unpack_from('<H', r, 12)[0],
                           7: _st.unpack_from('<H', r, 14)[0],
                           8: r[16], 9: r[17], 10: r[18], 11: r[19],
                           12: r[20], 13: r[21], 17: r[25], 18: r[26],
                           29: _st.unpack_from('<H', r, 48)[0]}
                    for k, v in enumerate(_st.unpack_from('<10H', r, 28)):
                        upd[EQUIP_TOKENS[k]] = v
                    for k, v in enumerate(_st.unpack_from('<10H', r, 50)):
                        upd[ABIL_TOKENS[k]] = v
                    self.status_lines[li] = replace_tokens(self.status_lines[li], upd)
                    if r[8] != typ:    # typ in der Listenansicht aktualisieren
                        self.char_rows[i] = (li, unit, name, r[8])
        except OSError:
            pass

    # ---------- Speichern ----------
    def _sync_arm9_status(self, out):
        """Alle db_status.inc-Werte in die kompilierte ARM9-Stat-Tabelle der
        Ziel-ROM spiegeln - nur DIE liest die Engine (in-game verifiziert:
        reine .inc-Aenderungen haben keinen Effekt)."""
        import struct as _st
        target = out or self.rom_var.get()
        n = 0
        with open(target, 'r+b') as f:
            for li, unit, name, typ in self.char_rows:
                off = ARM9_STATUS_ROM + (unit - 15) * 70
                if off < 0x4000:
                    continue
                f.seek(off + 6)
                if _st.unpack('<H', f.read(2))[0] != unit:
                    continue    # kein ARM9-Record fuer diese Unit
                t = [v for _, _, v in line_tokens(self.status_lines[li])]
                f.seek(off + 4)
                f.write(_st.pack('<H', t[0] & 0xFFFF))                 # person
                f.seek(off + 8)
                f.write(bytes([t[2] & 0xFF, t[3] & 0xFF, t[4] & 0xFF,  # typ,unk3,face
                               min(t[5], 99)]))                        # lv
                f.write(_st.pack('<HH', min(t[6], 65535), min(t[7], 65535)))  # hp,sp
                f.write(bytes([min(t[8], 255), min(t[9], 255), min(t[10], 255),
                               min(t[11], 255), min(t[12], 255),       # atk..mov
                               t[13] & 0xFF]))                         # aType
                f.seek(off + 25)
                f.write(bytes([t[17] & 0xFF, t[18] & 0xFF]))           # unk17, S-Pressure
                f.seek(off + 28)
                f.write(_st.pack('<10H', *[v & 0xFFFF for v in t[19:29]]))  # Equip
                f.seek(off + 48)
                f.write(_st.pack('<H', t[29] & 0xFFFF))
                f.write(_st.pack('<10H', *[v & 0xFFFF for v in t[30:40]]))  # Faehigkeiten
                n += 1
        return n

    def _patch_btower(self, out):
        """Map-Zuordnung in db_btower.inc UND in der ARM9-Binaertabelle patchen.
        Die ARM9-Tabelle ist die massgebliche Engine-Quelle (wie bei db_status);
        die .inc ist vermutlich nur ein Build-Artefakt -> ihr Write ist
        best-effort (wird bei Platzmangel uebersprungen, statt den ganzen
        Speichervorgang mit "db_btower.inc wird zu gross" abzubrechen)."""
        # 1) .inc-Datei (Groesse muss gleich bleiben -> Token ersetzen + auffuellen)
        raw = self.fs.read('/yamada/DataBase/db_btower.inc').decode('ascii')
        orig_size = len(raw)
        lines = raw.split('\r\n')
        for i, line in enumerate(lines):
            toks = line_tokens(line)
            if len(toks) >= 3 and toks[0][2] in self.dirty_maps:
                lines[i] = replace_tokens(line, {1: self.btower[toks[0][2]]})
        text = '\r\n'.join(lines)
        if len(text) > orig_size:
            # Notfall: Leerzeichen nach Kommas entfernen, damit es passt
            text = text.replace(', ', ',')
        if len(text) <= orig_size:
            text += ' ' * (orig_size - len(text))
            self.fs.write('/yamada/DataBase/db_btower.inc', text.encode('ascii'), out)
        # sonst .inc unveraendert lassen - ARM9 unten ist die Wahrheit
        # 2) ARM9-Binaertabelle @0xf3b58 (u16-Tripel {etage, map, party}) in der
        #    ZIEL-Datei patchen (nach fs.write existiert die Kopie bereits)
        import struct as _st
        target = out or self.rom_var.get()
        with open(target, 'r+b') as f:
            f.seek(0x20)
            arm9_off = _st.unpack('<I', f.read(4))[0]
            for floor in sorted(self.dirty_maps):
                pos = arm9_off + 0xf3b58 + (floor - 1) * 6
                f.seek(pos)
                fl, mp, pt = _st.unpack('<3H', f.read(6))
                if fl != floor:
                    raise ValueError(f'ARM9-btower-Tabelle: erwartete Etage {floor} '
                                     f'@0x{pos:X}, fand {fl}')
                f.seek(pos + 2)
                f.write(_st.pack('<H', self.btower[floor]))

    def save_all(self):
        if not self.fs:
            return
        if not (self.dirty_status or self.dirty_floors or self.dirty_party
                or self.dirty_skill or self.dirty_maps or self.dirty_names):
            self.status_var.set('Keine Aenderungen vorhanden.')
            return
        out = None if self.save_mode.get() == 'orig' else self.copy_var.get()
        if self.save_mode.get() == 'orig' and not messagebox.askyesno(
                'Original ueberschreiben?', 'Wirklich die Original-ROM veraendern?'):
            return
        def write_inc(path, lines, orig_size):
            text = '\r\n'.join(lines)
            if len(text) > orig_size:
                # Notfall: Leerzeichen nach Kommas entfernen bis es passt
                text = text.replace(', ', ',')
                if len(text) > orig_size:
                    raise ValueError(f'{path} wird zu gross - Werte kuerzen')
            text += ' ' * (orig_size - len(text))
            self.fs.write(path, text.encode('ascii'), out)
        try:
            if self.dirty_status:
                # .inc ist nur Build-Artefakt (Engine liest ARM9!) - wenn die
                # Werte nicht mehr reinpassen, einfach ueberspringen
                try:
                    write_inc(STATUS_PATH, self.status_lines, self.status_orig_size)
                except ValueError:
                    pass
            if self.dirty_skill:
                write_inc('/yamada/DataBase/db_skill.inc', self.skill_lines,
                          self.skill_orig_size)
            # AI-Skill-Edits (Subfile 1) fliessen als Basis mit ein
            for floor in sorted(set(self.dirty_floors) | set(self.ai_base)):
                base = self.ai_base.get(floor) or self.narc_base.get(floor)
                narc = pack_units(self.fs, floor, self.tower_cache[floor], base=base)
                self.fs.write(f'/yamada/DataBase/db_dpos_{900+floor}.narc', narc, out)
            for floor in sorted(self.dirty_party):
                narc = pack_party(self.fs, floor, self.party_cache[floor])
                self.fs.write(f'/yamada/DataBase/db_party_{900+floor}.narc', narc, out)
            if self.dirty_names:
                # Char-Designer-Umbenennungen: s_name.bin (und _fre) neu packen
                for path in ('/yamada/ScrDat/s_name.bin',
                             '/yamada/ScrDat/s_name_fre.bin'):
                    if path in self.fs.by_path:
                        self.fs.write(path, bgsm_replace_strings(
                            self.fs.read(path), self.dirty_names), out)
            # ARM9-Patches brauchen eine existierende Zieldatei (falls bisher
            # kein fs.write lief, z. B. weil der .inc-Write uebersprungen wurde)
            if (self.dirty_maps or self.dirty_status) and out and not os.path.exists(out):
                shutil.copyfile(self.rom_var.get(), out)
            if self.dirty_maps:
                self._patch_btower(out)
            if self.dirty_status:
                self._sync_arm9_status(out)
        except Exception as e:
            messagebox.showerror('Fehler beim Speichern', str(e))
            return
        target = out or self.rom_var.get()
        n = ((1 if self.dirty_status else 0) + (1 if self.dirty_skill else 0)
             + len(self.dirty_floors) + len(self.dirty_party)
             + len(self.dirty_maps) + (1 if self.dirty_names else 0))
        # Umbenennungen sind jetzt in der ROM -> ins Namens-Modell uebernehmen
        self.names.update(self.dirty_names)
        self.char_rows = [(l, u, self.dirty_names.get(u, nm), t)
                          for l, u, nm, t in self.char_rows]
        self.dirty_names = {}
        self._fill_charlist()
        self._fill_unit_choices()
        self._fill_designer_list()
        self.dirty_status = False
        self.dirty_skill = False
        self.dirty_floors = set()
        self.dirty_party = set()
        self.dirty_maps = set()
        self.narc_base = {}
        self.ai_base = {}
        _ic = self._sync_icloud(target)
        _ictxt = f' + {_ic} in iCloud gespiegelt' if _ic else ''
        self.status_var.set(f'{n} Datei(en) gespeichert nach '
                            f'{os.path.basename(target)}{_ictxt}')
        if self.autostart_var.get() and os.path.exists(DESMUME_EXE):
            self._launch_desmume(target)
            self.status_var.set(f'{n} Datei(en) gespeichert{_ictxt} - DeSmuME '
                                f'gestartet mit {os.path.basename(target)}')
        else:
            messagebox.showinfo('Gespeichert', f'Aenderungen geschrieben nach:\n{target}')


if __name__ == '__main__':
    app = App()
    if '--selftest' in sys.argv:
        app.withdraw()
        app.update()
        app.load_rom()
        app.charlist.selection_set(0)
        app._on_char_select()
        app.stat_vars[6].set('9999')      # HP von Yamamoto testweise
        app._apply_char()
        assert '9999' in app.status_lines[app.char_rows[0][0]]
        app.filter_var.set('Nur spielbare')
        app._fill_charlist()
        assert 0 < app.charlist.size() < len(app.char_rows)
        n_playable = app.charlist.size()
        app._load_floor()
        assert len(app.safe_units) == 195 and len(app.unit_char['values']) == 195
        assert 2 in app.risky_units and 94 in app.safe_units  # Sasakibe unfertig, Ichigo ok
        # Charakterliste zeigt keine unfertigen mehr
        app.filter_var.set('Alle'); app.search_var.set(''); app._fill_charlist()
        shown = {app.char_rows[[r[0] for r in app.char_rows].index(li)][1]
                 for li in app._visible}
        assert app.charlist.size() == len(app.safe_units)
        assert not (shown & app.risky_units), 'unfertige Charaktere sichtbar!'
        # Einsetzen eines unfertigen Charakters wird hart geblockt
        import tkinter.messagebox as _mb
        _err = []
        _orig = _mb.showerror
        _mb.showerror = lambda *a, **k: _err.append(a)
        app.tree.selection_set('17'); app._on_unit_select()
        app.unit_char.set('2 Sasakibe'); app._apply_unit()
        _mb.showerror = _orig
        u17 = [u for u in app.tower_cache[1] if u['slot'] == 17][0]
        assert u17['char'] != 2 and _err, 'Block griff nicht'
        assert app._face_image(94) is not None            # Ichigo-Portrait
        assert app.face_label.cget('image') != ''         # Portrait im Panel sichtbar
        app.tree.selection_set('16')
        app._on_unit_select()                             # Gegner ohne Portrait -> Text
        app.ptree.selection_set('1')
        app._on_pslot_select()
        app.pslot_vars['x'].set('12')
        app._apply_pslot()
        assert app.party_cache[1][0]['x'] == 12 and 1 in app.dirty_party
        # Karte: Bild geladen, Klick versetzt gewaehlte Einheit
        img = app._map_image(1)
        assert img is not None and img.width() >= 256, 'Karte fehlt'
        app.tree.selection_set('16'); app._on_unit_select()
        class Ev: x, y = 40, 40                       # Grid-Zelle (5,5) -> Einheit (6,6)
        app._canvas_click(Ev)
        u16 = [u for u in app.tower_cache[1] if u['slot'] == 16][0]
        assert (u16['x'], u16['y']) == (6, 6), (u16['x'], u16['y'])
        # Skills-Tab: Liste voll, Auswahl + Aenderung funktioniert
        app.skill_search.set(''); app._fill_skill_list()
        assert app.skill_list.size() == 116, app.skill_list.size()
        app.skill_list.selection_set(6); app._on_skill_select()   # #7 White Lightning
        assert 'White Lightning' in app.skill_title.cget('text')
        assert app.skill_vars['cost'].get() == '15'
        app.skill_vars['cost'].set('5'); app._apply_skill()
        assert app.dirty_skill and '"5' in app.skill_lines[app._skill_visible[6]]
        # neue Stat-Felder (S-Pressure = Token 18)
        app.charlist.selection_set(0); app._on_char_select()
        assert app.stat_vars[18].get() == '40'   # Yamamoto S-Pressure
        assert app.abil_list.size() == 298   # nicht-leere Ability-Namen
        # Ability-Typen: 100 Sai = Skill-Granter fuer Skill 1, 323 Burn 1 = passiv
        assert app.abil_kind[100] == 2 and app.abil_ref[100] == 1
        assert app._abil_is_active(106) and not app._abil_is_active(323)
        assert 'Sai' in app._abil_info(100) or 'Skill #1' in app._abil_info(100)
        n_act = sum(1 for a in app.abil_names
                    if app.abil_names[a].strip() and app._abil_is_active(a))
        assert n_act > 100, n_act   # Zanpakuto+Skills+Bankai etc.
        # Save-Manager: .dsv-Pfad haengt am ROM-Dateinamen
        assert app._dsv_path().endswith('Bleach3P modded.dsv'), app._dsv_path()
        # Modell wurde beim Laden aus der ARM9-Tabelle befuellt (nicht .inc)
        import struct as _st3
        with open(app.rom_var.get(), 'rb') as _f:
            _f.seek(ARM9_STATUS_ROM + (146 - 15) * 70 + 12)
            _hp146 = _st3.unpack('<H', _f.read(2))[0]
        _li146 = [li for li, u, _, _ in app.char_rows if u == 146][0]
        assert line_tokens(app.status_lines[_li146])[6][2] == _hp146, 'ARM9->Modell-Sync fehlt'
        # Randomizer: Etage 2 mit Ziel-Level 80 fuellen
        random.seed(42)
        app.floor_var.set(2)
        app._load_floor()
        app.rand_level_var.set('80')
        app.rand_min_var.set('6')
        app.rand_max_var.set('20')
        app._randomize_floor()
        en = [u for u in app.tower_cache[2] if u['slot'] >= 16]
        assert 6 <= len(en) <= 20, len(en)
        # Slot-Regel: Vanilla-Slots zuerst, Extra-Slots schliessen darueber
        # lueckenlos an (Extra-Slots in-game verifiziert, Etage 1 2026-07-06)
        _tpl2 = VANILLA_REF['floors']['2']
        _van_slots = {t['slot'] for t in _tpl2}
        assert len(en) <= MAX_UNIQUE_SPRITES
        _extra_slots = {u['slot'] for u in en} - _van_slots
        assert all(s > max(_van_slots) for s in _extra_slots), 'fremde Slots!'
        assert len(en) <= len(_tpl2) or _extra_slots, 'Extra-Slots nicht genutzt'
        cells = set(app._walkable_cells(2))
        assert all((u['x'] - 1, u['y'] - 1) in cells for u in en), 'Gegner auf unbegehbarem Feld'
        # Alle ORIGINAL-Einheiten stehen 1-basiert auf Wert-10-Feldern -
        # gegen die QUASI-VANILLA-Referenz pruefen (die Arbeits-ROM darf
        # beliebig umgebaute Etagen enthalten)
        from tower import floor_units as _fu, party_slots as _ps
        _vref = os.path.join(HERE, 'Bleach3P_test_mod.nds')
        if os.path.exists(_vref):
            from romfs import RomFS as _RFv
            _fsv = _RFv(_vref)
            for _fl in (1, 5, 30):
                _g = narc_subfiles(_fsv.read(
                    f'/yamada/DataBase/db_dpos_{900+_fl}.narc'))[2]
                _c = {(x, y) for y in range(39) for x in range(39)
                      if y * 39 + x < len(_g) and _g[y * 39 + x] == 10}
                for _u in _fu(_fsv, _fl):
                    if _u['x'] == 0 or _u['y'] == 0:
                        continue    # Spezial-Records ohne Position (Verstaerkung)
                    assert (_u['x'] - 1, _u['y'] - 1) in _c, (_fl, _u)
                for _s in _ps(_fsv, _fl):
                    assert (_s['x'] - 1, _s['y'] - 1) in _c, (_fl, _s)
        assert len({(u['x'], u['y']) for u in en}) == len(en), 'Positionen doppelt belegt'
        assert all(u['char'] in app.safe_units for u in en), 'unsicherer Charakter gespawnt'
        assert all(75 <= u['level'] <= 85 for u in en), 'Level ausserhalb 80+-5'
        assert all(u['active'] == 3 for u in en), 'Randomizer-Einheit nicht im Gegner-Team!'
        # Original-Turmgegner sind alle Team 3 (active=1 waere Spielerseite)
        assert all(u['active'] == 3 for u in _fu(app.fs, 1)), 'Floor-1-Original nicht Team 3?'
        assert 2 in app.dirty_floors
        spawn_zone = {(s['x'] + dx, s['y'] + dy) for s in app.party_cache[2]
                      for dx in (-1, 0, 1) for dy in (-1, 0, 1)}
        assert not any((u['x'], u['y']) in spawn_zone for u in en), 'Gegner am Spieler-Spawn'
        # Pool: nur Gegner-Typen (typ != 1), vanilla-erprobt, Blacklist raus
        typ_by_unit = {u: t for _, u, _, t in app.char_rows}
        # typ=1 ist jetzt erlaubt, sofern einzeln verifiziert (Captains etc.)
        assert all(c in VERIFIED_POOL_IDS for c in app.enemy_pool)
        assert 113 in app.enemy_pool and 117 in app.enemy_pool     # Ulquiorra/Yammy (Gegner-Ver.)
        assert 114 not in app.enemy_pool and 118 not in app.enemy_pool  # rekrutierbare Duplikate
        assert not ({176, 177, 185, 47} & app.enemy_pool)          # Whole/SkyRift/Roster-Rangiku
        # Roster-Flag aus db_partner: Rekrutierbare (Shinji 179 & Co.) raus,
        # deren reine Enemy-Kopien (242/247) bleiben drin
        assert not ({95, 96, 97, 101, 112, 179, 180} & app.enemy_pool), 'Roster-Flag ignoriert'
        assert 247 in app.enemy_pool and 242 in app.enemy_pool
        # 110 statt 111: Familiar 151 = XP-Farm-Dummy (Blacklist)
        assert len(app.enemy_pool) == 110, len(app.enemy_pool)
        assert 151 not in app.enemy_pool and 152 in app.enemy_pool
        assert {9, 89, 141, 198, 254, 228} <= app.enemy_pool   # Exoten+Captains+Aizen+Ichigo+Rukia
        assert all(u['char'] in app.enemy_pool for u in en)
        # Verhalten 'Aggressiv' (Default): AI-Typ 3, Aggro 100
        assert all(u['raw'][1] == 3 and u['raw'][2] == 100 for u in en), 'AI/Aggro fehlt'
        # Jeder Charakter maximal einmal pro Etage
        assert len({u['char'] for u in en}) == len(en), 'Charakter doppelt gespawnt!'
        assert len(en) <= MAX_UNIQUE_SPRITES
        assert len({u['char'] for u in en}) <= MAX_UNIQUE_SPRITES, \
            'zu viele unique Sprites (DS-RAM!)'
        assert not (BIG_UNITS & {u['char'] for u in en}), 'Riese im Randomizer-Ergebnis!'
        # Randomisierte Etage laesst sich packen (54-Byte-Records ok)
        from tower import pack_units as _pk
        _pk(app.fs, 2, app.tower_cache[2])
        # Normal-Randomizer boostet Stats mit (Faktor 1.8 bei Ziel-Level 80)
        assert app.god_boosted and app.dirty_status, 'Stat-Skalierung lief nicht'
        # GOD-MODE: Lv 91-99, Stats x3/x2 (nur fuer frisch geboostete Chars pruefbar)
        app.floor_var.set(3); app._load_floor()
        hp_before = {}
        for _li, _u, _nm, _t in app.char_rows:
            hp_before[_u] = line_tokens(app.status_lines[_li])[6][2]
        _pre = set(app.god_boosted)
        app._randomize_floor(god=True)
        gen = [u for u in app.tower_cache[3] if u['slot'] >= 16]
        assert all(91 <= u['level'] <= 99 for u in gen), 'GOD-MODE Level falsch'
        _newly = app.god_boosted - _pre
        if _newly:
            _gc = next(iter(_newly))
            _gli = [li for li, u, _, _ in app.char_rows if u == _gc][0]
            _gt = [v for _, _, v in line_tokens(app.status_lines[_gli])]
            _vb = VANILLA_REF['stats'].get(str(_gc))
            _hp0 = _vb[0] if _vb else hp_before[_gc]
            assert _gt[6] == min(int(_hp0 * 3.0 * LEVEL_STAT_SCALE), 30000), (_gt[6], _hp0)
            # Skill-Randomisierung: Slots 1-5 aktiv (kind 2), 6-9 passiv
            assert all(app.abil_kind.get(v) == 2 for v in _gt[31:36]), _gt[31:36]
            assert all(app.abil_kind.get(v) in (3, 4, 5, 7) for v in _gt[36:40]), _gt[36:40]
        # Preset-Batches: nur Pool-IDs, keine Riesen; Captains-Batch landet komplett
        for _nm, _ids in PRESET_BATCHES.items():
            assert set(_ids) <= VERIFIED_POOL_IDS, f'{_nm}: fremde ID'
            assert not (set(_ids) & BIG_UNITS), f'{_nm}: Riese enthalten'
        # NONCOM-Erkennung (Attribut 0/4): crashen bei Angriff/Pressure
        assert {251, 134, 197, 105, 89, 92, 9, 135, 238, 240} <= app.noncom_units
        assert not (app.noncom_units & {u['char'] for u in en}), 'NONCOM im Randomizer!'
        app.floor_var.set(4); app._load_floor()
        app._randomize_floor(preset=PRESET_BATCHES['Captains (Turm)'],
                             preset_name='Captains (Turm)')
        _en4 = [u for u in app.tower_cache[4] if u['slot'] >= 16]
        _exp4 = set(PRESET_BATCHES['Captains (Turm)']) - app.noncom_units
        assert len(_en4) == len(_exp4) == 9, len(_en4)   # Unohana (NONCOM) fehlt
        assert {u['char'] for u in _en4} == _exp4
        # Copy/Paste: gewaehlte Einheit duplizieren (Werte uebernommen, neuer Slot)
        _src = _en4[0]
        app.tree.selection_set(str(_src['slot']))
        app._copy_unit()
        _n4 = len(app.tower_cache[4])
        app._paste_unit()
        assert len(app.tower_cache[4]) == _n4 + 1, 'Paste hat keine Einheit erzeugt'
        _pasted = max(app.tower_cache[4], key=lambda u: u['slot'])
        assert _pasted['char'] == _src['char'] and _pasted['level'] == _src['level']
        assert _pasted['raw'] == _src['raw'] and _pasted['active'] == _src['active']
        assert _pasted['slot'] != _src['slot']
        assert (_pasted['x'], _pasted['y']) != (_src['x'], _src['y']), 'gleiche Position'
        assert (_pasted['x'] - 1, _pasted['y'] - 1) in set(app._walkable_cells(4))
        # Skill-Chaos: alle Gegner bekommen AI-Skills (Subfile 1)
        from tower import ai_block as _aib
        app.floor_var.set(4); app._load_floor()
        app._skill_chaos()
        _narc4 = app.ai_base.get(4)
        assert _narc4, 'Skill-Chaos hat keine ai_base erzeugt'
        _en4b = sorted((u for u in app.tower_cache[4] if u['slot'] >= 16),
                       key=lambda u: u['slot'])
        for _i in range(len(_en4b)):
            _ids = [s for s in _aib(_narc4, _i)[1] if s in app.skill_names]
            assert 1 <= len(_ids) <= 5, (_i, _ids)
        assert 4 in app.dirty_floors
        # Char-Designer: BGSM-Umbenennung + Stats + Platzieren
        from formats import bgsm_replace_strings as _bgr
        _sn = app.fs.read('/yamada/ScrDat/s_name.bin')
        _sn2 = _bgr(_sn, {141: 'TESTZILLA'})
        assert len(_sn2) == len(_sn)
        assert bgsm_strings(_sn2)[141] == 'TESTZILLA'
        assert bgsm_strings(_sn2)[132] == bgsm_strings(_sn)[132], 'Nachbar-Name kaputt'
        app.des_list.selection_clear(0, 'end')
        app.des_list.selection_set(app._des_visible.index(141))
        app._on_designer_select()
        app.des_name.set('TESTZILLA')
        app.des_stats[6].set('9999')
        app._designer_save()
        assert app.dirty_names == {141: 'TESTZILLA'}
        _li141 = [li for li, u, _, _ in app.char_rows if u == 141][0]
        assert line_tokens(app.status_lines[_li141])[6][2] == 9999
        app.des_list.selection_set(app._des_visible.index(141))   # nach Save neu waehlen
        app.floor_var.set(5); app._load_floor()
        _slots_before = {u['slot'] for u in app.tower_cache[5]}
        app._designer_place()
        _en5 = [u for u in app.tower_cache[5] if u['slot'] >= 16]
        _new = [u for u in app.tower_cache[5] if u['slot'] not in _slots_before]
        assert len(_new) == 1, _new
        _nu = _new[0]
        assert _nu['char'] == 141 and _nu['active'] == 3 and _nu['raw'][1] == 3
        assert (_nu['x'] - 1, _nu['y'] - 1) in set(app._walkable_cells(5))
        app.dirty_names = {}    # Testumbenennung nicht weiterverwenden
        # Map-Wechsel: Etage 2 auf die Map von Etage 1 umstellen
        app.floor_var.set(2); app._load_floor()
        _new_map = next(m for m in app._map_choice_ids
                        if m != app.btower_orig[2] and m in app._map_donor_floors)
        app.map_combo.current(app._map_choice_ids.index(_new_map))
        app._change_map()
        assert app.btower[2] == _new_map and 2 in app.dirty_maps and 2 in app.narc_base
        from formats import narc_subfiles as _ns
        _donor_fl = next(f for f, m in sorted(app.btower_orig.items()) if m == _new_map)
        _donor_sub2 = _ns(app.fs.read(f'/yamada/DataBase/db_dpos_{900+_donor_fl}.narc'))[2]
        assert _ns(app.narc_base[2])[2] == _donor_sub2, 'Terrain nicht vom Donor'
        _packed = _pk(app.fs, 2, app.tower_cache[2], base=app.narc_base[2])
        assert _ns(_packed)[2] == _donor_sub2
        # btower-Patch End-to-End auf Wegwerf-Kopie (.inc + ARM9)
        import tempfile, struct as _st2
        _tmp = os.path.join(tempfile.gettempdir(), 'bl3p_btower_test.nds')
        app._patch_btower(_tmp)
        from romfs import RomFS as _RF
        _fs2 = _RF(_tmp)
        _rows = parse_inc(_fs2.read('/yamada/DataBase/db_btower.inc').decode('ascii'))
        assert {r[0]: r[1] for r in _rows}[2] == _new_map, 'btower.inc nicht gepatcht'
        with open(_tmp, 'rb') as _f:
            _f.seek(0x20)
            _a9 = _st2.unpack('<I', _f.read(4))[0]
            _f.seek(_a9 + 0xf3b58 + 6)
            _fl, _mp, _pt = _st2.unpack('<3H', _f.read(6))
        assert (_fl, _mp) == (2, _new_map), 'ARM9-btower nicht gepatcht'
        # ARM9-Stat-Sync: geboostete Werte + Faehigkeiten landen im Record
        _n9 = app._sync_arm9_status(_tmp)
        assert _n9 > 200, _n9
        _bu = next(iter(app.god_boosted))
        _bli = [li for li, u, _, _ in app.char_rows if u == _bu][0]
        _bt = [v for _, _, v in line_tokens(app.status_lines[_bli])]
        with open(_tmp, 'rb') as _f:
            _off = ARM9_STATUS_ROM + (_bu - 15) * 70
            _f.seek(_off + 6)
            assert _st2.unpack('<H', _f.read(2))[0] == _bu
            _f.seek(_off + 12)
            _hp, _sp = _st2.unpack('<HH', _f.read(4))
            _f.seek(_off + 50)
            _ab = list(_st2.unpack('<10H', _f.read(20)))
        assert _hp == min(_bt[6], 65535), (_hp, _bt[6])
        assert _ab == _bt[30:40], (_ab, _bt[30:40])
        os.remove(_tmp)
        # Relocation: groessere Donor-Map (31 = 19876 B) auf eine kleine
        # 19332-Etage legen und per Save in freien ROM-Platz umziehen
        _relo = os.path.join(tempfile.gettempdir(), 'bl3p_reloc_test.nds')
        import shutil as _sh
        _sh.copyfile(app.rom_var.get(), _relo)
        _fsR = _RF(_relo)
        _big = _fsR.read('/yamada/DataBase/db_dpos_912.narc')   # Map 31, 19876 B
        assert len(_big) == 19876
        _slot3 = _fsR.fat[_fsR.by_path['/yamada/DataBase/db_dpos_903.narc']]
        assert _slot3[1] - _slot3[0] == 19332              # Etage 3 hat kleinen Slot
        _packedR = _pk(_fsR, 3, _fu(_fsR, 3), base=_big)
        assert len(_packedR) == 19876
        _fsR.write('/yamada/DataBase/db_dpos_903.narc', _packedR)  # in-place -> Relocation
        _fsV = _RF(_relo)
        _backR = _fsV.read('/yamada/DataBase/db_dpos_903.narc')
        assert _backR == _packedR, 'Relocation-Ruecklese falsch'
        _newfat = _fsV.fat[_fsV.by_path['/yamada/DataBase/db_dpos_903.narc']]
        assert _newfat[0] >= 0x78e8a14, 'nicht in freien Platz umgezogen'
        assert _fsV.read('/yamada/DataBase/db_dpos_901.narc') == \
            app.fs.read('/yamada/DataBase/db_dpos_901.narc'), 'Nachbar-Datei kaputt'
        os.remove(_relo)
        # Hit & Run (375) darf NIE in Zufalls-Loadouts landen (AI-Endloszuege)
        for _li2, _u2, _, _ in app.char_rows:
            if _u2 in app.god_boosted:
                _t2 = [v for _, _, v in line_tokens(app.status_lines[_li2])]
                assert 375 not in _t2[31:40], f'Hit&Run bei {_u2} gewuerfelt!'
        # Batch-Filter: "nur Hollows" liefert ausschliesslich Hollow-IDs
        app.rand_only.set('Hollows (klein/mittel)')
        app.floor_var.set(6); app._load_floor()
        app._randomize_floor()
        _en6 = [u for u in app.tower_cache[6] if u['slot'] >= 16]
        assert _en6 and {u['char'] for u in _en6} <= \
            set(PRESET_BATCHES['Hollows (klein/mittel)']), 'Batch-Filter wirkt nicht'
        app.rand_only.set('- alle -')
        # Story-Maps: Free-Battle-Donor (4 Subfiles) UND Story-Kampf-Donor
        # mit nur 3 Subfiles (Spawn-Subfile kommt von der eigenen Etage)
        _story = sorted(app.map_fb_donors)
        assert _story, 'keine Story-Maps gefunden'
        # Donor-Mengen sind dynamisch (Map-Wechsel verschieben Maps zwischen
        # Turm- und Story-Donoren) - nur die GESAMT-Abdeckung ist fix
        _all_maps = set(_story) | set(app._map_donor_floors)
        assert {1, 3, 5, 8, 9, 12, 18, 23, 28, 32} <= _all_maps, _all_maps
        _test_maps = [_story[0]]
        _st3 = [m for m in _story if app.map_fb_donors[m][0] == 'story']
        if _st3:
            _test_maps.append(_st3[0])
        for _sm in _test_maps:              # fb-Donor + Story-Kampf-Donor
            app.floor_var.set(6); app._load_floor()
            app.map_combo.current(app._map_choice_ids.index(_sm))
            app._change_map()
            assert app.btower[6] == _sm and 6 in app.narc_base
            _msubs = _ns(app.narc_base[6])
            assert len(_msubs) == 4, f'Map {_sm}: {len(_msubs)} Subfiles'
            assert [len(s) for s in _msubs][:2] == [6912, 9288], 'Donor-Rebuild falsch'
            assert set(_msubs[2]) <= {0, 10, 255}, 'Subfile 2 ist kein Terrain-Grid'
            _wg = _msubs[2]
            for _s6 in app.party_cache[6]:
                assert _wg[(_s6['y'] - 1) * 39 + (_s6['x'] - 1)] == 10, 'Deploy nicht begehbar'
            _pk(app.fs, 6, app.tower_cache[6], base=app.narc_base[6])   # packbar
            # zuruecksetzen fuer den naechsten Durchlauf
            app.btower[6] = app.btower_orig[6]
            app.narc_base.pop(6, None)
            app.dirty_maps.discard(6)
            app.map_cache.pop(6, None); app.walk_cache.pop(6, None)
        # Slots auffuellen: alle sicheren Chars haben danach 9 Faehigkeiten
        _orig_ask = messagebox.askyesno
        messagebox.askyesno = lambda *a, **k: True
        app._fill_all_ability_slots()
        messagebox.askyesno = _orig_ask
        for _li3, _u3, _, _ in app.char_rows:
            if _u3 in app.risky_units:
                continue
            _t3 = [v for _, _, v in line_tokens(app.status_lines[_li3])]
            assert 0 not in _t3[31:40], f'Unit {_u3} hat leere Slots'
        # Map-Namen: freie Beschriftung ueber map_names.json
        app.map_names[31] = 'Testland'
        app._refresh_map_combo()
        _i31 = app._map_choice_ids.index(31)
        assert 'Testland' in app.map_combo['values'][_i31], app.map_combo['values'][_i31]
        del app.map_names[31]
        # Skill-Picker: Feld-Roundtrip (Set-ID bleibt erhalten)
        app.charlist.selection_set(0); app._on_char_select()
        before = app.abil_var.get()
        assert before.split(',')[0].strip() == '1'   # Yamamotos Skill-Set-ID
        print(f'SELFTEST OK - {n_playable} spielbare Einheiten im Filter, '
              f'Skills/Pressure-Editing funktioniert, Randomizer: {len(en)} Gegner ok')
        app.destroy()
    else:
        app._start_icloud_watcher()   # In-Game-Saves -> iCloud (iPhone)
        app.mainloop()
