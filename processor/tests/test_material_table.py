import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[1]))
from extract_material_table import parse_materials, validate_materials


COMPLETE_BLOCK = """
Material.active 4
Material.name "Tarmac"
Material.type 0
Material.friction 1.2
Material.elasticity 0
Material.resistance 0.04
"""


def test_complete_block_parses_and_validates():
    entries = parse_materials(COMPLETE_BLOCK)
    assert entries == [{"id": 4, "name": "Tarmac", "friction": 1.2,
                        "elasticity": 0.0, "resistance": 0.04}]
    validate_materials(entries)  # must not raise


def test_truncated_block_is_rejected_before_any_write():
    # Review finding S1-F01: an incomplete source must never replace a good
    # material table. Validation raises before the config file is touched.
    truncated = 'Material.active 7\nMaterial.name "Truncated"\n'
    entries = parse_materials(truncated)
    with pytest.raises(ValueError, match="missing fields"):
        validate_materials(entries)


def test_empty_and_duplicate_id_inputs_are_rejected():
    with pytest.raises(ValueError, match="no materials"):
        validate_materials([])
    duplicate = COMPLETE_BLOCK + COMPLETE_BLOCK
    with pytest.raises(ValueError, match="duplicate material id"):
        validate_materials(parse_materials(duplicate))
