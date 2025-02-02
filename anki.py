import csv
from gtts import gTTS
import os

# READ ---------- READ

filtered_in = []
filtered_out = []

# csv_file = r'C:\Users\Mac\Desktop\gTTS PT\PT 1-27.csv'
# en_folder = r'C:\Users\Mac\Desktop\gTTS PT\EN'
# pt_folder = r'C:\Users\Mac\Desktop\gTTS PT\PT'

csv_file = 'PT 2-1.csv'
en_folder = 'EN'        
pt_folder = 'PT'

with open(csv_file, mode='r', encoding='utf-8') as file:
    reader = csv.reader(file)
    next(reader)  # Skip the header, if there is one
    for row in reader:
        english_word = row[0].strip()
        portuguese_word = row[1].strip()

        # Skip capitalized words and add them to filtered_out
        if english_word.istitle() or portuguese_word.istitle():
            filtered_out.append((english_word, portuguese_word))
        elif english_word and portuguese_word:  # Check if neither word is empty
            filtered_in.append((english_word, portuguese_word))

# Step 2: Sort the list alphabetically by the English word
filtered_in.sort(key=lambda x: x[0])

filtered_result = 'filtered_words.csv'

with open(filtered_result, mode='w', encoding='utf-8', newline='') as file:
    writer = csv.writer(file)
    # Write header row if desired
    # Write each row from filtered_in
    for row in filtered_in:
        writer.writerow(row)

# Step 4: Print filtered-out words to the console
print("\nFiltered-out words (capitalized or skipped):")
for english_word, portuguese_word in filtered_out:
    print(f"English: {english_word}, Portuguese: {portuguese_word}")

# AUDIO ---------- AUDIO

# Get existing files in EN and PT folders
existing_en_files = {f.rsplit("_en.mp3", 1)[0] for f in os.listdir(en_folder) if f.endswith("_en.mp3")}
existing_pt_files = {f.rsplit("_pt.mp3", 1)[0] for f in os.listdir(pt_folder) if f.endswith("_pt.mp3")}

# Filter words to process
words_to_process = [
    (english_word, portuguese_word)
    for english_word, portuguese_word in filtered_in
    if english_word not in existing_en_files or portuguese_word not in existing_pt_files
]

# Generate audio files
for english_word, portuguese_word in words_to_process:
    # Generate English audio if not already present
    if english_word not in existing_en_files:
        tts = gTTS(text=english_word, lang='en')
        mp3_filename = f"{english_word}_en.mp3"
        mp3_path = os.path.join(en_folder, mp3_filename)
        tts.save(mp3_path)
    
    # Generate Portuguese audio if not already present
    if portuguese_word not in existing_pt_files:
        tts = gTTS(text=portuguese_word, lang='pt')
        mp3_filename = f"{portuguese_word}_pt.mp3"
        mp3_path = os.path.join(pt_folder, mp3_filename)
        tts.save(mp3_path)

# ANKI ---------- ANKI

anki_csv_file = 'anki_flashcards.csv'

with open(anki_csv_file, mode='w', newline='', encoding='utf-8') as file:
    writer = csv.writer(file)
    # writer.writerow(["Front", "Back"])  # Add header

    for english_word, portuguese_word in words_to_process:
        # Prepare the front and back with audio references
        mp3_filename_en = f"{english_word}_en.mp3"
        mp3_filename_pt = f"{portuguese_word}_pt.mp3"
        front_text = f"{english_word}<br>[sound:{mp3_filename_en}]"
        back_text = f"{portuguese_word}<br>[sound:{mp3_filename_pt}]"

        print(f"Front: {front_text}, Back: {back_text}, new card added!")
        
        # Write each flashcard to the CSV
        writer.writerow([front_text, back_text])

print(f"New Anki CSV file created: {anki_csv_file}")
