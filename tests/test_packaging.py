import unittest
from pathlib import Path
from scripts.native_inventory import notice_group

class NativeInventoryTests(unittest.TestCase):
    def test_unknown_binary_needs_review(self):
        with self.assertRaises(ValueError):
            notice_group(Path("unexpected.dll"))

    def test_asio_is_rejected_even_inside_known_provider(self):
        with self.assertRaises(ValueError):
            notice_group(Path("_sounddevice_data/portaudio-binaries/libportaudio64bit-asio.dll"))

    def test_native_provider_mapping(self):
        self.assertEqual(notice_group(Path("livekit/rtc/resources/livekit_ffi.dll")), "livekit")
        self.assertEqual(notice_group(Path("libcrypto-3.dll")), "python")
        self.assertEqual(notice_group(Path("numpy.libs/libscipy_openblas64.dll")), "numpy")
