from owsh.config import Config
from owsh.i18n import I18n, available_languages, load_phrases, placeholders


def test_en_and_ko_available():
    assert {"en", "ko"} <= set(available_languages())


def test_all_languages_have_identical_keys():
    en = load_phrases("en")
    for lang in available_languages():
        other = load_phrases(lang)
        assert set(other) == set(en), f"{lang}: missing {set(en) - set(other)}, extra {set(other) - set(en)}"


def test_placeholders_identical_per_key():
    en = load_phrases("en")
    for lang in available_languages():
        other = load_phrases(lang)
        for key, text in en.items():
            assert placeholders(other[key]) == placeholders(text), f"{lang}:{key}"


def test_no_empty_phrases():
    for lang in available_languages():
        for key, text in load_phrases(lang).items():
            assert text.strip(), f"{lang}:{key} is empty"


def test_every_configured_class_has_names():
    en = load_phrases("en")
    for label in Config().vision.detector.classes:
        assert f"class.{label}.one" in en and f"class.{label}.many" in en


def test_format_and_fallbacks():
    t = I18n("ko")
    assert t.t("fault.recovered", component="카메라") == "카메라 복구됨."
    assert t.t("no.such.key") == "no.such.key"
    assert t.t("fault.recovered") == "{component} 복구됨."  # missing param kept, no crash
    assert I18n("en").sentence("approach.p2.left", what="bicycle") == "Bicycle approaching from the left."
    assert I18n("en").class_name("person", 2) == "2 people"
    assert t.class_name("dog", 3) == "개 3마리"
    assert t.class_name("unicorn") == "물체"
    assert not I18n("en").set_lang("xx")


def test_safety_phrases_short():
    # imminent-hazard phrases must be short enough to be spoken in about a second
    for lang in ("en", "ko"):
        p = load_phrases(lang)
        for key in ("obstacle.stop", "obstacle.ahead", "drop.big", "drop.step_down", "drop.step_up"):
            assert len(p[key]) <= 20, f"{lang}:{key}"
