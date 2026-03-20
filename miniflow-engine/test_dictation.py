"""
Tests for dictation.py — 100 tests covering get_dictation_status(),
start_dictation(), stop_dictation(), set_event_broadcaster(), _emit(),
check_accessibility(), open_accessibility_settings(), and type_text().
"""
import asyncio
import pytest
from unittest.mock import patch, MagicMock, AsyncMock, call
import sys, os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dictation

# ── Helpers ───────────────────────────────────────────────────────────────────

def run(coro):
    return asyncio.run(coro)

@pytest.fixture(autouse=True)
def reset_state():
    """Reset module globals before every test."""
    dictation._active = False
    dictation._broadcaster = None
    yield
    dictation._active = False
    dictation._broadcaster = None

# ── get_dictation_status() (1–15) ─────────────────────────────────────────────

class TestGetDictationStatus:
    def test_01_initial_status_is_false(self):
        assert dictation.get_dictation_status() is False

    def test_02_returns_bool(self):
        assert isinstance(dictation.get_dictation_status(), bool)

    def test_03_status_after_manual_set_true(self):
        dictation._active = True
        assert dictation.get_dictation_status() is True

    def test_04_status_after_manual_set_false(self):
        dictation._active = True
        dictation._active = False
        assert dictation.get_dictation_status() is False

    def test_05_status_true_after_start(self):
        run(dictation.start_dictation())
        assert dictation.get_dictation_status() is True

    def test_06_status_false_after_stop(self):
        run(dictation.start_dictation())
        run(dictation.stop_dictation())
        assert dictation.get_dictation_status() is False

    def test_07_status_false_after_double_stop(self):
        run(dictation.start_dictation())
        run(dictation.stop_dictation())
        run(dictation.stop_dictation())
        assert dictation.get_dictation_status() is False

    def test_08_status_reflects_latest_state(self):
        run(dictation.start_dictation())
        run(dictation.stop_dictation())
        run(dictation.start_dictation())
        assert dictation.get_dictation_status() is True

    def test_09_multiple_starts_still_true(self):
        run(dictation.start_dictation())
        run(dictation.start_dictation())
        assert dictation.get_dictation_status() is True

    def test_10_toggle_start_stop_five_times(self):
        for _ in range(5):
            run(dictation.start_dictation())
            run(dictation.stop_dictation())
        assert dictation.get_dictation_status() is False

    def test_11_status_not_affected_by_broadcaster(self):
        dictation._broadcaster = AsyncMock()
        assert dictation.get_dictation_status() is False

    def test_12_status_true_with_broadcaster_set(self):
        dictation._broadcaster = AsyncMock()
        run(dictation.start_dictation())
        assert dictation.get_dictation_status() is True

    def test_13_status_false_no_start_called(self):
        dictation._broadcaster = AsyncMock()
        assert dictation.get_dictation_status() is False

    def test_14_direct_module_attribute_matches_getter(self):
        dictation._active = True
        assert dictation.get_dictation_status() == dictation._active

    def test_15_status_is_not_none(self):
        assert dictation.get_dictation_status() is not None

# ── start_dictation() (16–30) ─────────────────────────────────────────────────

