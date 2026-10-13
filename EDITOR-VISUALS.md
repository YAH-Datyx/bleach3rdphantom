# Editor-Visuals — Zusammenfassung für die Design-AI

> Ziel: Ein **besseres, moderneres Design** für unseren Desktop-Editor.
> Diese Datei beschreibt den **aktuellen visuellen Ist-Zustand** so genau,
> dass du daraus ein konkretes Design-/Restyle-Script erstellen kannst.

---

## 0. WICHTIGSTER CONSTRAINT (bitte zuerst lesen)

Der Editor ist eine **Python-Desktop-App mit `tkinter` / `ttk`** (Standard-
Library, **keine** Web-Technologie, **kein** Qt, **kein** CustomTkinter).
Das Styling passiert über:
- `ttk.Style()` mit `.configure(...)` / `.map(...)` pro Widget-Klasse
- direkte `bg=`/`fg=`/`font=`-Argumente bei klassischen `tk`-Widgets
  (`tk.Canvas`, `tk.Text`, `tk.Listbox`)

**Deine Ausgabe muss in reinem tkinter/ttk umsetzbar sein.** Das heißt konkret:
- ❌ **keine** echten runden Ecken, Schatten, Gradienten, Blur, Transparenz
  (tkinter kann das nativ nicht — höchstens gefaked über Canvas-Zeichnung)
- ❌ keine Web-Fonts / Icons aus Font-Awesome etc. — nur **System-Fonts**
  (Windows: Segoe UI, Bahnschrift, Consolas sind verfügbar)
- ✅ erlaubt: Farbpalette, Flat-Design, Padding/Spacing, Font-Hierarchie,
  Zeilenhöhen, Trennlinien, Akzentfarben, Hover-/Active-States,
  Treeview-Zebra-Streifen, Emoji/Unicode-Glyphen als „Icons"
- ✅ Wenn du fancy Elemente willst (Cards mit Rundung, Badges, Progress-Bars),
  müssen sie über `tk.Canvas`-Zeichnung gehen — dann bitte explizit als
  „Canvas-Widget" beschreiben.

**Bevorzugtes Output-Format:** Ein **Design-Konzept in Prosa + eine konkrete
Farb-/Font-/Spacing-Spezifikation** (Tabelle mit Rollen → Hex/Werte), plus
optional Pseudocode für die `ttk.Style`-Konfiguration. Bitte **kein** Umbau
der App-Logik — nur Optik.

---

## 1. App-Rahmen

| Element        | Ist-Wert |
|----------------|----------|
| Framework      | Python 3 + tkinter/ttk, ttk-Theme-Basis `clik`/`default` |
| Fenstertitel   | `BLEACH: The 3rd Phantom - Mod Studio` |
| Fenstergröße   | `1420 × 820` px (resizable) |
| Grundlayout    | **Top-Bar** (ROM-Zeile) · **Center** (Tab-Notebook) · **Bottom-Bar** (Status + Speichern) |

---

## 2. Aktuelle Farbpalette (exakte Hex-Werte)

Dark-Theme, „fast schwarz mit Blaustich" + **Ichigo-Orange** als einziger Akzent.

