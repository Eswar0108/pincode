import numpy as np
import cv2
from pathlib import Path

project_dir = Path('/Users/tesjeswarreddy/Downloads/python/Github Contributions/ai-video-factory/projects/test_brain_memory')
voice_file = project_dir / 'voice' / 'narration.wav'

# Simple approach: just generate 3 mouth shape images
# Closed, neutral, open
mouth_shapes = ['closed', 'neutral', 'open']

for i, shape in enumerate(mouth_shapes):
    img_size = 400
    img = np.zeros((img_size, img_size, 4), dtype=np.uint8)
    img[:] = (30, 30, 50, 255)
    center = (img_size // 2, img_size // 2)
    radius = img_size // 2 - 20
    cv2.circle(img, center, radius, (60, 60, 100, 255), -1)
    mouth_y = img_size // 2 + 20
    mouth_radius = 30
    if shape == 'closed':
        # Closed mouth - thin line
        cv2.ellipse(img, (center[0], mouth_y), (mouth_radius, 15), 0, 0, 360, (255, 255, 255, 255), -1)
    elif shape == 'neutral':
        # Neutral mouth - slight curve
        cv2.ellipse(img, (center[0], mouth_y), (mouth_radius, 15), 0, 0, 180, (255, 255, 255, 255), 2)
    else:
        # Open mouth - wider curve
        cv2.ellipse(img, (center[0], mouth_y), (mouth_radius, 25), 0, 0, 180, (255, 255, 255, 255), 4)
    cv2.imwrite(str(project_dir / 'avatar' / f'mouth_{i}.png'), img)
    print(f'Saved mouth_{i}.png for {shape}')

print('Generated 3 mouth shape images')