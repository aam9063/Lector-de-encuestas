"""Output sanitizer: mask voting-estimate figures in every output text (never leaks)."""

from ficha_tecnica.sanitizer.detector import find_leaks
from ficha_tecnica.sanitizer.mask import MASK, mask_vote_estimates

__all__ = ["MASK", "find_leaks", "mask_vote_estimates"]
