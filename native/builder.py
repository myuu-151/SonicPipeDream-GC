"""Sonic Pipe Dream Builder: the GameCube disc image from this repo, in a window.

    Double-click "Build Sonic Pipe Dream.bat" (or: python native/builder.py)

It checks what the build needs (Python's Pillow and numpy, devkitPro, Octave-libogc, and the PC
repo, SonicPipeDream, beside this one) and says how to fix what's missing. Then one button makes
what isn't in git -- the sky's textures (from the PC repo's sky generator) and the seven other
skies (copied from the PC repo) -- packages the disc with Octave, gives it its name, and shows
where the ISO is. Everything else (stages, Sonic, sounds, music, menus) is in git.

Every step runs in the background, without a console window of its own; the window shows each
step's progress, and of the output only the steps and errors ("Show every line" for the rest).
All of it is in proj/Intermediate/builder.log. The folders chosen are remembered in
native/.builder.json (not in git).
"""
import json
import os
import queue
import re
import subprocess
import sys
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, ttk

HERE = Path(__file__).resolve().parents[1]
PROJ = HERE / 'proj'
ISO = PROJ / 'Packaged' / 'GameCube' / 'SonicPipeDream.iso'
PACKAGED = PROJ / 'Packaged' / 'GameCube' / 'SonicPipeDream'
SETTINGS = Path(__file__).with_name('.builder.json')
LOG_FILE = PROJ / 'Intermediate' / 'builder.log'
LOW_PRIORITY = 0x4000 | 0x08000000  # below normal, no console window (Windows)
# "@@ DONE TOTAL": how far a step is (export_assets_gc.py prints it when BUILD_PROGRESS is set).
PROGRESS = re.compile(r'^@@ (\d+) (\d+)$')
SOURCE_LINE = re.compile(r'^[\w.+-]+\.(?:cpp|c)$')
# Octave's packaging chatter: never an error, even where it says so.
NOISE = re.compile(r'^(?:Asset (?:loaded|saved)|Unloading|Loading script|Cannot unload|Auto-parenting|\[Exec\]|'
                   r'Attempting to watch|Headless mode|Running EngineStartup|\(Octave\)|Begin packaging|'
                   r'DevkitPro is installed|Shutdown Complete|Failed to open file|Stream failed|_mkdir error|'
                   r'make(?:\[\d+\])?: |\[ -d |\s*>>|\s*\d+ [Ff]ile\(s\) (?:copied|moved)|The file cannot be copied|'
                   r'The system cannot find the file|[A-Za-z]:[\\/])')
IMPORTANT = re.compile(r'\berror\b|undefined reference|No rule to make|ld returned|\bfailed\b|Traceback', re.IGNORECASE)


def msys(path):
    """C:\\devkitPro -> /c/devkitPro, as devkitPro's makefiles want it."""
    p = Path(path).as_posix()
    return f'/{p[0].lower()}{p[2:]}' if len(p) > 1 and p[1] == ':' else p


def find_devkitpro():
    for candidate in (os.environ.get('DEVKITPRO_WIN'), os.environ.get('DEVKITPRO'), r'C:\devkitPro',
                      r'C:\gekko-toolchain'):
        if not candidate:
            continue
        if candidate.startswith('/') and len(candidate) > 2 and candidate[2] == '/':
            candidate = f'{candidate[1].upper()}:{candidate[2:]}'  # /c/devkitPro
        elif candidate.startswith('/opt/devkitpro'):
            candidate = r'C:\devkitPro'
        if (Path(candidate) / 'devkitPPC' / 'bin' / 'powerpc-eabi-gcc.exe').exists():
            return Path(candidate)
    return None


def default_folder(*names):
    """The first of these folders beside this repo (or beside its parent) that exists."""
    for base in (HERE.parent, HERE.parent.parent):
        for name in names:
            if (base / name).is_dir():
                return str(base / name)
    return str(HERE.parent / names[0])


