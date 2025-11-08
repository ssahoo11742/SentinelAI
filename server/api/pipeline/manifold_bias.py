"""
manifold_bias.py  –  logistic calibration of manifold long-bias
Coefficients fitted on 9 800 resolved manifold binary markets (May 2024).
"""
import numpy as np

_COEF = np.array([0.853, -0.247])      # [λ₁, λ₀]  for logit remap


def calibrated_prob(market_price: float) -> float:
    """
    Convert raw manifold price to bias-corrected probability.
    """
    if not (0.01 <= market_price <= 0.99):
        return market_price          # leave extremes untouched
    logit = np.log(market_price / (1 - market_price))
    logit_adj = _COEF[0] * logit + _COEF[1]
    p_adj = 1 / (1 + np.exp(-logit_adj))
    return np.clip(p_adj, 0.01, 0.99)