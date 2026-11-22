"""Common Studio core: the model, the canonical score representation and the recording-id grammar."""

from .ir import SCHEMA, VERSION, canonical_json, fromIR, from_ir, ir_hash, toIR, to_ir
from .model import Arrangement, ArrangementGenerator, BeatGrid, Note, Part, Work, as_beat
from .recording_id import RecordingId, arrangement_id, format_recording_id, parse_recording_id

__all__ = [
    "Arrangement", "ArrangementGenerator", "BeatGrid", "Note", "Part", "RecordingId", "SCHEMA", "VERSION", "Work",
    "arrangement_id", "as_beat", "canonical_json", "format_recording_id", "fromIR", "from_ir", "ir_hash",
    "parse_recording_id", "toIR", "to_ir",
]
