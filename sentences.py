import csv
import openai
import os
import random
import re
import time
from google.cloud import texttospeech
from gtts import gTTS

batch_size = 10
list_size = 100
csv_in = 'filtered.csv'
csv_out = 'sentences.csv'
en_folder = 'EN_'
pt_folder = 'PT_'

client = openai.OpenAI()

def clean_word(word):
    word = word.strip() # Strip any excess whitespace (including whitespace left after removing parentheses)
    word_no_parens = re.sub(r'\s*\([^)]*\)\s*', ' ', word) # Remove text within parentheses and the parentheses themselves

    if word_no_parens.lower().startswith('to '):
        word_no_parens = word_no_parens[3:]
        word_no_parens = word_no_parens.strip() # Strip any whitespace
    
    return word_no_parens

def generate_audio(text, file, lang, voice_name = None, pitch = 0, speaking_rate = 1.0): # Generates audio using gTTS for English and Google Cloud TTS for Portuguese
    if lang == 'en': # Use gTTS for English
        print(f"Generating EN audio with gTTS for: '{text}'")
        try:
            tts = gTTS(text = text, lang='en')
            tts.save(file)
        except Exception as e:
            print(f"Error generating gTTS audio for {file}: {e}")

    else: # Use Google Cloud TTS for Portuguese
        print(f"Generating PT audio with Google Cloud TTS for: '{text}'")
        try:
            client = texttospeech.TextToSpeechClient()
            synthesis_input = texttospeech.SynthesisInput(text = text)
            lang_code_map = {'pt': 'pt-BR'} # Determine language code for Google Cloud TTS
            language_code = lang_code_map.get(lang, lang) # Default to lang if not in map
            voice = texttospeech.VoiceSelectionParams(language_code = language_code, name = voice_name)
            audio_config = texttospeech.AudioConfig(audio_encoding = texttospeech.AudioEncoding.MP3, pitch = pitch, speaking_rate = speaking_rate)
            response = client.synthesize_speech(input = synthesis_input, voice = voice, audio_config = audio_config)

            with open(file, "wb") as out:
                out.write(response.audio_content)
        except Exception as e:
            print(f"Error generating Google Cloud TTS audio for {file}: {e}")

def generate_and_parse_sentences(words):
    cleaned_words = [w.strip() for w in words]
    join_words = ", ".join(cleaned_words)
    
    prompt = f"""
    You are a helpful assistant that generates language-learning sentences.
    Your task is to generate one simple sentence for each of the following words: {join_words}.

    Follow these rules precisely:
    1. For each word, provide a numbered response.
    2. Each numbered response must contain three lines, prefixed with "WORD:", "EN:", and "PT:".
    3. The "EN:" sentence must use the given word.
    4. The "PT:" sentence must be a direct translation of the "EN:" sentence.
    5. All sentences must end with a period.
    6. VERY IMPORTANT: Do not include any introductory or concluding text. Your response should begin immediately with "1." and contain only the numbered list of sentences.
    7. Be creative. In the past, you have been prone to providing me repeat sentences for the same words.

    Example output format:
    1. WORD: Brazil
    EN: I really like Brazil.
    PT: Eu gosto muito do Brasil.
    2. WORD: cat
    EN: The cat is sleeping.
    PT: O gato está dormindo."""
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}]
    )
    text = response.choices[0].message.content.strip()
    word_sentence_pairs = {}
    
    # Split into entries
    entries = re.split(r'\n\s*\d+\.\s*', '\n' + text)
    if entries and not entries[0].strip():
        entries = entries[1:]
    
    for entry in entries:
        lines = [line.strip() for line in entry.strip().split('\n') if line.strip()]
        if len(lines) >= 3:
            word_match = re.match(r'WORD:\s*(.*)', lines[0], re.IGNORECASE)
            if word_match:
                original_word = word_match.group(1).strip()
                en_sentence = None
                pt_sentence = None
                
                for line in lines[1:]:
                    if re.match(r'^\s*EN\s*:', line, re.IGNORECASE):
                        en_sentence = line.split(":", 1)[1].strip()
                    elif re.match(r'^\s*PT\s*:', line, re.IGNORECASE):
                        pt_sentence = line.split(":", 1)[1].strip()
                
                if original_word and en_sentence and pt_sentence:
                    word_sentence_pairs[original_word.lower()] = (en_sentence, pt_sentence)
    
    found_pairs = []
    missing_words = []
    
    for word in cleaned_words:
        word_lower = word.lower()
        if word_lower in word_sentence_pairs:
            found_pairs.append((word, word_sentence_pairs[word_lower]))
        else:
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
        original = row[0].strip()
        cleaned = clean_word(original)
        print(f"Original: '{original}' → Cleaned: '{cleaned}'")
    
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
            cleaned_word_en = clean_word(word_en) # Fix this
            word_pt = original_row[1].strip()
            en_audio = os.path.join(en_folder, f"{cleaned_word_en}__en.mp3") # Fix this
            pt_audio = os.path.join(pt_folder, f"{word_pt}__pt.mp3")

            print(f"'{cleaned_word_en}': '{en_sentence}' -> {en_audio}")
            generate_audio(en_sentence, en_audio, lang = 'en') # Use gTTS for English
            print(f"'{word_pt}': '{pt_sentence}' -> {pt_audio}")
            generate_audio(pt_sentence, pt_audio, lang = "pt-BR", voice_name = "pt-BR-Chirp3-HD-Achernar", pitch = 0, speaking_rate = 0.95) # Use Google Cloud TTS for Portuguese
            front = f"{en_sentence}<br>[sound:{os.path.basename(en_audio)}]"
            back = f"{pt_sentence}<br>[sound:{os.path.basename(pt_audio)}]"
            writer.writerow([front, back])
            
            count += 1

            if count >= list_size: # Stop after processing X words
                break

print(f"Successfully wrote {count} sentence pairs to the output file '{csv_out}'.")