import csv
from gtts import gTTS
import os

# READ ---------- READ

csv_in = 'PT 2-6.csv'
csv_out = 'words.csv'
en_folder = r'C:\Users\Mac\AppData\Roaming\Anki2\Mac\collection.media'
pt_folder = r'C:\Users\Mac\AppData\Roaming\Anki2\Mac\collection.media'

filter_in = []
filter_out = []

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

# Utility for Sentences script
filter_result = 'filtered.csv'

with open(filter_result, mode='w', encoding='utf-8', newline='') as file:
    writer = csv.writer(file)

    for row in filter_in:
        writer.writerow(row)

# AUDIO ---------- AUDIO

en_exists = {f.rsplit("_en.mp3", 1)[0] for f in os.listdir(en_folder) if f.endswith("_en.mp3")}
pt_exists = {f.rsplit("_pt.mp3", 1)[0] for f in os.listdir(pt_folder) if f.endswith("_pt.mp3")}

# Filter words to process
gTTS_list = [
    (en_word, pt_word)
    for en_word, pt_word in filter_in
    if en_word not in en_exists or pt_word not in pt_exists
]

# Generate audio files
for en_word, pt_word in gTTS_list:
    if en_word not in en_exists:
        tts = gTTS(text=en_word, lang='en')
        mp3_name = f"{en_word}_en.mp3"
        mp3_path = os.path.join(en_folder, mp3_name)
        tts.save(mp3_path)
    
    if pt_word not in pt_exists:
        tts = gTTS(text=pt_word, lang='pt')
        mp3_name = f"{pt_word}_pt.mp3"
        mp3_path = os.path.join(pt_folder, mp3_name)
        tts.save(mp3_path)

# ANKI ---------- ANKI

with open(csv_out, mode='w', newline='', encoding='utf-8') as file:
    writer = csv.writer(file)

    for en_word, pt_word in gTTS_list:
        front = f"{en_word}<br>[sound:{f"{en_word}_en.mp3"}]"
        back = f"{pt_word}<br>[sound:{f"{pt_word}_pt.mp3"}]"
        
        writer.writerow([front, back])

        print(f"Front: {front}, Back: {back}, new card added!")
