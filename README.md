# numpy-shaketune

[Klippain Shake&Tune](https://github.com/Frix-x/klippain-shaketune) for printers whose Python only has **numpy**,
like the FlashForge Creator 5 (32-bit MIPS, no matplotlib, scipy or Pillow builds).

Shake&Tune itself is not changed. This repo adds small numpy/stdlib stand-ins for the three packages it needs
besides numpy, and a Klipper extra that loads the real Shake&Tune with them:

| Package | Shake&Tune uses it for | Stand-in |
|---|---|---|
| matplotlib | every graph | `compat/matplotlib`: a numpy rasteriser that draws the same figures (DejaVu Sans text, antialiased lines and fills, legends, tables, spectrograms, polar and 3D axes) and writes real PNGs |
| zstandard | compressing raw recordings (`.stdata`) | `compat/zstandard`: gzip streams with the same API |
| GitPython | the version string on the graphs | `compat/git`: asks the `git` program, or reads `.git` directly |

The stand-ins go at the **end** of Python's path, so a printer that has the real packages keeps using them.
The numbers on the graphs come from Shake&Tune's own numpy code, so recommendations are identical; the drawing is
a close match to matplotlib's.

## Install (any Klipper or Kalico printer)

This is the `manual` branch. On OpenCreator printers, the `main` branch installs with `oc-plugin` instead.

Needs git and numpy in Klipper's Python (every Klipper install has numpy for input shaping). Then:

```
git clone -b manual https://github.com/FlashForge-C5-Modding-Group/numpy-shaketune ~/numpy-shaketune
~/numpy-shaketune/install.sh
```

`install.sh` finds Klipper and the config folder (`~/klipper` and `~/printer_data/config`, plus the usual
OpenCreator and K1 locations), downloads upstream Shake&Tune into `upstream/`, links `shaketune.py` into
`klippy/plugins` (Kalico) or `klippy/extras` (Klipper), copies `shaketune.cfg` next to `printer.cfg`, adds
`[include shaketune.cfg]` above the SAVE_CONFIG block (backup in `printer.cfg.before-shaketune`) and restarts Klipper.

| Option | |
|---|---|
| `--klipper DIR` | Klipper checkout, if it isn't found on its own |
| `--config DIR` | folder with `printer.cfg` |
| `--no-restart` | don't restart Klipper |
| `--uninstall` | remove the link, the include line and `upstream/` (keeps `shaketune.cfg` and the results) |

To update, run `git -C ~/numpy-shaketune pull` and `~/numpy-shaketune/install.sh` again; that also pulls the newest
Shake&Tune.

Use it like normal Shake&Tune: `AXES_SHAPER_CALIBRATION`, `COMPARE_BELTS_RESPONSES`, `CREATE_VIBRATIONS_PROFILE`,
`AXES_MAP_CALIBRATION`, `EXCITATE_AXIS_AT_FREQ`. Graphs go to `ShakeTune_results` next to `printer.cfg` (set
`result_folder` in `[shaketune]` to change it). Other options are in Shake&Tune's
[docs](https://github.com/Frix-x/klippain-shaketune/blob/main/docs/README.md).

## Creality K1 / K1 SE (Simple AF)

This `k1` branch is the `manual` branch with fixes for the older Python stack on K1-series printers running
Simple AF (pellcorp): Python 3.8, numpy 1.16 and matplotlib 2.2.

```
git clone -b k1 https://github.com/FlashForge-C5-Modding-Group/numpy-shaketune /usr/data/numpy-shaketune
sh /usr/data/numpy-shaketune/install.sh
```

It finds `/usr/data/klipper` (Kalico) and `/usr/data/printer_data/config`, and restarts Klipper with
`/etc/init.d/S55klipper_service`.

- matplotlib 2.2 is too old for Shake&Tune 6, so the compat matplotlib is used instead whenever the installed one is
  older than 3.5. zstandard and GitPython still come from the system if they're there.
- Shake&Tune 6 says it needs Python 3.9, but only its command line tool (`shaketune.cli`) uses 3.9 syntax; the part
  Klipper loads works on 3.8.
- Memory is tight on a K1 SE (209 MB): an input shaper graph peaks around 105 MB and takes about a minute. Simple AF's
  128 MB swap file covers the rest. Close the camera stream while Shake&Tune draws if Klipper reports timer errors.
- The K1's POSIX semaphores are broken, so `multiprocessing.Queue` and `Value` hang and recordings never get written.
  When the loader finds that, it gives Shake&Tune's recorder a pipe-based queue and shared-memory flag instead
  (`compat/_nst_pipequeue.py`). Other systems keep the real ones.
- Simple AF's own `BELTS_SHAPER_CALIBRATION` macro stays; Shake&Tune's belts test is `COMPARE_BELTS_RESPONSES`.

## How it loads

`shaketune.py` is the Klipper extra for `[shaketune]`. It appends `compat/` to Python's path, loads
`upstream/shaketune` as the package `extras.shaketune_upstream` (Shake&Tune imports Klipper's `shaper_calibrate`
relative to `extras`, so it has to live there), defaults `result_folder` to the printer's config folder and hands the
config to Shake&Tune's own `load_config`.

## Notes

- Graphs take a while on a slow CPU. On a Creator 5 drawing a graph takes about 10 s; an input shaper graph needs
  about a minute in total because Klipper's own filter fitting (`shaper_calibrate`) is most of the work.
- Raw recordings written with the zstandard stand-in are gzip, not Zstandard. Reading a real `.zst` recording needs the
  real zstandard package.
- The Klippain logo on the graphs is upside down on purpose. Set `UPSIDE_DOWN_LOGO = False` in
  `compat/matplotlib/axes.py` to turn it the right way up.
- Only the parts of matplotlib Shake&Tune calls are implemented; other programs that need matplotlib won't work with it.

## Licence

GPL-3.0, like Shake&Tune. The font outlines in `compat/matplotlib/_data` are from DejaVu Sans (Bitstream Vera
licence, free to redistribute).
