import csv
import openai
import os
import random
import re
import time
from gtts import gTTS

csv_in = 'filtered.csv'
csv_out = 'sentences.csv'
en_folder = 'EN_'
pt_folder = 'PT_'

client = openai.OpenAI()

def clean_word(word):
    # Clean a word by:
    # 1. Removing any text within parentheses and the parentheses themselves
    # 2. Removing the 'to ' prefix from verbs
    # 3. Stripping any excess whitespace (including whitespace left after removing parentheses)
    # First strip leading/trailing whitespace
    word = word.strip()
    
    # Remove text within parentheses and the parentheses themselves
    word_no_parens = re.sub(r'\s*\([^)]*\)\s*', ' ', word)
    
    # Remove 'to ' prefix if it exists
    if word_no_parens.lower().startswith('to '):
        word_no_parens = word_no_parens[3:]
    
    # Final strip to remove any whitespace (including any left in the middle after removing parentheses)
    word_no_parens = word_no_parens.strip()
    
    return word_no_parens

def make_audio(text, file, lang="pt"):
    # Generate TTS audio for a given sentence.
    tts = gTTS(text, lang=lang)
    tts.save(file)

def word_in_sentence(word, sentence):
    # Clean the word and ensure it's treated as a whole word in the sentence
    word = word.strip().lower()
    word_pattern = r'\b' + re.escape(word) + r'\b'
    return bool(re.search(word_pattern, sentence.lower()))

def make_sentences(words):
    # Ensure all words are cleaned before sending to API
    cleaned_words = [w.strip() for w in words]
    join_words = ", ".join(cleaned_words)
    
    prompt = f"""Generate exactly one simple sentence for each of the following words: {join_words}.
    For each word, provide a numbered response that includes:
    1. The original word
    2. An English sentence using that word
    3. The Portuguese translation of that sentence
    
    Each sentence should be simple and suitable for an English speaker learning basic Portuguese.
    All sentences must end with a period.
    Please try to make the translations as close as possible. Using this prompt in the past has resulted in translations that could be more similar.

    Example output:
    1. WORD: Brazil
    EN: I really like Brazil.
    PT: Eu gosto muito do Brasil.

    2. WORD: cat
    EN: The cat is sleeping.
    PT: O gato está dormindo."""

    response = client.chat.completions.create(
        model="gpt-3.5-turbo-1106",
        messages=[{"role": "user", "content": prompt}]
    )

    text = response.choices[0].message.content.strip()
    
    # Uncomment when debugging
    # print("RAW RESPONSE FROM OPENAI:", repr(text))
    
    # Process the text to extract word-sentence pairs
    word_sentence_pairs = {}
    
    # Split by numbered entries (1., 2., etc.)
    entries = re.split(r'\n\s*\d+\.\s*', '\n' + text)
    if entries and not entries[0].strip():  # Remove empty first entry if present
        entries = entries[1:]
    
    for entry in entries:
        lines = entry.strip().split('\n')
        if len(lines) >= 3:
            # Extract the original word
            word_match = re.match(r'WORD:\s*(.*)', lines[0])
            if word_match:
                original_word = word_match.group(1).strip()
                # Find the English and Portuguese sentences
                en_sentence = None
                pt_sentence = None
                
                for line in lines[1:]:
                    if line.startswith('EN:'):
                        en_sentence = line[3:].strip()
                    elif line.startswith('PT:'):
                        pt_sentence = line[3:].strip()
                
                if original_word and en_sentence and pt_sentence:
                    word_sentence_pairs[original_word.lower()] = (en_sentence, pt_sentence)
    
    # Check which words were successfully processed
    found_pairs = []
    missing_words = []
    
    for word in cleaned_words:  # Use cleaned words for consistency
        word_lower = word.lower()
        if word_lower in word_sentence_pairs:
            found_pairs.append((word, word_sentence_pairs[word_lower]))
        else:
            # Check if the word appears in any sentence even if not explicitly labeled
            found = False
            for _, (en_sent, pt_sent) in word_sentence_pairs.items():
                if word_in_sentence(word, en_sent):
                    found_pairs.append((word, (en_sent, pt_sent)))
                    found = True
                    break
            
            if not found:
                missing_words.append(word)
    
    if missing_words:
        print(f"Words missing from response: {missing_words}")
    
    return found_pairs, missing_words

with open(csv_in, "r", encoding="utf-8") as infile, open(csv_out, "w", encoding="utf-8", newline="") as outfile:
    reader = list(csv.reader(infile))
    writer = csv.writer(outfile)

    # Randomly select X words
    random_words = random.sample(reader, min(100, len(reader)))
    
    # Create a mapping of cleaned words to original rows
    word_to_row_map = {}
    for row in random_words:
        clean_en_word = clean_word(row[0].strip())
        word_to_row_map[clean_en_word] = row
    
    # Get the list of cleaned words
    words_to_process = list(word_to_row_map.keys())
    
    batch_size = 100
    processed_results = []
    
    # Process words in smaller batches
    for i in range(0, len(words_to_process), batch_size):
        batch = words_to_process[i:i + batch_size]
        print(f"Processing batch: {batch}")
        
        try:
            # First attempt
            results, missing = make_sentences(batch)
            
            # Add successful results
            processed_results.extend(results)
            
            # Retry for missing words (up to 2 attempts)
            retry_count = 0
            while missing and retry_count < 2:
                retry_count += 1
                print(f"Retry {retry_count} for missing words: {missing}")
                time.sleep(2)  # Wait a bit before retrying
                
                retry_results, still_missing = make_sentences(missing)
                
                # Add successful retries to our results
                processed_results.extend(retry_results)
                
                missing = still_missing
                if not missing:
                    print("All words successfully processed after retry!")
                elif retry_count == 2:
                    print(f"Failed to generate sentences for: {missing}")
            
        except Exception as e:
            print(f"Error processing batch: {e}")
        
        # Reduce risk of hitting API limits
        time.sleep(1)
    
    # Process generated sentences
    count = 0
    for word, sentence_pair in processed_results:
        # Look up the original row using the cleaned word
        if word in word_to_row_map:
            original_row = word_to_row_map[word]
            
            en_sentence, pt_sentence = sentence_pair
            word_en = original_row[0].strip()
            word_pt = original_row[1].strip()

            en_audio = os.path.join(en_folder, f"{word_en}__en.mp3")
            pt_audio = os.path.join(pt_folder, f"{word_pt}__pt.mp3")

            print(f"Making EN audio for '{word_en}': '{en_sentence}' -> {en_audio}")
            print(f"Making PT audio for '{word_pt}': '{pt_sentence}' -> {pt_audio}")
        
            make_audio(en_sentence, en_audio, lang="en")
            make_audio(pt_sentence, pt_audio, lang="pt")

            front = f"{en_sentence}<br>[sound:{os.path.basename(en_audio)}]"
            back = f"{pt_sentence}<br>[sound:{os.path.basename(pt_audio)}]"

            writer.writerow([front, back])
            
            count += 1
            # Stop after processing X words
            if count >= 100:
                break