import os
from dotenv import load_dotenv
load_dotenv()

from agent.llm import call_llm

def test():
    # Create a small dummy file
    filename = "test_audio.webm"
    with open(filename, "wb") as f:
        # Just write some arbitrary bytes to simulate a webm header/data
        f.write(b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x22\x56\x00\x00\x22\x56\x00\x00\x01\x00\x08\x00data\x00\x00\x00\x00")
        
    print("Testing call_llm with dummy webm attachment...")
    try:
        res = call_llm(
            prompt="Identify if this is an audio file and say hello.",
            attachment_path=filename,
            model="gemini-2.5-flash"
        )
        print("Success! Output:")
        print(res)
    except Exception as e:
        print("Failed with exception:")
        import traceback
        traceback.print_exc()
    finally:
        if os.path.exists(filename):
            os.remove(filename)

if __name__ == "__main__":
    test()
