"""
Process-global lock for torch model initialization.

accelerate's init_empty_weights() monkey-patches torch.nn.Module.__init__
globally (not thread-locally). While this context is active, ANY nn.Module
creation in ANY thread produces meta tensors instead of real ones.

This lock must be held by any code that:
1. Loads models via libraries that use init_empty_weights() (e.g. sentence_transformers)
2. Constructs torch models that need real tensors (e.g. Kokoro TTS)

See: ai/semantic_search.py, audio/kokoro_tts.py
"""

import threading

model_init_lock = threading.Lock()