class TestStartDictation:
    def test_16_sets_active_true(self):
        run(dictation.start_dictation())
        assert dictation._active is True

    def test_17_returns_coroutine(self):
        import inspect
        coro = dictation.start_dictation()
        assert inspect.iscoroutine(coro)
        run(coro)

    def test_18_emits_dictation_status_event(self):
        mock_broadcaster = AsyncMock()
        dictation._broadcaster = mock_broadcaster
        run(dictation.start_dictation())
        mock_broadcaster.assert_called_once_with("dictation-status", {"active": True, "error": None})

    def test_19_emits_active_true_in_payload(self):
        mock_broadcaster = AsyncMock()
        dictation._broadcaster = mock_broadcaster
        run(dictation.start_dictation())
        _, payload = mock_broadcaster.call_args[0]
        assert payload["active"] is True

    def test_20_emits_error_none_in_payload(self):
        mock_broadcaster = AsyncMock()
        dictation._broadcaster = mock_broadcaster
        run(dictation.start_dictation())
        _, payload = mock_broadcaster.call_args[0]
        assert payload["error"] is None

    def test_21_no_broadcaster_no_error(self):
        dictation._broadcaster = None
        run(dictation.start_dictation())  # should not raise
        assert dictation._active is True

    def test_22_called_twice_still_active(self):
        run(dictation.start_dictation())
        run(dictation.start_dictation())
        assert dictation._active is True

    def test_23_broadcaster_called_each_start(self):
        mock_broadcaster = AsyncMock()
        dictation._broadcaster = mock_broadcaster
        run(dictation.start_dictation())
        run(dictation.start_dictation())
        assert mock_broadcaster.call_count == 2

    def test_24_start_after_stop_sets_active_true(self):
        run(dictation.start_dictation())
        run(dictation.stop_dictation())
        run(dictation.start_dictation())
        assert dictation._active is True

    def test_25_start_event_name_is_correct(self):
        mock_broadcaster = AsyncMock()
        dictation._broadcaster = mock_broadcaster
        run(dictation.start_dictation())
        event_name = mock_broadcaster.call_args[0][0]
        assert event_name == "dictation-status"

    def test_26_start_active_set_before_emit(self):
        captured = {}
        async def broadcaster(event, payload):
            captured["active_at_emit"] = dictation._active
        dictation._broadcaster = broadcaster
        run(dictation.start_dictation())
        assert captured["active_at_emit"] is True

    def test_27_start_does_not_affect_broadcaster_reference(self):
        mock = AsyncMock()
        dictation._broadcaster = mock
        run(dictation.start_dictation())
        assert dictation._broadcaster is mock

    def test_28_start_returns_none(self):
        result = run(dictation.start_dictation())
        assert result is None

    def test_29_start_ten_times_active_remains_true(self):
        for _ in range(10):
            run(dictation.start_dictation())
        assert dictation._active is True

    def test_30_start_broadcaster_receives_dict_payload(self):
        mock_broadcaster = AsyncMock()
        dictation._broadcaster = mock_broadcaster
        run(dictation.start_dictation())
        _, payload = mock_broadcaster.call_args[0]
        assert isinstance(payload, dict)

# ── stop_dictation() (31–45) ──────────────────────────────────────────────────

class TestStopDictation:
    def test_31_sets_active_false(self):
        dictation._active = True
        run(dictation.stop_dictation())
        assert dictation._active is False

    def test_32_emits_dictation_status_event(self):
        mock_broadcaster = AsyncMock()
        dictation._broadcaster = mock_broadcaster
        run(dictation.stop_dictation())
        mock_broadcaster.assert_called_once_with("dictation-status", {"active": False, "error": None})

    def test_33_emits_active_false_in_payload(self):
        mock_broadcaster = AsyncMock()
        dictation._broadcaster = mock_broadcaster
        run(dictation.stop_dictation())
        _, payload = mock_broadcaster.call_args[0]
        assert payload["active"] is False

    def test_34_emits_error_none_in_payload(self):
        mock_broadcaster = AsyncMock()
        dictation._broadcaster = mock_broadcaster
        run(dictation.stop_dictation())
        _, payload = mock_broadcaster.call_args[0]
        assert payload["error"] is None

    def test_35_no_broadcaster_no_error(self):
        dictation._broadcaster = None
        run(dictation.stop_dictation())
        assert dictation._active is False

    def test_36_stop_without_start_still_false(self):
        run(dictation.stop_dictation())
        assert dictation._active is False

    def test_37_stop_after_start_sets_false(self):
        run(dictation.start_dictation())
        run(dictation.stop_dictation())
        assert dictation._active is False

    def test_38_stop_called_twice_still_false(self):
        run(dictation.stop_dictation())
        run(dictation.stop_dictation())
        assert dictation._active is False

    def test_39_stop_event_name_is_correct(self):
        mock_broadcaster = AsyncMock()
        dictation._broadcaster = mock_broadcaster
        run(dictation.stop_dictation())
        assert mock_broadcaster.call_args[0][0] == "dictation-status"

    def test_40_stop_broadcaster_called_each_time(self):
        mock_broadcaster = AsyncMock()
        dictation._broadcaster = mock_broadcaster
        run(dictation.stop_dictation())
        run(dictation.stop_dictation())
        assert mock_broadcaster.call_count == 2

    def test_41_stop_returns_none(self):
        result = run(dictation.stop_dictation())
        assert result is None

    def test_42_stop_returns_coroutine(self):
        import inspect
        coro = dictation.stop_dictation()
        assert inspect.iscoroutine(coro)
        run(coro)

    def test_43_start_stop_start_stop_cycle(self):
        for _ in range(3):
            run(dictation.start_dictation())
            assert dictation._active is True
            run(dictation.stop_dictation())
            assert dictation._active is False

    def test_44_stop_broadcaster_receives_dict_payload(self):
        mock_broadcaster = AsyncMock()
        dictation._broadcaster = mock_broadcaster
        run(dictation.stop_dictation())
        _, payload = mock_broadcaster.call_args[0]
        assert isinstance(payload, dict)

    def test_45_stop_active_set_before_emit(self):
        dictation._active = True
        captured = {}
        async def broadcaster(event, payload):
            captured["active_at_emit"] = dictation._active
        dictation._broadcaster = broadcaster
        run(dictation.stop_dictation())
        assert captured["active_at_emit"] is False

