import pytest

from common_studio import RecordingId, arrangement_id, format_recording_id, parse_recording_id


@pytest.mark.parametrize(
    "text, parts",
    [
        ("work--style", ("work", "style", None, None)),
        ("work--style@venue", ("work", "style", "venue", None)),
        ("work--style+treatment", ("work", "style", None, "treatment")),
        ("work--style@venue+treatment", ("work", "style", "venue", "treatment")),
        ("ode-to-joy--string-quartet@small-hall+warm-tape", ("ode-to-joy", "string-quartet", "small-hall", "warm-tape")),
        ("a1--b2@c3+d4", ("a1", "b2", "c3", "d4")),
    ],
)
def test_each_shape_parses_and_formats_back(text, parts):
    rid = parse_recording_id(text)
    assert (rid.work, rid.style, rid.venue, rid.treatment) == parts
    assert format_recording_id(rid) == text
    assert str(rid) == text


def test_arrangement_id_is_work_double_hyphen_style():
    assert arrangement_id("work", "style") == "work--style"
    assert parse_recording_id("work--style@v+t").arrangement == "work--style"


@pytest.mark.parametrize(
    "bad",
    [
        "",
        "work",
        "work-style",
        "work--",
        "--style",
        "work--style@",
        "work--style+",
        "work--style+t@v",
        "Work--style",
        "work--sty le",
        "work---style",
        "work--style@venue@again",
        "work--style+a+b",
        "-work--style",
        "work--style-",
        " work--style",
    ],
)
def test_text_outside_the_grammar_is_refused(bad):
    with pytest.raises(ValueError):
        parse_recording_id(bad)


def test_non_text_is_refused():
    with pytest.raises(ValueError):
        parse_recording_id(None)  # type: ignore[arg-type]


@pytest.mark.parametrize("field", ["work", "style", "venue", "treatment"])
def test_building_an_id_checks_every_part(field):
    kwargs = {"work": "w", "style": "s", "venue": "v", "treatment": "t"}
    kwargs[field] = "Bad Name"
    with pytest.raises(ValueError):
        RecordingId(**kwargs)


def test_a_double_hyphen_cannot_hide_inside_a_part():
    with pytest.raises(ValueError):
        RecordingId("a--b", "s")
