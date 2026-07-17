# OpenPACE

Code, STL and Gerber files for EvoFlow and EvoSampler, together with the companion software repositories included as submodules.

## Repository layout

| Path | Contents |
|------|----------|
| `EvoFlow` | EvoFlow reactor — STL and Gerber files |
| `EvoSampler` | EvoSampler — code, STL and Gerber files |
| `EvoMonitor` | Real-time monitoring dashboard (EvoHub appliance) — submodule of [Schwank-Lab/evoflow-monitor](https://github.com/Schwank-Lab/evoflow-monitor) |
| `EvoGenotype` | PACE genotype-trajectory analysis CLI — submodule of [Schwank-Lab/evo-genotype](https://github.com/Schwank-Lab/evo-genotype) |
| `Evotool` | Reactor control tool (`evotool.py`) and Pico controller firmware — submodule of [Schwank-Lab/evoflow-reactor](https://github.com/Schwank-Lab/evoflow-reactor) |

## Cloning

`EvoMonitor`, `EvoGenotype` and `Evotool` are git submodules, so clone recursively:

```bash
git clone --recursive https://github.com/GibsonAssembly/OpenPACE.git
```

If you already cloned without `--recursive`, initialise them with:

```bash
git submodule update --init --recursive
```
