import pytest

from services import backlight


def _device(root, name, brightness, max_brightness):
    d = root / name
    d.mkdir(parents=True)
    (d / 'brightness').write_text(f'{brightness}\n')
    (d / 'max_brightness').write_text(f'{max_brightness}\n')
    return d


def test_finds_any_device_name(tmp_path):
    # 118's panel, not the 11-0045 that used to be hard-coded.
    d = _device(tmp_path, 'panel_backlight@1', 15, 31)
    assert backlight.find_backlight(str(tmp_path)) == str(d)


def test_skips_entries_without_brightness_files(tmp_path):
    (tmp_path / 'broken').mkdir()
    d = _device(tmp_path, 'zz_panel', 10, 31)
    assert backlight.find_backlight(str(tmp_path)) == str(d)


def test_no_device_returns_none(tmp_path):
    # jh-pi (HDMI) has an empty /sys/class/backlight.
    assert backlight.find_backlight(str(tmp_path)) is None
    assert backlight.find_backlight(str(tmp_path / 'missing')) is None
    assert backlight.read_percent(str(tmp_path)) is None
    assert backlight.write_percent(50, str(tmp_path)) is None


@pytest.mark.parametrize('percent', [0, 1, 25, 50, 73, 99, 100])
def test_max_31_matches_the_old_hard_coded_mapping(percent):
    old_set = int(8 + (percent / 100.0) * (31 - 8))
    assert backlight.percent_to_raw(percent, 31) == old_set


@pytest.mark.parametrize('raw', [0, 8, 9, 15, 20, 30, 31, 40])
def test_max_31_read_matches_the_old_mapping(raw):
    if raw <= 8:
        old = 0
    elif raw >= 31:
        old = 100
    else:
        old = int(((raw - 8) / (31 - 8)) * 100)
    assert backlight.raw_to_percent(raw, 31) == old


def test_other_max_scales_and_keeps_a_floor():
    assert backlight.percent_to_raw(0, 255) == 66   # 255 * 8/31, never black
    assert backlight.percent_to_raw(100, 255) == 255
    assert backlight.percent_to_raw(150, 255) == 255
    assert backlight.percent_to_raw(-5, 255) == 66


def test_read_and_write_round_trip(tmp_path):
    d = _device(tmp_path, 'panel_backlight@1', 15, 31)
    assert backlight.read_percent(str(tmp_path)) == 30
    device, raw, max_raw = backlight.write_percent(100, str(tmp_path))
    assert (device, raw, max_raw) == (str(d), 31, 31)
    assert (d / 'brightness').read_text() == '31'
    assert backlight.read_percent(str(tmp_path)) == 100
