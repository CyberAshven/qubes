# Patches

These files patch the PyInstaller bundle at `D:\Qubes\qubes-backend\_internal\`.

## torch/

Fixes for missing torch submodules in the bundled build (torch 2.10.0+cpu). The PyInstaller
bundle strips `torch.distributed`, `torch.futures`, and `torch.rpc` — but TTS (Kokoro) and
GPU acceleration code paths import them. Without these patches, Qubes errors on:
- `No module named 'torch.distributed'`
- `cannot import name 'Future' from 'torch.futures'`
- `cannot import name 'nn' from partially initialized module 'torch'`

### How to apply after a Qubes update:
Copy these files into `D:\Qubes\qubes-backend\_internal\torch\`:
```
patches/torch/distributed/__init__.py  → _internal/torch/distributed/__init__.py
patches/torch/futures/__init__.py      → _internal/torch/futures/__init__.py
patches/torch/rpc/__init__.py          → _internal/torch/rpc/__init__.py
patches/torch/nn/__init__.py           → _internal/torch/nn/__init__.py  (replaces existing)
```
