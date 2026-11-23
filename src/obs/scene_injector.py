import json
import logging
import os
import shutil
import subprocess
import time
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("OBSSceneInjector")

class OBSSceneInjector:
    """
    Automates OBS Studio configuration:
    - Injects BGMI_Audio_Sink.monitor as a dedicated audio capture source.
    - Injects Android camera / window feed as dedicated visual source.
    - Creates reliable backups before any file modification.
    - Checks and controls OBS Studio process.
    """
    def __init__(self, config_dir: Optional[Path] = None):
        if config_dir is None:
            self.config_dir = Path.home() / ".config" / "obs-studio"
        else:
            self.config_dir = Path(config_dir)
        self.scenes_dir = self.config_dir / "basic" / "scenes"

    def is_obs_installed(self) -> bool:
        return shutil.which("obs") is not None

    def is_obs_running(self) -> bool:
        try:
            res = subprocess.run(["pgrep", "-x", "obs"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return res.returncode == 0
        except Exception:
            return False

    def get_active_scene_collection_file(self) -> Optional[Path]:
        if not self.scenes_dir.exists():
            return None
        # Try global.ini to see active collection, or pick first json
        global_ini = self.config_dir / "global.ini"
        collection_name = None
        if global_ini.exists():
            try:
                with open(global_ini, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.startswith("SceneCollection="):
                            collection_name = line.split("=", 1)[1].strip()
                            break
            except Exception:
                pass

        if collection_name:
            target = self.scenes_dir / f"{collection_name}.json"
            if target.exists():
                return target

        # Default fallback to Untitled.json or first .json file
        json_files = list(self.scenes_dir.glob("*.json"))
        # Exclude backup files
        valid_files = [f for f in json_files if not f.name.endswith(".bak")]
        if valid_files:
            for f in valid_files:
                if f.stem == "Untitled":
                    return f
            return valid_files[0]
        return None

    def inject_pipeline_sources(
        self,
        sink_name: str = "BGMI_Audio_Sink",
        v4l2_device: Optional[str] = "/dev/video10",
        mic_device: str = "default"
    ) -> Tuple[bool, str]:
        scene_file = self.get_active_scene_collection_file()
        if not scene_file:
            return False, "OBS scenes directory or scene file not found"

        # 1. Create timestamped backup
        backup_path = scene_file.parent / f"{scene_file.name}.bak.{int(time.time())}"
        try:
            shutil.copy2(scene_file, backup_path)
            logger.info(f"Created OBS scene backup at {backup_path}")
        except Exception as e:
            return False, f"Failed to create OBS backup: {e}"

        # 2. Load JSON
        try:
            with open(scene_file, "r", encoding="utf-8") as f:
                scene_data = json.load(f)
        except Exception as e:
            return False, f"Failed to read OBS scene JSON: {e}"

        sources = scene_data.setdefault("sources", [])
        existing_names = {s.get("name") for s in sources if isinstance(s, dict)}

        audio_source_name = "BGMI Audio Stream (Isolated)"
        mic_source_name = "Player Microphone (My Mic)"
        video_source_name = "Android Mobile Video"
        audio_uuid = str(uuid.uuid4())
        mic_uuid = str(uuid.uuid4())
        video_uuid = str(uuid.uuid4())

        modified = False

        # 3. Inject Game & Friends Audio Source
        if audio_source_name not in existing_names:
            audio_source = {
                "name": audio_source_name,
                "uuid": audio_uuid,
                "id": "pulse_input_capture",
                "versioned_id": "pulse_input_capture",
                "settings": {
                    "device_id": f"{sink_name}.monitor"
                },
                "mixers": 255,
                "sync": 0,
                "flags": 0,
                "volume": 1.0,
                "balance": 0.5,
                "enabled": True,
                "muted": False,
                "monitoring_type": 0
            }
            sources.append(audio_source)
            modified = True
            logger.info(f"Injected OBS audio source: {audio_source_name}")

        # 4. Inject Player Microphone Source (Krisp AI clean or default)
        if mic_source_name not in existing_names:
            mic_source = {
                "name": mic_source_name,
                "uuid": mic_uuid,
                "id": "pulse_input_capture",
                "versioned_id": "pulse_input_capture",
                "settings": {
                    "device_id": mic_device
                },
                "mixers": 255,
                "sync": 0,
                "flags": 0,
                "volume": 1.0,
                "balance": 0.5,
                "enabled": True,
                "muted": False,
                "monitoring_type": 0
            }
            sources.append(mic_source)
            modified = True
            logger.info(f"Injected OBS mic source: {mic_source_name}")

        # 5. Inject Video Source
        if video_source_name not in existing_names:
            # If v4l2 device provided and exists, use v4l2_input; else use window capture
            if v4l2_device and os.path.exists(v4l2_device):
                video_source = {
                    "name": video_source_name,
                    "uuid": video_uuid,
                    "id": "v4l2_input",
                    "versioned_id": "v4l2_input",
                    "settings": {
                        "device_id": v4l2_device
                    },
                    "enabled": True
                }
            else:
                # PipeWire Window Capture
                video_source = {
                    "name": video_source_name,
                    "uuid": video_uuid,
                    "id": "pipewire-window-capture-source",
                    "versioned_id": "pipewire-window-capture-source",
                    "settings": {},
                    "enabled": True
                }
            sources.append(video_source)
            modified = True
            logger.info(f"Injected OBS video source: {video_source_name}")

        # 6. Add to current scene items if present
        current_scene_name = scene_data.get("current_scene")
        for s in sources:
            if s.get("id") == "scene" and s.get("name") == current_scene_name:
                items = s.setdefault("settings", {}).setdefault("items", [])
                item_names = {it.get("name") for it in items}
                id_counter = s["settings"].get("id_counter", len(items) + 1)

                if audio_source_name not in item_names:
                    id_counter += 1
                    items.append({
                        "name": audio_source_name,
                        "source_uuid": audio_uuid,
                        "visible": True,
                        "id": id_counter
                    })
                    modified = True

                if mic_source_name not in item_names:
                    id_counter += 1
                    items.append({
                        "name": mic_source_name,
                        "source_uuid": mic_uuid,
                        "visible": True,
                        "id": id_counter
                    })
                    modified = True

                if video_source_name not in item_names:
                    id_counter += 1
                    items.append({
                        "name": video_source_name,
                        "source_uuid": video_uuid,
                        "visible": True,
                        "id": id_counter,
                        "bounds": {"x": 1920.0, "y": 1080.0},
                        "bounds_type": 2
                    })
                    modified = True

                s["settings"]["id_counter"] = id_counter

        # 6. Save modified file
        if modified:
            try:
                temp_file = scene_file.parent / f"{scene_file.name}.tmp"
                with open(temp_file, "w", encoding="utf-8") as f:
                    json.dump(scene_data, f, indent=2)
                os.replace(temp_file, scene_file)
                return True, f"Injected audio ({audio_source_name}) and video ({video_source_name}) into {scene_file.name}"
            except Exception as e:
                return False, f"Failed to save modified OBS scene: {e}"

        return True, "OBS sources already present in active scene"

    def launch_obs(self, nice_priority: int = -5) -> Tuple[bool, str]:
        if self.is_obs_running():
            return True, "OBS Studio is already running"

        if not self.is_obs_installed():
            return False, "OBS Studio is not installed"

        try:
            cmd = ["obs"]
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
            return True, f"OBS Studio launched (PID: {proc.pid})"
        except Exception as e:
            return False, f"Failed to start OBS Studio: {e}"
