import csv
import openai
import os
import random
import re
import time
from gtts import gTTS

batch_size = 10
list_size = 100
csv_in = 'filtered.csv'
csv_out = 'sentences.csv'
en_folder = 'EN_'
pt_folder = 'PT_'

client = openai.OpenAI()

def clean_word(word):
    # Removing parenthesis and any text within. Remove the 'to ' prefix from verbs. Stripping any excess whitespace.
    word = word.strip()
    word_no_parens = re.sub(r'\s*\([^)]*\)\s*', ' ', word)
    
    # Remove 'to ' prefix if it exists
    # if word_no_parens.lower().startswith('to '):
    #     word_no_parens = word_no_parens[3:]

    word_no_parens = word_no_parens.strip()
    
    return word_no_parens

def generate_audio(text, file, lang="pt"):
    tts = gTTS(text, lang=lang)
    tts.save(file)

def generate_and_parse_sentences(words):
    cleaned_words = [w.strip() for w in words] # Ensure all words are cleaned before sending to API
    join_words = ", ".join(cleaned_words)
    
    prompt = f"""You are a helpful assistant that generates language-learning sentences.
    Your task is to generate one simple sentence for each of the following words: {join_words}.

    Follow these rules precisely:
    1. For each word, provide a numbered response.
    2. Each numbered response must contain three lines, prefixed with "WORD:", "EN:", and "PT:".
    3. The "EN:" sentence must use the given word.
    4. The "PT:" sentence must be a direct translation of the "EN:" sentence.
    5. All sentences must end with a period.
    6. VERY IMPORTANT: Do not include any introductory or concluding text. Your response should begin immediately with "1." and contain only the numbered list of sentences.

    Example output format:
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
    word_sentence_pairs = {} # Process the text to extract word-sentence pairs
    
    entries = re.split(r'\n\s*\d+\.\s*', '\n' + text) # Split by numbered entries (1., 2., etc.)
    if entries and not entries[0].strip():  # Remove empty first entry if present
        entries = entries[1:]
    
    for entry in entries:
        lines = entry.strip().split('\n')
        if len(lines) >= 3:
            word_match = re.match(r'WORD:\s*(.*)', lines[0]) # Extract the original word
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
    
    for word in cleaned_words:
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
    
    return found_pairs, missing_words

def word_in_sentence(word, sentence):
    # Clean the word and ensure it's treated as a whole word in the sentence
    word = word.strip().lower()
    word_pattern = r'\b' + re.escape(word) + r'\b'
    return bool(re.search(word_pattern, sentence.lower()))

with open(csv_in, "r", encoding="utf-8") as infile:
    reader = list(csv.reader(infile))

    print(f"DEBUG: Successfully loaded {len(reader)} words from '{csv_in}'.")

    random_words = random.sample(reader, min(list_size, len(reader))) # Randomly select X words

    print(f"DEBUG: Created a random sample of {len(random_words)} words to process.")
    
    word_to_row_map = {} # Map cleaned words to original rows

    for row in random_words:
        clean_en_word = clean_word(row[0].strip())
        word_to_row_map[clean_en_word] = row
    
    words_to_process = list(word_to_row_map.keys()) # Get the list of cleaned words
    
    processed_results = []

    total_words = len(words_to_process)
    num_batches = (total_words + batch_size - 1) // batch_size
    print(f"\nDEBUG: Setup complete. Processing {total_words} words in {num_batches} batches...")
    
    # Process words in smaller batches
    for i in range(0, len(words_to_process), batch_size):
        batch_num = (i // batch_size) + 1
        batch = words_to_process[i:i + batch_size]
        print(f"\n--- Starting Batch {batch_num} of {num_batches} ---")
        
        try:
            results, missing = generate_and_parse_sentences(batch)

            print(f"DEBUG: API call for Batch {batch_num} returned {len(results)} successful pairs and {len(missing)} missing words.")
                      
            processed_results.extend(results) # Add successful results
            
            # Retry for missing words (up to 2 attempts)
            retry_count = 0
            while missing and retry_count < 2:
                retry_count += 1
                print(f"Retry {retry_count} for missing words: {missing}")
                time.sleep(5)  # Wait before retrying
                
                retry_results, still_missing = generate_and_parse_sentences(missing)
                              
                processed_results.extend(retry_results) # Add successful retries to our results
                
                missing = still_missing
                if not missing:
                    print("All words successfully processed after retry!")
                elif retry_count == 2:
                    print(f"Failed to generate sentences for: {missing}")
            
        except Exception as e:
            print(f"Error processing batch: {e}")
        
        time.sleep(2) # Reduce risk of hitting API limits
    
    count = 0


print(f"\nWriting {len(processed_results)} results to {csv_out}...") # This entire block runs only AFTER all API calls are complete. Writes all results to sentences.csv

with open(csv_out, "w", encoding="utf-8", newline="") as outfile:
    writer = csv.writer(outfile)
    
    count = 0
    for word, sentence_pair in processed_results:
        if word in word_to_row_map:
            original_row = word_to_row_map[word]
            en_sentence, pt_sentence = sentence_pair
            word_en = original_row[0].strip()
            word_pt = original_row[1].strip()
            en_audio = os.path.join(en_folder, f"{word_en}__en.mp3")
            pt_audio = os.path.join(pt_folder, f"{word_pt}__pt.mp3")

            print(f"Making EN audio for '{word_en}': '{en_sentence}' -> {en_audio}")
            print(f"Making PT audio for '{word_pt}': '{pt_sentence}' -> {pt_audio}")
        
            generate_audio(en_sentence, en_audio, lang="en")
            generate_audio(pt_sentence, pt_audio, lang="pt")

            front = f"{en_sentence}<br>[sound:{os.path.basename(en_audio)}]"
            back = f"{pt_sentence}<br>[sound:{os.path.basename(pt_audio)}]"
            writer.writerow([front, back])
            
            count += 1

            # Stop after processing X words
            if count >= list_size:
                break

print("\n" + "="*25 + " SCRIPT FINISHED " + "="*25)
print(f"Successfully wrote {count} sentence pairs to the output file '{csv_out}'.")