| Rolle (Code-Konstante) | Hex       | Verwendung |
|------------------------|-----------|------------|
| `G_BG`   Haupt-BG      | `#111318` | Fenster-/Tab-Hintergrund (fast schwarz, leicht blau) |
| `G_DARK` Panel/Button  | `#1a1d24` | Buttons, Tab-Header-Fläche, Treeview-Heading |
| `G_FIELD` Listen-BG    | `#20242d` | Tabellen-/Listen-Hintergrund |
| `G_INPUT` Eingabe-BG   | `#2a2f3a` | Entry/Combobox/Spinbox-Felder |
| `G_GOLD` **Akzent**    | `#ff7a1a` | Überschriften, Auswahl, Aktions-Buttons, Pfeile, Cursor (heißt „Gold", ist aber Orange) |
| `G_RED` Gefahr         | `#d92b2b` | GOD-MODE / destruktive Aktionen (Blut-Rot) |
| `G_TEXT` Haupttext     | `#eceff4` | Standard-Text (fast weiß) |
| `G_HINT` gedämpft      | `#8f9aa8` | Hinweise, inaktive Tab-Beschriftung |
| Rahmen/Border          | `#2c313c` | Borders, Hover-BG |
| Border hell            | `#3a4150` | Feld-Umrandungen |
| Erfolg/grün (vereinzelt)| `#7ee08a` | Status „ok"-Meldungen |
| Canvas-BG (Karte)      | `#0c0e12` | Tower-Map-Canvas |

**Akzent wird derzeit inflationär genutzt** (Überschriften UND Auswahl UND
Buttons UND Icons sind alle `#ff7a1a`) — ein Punkt, an dem ein besseres
Design differenzieren könnte.

---

## 3. Typografie

| Rolle          | Font | Größe |
|----------------|------|-------|
| Standard-Text  | Segoe UI | 10 |
| Bold/Labels    | Segoe UI Semibold | 10 |
| Sektions-Headings (`TLabelframe.Label`) | Bahnschrift | 11 |
| Tab-Beschriftung | Bahnschrift | 12 |
| Char-Titel (groß)| Bahnschrift | 15 |
| Monospace (Debuff-Text) | Consolas | 10 |

**Bahnschrift** (kondensierte Grotesk) gibt aktuell den „technischen/Anime-UI"-
Look. Design-AI darf Font-Hierarchie neu vorschlagen, muss aber bei
**Windows-System-Fonts** bleiben (Segoe UI, Segoe UI Variable, Bahnschrift,
Consolas, Cascadia Code sind sicher da).

---

## 4. Top-Bar (immer sichtbar, oben)

Eine horizontale Zeile:
`ROM: [_______________ Pfad-Entry, breit ___________] [...] [Laden]
[iCloud-Sync] [Save-Manager] [DSV vom Handy holen] [ROM aufs Handy]`
darunter eine zweite Zeile mit Radio-Buttons:
`Speichern als: (•) Kopie [___Pfad___]  ( ) Original  [☐ DeSmuME nach Speichern starten]`

Reine flache ttk-Buttons + Entrys, kein visuelles Gruppieren.

## 5. Bottom-Bar (immer sichtbar, unten)

`[Status-Text linksbündig .....................] [ Alle Änderungen in ROM speichern ]` (rechts, Accent-Button)

---

## 6. Center: Tab-Notebook — 5 Tabs

Tabs (Bahnschrift 12, inaktiv `#8f9aa8`, aktiv orange, flach, kein Rahmen):

### Tab 1 — „Charaktere"
- **Links:** schmale `Listbox` mit allen Charakteren (scrollbar), Suchfeld darüber.
- **Rechts:** Detail-Editor:
  - Kopf: großes Face-Bild (Sprite-Thumbnail) + Char-Name (Bahnschrift 15, orange)
    + Typ-Dropdown rechts.
  - Darunter Stat-Felder als Grid: Level, HP, SP, ATK, DEF, HIT, EVA … (Entry/Spinbox).
  - Ability-/Skill-Zeile mit Entry + „…"-Picker-Button.

### Tab 2 — „Bleach Tower" (das visuell komplexeste Tab)
- **Oben:** `Etage: [Dropdown]  Map: [Dropdown] [Map benennen…] [Map wechseln]`
- **Rechts:** **Karten-Canvas 460×400**, BG `#0c0e12`, in einem LabelFrame
  „Karte (Klick: Einheit versetzen / Marker wählen)". Zeichnet das isometrische/
  Grid-Terrain + Einheiten-Marker (klickbar). Bei Übergröße gedeckelt + scrollbar.
- **Links (füllt Rest):**
  - **Treeview-Tabelle** der Einheiten. Spalten:
    `slot | team | char | name | level | x | y | dir`
    (Breiten 45/65/55/185/55/45/45/45). Zebra wäre möglich, ist aktuell schlicht.
  - **Einheiten-Editor** unter der Tabelle (Felder für die gewählte Einheit).
  - **LabelFrame „Randomizer":** `Ziel-Level [ ] Gegner [ ] bis [ ] Verhalten [Dropdown]
    [Randomisieren]  [GOD-MODE (rot)] [Skill-Chaos] [ℹ]`
  - **Preset-Zeile:** `Preset-Batch: [Dropdown] [Anwenden]  [ALLE 30 Etagen randomisieren]`
  - **Filter-Zeile:** `Randomizer nur aus: […] / ohne: […] / Challenge: […]`
  - **Deploy-Slots:** kleine `Treeview` (Spalten slot/x/y, 4 Zeilen).

### Tab 3 — „Char-Designer"
- Layout wie „Charaktere": links Liste, rechts Editor mit Face + Name-Entry
  + Ability-Slots + Buttons „Speichern", „Auf Etage platzieren", Etagen-Label.

### Tab 4 — „Skills & Fähigkeiten"
- Liste/Übersicht der Skills & Abilities (Referenz-/Nachschlage-Tab).

### Tab 5 — „Debuffs & Status"
- Großes read-only `tk.Text`-Feld (Consolas 10) mit formatiertem Lexikon.
  Eigene Text-Tags: `h1` orange Bahnschrift 12 bold, `h2` orange, Fließtext hell.
  Wirkt wie eine „Dokumentations-/Wiki-Seite" im Editor.

---

## 7. Aktueller Gesamteindruck (ehrliche Einschätzung)

**Stil heute:** funktionaler Dark-Mode „Tool", flach, ein einziger Orange-Akzent,
Bahnschrift-Headlines für „Anime/Tech"-Anmutung. Alles dicht gepackt, wenig
Weißraum, Buttons und Felder ohne visuelle Gruppierung (Cards/Sektionen fehlen).
Die Orange-Akzentfarbe ist überall gleich → keine Hierarchie zwischen „Titel",
„Auswahl" und „Aktion". Treeviews sind schlicht ohne Zebra/Status-Färbung.

**Was ein besseres Design bringen sollte (Auftrag an dich):**
1. **Klare visuelle Hierarchie** — Akzentfarbe differenzieren (z. B. Primär-Aktion
   vs. neutrale Buttons vs. Überschrift). Ggf. 2. Akzentfarbe.
2. **Gruppierung / „Cards"** — verwandte Controls sichtbar zusammenfassen
   (Randomizer, Presets, Filter sind aktuell lose Zeilen). In tkinter über
   `LabelFrame` mit dezentem BG-Unterschied + mehr Padding lösbar.
3. **Spacing/Weißraum** — konsistentes Padding-Raster (z. B. 8/16 px).
4. **Treeview-Politur** — Zebra-Streifen, farbige Team-Spalte (Gegner rot,
   Spieler blau), lesbarere Heading-Zeile.
5. **Buttons** — konsistente Höhe/Padding, klarer Primär/Sekundär/Danger-Look
   (Danger = GOD-MODE rot behalten).
6. **Status-/Feedback-Farben** — grün/gelb/rot für Meldungen in der Bottom-Bar.
7. **Optional:** eigene, thematisch stimmige Palette (Bleach-Ästhetik:
   Schwarz/Weiß/Orange ist gesetzt, aber verfeinerbar).

**Deliverable, das ich (Claude Code) danach umsetze:** eine überarbeitete
`ttk.Style`-Konfiguration + geänderte Farb-/Font-Konstanten (`G_*` oben in
`stat_editor.py`) + ggf. Padding-/Gruppierungs-Anpassungen. Also bitte gib mir
**konkrete Werte** (Hex, Fonts, px-Padding, Widget-für-Widget), nicht nur
allgemeine Design-Prinzipien.
