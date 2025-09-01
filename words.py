import csv
from gtts import gTTS
import os
import re

csv_in = 'PT 8-23.csv'
csv_out = 'words.csv'
filtered_csv = 'filtered.csv'
en_folder = r'C:\Users\Mac\AppData\Roaming\Anki2\Mac\collection.media'
pt_folder = r'C:\Users\Mac\AppData\Roaming\Anki2\Mac\collection.media'

def remove_parentheses(word): return re.sub(r'\s*\(.*?\)', '', word).strip() # Removes text inside parentheses

all_pairs = []
with open(filtered_csv, 'r', newline='', encoding='utf-8') as file:
    reader = csv.reader(file)
    for row in reader:
        if row:
            all_pairs.append(tuple(row))

existing_pairs = set(all_pairs) # Create the set for fast lookups from the list we just made
new_pairs = []

print("Reading input file and adding new unique pairs...")
with open(csv_in, mode='r', encoding='utf-8') as file:
    reader = csv.reader(file)
    next(reader)
    
    for row in reader:
        en_word = row[0].strip()
        pt_word = row[1].strip()
        
        if not en_word or not pt_word:
            continue
            
        current_pair = (en_word, pt_word)

        if not (en_word.istitle() and pt_word.istitle()) and current_pair not in existing_pairs:
            all_pairs.append(current_pair) # Add pair to the master list
            new_pairs.append(current_pair) # Add pair for audio 
            existing_pairs.add(current_pair) # Add existing pair to avoid duplicates


print(f"Sorting all {len(all_pairs)} pairs...")
all_pairs.sort(key=lambda x: x[0]) # Sort list and overwrite the file

print(f"Overwriting '{filtered_csv}' with the newly sorted, complete list...")
# We now open in 'w' (write) mode to erase and rewrite the file
with open(filtered_csv, mode='w', newline='', encoding='utf-8') as file:
    writer = csv.writer(file)
    writer.writerows(all_pairs)

print("Process complete. The file is now perfectly sorted.")

en_exists = {f.rsplit("_en.mp3", 1)[0] for f in os.listdir(en_folder) if f.endswith("_en.mp3")}
pt_exists = {f.rsplit("_pt.mp3", 1)[0] for f in os.listdir(pt_folder) if f.endswith("_pt.mp3")}

# Generate gTTS list based on cleaned words for audio generation
gTTS_list = [
    (remove_parentheses(en_word), remove_parentheses(pt_word), en_word, pt_word)
    for en_word, pt_word in new_pairs
    if remove_parentheses(en_word) not in en_exists or remove_parentheses(pt_word) not in pt_exists
]

# Generate audio files
for en_clean, pt_clean, en_word, pt_word in gTTS_list:
    # If the cleaned word doesn't exist, generate audio
    if en_clean not in en_exists:
        tts = gTTS(text=en_clean, lang='en')
        mp3_name = f"{en_clean}_en.mp3"
        mp3_path = os.path.join(en_folder, mp3_name)
        tts.save(mp3_path)
        en_exists.add(en_clean)

    if pt_clean not in pt_exists:
        tts = gTTS(text=pt_clean, lang='pt')
        mp3_name = f"{pt_clean}_pt.mp3"
        mp3_path = os.path.join(pt_folder, mp3_name)
        tts.save(mp3_path)
        pt_exists.add(pt_clean) 

# Create Anki flashcards file
with open(csv_out, mode='w', newline='', encoding='utf-8') as file:
    writer = csv.writer(file)

    for en_clean, pt_clean, en_word, pt_word in gTTS_list:
        front = f"{en_word}<br>[sound:{en_clean}_en.mp3]"
        back = f"{pt_word}<br>[sound:{pt_clean}_pt.mp3]"
        
        writer.writerow([front, back])

        print(f"Front: {front}, Back: {back}, new card added!")

print(f"\n--- Script Complete ---\nTotal new pairs added this session: {len(new_pairs)}")