# ── set_event_broadcaster() and _emit() (46–60) ───────────────────────────────

class TestBroadcasterAndEmit:
    def test_46_set_broadcaster_stores_function(self):
        fn = AsyncMock()
        dictation.set_event_broadcaster(fn)
        assert dictation._broadcaster is fn

    def test_47_set_broadcaster_replaces_previous(self):
        fn1 = AsyncMock()
        fn2 = AsyncMock()
        dictation.set_event_broadcaster(fn1)
        dictation.set_event_broadcaster(fn2)
        assert dictation._broadcaster is fn2

    def test_48_set_broadcaster_to_none(self):
        dictation.set_event_broadcaster(AsyncMock())
        dictation._broadcaster = None
        assert dictation._broadcaster is None

    def test_49_emit_calls_broadcaster_with_event_and_payload(self):
        mock = AsyncMock()
        dictation._broadcaster = mock
        run(dictation._emit("test-event", {"key": "val"}))
        mock.assert_called_once_with("test-event", {"key": "val"})

    def test_50_emit_with_no_broadcaster_does_not_raise(self):
        dictation._broadcaster = None
        run(dictation._emit("event", {}))  # should not raise

    def test_51_emit_string_payload(self):
        mock = AsyncMock()
        dictation._broadcaster = mock
        run(dictation._emit("event", "string_payload"))
        mock.assert_called_once_with("event", "string_payload")

    def test_52_emit_none_payload(self):
        mock = AsyncMock()
        dictation._broadcaster = mock
        run(dictation._emit("event", None))
        mock.assert_called_once_with("event", None)

    def test_53_emit_integer_payload(self):
        mock = AsyncMock()
        dictation._broadcaster = mock
        run(dictation._emit("event", 42))
        mock.assert_called_once_with("event", 42)

    def test_54_emit_list_payload(self):
        mock = AsyncMock()
        dictation._broadcaster = mock
        run(dictation._emit("event", [1, 2, 3]))
        mock.assert_called_once_with("event", [1, 2, 3])

    def test_55_emit_called_multiple_times(self):
        mock = AsyncMock()
        dictation._broadcaster = mock
        for i in range(5):
            run(dictation._emit(f"event-{i}", {}))
        assert mock.call_count == 5

    def test_56_emit_correct_event_name(self):
        mock = AsyncMock()
        dictation._broadcaster = mock
        run(dictation._emit("custom-event", {}))
        assert mock.call_args[0][0] == "custom-event"

    def test_57_emit_correct_payload(self):
        mock = AsyncMock()
        dictation._broadcaster = mock
        payload = {"active": True, "error": None}
        run(dictation._emit("status", payload))
        assert mock.call_args[0][1] == payload

    def test_58_broadcaster_exception_propagates(self):
        async def bad_broadcaster(event, payload):
            raise RuntimeError("broadcast failed")
        dictation._broadcaster = bad_broadcaster
        with pytest.raises(RuntimeError):
            run(dictation._emit("event", {}))

    def test_59_set_broadcaster_accepts_regular_async_function(self):
        async def fn(event, payload): pass
        dictation.set_event_broadcaster(fn)
        assert dictation._broadcaster is fn

    def test_60_emit_after_set_broadcaster_uses_new_fn(self):
        fn1 = AsyncMock()
        fn2 = AsyncMock()
        dictation.set_event_broadcaster(fn1)
        dictation.set_event_broadcaster(fn2)
        run(dictation._emit("event", {}))
        fn1.assert_not_called()
        fn2.assert_called_once()