def console_python():
    """Python's console executable (python.exe beside pythonw.exe): the steps run under it with a
    hidden console, so nothing they start opens a window of its own."""
    exe = Path(sys.executable)
    if exe.name.lower() == 'pythonw.exe' and exe.with_name('python.exe').exists():
        return str(exe.with_name('python.exe'))
    return str(exe)


def made(name):
    """What export_assets_gc.py noted it made (proj/Intermediate/NAME.made), or None."""
    try:
        return int((PROJ / 'Intermediate' / (name + '.made')).read_text().strip())
    except (OSError, ValueError):
        return None


def sky_textures_ready():
    textures = PROJ / 'Assets' / 'Textures'
    have = len(list(textures.glob('T_S2Sky_*.oct'))) if textures.is_dir() else 0
    return have > 0 and made('sky_textures') == have


def skies_ready(pc):
    """Each of the PC repo's skies here, file for file."""
    src = Path(pc) / 'proj' / 'Assets' / 'Skies'
    if not src.is_dir():
        return False
    for sky in (d for d in src.iterdir() if d.is_dir()):
        dst = PROJ / 'Assets' / 'Skies' / sky.name
        if not dst.is_dir() or len(os.listdir(dst)) != len(os.listdir(sky)):
            return False
    return True


# --- the GameCube toolchain: devkitPro's install or gekko-toolchain, whichever is chosen ---------
TOOLCHAIN_SETTING = Path(__file__).with_name('.toolchain.json')   # (not in git)


def toolchain_path(candidate):
    """A toolchain folder from a folder or a DEVKITPRO-style value (/c/devkitPro), or None."""
    if not candidate:
        return None
    if candidate.startswith('/') and len(candidate) > 2 and candidate[2] == '/':
        candidate = f'{candidate[1].upper()}:{candidate[2:]}'
    elif candidate.startswith('/opt/devkitpro'):
        candidate = r'C:\devkitPro'
    path = Path(candidate)
    return path if (path / 'devkitPPC' / 'bin' / 'powerpc-eabi-gcc.exe').exists() else None


def toolchain_label(path):
    """"gekko-toolchain r49.2  (C:\\gekko-toolchain)" or "devkitPro r49.2  (C:\\devkitPro)"."""
    kind = 'gekko-toolchain' if (path / 'VERSIONS.txt').exists() and (path / 'Install.bat').exists() else 'devkitPro'
    version = ''
    try:
        version = next(line.split()[1].split('-')[0] for line in (path / 'VERSIONS.txt').read_text().splitlines()
                       if line.startswith('devkitPPC '))
    except (OSError, StopIteration, IndexError):
        # (Windows matches names regardless of case: devkitppc-rules would match a glob too)
        db = path / 'msys2' / 'var' / 'lib' / 'pacman' / 'local'
        found = sorted(m.group(1) for d in (db.iterdir() if db.is_dir() else ())
                       for m in [re.match(r'devkitPPC-(r[0-9.]+)-', d.name)] if m)
        if found:
            version = found[-1]
    return f'{kind} {version}'.strip() + f'  ({path})'


def toolchain_settings():
    try:
        return json.loads(TOOLCHAIN_SETTING.read_text())
    except (OSError, ValueError):
        return {}


def find_toolchains():
    """Every toolchain there is: DEVKITPRO's, C:\\devkitPro, C:\\gekko-toolchain, and folders chosen before."""
    found = []
    for candidate in (os.environ.get('DEVKITPRO_WIN'), os.environ.get('DEVKITPRO'), r'C:\devkitPro',
                      r'C:\gekko-toolchain', *toolchain_settings().get('folders', [])):
        path = toolchain_path(candidate)
        if path and all(path.resolve() != other.resolve() for other in found):
            found.append(path)
    return found


