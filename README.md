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

## Install (OpenCreator printers)

Needs git (`opkg install git` if it isn't there yet). Then:

```
oc-plugin install https://github.com/FlashForge-C5-Modding-Group/numpy-shaketune
```

The install script downloads upstream Shake&Tune into the plugin folder, the plugin manager links `shaketune.py`
into Klipper and `shaketune.cfg` into the config, and Klipper restarts. `oc-plugin update numpy-shaketune` pulls the
newest Shake&Tune; `oc-plugin remove numpy-shaketune` takes it all out again.

Use it like normal Shake&Tune: `AXES_SHAPER_CALIBRATION`, `COMPARE_BELTS_RESPONSES`, `CREATE_VIBRATIONS_PROFILE`,
`AXES_MAP_CALIBRATION`, `EXCITATE_AXIS_AT_FREQ`. Graphs go to `ShakeTune_results` next to `printer.cfg` (set
`result_folder` in `[shaketune]` to change it). Other options are in Shake&Tune's
[docs](https://github.com/Frix-x/klippain-shaketune/blob/main/docs/README.md).

For a printer without the OpenCreator plugin manager, use the `manual` branch.

## How it loads

`shaketune.py` is the Klipper extra for `[shaketune]`. It appends `compat/` to Python's path, loads
`upstream/shaketune` as the package `extras.shaketune_upstream` (Shake&Tune imports Klipper's `shaper_calibrate`
relative to `extras`, so it has to live there), defaults `result_folder` to the printer's config folder and hands the
config to Shake&Tune's own `load_config`.

## Notes

- Graphs take longer on a slow CPU (about 50 s for an input shaper graph on a Creator 5). Shake&Tune draws them in
  its background process, so printing isn't held up.
- Raw recordings written with the zstandard stand-in are gzip, not Zstandard. Reading a real `.zst` recording needs the
  real zstandard package.
- The Klippain logo on the graphs is upside down on purpose. Set `UPSIDE_DOWN_LOGO = False` in
  `compat/matplotlib/axes.py` to turn it the right way up.
- Only the parts of matplotlib Shake&Tune calls are implemented; other programs that need matplotlib won't work with it.

## Licence

GPL-3.0, like Shake&Tune. The font outlines in `compat/matplotlib/_data` are from DejaVu Sans (Bitstream Vera
licence, free to redistribute).