# ── check_accessibility() (61–73) ─────────────────────────────────────────────

class TestCheckAccessibility:
    def test_61_returns_bool(self):
        with patch("dictation.AXIsProcessTrusted", return_value=False):
            assert isinstance(dictation.check_accessibility(), bool)

    def test_62_returns_true_when_trusted(self):
        with patch("dictation.AXIsProcessTrusted", return_value=True):
            assert dictation.check_accessibility() is True

    def test_63_returns_false_when_not_trusted(self):
        with patch("dictation.AXIsProcessTrusted", return_value=False):
            assert dictation.check_accessibility() is False

    def test_64_calls_ax_is_process_trusted(self):
        with patch("dictation.AXIsProcessTrusted", return_value=False) as mock:
            dictation.check_accessibility()
            mock.assert_called_once()

    def test_65_multiple_calls_reflect_current_state(self):
        with patch("dictation.AXIsProcessTrusted", return_value=True):
            assert dictation.check_accessibility() is True
        with patch("dictation.AXIsProcessTrusted", return_value=False):
            assert dictation.check_accessibility() is False

    def test_66_return_value_matches_ax_return(self):
        for expected in [True, False]:
            with patch("dictation.AXIsProcessTrusted", return_value=expected):
                assert dictation.check_accessibility() == expected

    def test_67_does_not_modify_active_state(self):
        dictation._active = True
        with patch("dictation.AXIsProcessTrusted", return_value=False):
            dictation.check_accessibility()
        assert dictation._active is True

    def test_68_does_not_modify_broadcaster(self):
        mock = AsyncMock()
        dictation._broadcaster = mock
        with patch("dictation.AXIsProcessTrusted", return_value=False):
            dictation.check_accessibility()
        assert dictation._broadcaster is mock

    def test_69_called_ten_times_no_side_effects(self):
        with patch("dictation.AXIsProcessTrusted", return_value=False) as mock:
            for _ in range(10):
                dictation.check_accessibility()
            assert mock.call_count == 10

    def test_70_returns_not_none(self):
        with patch("dictation.AXIsProcessTrusted", return_value=False):
            assert dictation.check_accessibility() is not None

    def test_71_truthy_when_accessible(self):
        with patch("dictation.AXIsProcessTrusted", return_value=True):
            assert dictation.check_accessibility()

    def test_72_falsy_when_not_accessible(self):
        with patch("dictation.AXIsProcessTrusted", return_value=False):
            assert not dictation.check_accessibility()

    def test_73_independent_of_dictation_status(self):
        dictation._active = True
        with patch("dictation.AXIsProcessTrusted", return_value=False):
            result = dictation.check_accessibility()
        assert result is False
        assert dictation._active is True

# ── open_accessibility_settings() (74–82) ─────────────────────────────────────

class TestOpenAccessibilitySettings:
    def test_74_calls_subprocess_popen(self):
        with patch("dictation.subprocess.Popen") as mock_popen:
            dictation.open_accessibility_settings()
            mock_popen.assert_called_once()

    def test_75_opens_correct_url(self):
        with patch("dictation.subprocess.Popen") as mock_popen:
            dictation.open_accessibility_settings()
            args = mock_popen.call_args[0][0]
            assert "Privacy_Accessibility" in " ".join(args)

    def test_76_uses_open_command(self):
        with patch("dictation.subprocess.Popen") as mock_popen:
            dictation.open_accessibility_settings()
            args = mock_popen.call_args[0][0]
            assert args[0] == "open"

    def test_77_popen_called_with_list(self):
        with patch("dictation.subprocess.Popen") as mock_popen:
            dictation.open_accessibility_settings()
            args = mock_popen.call_args[0][0]
            assert isinstance(args, list)

    def test_78_returns_none(self):
        with patch("dictation.subprocess.Popen"):
            assert dictation.open_accessibility_settings() is None

    def test_79_does_not_raise(self):
        with patch("dictation.subprocess.Popen"):
            dictation.open_accessibility_settings()  # should not raise

    def test_80_does_not_modify_active_state(self):
        with patch("dictation.subprocess.Popen"):
            dictation.open_accessibility_settings()
        assert dictation._active is False

    def test_81_popen_called_exactly_once(self):
        with patch("dictation.subprocess.Popen") as mock_popen:
            dictation.open_accessibility_settings()
            assert mock_popen.call_count == 1

    def test_82_called_twice_opens_twice(self):
        with patch("dictation.subprocess.Popen") as mock_popen:
            dictation.open_accessibility_settings()
            dictation.open_accessibility_settings()
            assert mock_popen.call_count == 2