class Builder:
    def __init__(self, root):
        self.root = root
        self.lines = queue.Queue()
        self.busy = False
        self.ready = False
        root.title('Sonic Pipe Dream Builder')
        root.minsize(660, 520)
        settings = {}
        try:
            settings = json.loads(SETTINGS.read_text())
        except (OSError, ValueError):
            pass
        self.octave = tk.StringVar(value=settings.get('octave', default_folder('octave-libogc', 'Octave-libogc')))
        self.pc = tk.StringVar(value=settings.get('pc', default_folder('SonicPipeDream', 'Sonic2Special3D')))
        self.remake = tk.BooleanVar(value=False)
        self.verbose = tk.BooleanVar(value=False)
        self.entries = []  # every line of output: (text, shown without "Show every line")
        self.phase = ''
        self.step = ''

        pad = {'padx': 10, 'pady': 4}
        ttk.Label(root, text='Sonic Pipe Dream for the GameCube', font=('Segoe UI', 14, 'bold')).pack(anchor='w', **pad)

        checks = ttk.LabelFrame(root, text='What the build needs')
        checks.pack(fill='x', **pad)
        self.rows = {}
        for key, title in (('python', 'Python: Pillow and numpy'), ('devkitpro', 'GameCube toolchain'),
                           ('octave', 'Octave-libogc'), ('pc', 'Sonic Pipe Dream (PC repo)')):
            row = ttk.Frame(checks)
            row.pack(fill='x', padx=6, pady=2)
            mark = ttk.Label(row, width=3, font=('Segoe UI', 11, 'bold'))
            mark.pack(side='left')
            ttk.Label(row, text=title, width=26).pack(side='left')
            note = ttk.Label(row, foreground='#555')
            note.pack(side='left', fill='x', expand=True)
            if key in ('octave', 'pc'):
                ttk.Button(row, text='Choose...', command=lambda k=key: self.choose(k)).pack(side='right')
            if key == 'devkitpro':
                self.add_toolchain_switch(row)
            self.rows[key] = (mark, note)

        options = ttk.Frame(root)
        options.pack(fill='x', **pad)
        ttk.Checkbutton(options, text='Make the skies again', variable=self.remake).pack(side='left')

        buttons = ttk.Frame(root)
        buttons.pack(fill='x', **pad)
        self.build_button = ttk.Button(buttons, text='Build Sonic Pipe Dream', command=self.build)
        self.build_button.pack(side='left')
        self.open_button = ttk.Button(buttons, text='Open the ISO folder', command=self.open_folder)
        self.open_button.pack(side='left', padx=8)
        self.progress = ttk.Progressbar(buttons, mode='indeterminate', length=240, maximum=100)  # while building

        self.status = ttk.Label(root, text='')
        self.status.pack(anchor='w', **pad)

        ttk.Checkbutton(root, text='Show every line', variable=self.verbose,
                        command=self.show_log).pack(anchor='w', padx=10)
        frame = ttk.Frame(root)
        frame.pack(fill='both', expand=True, padx=10, pady=(0, 10))
        self.log = tk.Text(frame, height=14, wrap='none', font=('Consolas', 9), state='disabled')
        scroll = ttk.Scrollbar(frame, command=self.log.yview)
        self.log.configure(yscrollcommand=scroll.set)
        scroll.pack(side='right', fill='y')
        self.log.pack(side='left', fill='both', expand=True)

        self.check()
        self.update_open()
        root.after(100, self.pump)

    # --- what the build needs -------------------------------------------------

    # --- the toolchain switch ----------------------------------------------

    def add_toolchain_switch(self, row):
        """The devkitPro row's drop-down (every toolchain found) and Choose button (another folder)."""
        ttk.Button(row, text='Choose...', command=self.choose_toolchain).pack(side='right')
        self.toolchain_box = ttk.Combobox(row, state='readonly', width=44)
        self.toolchain_box.pack(side='right', padx=4)
        self.toolchain_box.bind('<<ComboboxSelected>>', lambda _e: self.pick_toolchain(self.toolchain_box.current()))
        self.toolchains = []

    def refresh_toolchains(self):
        """The toolchains found, into the drop-down; self.devkitpro the one chosen (else the first)."""
        self.toolchains = find_toolchains()
        self.toolchain_box['values'] = [toolchain_label(p) for p in self.toolchains]
        chosen = toolchain_settings().get('chosen')
        index = next((i for i, p in enumerate(self.toolchains) if chosen and p.resolve() == Path(chosen).resolve()), 0)
        self.devkitpro = self.toolchains[index] if self.toolchains else None
        if self.toolchains:
            self.toolchain_box.current(index)
        else:
            self.toolchain_box.set('')

    def save_toolchain(self, path, add=False):
        settings = toolchain_settings()
        settings['chosen'] = str(path)
        if add and str(path) not in settings.setdefault('folders', []):
            settings['folders'].append(str(path))
        try:
            TOOLCHAIN_SETTING.write_text(json.dumps(settings))
        except OSError:
            pass

    def pick_toolchain(self, index):
        if 0 <= index < len(self.toolchains):
            self.save_toolchain(self.toolchains[index])
            self.check()

    def choose_toolchain(self):
        folder = filedialog.askdirectory(title='A GameCube toolchain: devkitPro or gekko-toolchain (the folder with devkitPPC in it)')
        if not folder:
            return
        path = toolchain_path(folder)
        if path is None:
            self.set_row('devkitpro', False, f'no devkitPPC in {folder}')
            return
        self.save_toolchain(path, add=True)
        self.check()

    def set_row(self, key, ok, note):
        mark, label = self.rows[key]
        mark.configure(text='OK' if ok else 'X', foreground='#1a7f37' if ok else '#c62828')
        label.configure(text=note)

    def check(self):
        ok = True
        missing = []
        for module, package in (('PIL', 'pillow'), ('numpy', 'numpy')):
            try:
                __import__(module)
            except ImportError:
                missing.append(package)
        if missing:
            self.set_row('python', False, 'run: py -m pip install ' + ' '.join(missing))
            ok = False
        else:
            self.set_row('python', True, 'installed')
        self.refresh_toolchains()
        if self.devkitpro:
            self.set_row('devkitpro', True, '')
        else:
            self.set_row('devkitpro', False, 'install devkitPro with devkitPPC (devkitpro.org), or gekko-toolchain (github.com/myuu-151/gekko-toolchain)')
            ok = False
        octave = Path(self.octave.get())
        if not (octave / 'Octave.exe').exists():
            self.set_row('octave', False, f'no Octave.exe in {octave}')
            ok = False
        elif not (octave / 'Engine' / 'Build' / 'GCN' / 'libEngine.a').exists():
            self.set_row('octave', False, 'its GameCube engine library is not built (Engine/Build/GCN/libEngine.a)')
            ok = False
        else:
            self.set_row('octave', True, str(octave))
        pc = Path(self.pc.get())
        if not (pc / 'proj' / 'Assets' / 'Skies').is_dir() or not (pc / 'native' / 'gen_s2sky_assets.py').exists():
            self.set_row('pc', False, f'no Sonic Pipe Dream PC repo in {pc} (github.com/myuu-151/SonicPipeDream)')
            ok = False
        else:
            todo = [what for what, done in (('sky textures', sky_textures_ready()), ('skies', skies_ready(pc))) if not done]
            self.set_row('pc', True, str(pc) + (f'  ({" and ".join(todo)} made when building)' if todo else ''))
        self.ready = ok
        self.build_button.configure(state='normal' if ok and not self.busy else 'disabled')
        self.status.configure(text='Ready to build.' if ok else 'Fix the X items above, then build.')
        return ok

    def choose(self, key):
        var, title = {'octave': (self.octave, 'The Octave-libogc folder'),
                      'pc': (self.pc, "Sonic Pipe Dream's PC repo (SonicPipeDream)")}[key]
        folder = filedialog.askdirectory(title=title, initialdir=var.get() or str(HERE.parent))
        if folder:
            var.set(folder)
            try:
                SETTINGS.write_text(json.dumps({'octave': self.octave.get(), 'pc': self.pc.get()}))
            except OSError:
                pass
            self.check()

    # --- the window's log and progress -------------------------------------

    def write(self, text):
        self.log.configure(state='normal')
        self.log.insert('end', text)
        self.log.see('end')
        self.log.configure(state='disabled')

    def show_log(self):
        """The log again, every line or only those that matter."""
        self.log.configure(state='normal')
        self.log.delete('1.0', 'end')
        self.log.insert('end', ''.join(text + '\n' for text, shown in self.entries if shown or self.verbose.get()))
        self.log.see('end')
        self.log.configure(state='disabled')

    def pump(self):
        try:
            while True:
                kind, *rest = self.lines.get_nowait()
                if kind == 'line':
                    text, shown = rest
                    self.entries.append((text, shown))
                    if shown or self.verbose.get():
                        self.write(text + '\n')
                elif kind == 'phase':
                    self.phase = rest[0]
                    self.show_step('starting')
                elif kind == 'step':
                    self.show_step(rest[0])
                elif kind == 'progress':
                    self.show_progress(*rest)
                elif kind == 'done':
                    self.finished(*rest)
        except queue.Empty:
            pass
        self.root.after(100, self.pump)

    def show_step(self, step):
        """A step without a count yet: the bar moves to show it's working."""
        self.step = step
        self.progress.stop()
        self.progress.configure(mode='indeterminate')
        self.progress.start(12)
        self.status.configure(text=f'{self.phase}: {step}...')

    def show_progress(self, done, total):
        if str(self.progress.cget('mode')) != 'determinate':
            self.progress.stop()
            self.progress.configure(mode='determinate')
        percent = 100 * done // max(total, 1)
        self.progress.configure(value=percent)
        self.status.configure(text=f'{self.phase}: {self.step}, {done} of {total} ({percent}%)')

    def say(self, text):
        """A line of the builder's own, always shown."""
        self.lines.put(('line', text, True))
        with open(LOG_FILE, 'a', encoding='utf-8') as log:
            log.write(text + '\n')

    # --- building ---------------------------------------------------------

    def build(self):
        if self.busy or not self.check():
            return
        self.busy = True
        self.build_button.configure(state='disabled')
        self.progress.pack(side='right')
        self.status.configure(foreground='')
        self.entries = []
        self.show_log()
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        LOG_FILE.write_text('', encoding='utf-8')
        threading.Thread(target=self.run_build, daemon=True).start()

    def run(self, args, cwd, env, watch):
        """Runs a step, in the background at low priority; each line of its output to the log file,
        and to watch, which says whether the window shows it (and may note a step). True if it
        succeeded."""
        startup = None
        if os.name == 'nt':
            # Started hidden: Octave makes its window even when headless, and it would sit on the
            # screen, blank, while it packages.
            startup = subprocess.STARTUPINFO()
            startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startup.wShowWindow = 0  # SW_HIDE
        proc = subprocess.Popen(args, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                stdin=subprocess.DEVNULL, startupinfo=startup,
                                creationflags=LOW_PRIORITY if os.name == 'nt' else 0)
        with open(LOG_FILE, 'a', encoding='utf-8') as log:
            for raw in proc.stdout:
                # (a Windows program's lines end \r\n; a \r alone rewrites the line)
                text = raw.decode('utf-8', 'replace').rstrip('\r\n').split('\r')[-1].rstrip()
                if not text:
                    continue
                found = PROGRESS.match(text)
                if found:
                    self.lines.put(('progress', int(found[1]), int(found[2])))
                    continue
                log.write(text + '\n')
                self.lines.put(('line', text, watch(text)))
        return proc.wait() == 0

    def export(self, part, step):
        """A part of native/export_assets_gc.py, from the PC repo chosen."""
        self.lines.put(('step', step))
        env = dict(os.environ, SPD_PC_REPO=self.pc.get(), BUILD_PROGRESS='1', PYTHONUNBUFFERED='1')
        return self.run([console_python(), '-u', str(HERE / 'native' / 'export_assets_gc.py'), part], HERE, env,
                        lambda text: not NOISE.match(text))

    def watch_packaging(self, started, stop):
        """Octave says little while it packages (the project's Config.ini has its log off): the
        assets it has written so far, of the project's, are the progress."""
        total = sum(1 for _ in (PROJ / 'Assets').rglob('*.oct'))
        while not stop.is_set():
            done = 0
            if PACKAGED.is_dir():
                for path in PACKAGED.rglob('*.oct'):
                    try:
                        done += path.stat().st_mtime >= started
                    except OSError:
                        pass
            if done:
                self.lines.put(('progress', min(done, total), total))
            stop.wait(1.5)

    def run_build(self):
        ok = True
        pc = self.pc.get()
        remake = self.remake.get()
        if remake or not sky_textures_ready() or not skies_ready(pc):
            self.say('== Making what is not in git, from the PC repo')
            self.lines.put(('phase', 'Making the skies'))
            if remake or not sky_textures_ready():
                ok = self.export('sky_textures', "the sky's frames")
            if ok and (remake or not skies_ready(pc)):
                ok = self.export('skies', 'copying the seven other skies')
        if ok:
            self.say('== Building the disc with Octave')
            self.lines.put(('phase', 'Building the disc'))
            self.lines.put(('step', 'packaging the assets'))
            octave = Path(self.octave.get())
            dkp = self.devkitpro
            env = dict(os.environ)
            env['PATH'] = os.pathsep.join([str(dkp / 'devkitPPC' / 'bin'), str(dkp / 'tools' / 'bin'),
                                           str(dkp / 'msys2' / 'usr' / 'bin'), env.get('PATH', '')])
            env['DEVKITPRO'] = msys(dkp)
            env['DEVKITPPC'] = msys(dkp / 'devkitPPC')
            try:
                ISO.unlink()
            except OSError:
                pass
            started, stop = time.time() - 2, threading.Event()
            threading.Thread(target=self.watch_packaging, args=(started, stop), daemon=True).start()
            compiling = {'seen': False}

            def watch(text):
                if SOURCE_LINE.match(text) and not compiling['seen']:
                    compiling['seen'] = True
                    stop.set()
                    self.lines.put(('step', 'compiling the game'))
                elif text.startswith('linking'):
                    self.lines.put(('step', 'linking the game'))
                elif text.startswith('output ...'):
                    self.lines.put(('step', 'writing the disc image'))
                return bool(IMPORTANT.search(text)) and not NOISE.match(text)
            self.run([str(octave / 'Octave.exe'), '-headless', '-project', (PROJ / 'SonicPipeDream.octp').as_posix(),
                      '-build', 'GameCube'], octave, env, watch)
            stop.set()
            ok = ISO.exists()
            if ok:
                self.lines.put(('step', 'naming the disc'))
                ok = self.run([console_python(), str(HERE / 'native' / 'set_disc_name.py'), str(ISO)], HERE,
                              dict(os.environ), lambda text: True)
        self.lines.put(('done', ok))

    def finished(self, ok):
        self.busy = False
        self.progress.stop()
        self.progress.configure(mode='determinate', value=0)
        self.progress.pack_forget()
        self.build_button.configure(state='normal' if self.ready else 'disabled')
        if ok:
            size = ISO.stat().st_size / (1024 * 1024)
            self.status.configure(text=f'Done: {ISO} ({size:.0f} MB)', foreground='#1a7f37')
            self.entries.append((f'== Done: {ISO}', True))
            self.write(f'== Done: {ISO}\n')
        else:
            self.status.configure(text=f'The build failed: the log says why (all of it: {LOG_FILE}).',
                                  foreground='#c62828')
            if not self.verbose.get():
                # what led up to it, which the short log may not have shown
                hidden = [text for text, shown in self.entries if not shown][-25:]
                if hidden:
                    self.write('\n-- the last lines of output:\n' + ''.join(text + '\n' for text in hidden))
        self.check()
        self.update_open()

    def update_open(self):
        self.open_button.configure(state='normal' if ISO.exists() else 'disabled')

    def open_folder(self):
        if ISO.exists():
            subprocess.Popen(['explorer', '/select,', str(ISO)])


def main():
    root = tk.Tk()
    try:
        ttk.Style().theme_use('vista')
    except tk.TclError:
        pass
    Builder(root)
    root.mainloop()


if __name__ == '__main__':
    main()
