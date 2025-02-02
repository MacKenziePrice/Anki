import csv
import openai
import os
import time
from gtts import gTTS

# Set up OpenAI client (key provided from ENV)
client = openai.OpenAI()

# Input and output files
anki_out = 'anki_out.csv'
input_csv = 'filtered_words.csv'
output_csv = 'anki_sentences.csv'
en_folder = 'ENS'
pt_folder = 'PTS'

# Function to generate sentences using OpenAI API
def generate_sentences(word):
    prompt = f"""Generate a simple sentence in English using the word '{word}'. 
    The sentence should be simple and suitable for a beginner learning English. 
    After that, provide the Portuguese translation of the sentence. 
    Output format: 
    English sentence first, then the Portuguese translation."""
    
    response = client.chat.completions.create(
        model="gpt-3.5-turbo-1106",
        messages=[{"role": "user", "content": prompt}]
    )

    text = response.choices[0].message.content.strip()
    
    # Expecting output like: "The cat is sleeping. O gato está dormindo."
    if ". " in text:
        en_sentence, pt_sentence = text.split(". ", 1)
        return en_sentence.strip(), pt_sentence.strip()
    else:
        return None, None

# Function to generate MP3 files
def generate_audio(text, filename, lang="pt"):
    tts = gTTS(text, lang=lang)
    tts.save(filename)

# ----- ANKI -----


# with open(input_csv, "r", encoding="utf-8") as file:
#     anki_file = 'anki_sentences.csv'
#     reader = csv.reader(file)
#     word_count = 0
    
#     for row in reader:
#         word = row[0].strip()
#         word_en = row[0].strip()
#         word_pt = row[1].strip()
        
#         en_sentence, pt_sentence = generate_sentences(word)
#         if not en_sentence or not pt_sentence:
#             continue
        
#         en_audio = os.path.join(en_folder, f"{word_en}_en.mp3")
#         pt_audio = os.path.join(pt_folder, f"{word_pt}_pt.mp3")
#         print(en_audio)
#         print(pt_audio)

#         # Generate and save audio
#         generate_audio(en_sentence, en_audio, lang="en")
#         generate_audio(pt_sentence, pt_audio, lang="pt")

#         with open("anki_out.csv", "w", encoding="utf-8", newline="") as file:
#             writer = csv.writer(file)
#             for row in reader:
#                 writer.writerow((en_sentence, pt_sentence))

with open(input_csv, "r", encoding="utf-8") as infile, open("anki_out.csv", "a", encoding="utf-8", newline="") as outfile:
    reader = csv.reader(infile)
    writer = csv.writer(outfile)

    word_count = 0
    
    for row in reader:
        word_en = row[0].strip()
        word_pt = row[1].strip()
        
        en_sentence, pt_sentence = generate_sentences(word_en)
        if not en_sentence or not pt_sentence:
            continue
        
        print(word_en)

        en_audio = os.path.join(en_folder, f"{word_en}__en.mp3")
        pt_audio = os.path.join(pt_folder, f"{word_pt}__pt.mp3")

        print(f"Generating EN audio: '{en_sentence}' -> {en_audio}")
        print(f"Generating PT audio: '{pt_sentence}' -> {pt_audio}")
    
        # Generate and save audio
        generate_audio(en_sentence, en_audio, lang="en")
        generate_audio(pt_sentence, pt_audio, lang="pt")

        front = f"{en_sentence}<br>[sound:{os.path.basename(en_audio)}]"
        back = f"{pt_sentence}<br>[sound:{os.path.basename(pt_audio)}]"

        # Write the sentence pair and audio paths to CSV
        writer.writerow([front, back])

        word_count += 1
        if word_count >= 10:  # Limit processing to 10 words
            break

        # Avoid rate limits
        time.sleep(1)

        word_count += 1
        if word_count >= 3:  # Stop after 3 words
            break



