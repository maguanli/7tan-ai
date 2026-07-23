import os
print('ONNX:', os.path.exists(r'G:\piper\piper\voices\zh_CN-huayan-medium.onnx'))
print('JSON:', os.path.exists(r'G:\piper\piper\voices\zh_CN-huayan-medium.onnx.json'))
# Also test tts
import sys
sys.path.insert(0, '.')
from data.plugins.tts_piper.tools import tts_speak, tts_status
print('Status:', tts_status())
result = tts_speak("测试语音", play=True, strip_code=True)
print('Result:', result)
