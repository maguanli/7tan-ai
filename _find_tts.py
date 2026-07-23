import re
with open('src/ui/chat_page.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()
for i, l in enumerate(lines):
    low = l.lower()
    if any(k in low for k in ['stream_finish', 'on_response', 'speak_response', 'tts_speak', '_on_stream', 'agent_done', 'response_done', 'reply_complete', 'emit.*finish']):
        print(f"{i+1}: {l.rstrip()}")
# Also search for where assistant message is completed
print("--- searching for _add_message assistant ---")
for i, l in enumerate(lines):
    if '_add_message' in l.lower() and 'assistant' in l.lower():
        print(f"{i+1}: {l.rstrip()}")
print("--- searching for self._streaming or is_streaming ---")
for i, l in enumerate(lines):
    if 'streaming' in l.lower():
        print(f"{i+1}: {l.rstrip()}")
