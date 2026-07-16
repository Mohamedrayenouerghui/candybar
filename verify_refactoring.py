
#!/usr/bin/env python3
"""
Verification script to test refactoring
"""

print("=== Testing imports ===")
from src.logging import get_logger
from src.config.persistence import DisplayPersistence
from src.utils.stats import UsageStats
from src.utils.network_helper import NetworkHelper
from src.utils.common import get_app_data_dir
from src.mqtt.client import MQTTClient
from src.audio.engine import AudioEngine
from src.display.font_manager import FontManager
print("✓ All imports succeeded!")

print("\n=== Testing common.get_app_data_dir ===")
data_dir = get_app_data_dir()
print(f"✓ App data directory: {data_dir}")
import os
assert os.path.isdir(data_dir)
print("✓ App data directory exists!")

print("\n=== Testing persistence ===")
persistence = DisplayPersistence()
test_val = "test_refactor_123"
persistence.save("test_refactor_key", test_val)
assert persistence.load("test_refactor_key") == test_val
print("✓ Persistence save/load works!")

print("\n=== Testing usage stats ===")
stats = UsageStats()
stats_dict = stats.as_dict()
assert "uptime" in stats_dict
print("✓ Usage stats work!")

print("\n=== Testing font manager ===")
font_manager = FontManager()
assert hasattr(font_manager, "listFonts")
print("✓ Font manager imports okay!")

print("\n=== Testing MQTT client ===")
mqtt = MQTTClient()
assert hasattr(mqtt, "connect_broker")
print("✓ MQTT client imports okay!")

print("\n=== Testing audio engine ===")
audio_engine = AudioEngine()
assert hasattr(audio_engine, "set_data_dir")
print("✓ Audio engine imports okay!")

print("\n=== Testing network helper ===")
network = NetworkHelper()
assert network.adminUrl is not None
print("✓ Network helper okay!")

print("\n=== VERIFICATION SUCCESS ===\n")

