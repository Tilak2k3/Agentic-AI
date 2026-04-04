from pathlib import Path
from agentic_ai.inputs import read_text_document, extract_meeting_text, extract_text_from_eml_path

# # SOW / kickoff / docs
# print(read_text_document(Path(r"D:\docs\scope.docx")))

# # Meeting: text file or audio (audio needs HUGGINGFACE_API_KEY / HF_TOKEN)
# print(extract_meeting_text(Path(r"D:\Agentic_AI\Agentic-AI\tests\fixtures\sample_meeting.txt")))
# # print(extract_meeting_text(Path(r"D:\recordings\call.flac")))

# # Saved .eml
# # print(extract_text_from_eml_path(Path(r"D:\mail\thread.eml")))

print(extract_meeting_text(Path(r"D:\Agentic AI-plan\sample1.mp3")))