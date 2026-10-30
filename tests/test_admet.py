import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pandas as pd

from app.services.admet import predictor


def test_overlapping_predictions_run_one_at_a_time(monkeypatch):
    # Overlapping registrations each start an ADMET background task (asyncio.to_thread). admet_ai
    # can't run two predictions at once on the shared model, so predict_batch must take turns.
    running, overlapped = 0, False
    counter = threading.Lock()

    class SlowModel:
        def predict(self, smiles):
            nonlocal running, overlapped
            with counter:
                running += 1
                overlapped |= running > 1
            time.sleep(0.05)
            with counter:
                running -= 1
            return pd.DataFrame({"prop": [1.0] * len(smiles)}, index=smiles)

    monkeypatch.setattr(predictor, "_get_model", lambda: SlowModel())
    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(predictor.predict_batch, [["CCO"], ["CCN"]]))

    assert not overlapped
    assert results == [[("CCO", {"prop": 1.0})], [("CCN", {"prop": 1.0})]]