# ── type_text() (83–100) ──────────────────────────────────────────────────────

class TestTypeText:
    def _mocks(self):
        mock_quartz = MagicMock()
        mock_quartz.kCGEventSourceStateHIDSystemState = 0
        mock_quartz.kCGHIDEventTap = 0
        mock_appkit = MagicMock()
        mock_pb = MagicMock()
        mock_pb.stringForType_.return_value = "previous"
        mock_appkit.NSPasteboard.generalPasteboard.return_value = mock_pb
        mock_appkit.NSPasteboardTypeString = "public.utf8-plain-text"
        return mock_quartz, mock_appkit, mock_pb

    def _patch(self, mock_quartz, mock_appkit):
        return patch.dict("sys.modules", {"Quartz": mock_quartz, "AppKit": mock_appkit})

    def test_83_empty_text_returns_immediately(self):
        mock_quartz, mock_appkit, mock_pb = self._mocks()
        with self._patch(mock_quartz, mock_appkit):
            dictation.type_text("")
        mock_pb.setString_forType_.assert_not_called()

    def test_84_calls_cgevent_source_create(self):
        mock_quartz, mock_appkit, _ = self._mocks()
        with self._patch(mock_quartz, mock_appkit):
            with patch("time.sleep"):
                dictation.type_text("hello")
        mock_quartz.CGEventSourceCreate.assert_called_once()

    def test_85_calls_cgevent_create_keyboard_event_twice(self):
        mock_quartz, mock_appkit, _ = self._mocks()
        with self._patch(mock_quartz, mock_appkit):
            with patch("time.sleep"):
                dictation.type_text("hello")
        assert mock_quartz.CGEventCreateKeyboardEvent.call_count == 2

    def test_86_sets_text_on_pasteboard(self):
        mock_quartz, mock_appkit, mock_pb = self._mocks()
        with self._patch(mock_quartz, mock_appkit):
            with patch("time.sleep"):
                dictation.type_text("hi")
        mock_pb.setString_forType_.assert_called()
        assert mock_pb.setString_forType_.call_args_list[0][0][0] == "hi"

    def test_87_calls_cgevent_post_twice(self):
        mock_quartz, mock_appkit, _ = self._mocks()
        with self._patch(mock_quartz, mock_appkit):
            with patch("time.sleep"):
                dictation.type_text("hi")
        assert mock_quartz.CGEventPost.call_count == 2

    def test_88_clears_pasteboard_before_setting(self):
        mock_quartz, mock_appkit, mock_pb = self._mocks()
        with self._patch(mock_quartz, mock_appkit):
            with patch("time.sleep"):
                dictation.type_text("hello")
        mock_pb.clearContents.assert_called()

    def test_89_restores_previous_clipboard(self):
        mock_quartz, mock_appkit, mock_pb = self._mocks()
        mock_pb.stringForType_.return_value = "old content"
        with self._patch(mock_quartz, mock_appkit):
            with patch("time.sleep"):
                dictation.type_text("hello")
        calls = mock_pb.setString_forType_.call_args_list
        assert any(c[0][0] == "old content" for c in calls)

    def test_90_quartz_exception_caught_silently(self):
        mock_quartz, mock_appkit, _ = self._mocks()
        mock_quartz.CGEventSourceCreate.side_effect = Exception("Quartz error")
        with self._patch(mock_quartz, mock_appkit):
            dictation.type_text("hello")  # should not raise

    def test_91_empty_text_skips_cgevent_post(self):
        mock_quartz, mock_appkit, _ = self._mocks()
        with self._patch(mock_quartz, mock_appkit):
            dictation.type_text("")
        mock_quartz.CGEventPost.assert_not_called()

    def test_92_single_char_text(self):
        mock_quartz, mock_appkit, _ = self._mocks()
        with self._patch(mock_quartz, mock_appkit):
            with patch("time.sleep"):
                dictation.type_text("a")
        assert mock_quartz.CGEventPost.call_count == 2

    def test_93_long_text_single_paste(self):
        mock_quartz, mock_appkit, _ = self._mocks()
        with self._patch(mock_quartz, mock_appkit):
            with patch("time.sleep"):
                dictation.type_text("a" * 500)
        assert mock_quartz.CGEventPost.call_count == 2

    def test_94_unicode_text_processed(self):
        mock_quartz, mock_appkit, _ = self._mocks()
        with self._patch(mock_quartz, mock_appkit):
            with patch("time.sleep"):
                dictation.type_text("héllo wörld")
        assert mock_quartz.CGEventPost.call_count == 2

    def test_95_emoji_text_processed(self):
        mock_quartz, mock_appkit, _ = self._mocks()
        with self._patch(mock_quartz, mock_appkit):
            with patch("time.sleep"):
                dictation.type_text("hello 😊")
        assert mock_quartz.CGEventPost.call_count == 2

    def test_96_newline_pasted_as_single_operation(self):
        mock_quartz, mock_appkit, mock_pb = self._mocks()
        with self._patch(mock_quartz, mock_appkit):
            with patch("time.sleep"):
                dictation.type_text("line1\nline2")
        assert mock_quartz.CGEventPost.call_count == 2

    def test_97_does_not_modify_active_state(self):
        mock_quartz, mock_appkit, _ = self._mocks()
        dictation._active = False
        with self._patch(mock_quartz, mock_appkit):
            with patch("time.sleep"):
                dictation.type_text("hello")
        assert dictation._active is False

    def test_98_returns_none(self):
        mock_quartz, mock_appkit, _ = self._mocks()
        with self._patch(mock_quartz, mock_appkit):
            with patch("time.sleep"):
                result = dictation.type_text("hello")
        assert result is None

    def test_99_cmd_v_key_code_used(self):
        mock_quartz, mock_appkit, _ = self._mocks()
        with self._patch(mock_quartz, mock_appkit):
            with patch("time.sleep"):
                dictation.type_text("hi")
        calls = mock_quartz.CGEventCreateKeyboardEvent.call_args_list
        assert calls[0][0][1] == 0x09  # V key
        assert calls[1][0][1] == 0x09

    def test_100_key_down_then_key_up(self):
        mock_quartz, mock_appkit, _ = self._mocks()
        with self._patch(mock_quartz, mock_appkit):
            with patch("time.sleep"):
                dictation.type_text("hi")
        calls = mock_quartz.CGEventCreateKeyboardEvent.call_args_list
        assert calls[0][0][2] is True   # key down
        assert calls[1][0][2] is False  # key up


