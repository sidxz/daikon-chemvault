import json
from threading import Lock
from typing import List, Tuple
from app.core.logging_config import logger

_model = None
_model_lock = Lock()


def _get_model():
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:
                from admet_ai import ADMETModel
                logger.info("Loading admet_ai model (first request)…")
                _model = ADMETModel()
                logger.info("admet_ai model loaded")
    return _model


def predict_batch(smiles_list: List[str]) -> List[Tuple[str, dict]]:
    """Return [(smiles, props), …] for each input SMILES that admet_ai accepted.

    admet_ai drops SMILES that RDKit can't parse, so the output may be shorter
    than the input — callers must map results back by SMILES rather than by
    positional zip. Roundtrips through pandas' JSON serializer so numpy scalars
    (float32 from Chemprop) become native Python types and NaN becomes null,
    both required for JSONB persistence via asyncpg.
    """
    model = _get_model()
    df = model.predict(smiles=smiles_list)
    records = json.loads(df.to_json(orient="records"))
    return list(zip(df.index.tolist(), records))


def get_model_version() -> str:
    import admet_ai
    return getattr(admet_ai, "__version__", "unknown")
