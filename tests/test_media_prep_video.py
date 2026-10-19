import os
import threading

import pytest
from PIL import Image as PILImage

from services import media_prep
from tests.conftest import make_rotated_video, make_video, needs_ffmpeg

pytestmark = needs_ffmpeg


def _transcode(tmp_path, src):
    info = media_prep.probe(src)
    dst = str(tmp_path / 'out.mp4')
    media_prep.transcode_video(src, dst, info)
    return media_prep.probe(dst)


def test_small_h264_is_compatible(tmp_path):
    info = media_prep.probe(make_video(str(tmp_path / 'a.mp4')))
    assert info['vcodec'] == 'h264' and info['acodec'] == 'aac'
    assert media_prep.video_is_playable(info)
    assert media_prep.video_is_compatible(info)


def test_60fps_is_playable_but_transcoded_to_30(tmp_path):
    src = make_video(str(tmp_path / 'a.mp4'), fps=60)
    info = media_prep.probe(src)
    assert media_prep.video_is_playable(info)
    assert not media_prep.video_is_compatible(info)
    out = _transcode(tmp_path, src)
    assert abs(out['fps'] - 30) < 0.5
    assert media_prep.video_is_compatible(out)


def test_large_h264_is_playable_and_shrunk_to_720(tmp_path):
    src = make_video(str(tmp_path / 'a.mp4'), size=(1280, 800))
    info = media_prep.probe(src)
    assert media_prep.video_is_playable(info)
    assert not media_prep.video_is_compatible(info)
    out = _transcode(tmp_path, src)
    assert (out['width'], out['height']) == (1152, 720)
    assert media_prep.video_is_compatible(out)


def test_hevc_10bit_is_not_playable_until_transcoded(tmp_path):
    src = make_video(str(tmp_path / 'a.mov'), vcodec='libx265', pix_fmt='yuv420p10le')
    info = media_prep.probe(src)
    assert info['vcodec'] == 'hevc'
    assert not media_prep.video_is_playable(info)
    out = _transcode(tmp_path, src)
    assert media_prep.video_is_compatible(out)


def test_rotation_is_burned_in(tmp_path):
    src = make_rotated_video(str(tmp_path / 'a.mov'), size=(320, 240))
    info = media_prep.probe(src)
    assert info['rotation'] in (90, 270)
    assert not media_prep.video_is_playable(info)
    out = _transcode(tmp_path, src)
    assert out['rotation'] == 0
    assert (out['width'], out['height']) == (240, 320)


def test_odd_width_portrait_transcodes(tmp_path):
    src = make_video(str(tmp_path / 'a.mp4'), size=(721, 1281), pix_fmt='yuv444p')
    out = _transcode(tmp_path, src)
    assert (out['width'], out['height']) == (720, 1280)


def test_pcm_audio_is_not_playable(tmp_path):
    info = media_prep.probe(make_video(str(tmp_path / 'a.mov'), audio='pcm_s16le'))
    assert info['acodec'] == 'pcm_s16le'
    assert not media_prep.video_is_playable(info)


def test_no_audio_is_fine(tmp_path):
    info = media_prep.probe(make_video(str(tmp_path / 'a.mp4'), audio=None))
    assert info['acodec'] is None
    assert media_prep.video_is_compatible(info)


def test_poster_for_half_second_video(tmp_path):
    src = make_video(str(tmp_path / 'a.mp4'), duration=0.5)
    dst = str(tmp_path / 'a.poster.jpg')
    media_prep.extract_poster(src, dst)
    with PILImage.open(dst) as img:
        assert img.size == (320, 240)
    assert not os.path.exists(dst + media_prep.PART_SUFFIX)


def test_cancel_stops_ffmpeg_and_leaves_nothing(tmp_path):
    src = make_video(str(tmp_path / 'long.mp4'), size=(1280, 720), duration=10, audio=None,
                     extra=('-preset', 'ultrafast'))
    out_dir = tmp_path / 'out'
    out_dir.mkdir()
    dst = str(out_dir / 'long.mp4.mp4')
    cancel = threading.Event()
    threading.Timer(0.5, cancel.set).start()
    with pytest.raises(media_prep.TranscodeCancelled):
        media_prep.transcode_video(src, dst, media_prep.probe(src), cancel)
    assert os.listdir(out_dir) == []


def test_probe_rejects_non_video(tmp_path):
    bad = tmp_path / 'bad.mp4'
    bad.write_text('not a video')
    with pytest.raises(Exception):
        media_prep.probe(str(bad))
