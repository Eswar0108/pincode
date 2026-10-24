import json
from pathlib import Path
import subprocess

project_dir = Path('/Users/tejeswarreddy/Downloads/python/Github Contributions/ai-video-factory/projects/test_brain_memory')

with open(project_dir / 'script.json', 'r') as f:
    script = json.load(f)

full_text = ' '.join(scene['narration'] for scene in script['scenes'])
print(f"Total narration text: {len(full_text)} chars, {len(script['scenes'])} scenes")

voice_file = project_dir / 'voice' / 'narration.wav'
model_path = Path('/Users/tejeswarreddy/Downloads/python/Github Contributions/ai-video-factory/models/tts/en_US-lessac-medium.onnx')
config_path = Path('/Users/tejeswarreddy/Downloads/python/Github Contributions/ai-video-factory/models/tts/en_US-lessac-medium.onnx.json')

print(f"Model: {model_path}")
print(f"Config: {config_path}")
print("Generating voice... This may take a few minutes.")

result = subprocess.run(
    [
        '/opt/miniconda3/bin/piper',
        '--model', str(model_path),
        '--config', str(config_path),
        '--output_file', str(voice_file),
        '--sentence-silence', '0.2',
        '--noise-scale', '0.667',
        '--noise-w-scale', '0.8',
    ],
    input=full_text,
    text=True,
    capture_output=True,
    timeout=300,
)

if result.returncode == 0:
    size = voice_file.stat().st_size
    print(f"Voice generated: {voice_file} ({size} bytes)")
else:
    print(f"FAILED with code {result.returncode}")
    print(result.stdout)
    print(result.stderr)
    raise SystemExit(1)
PYEOF
