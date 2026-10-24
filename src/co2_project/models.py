"""Training-only scaling and the fixed regression and neural-network recipes."""
from __future__ import annotations

import hashlib
import warnings
from dataclasses import dataclass
from time import perf_counter

import numpy as np
import pandas as pd
from sklearn.neural_network import MLPRegressor
from threadpoolctl import threadpool_limits


def neural_settings(seed=42):
    """Return the frozen NN recipe used for both input groups.

    Args:
        seed: Model initialization seed, separate from fault placement seeds.
    Returns:
        dict: MLPRegressor parameters; no internal early-stopping split is used.
    """
    return dict(hidden_layer_sizes=(16, 8), activation="relu", solver="adam",
                alpha=.01, batch_size=128, learning_rate_init=.001, max_iter=400,
                shuffle=False, random_state=seed, tol=1e-4, early_stopping=False,
                n_iter_no_change=20)


@dataclass
class NeuralFit:
    """A fitted NN together with training-only scaling, warnings and batch fit time.

    x_mean/x_scale describe input columns; y_mean/y_scale describe CO2 in ppm.
    The trained object never refits when predict is called.
    """
    model: MLPRegressor
    columns: list
    x_mean: np.ndarray
    x_scale: np.ndarray
    y_mean: float
    y_scale: float
    warnings: list
    seconds: float

    def predict(self, features):
        """Predict CO2 ppm from a finite DataFrame using the recorded column order.

        Args:
            features: Eligible input rows; columns must include all fitted inputs.
        Returns:
            pandas.Series: Predictions in ppm with the supplied row index.
        Raises:
            ValueError: Inputs are not finite.
            KeyError: A fitted column is missing.
        """
        values = features.loc[:, self.columns].to_numpy()
        if not np.isfinite(values).all():
            raise ValueError("Predictor inputs must be finite.")
        with threadpool_limits(limits=1):
            scaled = self.model.predict((values - self.x_mean) / self.x_scale)
        return pd.Series(self.y_mean + self.y_scale * scaled, index=features.index)

    def metadata(self):
        """Return serializable fit settings, weight digest and warnings.

        Returns:
            dict: Parameter count, epochs and provenance; no measurements or weights.
        """
        arrays = self.model.coefs_ + self.model.intercepts_
        return {"features": self.columns, "epochs": int(self.model.n_iter_),
                "parameters": sum(a.size for a in arrays), "settings": self.model.get_params(),
                "weights_sha256": hashlib.sha256(b"".join(a.tobytes() for a in arrays)).hexdigest(),
                "warnings": [str(w.message) for w in self.warnings], "fit_on": "original training only"}


def fit_neural(train_x, train_y, seed=42, settings=None):
    """Fit the fixed NN with means and scales learned only from supplied training rows.

    Args:
        train_x: Training feature DataFrame; no validation/test rows are passed.
        train_y: Corresponding original CO2 Series in ppm.
        seed: Initialization seed if settings is omitted.
        settings: Optional fixed MLPRegressor configuration, not a search grid.
    Returns:
        NeuralFit: Model, scalers, warnings and fit time.
    Raises:
        ValueError: The target is constant/nonfinite or inputs are nonfinite.
    """
    started = perf_counter()
    x = train_x.to_numpy()
    if not np.isfinite(x).all() or not np.isfinite(train_y.to_numpy()).all():
        raise ValueError("Training inputs and target must be finite.")
    x_mean, x_scale = x.mean(axis=0), x.std(axis=0)
    x_scale[x_scale == 0] = 1
    y_mean, y_scale = float(train_y.mean()), float(train_y.std(ddof=0))
    if y_scale <= 0:
        raise ValueError("Training CO2 target must vary.")
    model = MLPRegressor(**(settings if settings is not None else neural_settings(seed)))
    with warnings.catch_warnings(record=True) as caught, threadpool_limits(limits=1):
        warnings.simplefilter("always")
        model.fit((x - x_mean) / x_scale, (train_y.to_numpy() - y_mean) / y_scale)
    return NeuralFit(model, list(train_x.columns), x_mean, x_scale, y_mean, y_scale,
                     list(caught), perf_counter() - started)


def predict_ols_features(model, features):
    """Apply fitted standardized OLS to a feature DataFrame without refitting.

    Args:
        model: Mapping returned by fit_ols.
        features: Eligible rows including all fitted input columns.
    Returns:
        pandas.Series: Predicted CO2 in ppm with the supplied index.
    Raises:
        KeyError: A fitted input column is missing.
    """
    x = features.loc[:, model["columns"]]
    design = np.column_stack([np.ones(len(x)), (x.to_numpy()-model["mean"])/model["scale"]])
    return pd.Series(design @ model["coefficients"], index=x.index)


def fit_ols(train_x, y):
    # train_x and y come from original training rows; scaling uses only these rows.
    """Fit standardized OLS on training X/y only; return columns, scaling and coefficients. Raise ValueError for rank deficiency."""
    mean=train_x.mean().to_numpy()
    scale=train_x.std(ddof=0).to_numpy().copy()
    scale[scale==0]=1
    design=np.column_stack([np.ones(len(train_x)),(train_x.to_numpy()-mean)/scale])
    coefficients,_,rank,_=np.linalg.lstsq(design,y.to_numpy(),rcond=None)
    if rank<design.shape[1]:
        raise ValueError('Training features are constant or linearly dependent; inspect or remove the affected feature.')
    return {"columns":list(train_x.columns),"mean":mean,"scale":scale,"coefficients":coefficients}

