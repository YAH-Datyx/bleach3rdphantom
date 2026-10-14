"""Selbsttest fuer den 370/401-Fix - laeuft OHNE ROM und OHNE Tkinter-Fenster.

    python tools/test_essential_abil.py

Prueft die beiden Stellen, die den HP-Bug-Verdacht aus HANDOVER 5.3 abdecken:
  1. _abil_loadout  - das Zufalls-Loadout loescht 370/401 nicht mehr
  2. _repair_essential_abil - traegt sie bei schon beschaedigten Chars nachtraeglich ein
"""
import os
import random
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, 'tools'))


def _stub_tkinter():
    """Ohne Display/tkinter (Cloud, CI) wird tkinter durch Platzhalter ersetzt.
    Getestet wird reine Datenlogik - es wird nie ein Fenster gebaut."""
    import types
    tk = types.ModuleType('tkinter')

    class _Any:
        def __init__(self, *a, **k):
            pass

        def __getattr__(self, name):
            return _Any()

        def __call__(self, *a, **k):
            return _Any()

    tk.Tk = type('Tk', (), {'__init__': lambda self, *a, **k: None,
                            '__getattr__': lambda self, n: _Any()})
    for n in ('Frame', 'Label', 'Button', 'Canvas', 'Listbox', 'Text', 'Toplevel',
              'StringVar', 'IntVar', 'PhotoImage', 'Menu', 'Scrollbar'):
        setattr(tk, n, _Any)
    for n in ('ttk', 'messagebox', 'filedialog', 'simpledialog'):
        sub = types.ModuleType('tkinter.' + n)
        sub.__getattr__ = lambda name: _Any()
        setattr(tk, n, sub)
        sys.modules['tkinter.' + n] = sub
    sys.modules['tkinter'] = tk


try:
    import tkinter                                           # noqa: F401
except ImportError:
    _stub_tkinter()

import stat_editor as SE                                     # noqa: E402

App = SE.App
TOK = SE.ABIL_TOKENS
N = SE.TOKENS_PER_LINE


def make_line(abil):
    """db_status.inc-artige Zeile mit 42 Zahlen; abil = 10 Faehigkeits-Slots."""
    toks = [0] * N
    for i, t in enumerate(TOK):
        toks[t] = abil[i]
    return '\t' + ', '.join(str(v) for v in toks) + ',\n'


def abil_of(line):
    toks = SE.line_tokens(line)
    return [toks[t][2] for t in TOK]


def test_reference():
    ess = SE.ESSENTIAL_ABIL
    assert ess, 'ESSENTIAL_ABIL ist leer - tools/gen_essential_abil.py laufen lassen'
    assert len(ess) == 59, len(ess)
    for u in ('141', '113', '115', '136', '140', '129'):      # Kampagnen-Chars
        assert ess[u] == [370, 401], (u, ess.get(u))
    assert '1' not in ess and '94' not in ess                # Yamamoto/Ichigo nicht
    assert '145' not in ess and '151' not in ess             # Hollows nicht
    print(f'  ok  Referenz: {len(ess)} Einheiten mit Pflicht-Faehigkeiten')


def test_loadout():
    actives = list(range(1, 60))
    passives = [a for a in range(200, 420) if a not in SE.ESSENTIAL_ABILITIES]
    random.seed(1)
    # a) Char MIT Pflicht-Faehigkeiten -> beide drin, hinten, Slot 0 unberuehrt
    for _ in range(200):
        upd = App._abil_loadout(141, actives, passives)
        assert set(upd) == set(TOK[1:]), 'Slot 0 darf nicht geschrieben werden'
        vals = [upd[t] for t in TOK[1:]]
        assert len(vals) == 9
        assert vals[-2:] == [370, 401], vals
        assert 0 not in vals, vals                 # keine leeren Slots
        assert len(set(vals)) == 9, vals           # keine Dubletten
    print('  ok  Loadout 141 Kenpachi: 370/401 immer auf den Slots 8+9')
    # b) Char OHNE Pflicht-Faehigkeiten -> 9 Zufallswerte wie bisher
    for _ in range(200):
        vals = [App._abil_loadout(145, actives, passives)[t] for t in TOK[1:]]
        assert len(vals) == 9 and 0 not in vals
        assert not (set(vals) & set(SE.ESSENTIAL_ABILITIES)), vals
    print('  ok  Loadout 145 Screamer: keine erfundenen Pflicht-Faehigkeiten')
    # c) winzige Pools brechen nicht
    vals = [App._abil_loadout(141, [1, 2], [300])[t] for t in TOK[1:]]
    assert vals[-2:] == [370, 401] and len(vals) == 9
    print('  ok  Loadout mit Mini-Pools stabil')


