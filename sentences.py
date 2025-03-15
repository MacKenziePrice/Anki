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
    # Remove parentheses and 'to ' prefix from verbs.
    word_en_no_parens = re.sub(r'\([^)]*\)', '', word)
    return word_en_no_parens[3:] if word_en_no_parens.lower().startswith('to ') else word_en_no_parens

def make_audio(text, file, lang="pt"):
    # Generate TTS audio for a given sentence.
    tts = gTTS(text, lang=lang)
    tts.save(file)

def make_sentences(words):
    # Generate sentences in bulk (batch of 10 words per request).
    join_words = ", ".join(words)
    prompt = f"""Generate exactly one simple sentence for each of the following words: {join_words}.
    Ensure that each sentence uses only one word from the list, and do not combine multiple words in the same sentence.
    Each sentence should be simple and suitable for an English speaker learning basic Portuguese, and it must end with a period.
    Then, provide the Portuguese translation of each sentence, ensuring it also ends with a period.
    Output format: Each English sentence first, followed by the Portuguese translation on a new line.

    Example output:
    I really like Brazil.
    Eu gosto muito do Brasil.

    The cat is sleeping.
    O gato está dormindo."""

    response = client.chat.completions.create(
        model="gpt-3.5-turbo-1106",
        messages=[{"role": "user", "content": prompt}]
    )

    text = response.choices[0].message.content.strip()
    
    # Split the response into pairs of English and Portuguese sentences
    sentence_pairs = text.split("\n\n")

    print("RAW RESPONSE FROM OPENAI:", repr(text))

    sentences = []
    for pair in sentence_pairs:
        # Split each pair by the first newline, assuming the first sentence is English and the second is Portuguese
        sentences_split = pair.split("\n")
        if len(sentences_split) == 2:
            en_sentence = sentences_split[0].strip()
            pt_sentence = sentences_split[1].strip()

            # Ensure both sentences are valid
            if en_sentence and pt_sentence:
                sentences.append((en_sentence, pt_sentence))
            else:
                print(f"PROBLEM! Skipping {words}: One of the sentences is empty.")
    
    # If we successfully extracted sentences, return them
    if sentences:
        return sentences
    else:
        print(f"PROBLEM! Skipping {words}: No valid sentences found.")
        return None

with open(csv_in, "r", encoding="utf-8") as infile, open(csv_out, "w", encoding="utf-8", newline="") as outfile:
    reader = list(csv.reader(infile))
    writer = csv.writer(outfile)

    # Randomly select X words
    random_words = random.sample(reader, min(20, len(reader)))
    
    # Clean words and prepare for batch processing
    words_to_process = [clean_word(row[0].strip()) for row in random_words]

    batch_size = 20
    batch_sentences = []
    
    for i in range(0, len(words_to_process), batch_size):
        batch = words_to_process[i:i + batch_size]
        print(f"Processing batch: {batch}")
        
        try:
            results = make_sentences(batch)
            batch_sentences.extend(results)
        except Exception as e:
            print(f"Error processing batch: {e}")
        
        # Reduce risk of hitting API limits
        time.sleep(1)

    # Process generated sentences
    for id, ((en_sentence, pt_sentence), row) in enumerate(zip(batch_sentences, random_words)):
        word_en = row[0].strip()
        word_pt = row[1].strip()

        en_audio = os.path.join(en_folder, f"{word_en}__en.mp3")
        pt_audio = os.path.join(pt_folder, f"{word_pt}__pt.mp3")

        # print(f"Making EN audio: '{en_sentence}' -> {en_audio}")
        # print(f"Making PT audio: '{pt_sentence}' -> {pt_audio}")
    
        make_audio(en_sentence, en_audio, lang="en")
        make_audio(pt_sentence, pt_audio, lang="pt")

        front = f"{en_sentence}<br>[sound:{os.path.basename(en_audio)}]"
        back = f"{pt_sentence}<br>[sound:{os.path.basename(pt_audio)}]"

        writer.writerow([front, back])
        
        # Stop after processing X words
        if id + 1 >= 20:  
            break
