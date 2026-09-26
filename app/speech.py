# -*- coding: utf-8 -*-
"""语音朗读。

优先用 Qt 自带的 QtTextToSpeech（底层就是 Windows SAPI），
不可用时退回调用 PowerShell 的 System.Speech，两条路都不需要额外依赖。
"""
from __future__ import annotations

import subprocess
import threading
from typing import Optional

from PyQt5.QtCore import QObject

_CREATE_NO_WINDOW = 0x08000000

try:  # PyQt5 的 TTS 模块并非所有发行版都带
    from PyQt5.QtCore import QLocale
    from PyQt5.QtTextToSpeech import QTextToSpeech

    HAS_QT_TTS = True
except Exception:  # noqa: BLE001
    HAS_QT_TTS = False

_LOCALES = {
    "zh-CHS": ("Chinese", "China"),
    "zh-CHT": ("Chinese", "Taiwan"),
    "en": ("English", "UnitedStates"),
    "ja": ("Japanese", "Japan"),
    "ko": ("Korean", "SouthKorea"),
    "fr": ("French", "France"),
    "de": ("German", "Germany"),
    "ru": ("Russian", "Russia"),
    "es": ("Spanish", "Spain"),
}


class Speaker(QObject):
    """朗读一段文本；同一时间只播一条。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tts = None
        self._proc: Optional[subprocess.Popen] = None
        self._lock = threading.Lock()
        if HAS_QT_TTS:
            try:
                self._tts = QTextToSpeech(self)
                self._tts.setRate(-0.1)
            except Exception:
                self._tts = None

    @property
    def available(self) -> bool:
        return self._tts is not None or True   # PowerShell 兜底总是可用

    @staticmethod
    def _locale_for(lang: str):
        if not HAS_QT_TTS:
            return None
        name = _LOCALES.get(lang)
        if not name:
            return QLocale()
        family = getattr(QLocale, name[0], None)
        country = getattr(QLocale, name[1], None)
        try:
            if family is not None and country is not None:
                return QLocale(family, country)
        except Exception:
            pass
        return QLocale()

    def speak(self, text: str, lang: str = "en") -> None:
        text = (text or "").strip()
        if not text:
            return
        self.stop()

        if self._tts is not None:
            try:
                loc = self._locale_for(lang)
                if loc is not None and loc.name():
                    self._tts.setLocale(loc)
                self._tts.stop()
                self._tts.say(text[:2000])
                return
            except Exception:
                pass
        self._speak_powershell(text)

    def _speak_powershell(self, text: str) -> None:
        script = (
            "Add-Type -AssemblyName System.Speech;"
            "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer;"
            "$s.Rate = 0;"
            "$s.Speak([Console]::In.ReadToEnd())"
        )
        try:
            proc = subprocess.Popen(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
                stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                creationflags=_CREATE_NO_WINDOW,
            )
            with self._lock:
                self._proc = proc
            proc.communicate(text[:2000].encode("utf-8", "replace"), timeout=120)
        except Exception:
            pass
        finally:
            with self._lock:
                self._proc = None

    def stop(self) -> None:
        if self._tts is not None:
            try:
                self._tts.stop()
            except Exception:
                pass
        with self._lock:
            proc = self._proc
        if proc and proc.poll() is None:
            try:
                proc.kill()
            except Exception:
                pass