# ── Newline substitution logic (inlined from main.py) ─────────────────────────

import re as _re


def _apply_newline_mode(transcript: str) -> str:
    """Mirror of the newline_mode block in main._transcribe_audio."""
    transcript = _re.sub(
        r'(\.)[ \t]*\b(?:new\s+line|newline)\b[ \t]*([a-zA-Z])',
        lambda m: m.group(1) + '\n' + m.group(2).upper(),
        transcript, flags=_re.I,
    )
    transcript = _re.sub(r'[ \t]*\b(?:new\s+line|newline)\b[ \t]*', '\n', transcript, flags=_re.I)
    return transcript


class TestNewlineSubstitution:
    def test_101_after_full_stop_capitalises(self):
        assert _apply_newline_mode("Hello world. new line this is fine") == "Hello world.\nThis is fine"

    def test_102_no_full_stop_no_capitalise(self):
        assert _apply_newline_mode("Hello world new line this is fine") == "Hello world\nthis is fine"

    def test_103_newline_keyword_variant(self):
        assert _apply_newline_mode("Done. newline next thought") == "Done.\nNext thought"

    def test_104_no_full_stop_newline_variant(self):
        assert _apply_newline_mode("Done newline next thought") == "Done\nnext thought"

    def test_105_multiple_new_lines_mixed(self):
        result = _apply_newline_mode("First sentence. new line second sentence new line third")
        assert result == "First sentence.\nSecond sentence\nthird"

    def test_106_end_of_string_no_following_word(self):
        assert _apply_newline_mode("Hello. new line") == "Hello.\n"

    def test_107_end_of_string_no_period(self):
        assert _apply_newline_mode("Hello new line") == "Hello\n"

    def test_108_case_insensitive_trigger(self):
        assert _apply_newline_mode("Hi. New Line there") == "Hi.\nThere"
