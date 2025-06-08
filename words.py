import csv
from gtts import gTTS
import os
import re

# READ ---------- READ

csv_in = 'PT 6-8.csv'
csv_out = 'words.csv'
en_folder = r'C:\Users\Mac\AppData\Roaming\Anki2\Mac\collection.media'
pt_folder = r'C:\Users\Mac\AppData\Roaming\Anki2\Mac\collection.media'

filter_in = []
filter_out = []

def remove_parentheses(word):
    #Removes text inside parentheses.
    return re.sub(r'\s*\(.*?\)', '', word).strip()

with open(csv_in, mode='r', encoding='utf-8') as file:
    reader = csv.reader(file)
    next(reader)  # Skip the header, if there is one
    for row in reader:
        en_word = row[0].strip()
        pt_word = row[1].strip()

        # Skip capitalized words and add them to filter_out
        if en_word.istitle() and pt_word.istitle():
            filter_out.append((en_word, pt_word))
        elif en_word and pt_word:  # Check if neither word is empty
            filter_in.append((en_word, pt_word))

# Sort the list alphabetically by the English word
filter_in.sort(key=lambda x: x[0])

# Save filtered words (without capitalized ones) to filtered.csv
with open("filtered.csv", mode="w", newline="", encoding="utf-8") as file:
    writer = csv.writer(file)
    writer.writerows(filter_in)

# AUDIO ---------- AUDIO

en_exists = {f.rsplit("_en.mp3", 1)[0] for f in os.listdir(en_folder) if f.endswith("_en.mp3")}
pt_exists = {f.rsplit("_pt.mp3", 1)[0] for f in os.listdir(pt_folder) if f.endswith("_pt.mp3")}

# Generate gTTS list based on cleaned words for audio generation
gTTS_list = [
    (remove_parentheses(en_word), remove_parentheses(pt_word), en_word, pt_word)
    for en_word, pt_word in filter_in
    if remove_parentheses(en_word) not in en_exists or remove_parentheses(pt_word) not in pt_exists
]

# Generate audio files
for en_clean, pt_clean, en_word, pt_word in gTTS_list:
    # If the cleaned word doesn't exist, generate audio
    if en_clean not in en_exists:
        tts = gTTS(text=en_clean, lang='en')
        mp3_name = f"{en_clean}_en.mp3"  # Correct filename for English
        mp3_path = os.path.join(en_folder, mp3_name)
        tts.save(mp3_path)
        en_exists.add(en_clean)  # Add to the set so we don't generate it again

    if pt_clean not in pt_exists:
        tts = gTTS(text=pt_clean, lang='pt')
        mp3_name = f"{pt_clean}_pt.mp3"  # Correct filename for Portuguese
        mp3_path = os.path.join(pt_folder, mp3_name)
        tts.save(mp3_path)
        pt_exists.add(pt_clean)  # Add to the set so we don't generate it again

# ANKI ---------- ANKI

# Create Anki flashcards CSV file
with open(csv_out, mode='w', newline='', encoding='utf-8') as file:
    writer = csv.writer(file)

    for en_clean, pt_clean, en_word, pt_word in gTTS_list:
        front = f"{en_word}<br>[sound:{en_clean}_en.mp3]"
        back = f"{pt_word}<br>[sound:{pt_clean}_pt.mp3]"
        
        writer.writerow([front, back])

        print(f"Front: {front}, Back: {back}, new card added!")

if filter_out:
    print("\n--- Filtered Out Words ---")
    for en_word, pt_word in filter_out:
        print(f"Skipped: {en_word} - {pt_word}")
