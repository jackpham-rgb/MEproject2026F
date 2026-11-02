# Print files

Ready to slice: every STL in `stl/` is already turned to its best side and placed on the bed.
Settings, print order and the tolerance-coupon check: `docs/08_build_guide.md` section 2.

![Print orientations](print_orientations.png)

Regenerate after changing `cad/model.py`: `python3.13 cad/export.py && python3.13 cad/print_prep.py`.