class FakeApp:
    """Minimal-Huelle: nur was _repair_essential_abil anfasst."""
    _repair_essential_abil = App._repair_essential_abil

    def __init__(self, rows):
        self.fs = object()
        self.dirty_status = False
        self.status_lines = [make_line(a) for _, a in rows]
        self.char_rows = [(i, u, f'Char{u}', 3) for i, (u, _) in enumerate(rows)]

    def _on_char_select(self, _=None):
        pass

    def _update_abil_preview(self):
        pass


def test_repair():
    rows = [
        # (unit, 10 Faehigkeits-Slots)  - Slot 0 = Set-ID
        (141, [75, 163, 165, 140, 120, 137, 302, 360, 364, 368]),   # beide weg
        (113, [36, 377, 370, 401, 0, 0, 0, 0, 0, 0]),               # intakt
        (136, [20, 227, 401, 0, 0, 0, 0, 0, 0, 0]),                 # 370 fehlt
        (145, [11, 163, 165, 140, 120, 137, 302, 360, 364, 368]),   # kein Anspruch
    ]
    app = FakeApp(rows)
    n = app._repair_essential_abil(silent=True)
    assert n == 2, n
    assert app.dirty_status

    a141 = abil_of(app.status_lines[0])
    assert a141[0] == 75, 'Set-ID in Slot 0 angetastet!'
    assert 370 in a141 and 401 in a141, a141
    assert a141[1:7] == [163, 165, 140, 120, 137, 302], a141   # vorne unberuehrt

    assert abil_of(app.status_lines[1]) == rows[1][1], 'intakter Char veraendert'

    a136 = abil_of(app.status_lines[2])
    assert a136[0] == 20 and a136[1] == 227
    assert 370 in a136 and 401 in a136, a136
    assert a136.count(401) == 1, a136              # nicht verdoppelt

    assert abil_of(app.status_lines[3]) == rows[3][1], 'Screamer angefasst'
    print('  ok  Reparatur: 2 von 4 Chars gefixt, Slot 0 + intakte unberuehrt')

    # Idempotenz: zweiter Lauf aendert nichts mehr
    before = list(app.status_lines)
    assert app._repair_essential_abil(silent=True) == 0
    assert app.status_lines == before
    print('  ok  Reparatur ist idempotent')


def test_wave_templates():
    """raw[0] (Welle) der Vanilla-Templates: der Randomizer muss 0 erzwingen."""
    bad = {f: sum(1 for t in tpl if t['raw'][0] != 0)
           for f, tpl in SE.VANILLA_REF['floors'].items()}
    bad = {f: n for f, n in bad.items() if n}
    assert bad, 'Testdaten unerwartet - keine Nachschub-Templates gefunden'
    assert sum(bad.values()) == 36, bad
    src = open(os.path.join(HERE, 'stat_editor.py')).read()
    assert 'raw[0] = 0' in src, '_randomize_floor erzwingt Welle 0 nicht'
    print(f'  ok  Welle: {sum(bad.values())} Nachschub-Templates auf den Etagen '
          + ', '.join(sorted(bad, key=int)) + ' -> raw[0]=0 erzwungen')


if __name__ == '__main__':
    print('Selbsttest 370/401 + Welle:')
    test_reference()
    test_loadout()
    test_repair()
    test_wave_templates()
    print('ALLE TESTS OK')
